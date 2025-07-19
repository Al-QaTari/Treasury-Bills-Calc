# cbe_scraper.py (النسخة النهائية المحسنة)
import os
import sys
import pandas as pd
from io import StringIO
import asyncio
from typing import Optional, Callable, Dict, Any
import logging
from contextlib import contextmanager
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
import redis
from redis.exceptions import RedisError

from treasury_core.ports import YieldDataSource, HistoricalDataStore
import constants as C
from utils import log_performance_metrics, safe_divide, truncate_text

logger = logging.getLogger(__name__)


@contextmanager
def suppress_output():
    """قمع المخرجات لتجنب الضوضاء في السجلات."""
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
    """
    محسن لجلب بيانات أذون الخزانة من موقع البنك المركزي المصري.
    
    التحسينات الجديدة:
    - تحسين التخزين المؤقت مع Redis
    - معالجة محسنة للأخطاء
    - تحسين الأداء مع Playwright
    - إضافة مقاييس الأداء
    - تحسين التحقق من صحة البيانات
    """
    
    def __init__(self):
        """تهيئة المحسن مع إعدادات محسنة."""
        self.redis_client = None
        self.cache_key = C.REDIS_CACHE_KEY
        self.cache_ttl_seconds = C.CACHE_TTL_SECONDS
        self.last_scrape_time = None
        self.scrape_stats = {
            "total_scrapes": 0,
            "successful_scrapes": 0,
            "failed_scrapes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
        # إعداد Redis إذا كان متاحاً
        self._setup_redis()
        
    def _setup_redis(self) -> None:
        """إعداد اتصال Redis مع معالجة محسنة للأخطاء."""
        redis_uri = os.environ.get("AIVEN_REDIS_URI")
        if redis_uri:
            try:
                self.redis_client = redis.from_url(
                    redis_uri,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # اختبار الاتصال
                self.redis_client.ping()
                logger.info("✅ Redis client initialized successfully.")
            except RedisError as e:
                logger.error(f"❌ Failed to initialize Redis client: {e}", exc_info=True)
                self.redis_client = None
        else:
            logger.warning("⚠️ AIVEN_REDIS_URI not set. Redis caching is disabled.")

    def _verify_page_structure(self, page_source: str) -> None:
        """التحقق من صحة هيكل الصفحة مع تحسينات."""
        missing_markers = []
        
        for marker in C.ESSENTIAL_TEXT_MARKERS:
            if marker not in page_source:
                missing_markers.append(marker)
        
        if missing_markers:
            error_msg = f"Page structure verification failed! Missing markers: {missing_markers}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.debug("✅ Page structure verification passed")

    def _parse_cbe_html(self, page_source: str) -> Optional[pd.DataFrame]:
        """
        تحليل HTML مع معالجة محسنة للأخطاء وتحسينات الأداء.
        """
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(page_source, "lxml")
            
            # البحث عن عناصر النتائج
            results_headers = soup.find_all(
                lambda tag: tag.name == "h2" and "النتائج" in tag.get_text()
            )
            
            if not results_headers:
                logger.warning("No results headers found in HTML")
                return None

            all_dataframes = []
            
            for header in results_headers:
                try:
                    section_df = self._parse_section(header)
                    if section_df is not None and not section_df.empty:
                        all_dataframes.append(section_df)
                except Exception as e:
                    logger.error(f"Error parsing section: {e}", exc_info=True)
                    continue

            if not all_dataframes:
                logger.warning("No valid data sections found")
                return None

            # دمج جميع البيانات
            final_df = pd.concat(all_dataframes, ignore_index=True)
            
            # معالجة التواريخ
            final_df = self._process_dates(final_df)
            
            # تنظيف وترتيب البيانات
            final_df = self._clean_and_sort_data(final_df)
            
            # تسجيل مقاييس الأداء
            log_performance_metrics(
                "_parse_cbe_html", 
                start_time, 
                {"sections_parsed": len(all_dataframes), "total_rows": len(final_df)}
            )
            
            return final_df
            
        except Exception as e:
            logger.error(f"❌ Critical error during HTML parsing: {e}", exc_info=True)
            return None

    def _parse_section(self, header) -> Optional[pd.DataFrame]:
        """تحليل قسم واحد من البيانات."""
        try:
            # البحث عن جدول التواريخ
            dates_table = header.find_next("table")
            if not dates_table:
                return None

            # تحليل جدول التواريخ
            dates_df = pd.read_html(StringIO(str(dates_table)))[0]
            tenors = (
                pd.to_numeric(dates_df.columns[1:], errors="coerce")
                .dropna()
                .astype(int)
                .tolist()
            )
            
            if not tenors:
                return None

            session_dates_row = dates_df[dates_df.iloc[:, 0] == "تاريخ الجلسة"]
            if session_dates_row.empty:
                return None

            session_dates = session_dates_row.iloc[0, 1 : len(tenors) + 1].tolist()
            
            # إنشاء DataFrame للتواريخ والآجال
            dates_tenors_df = pd.DataFrame({
                C.TENOR_COLUMN_NAME: tenors,
                C.SESSION_DATE_COLUMN_NAME: session_dates,
            })

            # البحث عن جدول العوائد
            accepted_bids_header = header.find_next(
                lambda tag: tag.name in ["p", "strong"]
                and C.ACCEPTED_BIDS_KEYWORD in tag.get_text()
            )
            
            if not accepted_bids_header:
                return None

            yields_table = accepted_bids_header.find_next("table")
            if not yields_table:
                return None

            # تحليل جدول العوائد
            yields_df_raw = pd.read_html(StringIO(str(yields_table)))[0]
            yields_df_raw.columns = ["البيان"] + tenors
            
            yield_row = yields_df_raw[
                yields_df_raw.iloc[:, 0].str.contains(C.YIELD_ANCHOR_TEXT, na=False)
            ]

            if yield_row.empty:
                return None

            yield_series = yield_row.iloc[0, 1:].astype(float)
            yield_series.name = C.YIELD_COLUMN_NAME
            
            # دمج البيانات
            section_df = dates_tenors_df.join(yield_series, on=C.TENOR_COLUMN_NAME)

            # التحقق من اكتمال البيانات
            if not section_df[C.YIELD_COLUMN_NAME].isnull().any():
                return section_df
                
        except Exception as e:
            logger.error(f"Error parsing section: {e}", exc_info=True)
            
        return None

    def _process_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """معالجة التواريخ مع تحسينات."""
        try:
            df["session_date_dt"] = pd.to_datetime(
                df[C.SESSION_DATE_COLUMN_NAME], 
                format=C.DATE_FORMAT, 
                errors="coerce"
            )
            
            df[C.DATE_COLUMN_NAME] = (
                df["session_date_dt"]
                .dt.tz_localize(
                    C.TIMEZONE, 
                    ambiguous="NaT", 
                    nonexistent="shift_forward"
                )
                .dt.tz_convert("UTC")
            )
            
            # إزالة الصفوف ذات التواريخ غير الصالحة
            df = df.dropna(subset=[C.DATE_COLUMN_NAME])
            
        except Exception as e:
            logger.error(f"Error processing dates: {e}", exc_info=True)
            
        return df

    def _clean_and_sort_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """تنظيف وترتيب البيانات."""
        try:
            # ترتيب حسب تاريخ الجلسة (الأحدث أولاً)
            df = df.sort_values("session_date_dt", ascending=False)
            
            # إزالة التكرارات مع الاحتفاظ بأحدث البيانات لكل أجل
            df = df.drop_duplicates(subset=[C.TENOR_COLUMN_NAME])
            
            # ترتيب نهائي حسب الأجل
            df = df.sort_values(by=C.TENOR_COLUMN_NAME)
            
            # إزالة العمود المؤقت
            if "session_date_dt" in df.columns:
                df = df.drop(columns=["session_date_dt"])
                
        except Exception as e:
            logger.error(f"Error cleaning and sorting data: {e}", exc_info=True)
            
        return df

    async def _scrape_from_web_async(self) -> Optional[pd.DataFrame]:
        """
        جلب البيانات من الويب باستخدام Playwright مع تحسينات شاملة.
        """
        start_time = time.time()
        browser = None
        context = None
        page = None
        
        try:
            logger.info("🚀 Starting web scraping with Playwright...")
            
            with suppress_output():
                async with async_playwright() as p:
                    # إعداد المتصفح
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-gpu",
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor"
                        ]
                    )
                    
                    # إعداد السياق
                    context = await browser.new_context(
                        user_agent=C.USER_AGENT,
                        viewport={"width": 1920, "height": 1080},
                        extra_http_headers={
                            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                        }
                    )
                    
                    # إنشاء الصفحة
                    page = await context.new_page()
                    
                    # تعيين مهلة أطول للتحميل
                    page.set_default_timeout(C.SCRAPER_TIMEOUT_SECONDS * 1000)
                    
                    # الانتقال إلى الصفحة
                    logger.debug(f"Navigating to: {C.CBE_DATA_URL}")
                    await page.goto(C.CBE_DATA_URL, wait_until="networkidle")
                    
                    # انتظار تحميل الجداول
                    await page.wait_for_selector(
                        "table", 
                        timeout=C.SCRAPER_TIMEOUT_SECONDS * 1000
                    )
                    
                    # انتظار إضافي لضمان تحميل المحتوى
                    await page.wait_for_timeout(2000)
                    
                    # الحصول على محتوى الصفحة
                    page_source = await page.content()
                    
                    # التحقق من صحة الهيكل
                    self._verify_page_structure(page_source)
                    
                    # تحليل البيانات
                    result = self._parse_cbe_html(page_source)
                    
                    # تحديث الإحصائيات
                    self.scrape_stats["total_scrapes"] += 1
                    if result is not None and not result.empty:
                        self.scrape_stats["successful_scrapes"] += 1
                        self.last_scrape_time = datetime.now()
                    else:
                        self.scrape_stats["failed_scrapes"] += 1
                    
                    # تسجيل مقاييس الأداء
                    log_performance_metrics(
                        "_scrape_from_web_async", 
                        start_time, 
                        {"rows_scraped": len(result) if result is not None else 0}
                    )
                    
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Playwright scraping failed: {e}", exc_info=True)
            self.scrape_stats["failed_scrapes"] += 1
            
            # محاولة التقاط لقطة شاشة للتشخيص
            if page:
                try:
                    screenshot_path = "/app/debug_screenshot.png"
                    await page.screenshot(
                        path=screenshot_path, 
                        full_page=True
                    )
                    logger.warning(f"📸 Screenshot saved at {screenshot_path}")
                except Exception as ss_err:
                    logger.warning(f"⚠️ Failed to capture screenshot: {ss_err}")
            
            return None
            
        finally:
            # تنظيف الموارد
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    async def get_latest_yields_async(
        self, force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        جلب أحدث بيانات العوائد مع تحسينات التخزين المؤقت.
        
        Args:
            force_refresh: إذا كان True، يتجاوز التخزين المؤقت
            
        Returns:
            DataFrame يحتوي على أحدث البيانات أو None
        """
        start_time = time.time()
        
        # محاولة جلب البيانات من التخزين المؤقت
        if not force_refresh and self.redis_client:
            cached_data = await self._get_cached_data()
            if cached_data is not None:
                self.scrape_stats["cache_hits"] += 1
                logger.info("✅ Cache hit! Loading data from Redis.")
                return cached_data
            else:
                self.scrape_stats["cache_misses"] += 1

        if force_refresh:
            logger.info("🔄 Force refresh enabled, bypassing cache.")

        # جلب البيانات من الويب
        live_data = await self._scrape_from_web_async()

        # حفظ البيانات في التخزين المؤقت
        if self.redis_client and live_data is not None and not live_data.empty:
            await self._cache_data(live_data)

        # تسجيل مقاييس الأداء
        log_performance_metrics(
            "get_latest_yields_async", 
            start_time, 
            {"force_refresh": force_refresh, "cache_used": not force_refresh}
        )
        
        return live_data

    async def _get_cached_data(self) -> Optional[pd.DataFrame]:
        """جلب البيانات من التخزين المؤقت."""
        try:
            cached_data = self.redis_client.get(self.cache_key)
            if cached_data:
                df = pd.read_json(StringIO(cached_data), lines=True)
                df[C.DATE_COLUMN_NAME] = pd.to_datetime(
                    df[C.DATE_COLUMN_NAME], 
                    errors="coerce", 
                    utc=True
                )
                return df
        except RedisError as e:
            logger.error(f"Redis cache read error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error parsing cached data: {e}", exc_info=True)
        
        return None

    async def _cache_data(self, df: pd.DataFrame) -> None:
        """حفظ البيانات في التخزين المؤقت."""
        try:
            logger.info(f"💾 Storing new data in Redis cache for {self.cache_ttl_seconds} seconds.")
            
            # تحويل البيانات إلى JSON
            json_data = df.to_json(orient="records", lines=True, date_format="iso")
            
            # حفظ في Redis
            self.redis_client.setex(
                self.cache_key,
                self.cache_ttl_seconds,
                json_data
            )
            
            logger.info("✅ Data cached successfully")
            
        except RedisError as e:
            logger.error(f"Redis cache write error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error caching data: {e}", exc_info=True)

    def get_latest_yields(self) -> Optional[pd.DataFrame]:
        """واجهة متزامنة لجلب البيانات."""
        return asyncio.run(self.get_latest_yields_async())

    def get_scrape_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الجلب."""
        return {
            **self.scrape_stats,
            "last_scrape_time": self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            "redis_available": self.redis_client is not None,
            "cache_ttl_seconds": self.cache_ttl_seconds
        }

    def clear_cache(self) -> bool:
        """مسح التخزين المؤقت."""
        try:
            if self.redis_client:
                self.redis_client.delete(self.cache_key)
                logger.info("✅ Cache cleared successfully")
                return True
        except RedisError as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
        return False


async def fetch_and_update_data_async(
    data_source: CbeScraper,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
    force_refresh: bool = False,
) -> bool:
    """
    جلب وتحديث البيانات بشكل متزامن مع تحسينات شاملة.
    
    Args:
        data_source: مصدر البيانات
        data_store: مخزن البيانات
        status_callback: دالة لتحديث الحالة
        force_refresh: إجبار التحديث
        
    Returns:
        True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    start_time = time.time()
    
    try:
        if status_callback:
            status_callback("جاري جلب البيانات...")

        # جلب أحدث البيانات
        latest_data = await data_source.get_latest_yields_async(force_refresh=force_refresh)

        if latest_data is not None and not latest_data.empty:
            if status_callback:
                status_callback("تم الجلب، جاري التحقق...")
                
            # التحقق من وجود بيانات جديدة
            db_session_date_str = data_store.get_latest_session_date()
            live_latest_date_str = latest_data[C.SESSION_DATE_COLUMN_NAME].iloc[0]

            # حفظ البيانات إذا كانت جديدة أو مطلوب تحديث إجباري
            if (
                force_refresh
                or not db_session_date_str
                or live_latest_date_str != db_session_date_str
            ):
                if status_callback:
                    status_callback("تم العثور على بيانات جديدة، جاري الحفظ...")
                    
                data_store.save_data(latest_data)
                
                if status_callback:
                    status_callback("اكتمل تحديث البيانات بنجاح!")
                    
                # تسجيل مقاييس الأداء
                log_performance_metrics(
                    "fetch_and_update_data_async", 
                    start_time, 
                    {"rows_updated": len(latest_data), "force_refresh": force_refresh}
                )
                
                return True
            else:
                if status_callback:
                    status_callback("البيانات محدثة بالفعل.")
                return False
        else:
            raise RuntimeError("فشل في جلب البيانات من المصدر")

    except Exception as e:
        logger.error(f"Error in fetch_and_update_data_async: {e}", exc_info=True)
        if status_callback:
            status_callback("فشل في تحديث البيانات")
        raise


def fetch_and_update_data(
    data_source: YieldDataSource,
    data_store: HistoricalDataStore,
    status_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """واجهة متزامنة لجلب وتحديث البيانات."""
    return asyncio.run(
        fetch_and_update_data_async(data_source, data_store, status_callback)
    )
