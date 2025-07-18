# cbe_scraper.py
import os
import sys
import pandas as pd
from io import StringIO
import asyncio
from typing import Optional, Callable
import logging
from contextlib import contextmanager

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import redis

from treasury_core.ports import YieldDataSource, HistoricalDataStore
import constants as C

logger = logging.getLogger(__name__)


@contextmanager
def suppress_output():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class CbeScraper(YieldDataSource):
    def __init__(self):
        self.redis_client = None
        redis_uri = os.environ.get("AIVEN_REDIS_URI")
        if redis_uri:
            try:
                self.redis_client = redis.from_url(redis_uri)
                logger.info("✅ Redis client initialized successfully.")
            except Exception:
                logger.error("❌ Failed to initialize Redis client", exc_info=True)
        else:
            logger.warning("⚠️ AIVEN_REDIS_URI not set. Redis caching is disabled.")

        self.cache_key = "cbe_latest_yields_cache"
        self.cache_ttl_seconds = 6 * 60 * 60

    def _verify_page_structure(self, page_source: str) -> None:
        for marker in C.ESSENTIAL_TEXT_MARKERS:
            if marker not in page_source:
                raise RuntimeError(
                    f"Page structure verification failed! Marker '{marker}' not found."
                )

    def _parse_cbe_html(self, page_source: str) -> Optional[pd.DataFrame]:
        # ... (This function remains unchanged)
        soup = BeautifulSoup(page_source, "lxml")
        try:
            results_headers = soup.find_all(
                lambda tag: tag.name == "h2" and "النتائج" in tag.get_text()
            )
            if not results_headers:
                return None

            all_dataframes = []
            for header in results_headers:
                dates_table = header.find_next("table")
                if not dates_table:
                    continue

                dates_df = pd.read_html(StringIO(str(dates_table)))[0]
                tenors = (
                    pd.to_numeric(dates_df.columns[1:], errors="coerce")
                    .dropna()
                    .astype(int)
                    .tolist()
                )
                session_dates_row = dates_df[dates_df.iloc[:, 0] == "تاريخ الجلسة"]

                if session_dates_row.empty or not tenors:
                    continue

                session_dates = session_dates_row.iloc[0, 1 : len(tenors) + 1].tolist()
                dates_tenors_df = pd.DataFrame(
                    {
                        C.TENOR_COLUMN_NAME: tenors,
                        C.SESSION_DATE_COLUMN_NAME: session_dates,
                    }
                )

                accepted_bids_header = header.find_next(
                    lambda tag: tag.name in ["p", "strong"]
                    and C.ACCEPTED_BIDS_KEYWORD in tag.get_text()
                )
                if not accepted_bids_header:
                    continue

                yields_table = accepted_bids_header.find_next("table")
                if not yields_table:
                    continue

                yields_df_raw = pd.read_html(StringIO(str(yields_table)))[0]
                yields_df_raw.columns = ["البيان"] + tenors
                yield_row = yields_df_raw[
                    yields_df_raw.iloc[:, 0].str.contains(C.YIELD_ANCHOR_TEXT, na=False)
                ]

                if yield_row.empty:
                    continue

                yield_series = yield_row.iloc[0, 1:].astype(float)
                yield_series.name = C.YIELD_COLUMN_NAME
                section_df = dates_tenors_df.join(yield_series, on=C.TENOR_COLUMN_NAME)

                if not section_df[C.YIELD_COLUMN_NAME].isnull().any():
                    all_dataframes.append(section_df)

            if not all_dataframes:
                return None

            final_df = pd.concat(all_dataframes, ignore_index=True)
            final_df["session_date_dt"] = pd.to_datetime(
                final_df[C.SESSION_DATE_COLUMN_NAME], format="%d/%m/%Y", errors="coerce"
            )
            final_df[C.DATE_COLUMN_NAME] = (
                final_df["session_date_dt"]
                .dt.tz_localize(
                    "Africa/Cairo", ambiguous="NaT", nonexistent="shift_forward"
                )
                .dt.tz_convert("UTC")
            )

            final_df = (
                final_df.sort_values("session_date_dt", ascending=False)
                .drop_duplicates(subset=[C.TENOR_COLUMN_NAME])
                .sort_values(by=C.TENOR_COLUMN_NAME)
            )
            return final_df
        except Exception as e:
            logger.error(
                f"❌ A critical error occurred during parsing: {e}", exc_info=True
            )
            return None

    async def _scrape_from_web_async(self) -> Optional[pd.DataFrame]:
        # ... (This function remains unchanged)
        logger.info("🚀 Scraping from the web asynchronously with Playwright...")
        with suppress_output():
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(
                        headless=True, args=["--disable-dev-shm-usage"]
                    )
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.1 Safari/537.36"
                    )
                    page = await context.new_page()
                    await page.goto(
                        C.CBE_DATA_URL, timeout=C.SCRAPER_TIMEOUT_SECONDS * 1000
                    )
                    await page.wait_for_selector(
                        "table", timeout=C.SCRAPER_TIMEOUT_SECONDS * 1000
                    )
                    page_source = await page.content()
                    await browser.close()
                    self._verify_page_structure(page_source)
                    return self._parse_cbe_html(page_source)
                except Exception as e:
                    logger.error(f"❌ Playwright scraping failed: {e}", exc_info=True)
                    try:
                        screenshot_path = "/app/debug.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.warning(
                            f"📸 Screenshot saved at {screenshot_path} for debugging."
                        )
                    except Exception as ss_err:
                        logger.warning(f"⚠️ Failed to capture screenshot: {ss_err}")
                    return None

    # --- START OF MODIFICATION ---
    async def get_latest_yields_async(
        self, force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetches T-bill data, using a cache to avoid redundant requests.
        Args:
            force_refresh: If True, bypasses the cache and fetches fresh data.
        """
        if not force_refresh and self.redis_client:
            try:
                cached_data = self.redis_client.get(self.cache_key)
                if cached_data:
                    logger.info("✅ Cache hit! Loading data from Redis.")
                    df = pd.read_json(StringIO(cached_data.decode("utf-8")), lines=True)
                    df[C.DATE_COLUMN_NAME] = pd.to_datetime(
                        df[C.DATE_COLUMN_NAME], errors="coerce", utc=True
                    )
                    return df
            except redis.exceptions.RedisError:
                logger.error("❌ Redis cache read error", exc_info=True)

        if force_refresh:
            logger.info("🔄 Force refresh enabled, bypassing cache.")

        live_data = await self._scrape_from_web_async()

        if self.redis_client and live_data is not None and not live_data.empty:
            try:
                logger.info(
                    f"💾 Storing new data in Redis cache for {self.cache_ttl_seconds} seconds."
                )
                self.redis_client.setex(
                    self.cache_key,
                    self.cache_ttl_seconds,
                    live_data.to_json(orient="records", lines=True, date_format="iso"),
                )
            except redis.exceptions.RedisError:
                logger.error("❌ Redis cache write error", exc_info=True)
        return live_data

    # --- END OF MODIFICATION ---

    def get_latest_yields(self) -> Optional[pd.DataFrame]:
        return asyncio.run(self.get_latest_yields_async())


# --- START OF MODIFICATION ---
async def fetch_and_update_data_async(
    data_source: CbeScraper,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
    force_refresh: bool = False,  # Add force_refresh parameter
) -> bool:
    if status_callback:
        status_callback("جاري جلب البيانات...")

    # Pass force_refresh to the data source
    latest_data = await data_source.get_latest_yields_async(force_refresh=force_refresh)

    if latest_data is not None and not latest_data.empty:
        if status_callback:
            status_callback("تم الجلب، جاري التحقق...")
        db_session_date_str = data_store.get_latest_session_date()
        live_latest_date_str = latest_data[C.SESSION_DATE_COLUMN_NAME].iloc[0]

        # Force save if force_refresh is true, otherwise check dates
        if (
            not force_refresh
            and db_session_date_str
            and live_latest_date_str == db_session_date_str
        ):
            if status_callback:
                status_callback("البيانات محدثة بالفعل.")
            return False

        if status_callback:
            status_callback("تم العثور على بيانات جديدة، جاري الحفظ...")
        data_store.save_data(latest_data)
        if status_callback:
            status_callback("اكتمل تحديث البيانات بنجاح!")
        return True

    raise RuntimeError("فشلت جميع المحاولات لجلب البيانات.")


# --- END OF MODIFICATION ---


def fetch_and_update_data(
    data_source: YieldDataSource,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    return asyncio.run(
        fetch_and_update_data_async(data_source, data_store, status_callback)
    )
