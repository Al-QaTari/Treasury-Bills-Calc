# postgres_manager.py (نسخة محسّنة بالكامل + دعم cache_resource)
import logging
import os
import pandas as pd
import psycopg2
import pytz
from typing import Optional, Tuple
from sqlalchemy import create_engine
import streamlit as st
from dotenv import load_dotenv

from treasury_core.ports import HistoricalDataStore
import constants as C

load_dotenv()  # ✅ بعد الاستيراد مباشرة

logger = logging.getLogger(__name__)


class PostgresDBManager(HistoricalDataStore):
    def __init__(self):
        self.conn_uri = os.environ.get("POSTGRES_URI")
        if not self.conn_uri:
            raise ValueError("متغير البيئة POSTGRES_URI غير موجود.")

        sqlalchemy_uri = self.conn_uri.replace(
            "postgres://", "postgresql+psycopg2://", 1
        )
        self.engine = create_engine(sqlalchemy_uri)

        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.conn_uri)

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{C.TABLE_NAME}" (
                            "{C.TENOR_COLUMN_NAME}" INTEGER NOT NULL,
                            "{C.YIELD_COLUMN_NAME}" REAL NOT NULL,
                            "{C.SESSION_DATE_COLUMN_NAME}" TEXT NOT NULL,
                            "{C.DATE_COLUMN_NAME}" TIMESTAMPTZ NOT NULL,
                            PRIMARY KEY ("{C.TENOR_COLUMN_NAME}", "{C.SESSION_DATE_COLUMN_NAME}")
                        );
                    """
                    )
            logger.info("✅ PostgreSQL table initialized or already exists.")
        except psycopg2.Error:
            logger.error("❌ PostgreSQL initialization failed", exc_info=True)
            raise

    def save_data(self, df: pd.DataFrame) -> None:
        df_to_save = df.copy()
        if "session_date_dt" in df_to_save.columns:
            df_to_save.drop(columns=["session_date_dt"], inplace=True)

        df_to_save[C.DATE_COLUMN_NAME] = pd.to_datetime(
            df_to_save[C.DATE_COLUMN_NAME], errors="coerce"
        )
        df_to_save = df_to_save[df_to_save[C.DATE_COLUMN_NAME].notnull()]
        if df_to_save.empty:
            logger.warning("⚠️ لم يتم حفظ أي بيانات: جميع القيم الزمنية غير صالحة.")
            return

        if df_to_save[C.DATE_COLUMN_NAME].dt.tz is None:
            df_to_save[C.DATE_COLUMN_NAME] = df_to_save[
                C.DATE_COLUMN_NAME
            ].dt.tz_localize("UTC")
        else:
            df_to_save[C.DATE_COLUMN_NAME] = df_to_save[
                C.DATE_COLUMN_NAME
            ].dt.tz_convert("UTC")

        records = df_to_save.to_dict("records")

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    for row in records:
                        cur.execute(
                            f"""
                            INSERT INTO "{C.TABLE_NAME}" 
                            ("{C.TENOR_COLUMN_NAME}", "{C.YIELD_COLUMN_NAME}", "{C.SESSION_DATE_COLUMN_NAME}", "{C.DATE_COLUMN_NAME}")
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT ("{C.TENOR_COLUMN_NAME}", "{C.SESSION_DATE_COLUMN_NAME}")
                            DO UPDATE SET 
                                "{C.YIELD_COLUMN_NAME}" = EXCLUDED."{C.YIELD_COLUMN_NAME}",
                                "{C.DATE_COLUMN_NAME}" = EXCLUDED."{C.DATE_COLUMN_NAME}";
                        """,
                            (
                                row[C.TENOR_COLUMN_NAME],
                                row[C.YIELD_COLUMN_NAME],
                                row[C.SESSION_DATE_COLUMN_NAME],
                                row[C.DATE_COLUMN_NAME],
                            ),
                        )
            logger.info(f"💾 {len(df_to_save)} سجل تم حفظه في PostgreSQL.")
        except psycopg2.Error:
            logger.error("❌ فشل في حفظ البيانات إلى PostgreSQL", exc_info=True)
            raise

    def clear_all_data(self) -> None:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f'TRUNCATE TABLE "{C.TABLE_NAME}" RESTART IDENTITY;')
            logger.info(f"🗑️ تم مسح جميع البيانات من الجدول: {C.TABLE_NAME}")
        except psycopg2.Error:
            logger.error("❌ فشل في مسح البيانات من PostgreSQL", exc_info=True)
            raise

    def load_latest_data(
        self,
    ) -> Tuple[pd.DataFrame, Tuple[Optional[str], Optional[str]]]:
        try:
            with self.engine.connect() as conn:
                query = f"""
                    SELECT 
                        t."{C.TENOR_COLUMN_NAME}", 
                        t."{C.YIELD_COLUMN_NAME}", 
                        t."{C.SESSION_DATE_COLUMN_NAME}",
                        (SELECT MAX("{C.DATE_COLUMN_NAME}") FROM "{C.TABLE_NAME}") as max_scrape_date
                    FROM "{C.TABLE_NAME}" t
                    WHERE t."{C.DATE_COLUMN_NAME}" = (
                        SELECT MAX(t2."{C.DATE_COLUMN_NAME}") 
                        FROM "{C.TABLE_NAME}" t2 
                        WHERE t2."{C.TENOR_COLUMN_NAME}" = t."{C.TENOR_COLUMN_NAME}"
                    )
                """
                df = pd.read_sql_query(query, conn)

                if df.empty or "max_scrape_date" not in df.columns:
                    return pd.DataFrame(), ("البيانات الأولية", None)

                max_date_raw = df["max_scrape_date"].iloc[0]
                if pd.isnull(max_date_raw):
                    return pd.DataFrame(), ("البيانات الأولية", None)

                last_update_dt_utc = pd.to_datetime(max_date_raw, errors="coerce")
                if pd.isnull(last_update_dt_utc):
                    return pd.DataFrame(), ("البيانات الأولية", None)

                if last_update_dt_utc.tzinfo is None:
                    last_update_dt_utc = last_update_dt_utc.tz_localize("UTC")
                else:
                    last_update_dt_utc = last_update_dt_utc.tz_convert("UTC")

                cairo_tz = pytz.timezone(C.TIMEZONE)
                last_update_dt_cairo = last_update_dt_utc.astimezone(cairo_tz)

                last_update_date = last_update_dt_cairo.strftime("%Y-%m-%d")
                last_update_time = last_update_dt_cairo.strftime("%I:%M %p")

                df.drop(columns=["max_scrape_date"], inplace=True)
                return df, (last_update_date, last_update_time)

        except Exception:
            logger.warning(
                "⚠️ لم يتم تحميل البيانات الأخيرة من PostgreSQL", exc_info=True
            )
            return pd.DataFrame(), ("البيانات الأولية", None)

    @st.cache_data
    def load_all_historical_data(_self) -> pd.DataFrame:
        """
        تحميل جميع البيانات التاريخية من قاعدة البيانات.
        يتم تخزين نتيجة هذه الدالة مؤقتاً لتجنب إعادة استدعاء قاعدة البيانات.
        """
        try:
            with _self.engine.connect() as conn:
                query = f'SELECT * FROM "{C.TABLE_NAME}"'
                df = pd.read_sql_query(query, conn)

                if df.empty:
                    return pd.DataFrame()

                # التأكد من أن عمود التاريخ من نوع datetime قبل الفرز
                df[C.DATE_COLUMN_NAME] = pd.to_datetime(df[C.DATE_COLUMN_NAME])
                return df.sort_values(by=C.DATE_COLUMN_NAME, ascending=False)

        except Exception:
            logger.error("❌ فشل تحميل البيانات التاريخية من PostgreSQL", exc_info=True)
            return pd.DataFrame()

    def get_latest_session_date(self) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT "{C.SESSION_DATE_COLUMN_NAME}"
                        FROM "{C.TABLE_NAME}"
                        ORDER BY to_date("{C.SESSION_DATE_COLUMN_NAME}", 'DD/MM/YYYY') DESC
                        LIMIT 1;
                    """
                    )
                    result = cur.fetchone()
                    return result[0] if result else None
        except psycopg2.Error:
            logger.error("❌ فشل في جلب آخر تاريخ جلسة من PostgreSQL", exc_info=True)
            return None


# ✅ كاش ستريمليت للحصول على نسخة واحدة من PostgreSQL manager
@st.cache_resource
def get_db_manager() -> HistoricalDataStore:
    """
    إرجاع كائن PostgresDBManager محمي بالكاش.
    """
    return PostgresDBManager()
