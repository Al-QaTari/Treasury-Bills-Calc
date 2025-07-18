# update_data.py
import os
import sys
import logging
import asyncio
import argparse  # New import
import sentry_sdk
from dotenv import load_dotenv

# إضافة مسار المشروع لدعم التشغيل من cron أو docker مباشرة
sys.path.append(os.getcwd())

from cbe_scraper import CbeScraper, fetch_and_update_data_async
from postgres_manager import PostgresDBManager
from utils import setup_logging


# --- START OF MODIFICATION ---
async def main(force_refresh: bool):
    """
    الدالة الرئيسية لتشغيل تحديث البيانات بشكل غير متزامن.
    """
    load_dotenv()

    # إعداد Sentry لمراقبة الأخطاء إن وُجد
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=1.0,
            environment="production-cron",
        )

    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("📦 بدء مهمة التحديث المجدولة (Async)...")
    logger.info("=" * 60)

    try:
        scraper_adapter = CbeScraper()

        postgres_uri = os.environ.get("POSTGRES_URI")
        if not postgres_uri:
            raise RuntimeError(
                "❌ متغير البيئة POSTGRES_URI غير مضبوط. لا يمكن تنفيذ التحديث."
            )

        db_adapter = PostgresDBManager()

        logger.info("⏳ جاري جلب وتحديث البيانات من موقع البنك المركزي...")
        # Pass the force_refresh flag down
        updated = await fetch_and_update_data_async(
            data_source=scraper_adapter,
            data_store=db_adapter,
            status_callback=lambda msg: logger.info(f"📌 {msg}"),
            force_refresh=force_refresh,
        )

        if updated:
            logger.info("✅ تم تحديث البيانات بنجاح.")
        else:
            logger.info("ℹ️ البيانات محدثة بالفعل، لا حاجة للحفظ.")

    except Exception as e:
        logger.critical(f"❗ فشل التحديث المجدول: {e}", exc_info=True)
        if sentry_dsn:
            sentry_sdk.capture_exception(e)
        sys.exit(1)

    finally:
        logger.info("=" * 60)
        logger.info("🛑 انتهاء تنفيذ المهمة المجدولة.")


if __name__ == "__main__":
    # Add argument parser to handle command-line flags
    parser = argparse.ArgumentParser(description="Update Treasury Bill data from CBE.")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass the cache and force a fresh data fetch from the website.",
    )
    args = parser.parse_args()

    # Run the main async function with the parsed argument
    asyncio.run(main(force_refresh=args.force_refresh))
# --- END OF MODIFICATION ---
