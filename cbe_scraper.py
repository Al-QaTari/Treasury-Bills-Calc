import os
import sys
import pandas as pd
from io import StringIO
import asyncio
from typing import Optional, Callable
import logging
from contextlib import contextmanager

from playwright.async_api import async_playwright, Browser
from bs4 import BeautifulSoup
import redis

# Assuming treasury_core and constants are in the same project structure
from treasury_core.ports import YieldDataSource, HistoricalDataStore
import constants as C

logger = logging.getLogger(__name__)


@contextmanager
def suppress_output():
    """A context manager to suppress stdout and stderr."""
    with open(os.devnull, "w") as devnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr


class CbeScraper(YieldDataSource):
    """
    Scrapes Egyptian T-bill yield data from the Central Bank of Egypt (CBE) website.
    Implements Redis caching to minimize redundant web requests.
    """

    def __init__(self):
        self.redis_client = self._initialize_redis()
        self.cache_key = "cbe_latest_yields_cache"
        self.cache_ttl_seconds = 6 * 60 * 60  # 6 hours

    def _initialize_redis(self) -> Optional[redis.Redis]:
        """Initializes the Redis client from an environment variable."""
        redis_uri = os.environ.get("AIVEN_REDIS_URI")
        if not redis_uri:
            logger.warning("⚠️ AIVEN_REDIS_URI not set. Redis caching is disabled.")
            return None
        try:
            client = redis.from_url(redis_uri)
            client.ping()  # Verify connection
            logger.info("✅ Redis client initialized and connected successfully.")
            return client
        except redis.exceptions.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}", exc_info=True)
        except Exception:
            logger.error(
                "❌ An unknown error occurred during Redis initialization.",
                exc_info=True,
            )
        return None

    def _verify_page_structure(self, page_source: str) -> None:
        """Ensures essential markers are present in the page HTML to detect layout changes."""
        for marker in C.ESSENTIAL_TEXT_MARKERS:
            if marker not in page_source:
                raise RuntimeError(
                    f"Page structure verification failed! Marker '{marker}' not found."
                )

    def _parse_cbe_html(self, page_source: str) -> Optional[pd.DataFrame]:
        """Parses the HTML content to extract T-bill yield data into a DataFrame."""
        try:
            soup = BeautifulSoup(page_source, "lxml")
            results_headers = soup.find_all(
                "h2", string=lambda text: text and "النتائج" in text
            )
            if not results_headers:
                logger.warning("⚠️ No 'Results' headers found on the page.")
                return None

            all_dataframes = []
            for header in results_headers:
                dates_table = header.find_next_sibling("table")
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
                yields_table = accepted_bids_header.find_next_sibling("table")
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
                logger.warning(
                    "⚠️ Could not extract any valid data sections after parsing."
                )
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
                f"❌ A critical error occurred during HTML parsing: {e}", exc_info=True
            )
            return None

    # --- START OF MODIFICATION ---
    async def _scrape_from_web_async(self) -> Optional[pd.DataFrame]:
        """Uses Playwright to launch a headless browser and scrape the page content with retries."""
        logger.info("🚀 Starting asynchronous web scrape with Playwright...")

        max_retries = 3
        retry_delay_seconds = 15

        for attempt in range(max_retries):
            logger.info(f"Scraping attempt {attempt + 1} of {max_retries}...")
            with suppress_output():
                async with async_playwright() as p:
                    browser: Optional[Browser] = None
                    try:
                        # More robust launch arguments for stability in docker/cron environments
                        browser_args = [
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                            "--single-process",
                        ]
                        browser = await p.chromium.launch(
                            headless=True, args=browser_args
                        )
                        context = await browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.1 Safari/537.36"
                        )
                        page = await context.new_page()

                        # Use 'networkidle' for more reliable page load detection and a longer timeout.
                        navigation_timeout = (
                            C.SCRAPER_TIMEOUT_SECONDS + 120
                        ) * 1000  # Add 2 extra minutes
                        await page.goto(
                            C.CBE_DATA_URL,
                            timeout=navigation_timeout,
                            wait_until="networkidle",
                        )

                        # As a final check, wait for a key element that indicates data is present.
                        await page.wait_for_selector(
                            "h2:has-text('النتائج') + table",
                            timeout=C.SCRAPER_TIMEOUT_SECONDS * 1000,
                        )

                        page_source = await page.content()
                        self._verify_page_structure(page_source)
                        parsed_data = self._parse_cbe_html(page_source)

                        if parsed_data is not None and not parsed_data.empty:
                            logger.info(
                                f"✅ Successfully scraped data on attempt {attempt + 1}."
                            )
                            return parsed_data  # Success, exit the loop

                        logger.warning(
                            f"⚠️ Scraped on attempt {attempt + 1}, but no data was parsed."
                        )

                    except Exception as e:
                        logger.error(
                            f"❌ Playwright scraping failed on attempt {attempt + 1}: {e}",
                            exc_info=True,
                        )
                        if "page" in locals():
                            try:
                                screenshot_path = (
                                    f"/app/debug_attempt_{attempt + 1}.png"
                                )
                                await page.screenshot(
                                    path=screenshot_path, full_page=True
                                )
                                logger.warning(
                                    f"📸 Screenshot saved at {screenshot_path} for debugging."
                                )
                            except Exception as ss_err:
                                logger.warning(
                                    f"⚠️ Failed to capture screenshot: {ss_err}"
                                )
                    finally:
                        if browser:
                            await browser.close()

            if attempt < max_retries - 1:
                logger.info(
                    f"Waiting {retry_delay_seconds} seconds before next attempt..."
                )
                await asyncio.sleep(retry_delay_seconds)

        logger.error(f"❌ All {max_retries} scraping attempts failed.")
        return None

    # --- END OF MODIFICATION ---

    async def get_latest_yields_async(
        self, force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Fetches T-bill data, using a cache to avoid redundant web requests.

        Args:
            force_refresh: If True, bypasses the cache and fetches fresh data from the web.
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
                logger.info("🔍 Cache miss. Proceeding to scrape from web.")
            except redis.exceptions.RedisError:
                logger.error(
                    "❌ Redis cache read error. Will scrape from web instead.",
                    exc_info=True,
                )

        if force_refresh:
            logger.info("🔄 Force refresh enabled, bypassing cache.")

        live_data = await self._scrape_from_web_async()

        if self.redis_client and live_data is not None and not live_data.empty:
            try:
                logger.info(
                    f"💾 Storing new data in Redis cache for {self.cache_ttl_seconds} seconds."
                )
                json_data = live_data.to_json(
                    orient="records", lines=True, date_format="iso"
                )
                self.redis_client.setex(
                    self.cache_key,
                    self.cache_ttl_seconds,
                    json_data,
                )
            except redis.exceptions.RedisError:
                logger.error(
                    "❌ Redis cache write error. Proceeding without caching.",
                    exc_info=True,
                )

        return live_data

    def get_latest_yields(self) -> Optional[pd.DataFrame]:
        """Synchronous wrapper for get_latest_yields_async."""
        return asyncio.run(self.get_latest_yields_async())


async def fetch_and_update_data_async(
    data_source: CbeScraper,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
    force_refresh: bool = False,
) -> bool:
    """
    Coordinates fetching the latest data and updating the historical data store if necessary.
    """

    def report_status(message: str):
        if status_callback:
            status_callback(message)

    report_status("جاري جلب أحدث البيانات...")
    latest_data = await data_source.get_latest_yields_async(force_refresh=force_refresh)

    if latest_data is None or latest_data.empty:
        raise RuntimeError("فشلت جميع المحاولات لجلب البيانات من المصدر.")

    report_status("تم الجلب، جاري التحقق من وجود تحديثات...")
    db_session_date_str = data_store.get_latest_session_date()
    live_latest_date_str = latest_data[C.SESSION_DATE_COLUMN_NAME].iloc[0]

    # Using > comparison assumes dates are consistently formatted (e.g., YYYY-MM-DD)
    # If not, they should be parsed to datetime objects first.
    is_new_data = not db_session_date_str or live_latest_date_str > db_session_date_str

    if force_refresh or is_new_data:
        reason = "التحديث الإجباري" if force_refresh else "البيانات الجديدة"
        report_status(f"تم العثور على تحديث ({reason})، جاري الحفظ...")
        try:
            data_store.save_data(latest_data)
            report_status("✅ اكتمل تحديث البيانات بنجاح!")
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ البيانات في المخزن: {e}", exc_info=True)
            report_status("❌ خطأ: فشل تحديث البيانات.")
            return False

    else:
        report_status("البيانات محدثة بالفعل. لا حاجة للحفظ.")
        return False


def fetch_and_update_data(
    data_source: CbeScraper,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
    force_refresh: bool = False,
) -> bool:
    """Synchronous wrapper for fetch_and_update_data_async."""
    return asyncio.run(
        fetch_and_update_data_async(
            data_source, data_store, status_callback, force_refresh
        )
    )
