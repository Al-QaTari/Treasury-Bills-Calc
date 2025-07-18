# tests/test_postgre_integration.py

import os
import pytest
import streamlit as st
from sqlalchemy import text

from cbe_scraper import CbeScraper
from postgres_manager import PostgresDBManager
from .test_cbe_scraper import MOCK_HTML_CONTENT
import constants as C  # 👈 تأكد أن constants.py فيه TABLE_NAME

# ✅ تخطي الاختبار تلقائيًا إذا POSTGRES_URI غير موجود
POSTGRES_URI = os.getenv("POSTGRES_URI")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URI,
    reason="❌ متغير البيئة POSTGRES_URI غير مضبوط، سيتم تخطي اختبار PostgreSQL.",
)


@pytest.fixture
def postgres_db():
    """
    🔧 قاعدة بيانات PostgreSQL نظيفة للاختبار
    """
    st.cache_data.clear()
    st.cache_resource.clear()
    db = PostgresDBManager()

    # 🧹 مسح الجدول بالكامل قبل كل اختبار
    with db.engine.begin() as conn:
        conn.execute(text(f'DELETE FROM "{C.TABLE_NAME}"'))

    return db


@pytest.mark.integration
def test_postgre_full_integration_parse_save_load(postgres_db):
    """
    🧪 اختبار PostgreSQL: تحليل → حفظ → تحميل → تحقق
    """
    scraper = CbeScraper()
    parsed_df = scraper._parse_cbe_html(MOCK_HTML_CONTENT)

    assert len(parsed_df) == 4

    postgres_db.save_data(parsed_df)

    latest_data, _ = postgres_db.load_latest_data()

    assert latest_data is not None
    assert len(latest_data) == 4

    df_91 = latest_data[latest_data["tenor"] == 91]
    assert not df_91.empty
    assert df_91["yield"].iloc[0] == 27.558
