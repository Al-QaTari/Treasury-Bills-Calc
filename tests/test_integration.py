# tests/test_integration.py
import sys
import os
import pytest
import pandas as pd
import streamlit as st

# تعديل مسار المشروع الرئيسي
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cbe_scraper import CbeScraper
from db_manager import SQLiteDBManager
from .test_cbe_scraper import MOCK_HTML_CONTENT


@pytest.fixture
def db_for_integration():
    """
    🔧 قاعدة بيانات SQLite مؤقتة في الذاكرة لاختبارات التكامل.
    """
    st.cache_data.clear()
    st.cache_resource.clear()
    return SQLiteDBManager(db_filename=":memory:")


def test_full_integration_parse_save_load(db_for_integration: SQLiteDBManager):
    """
    🧪 اختبار تكاملي كامل: تحليل HTML -> حفظ البيانات -> تحميلها -> التحقق منها.
    """
    # الخطوة 1: تحليل HTML
    scraper = CbeScraper()
    parsed_df = scraper._parse_cbe_html(MOCK_HTML_CONTENT)

    assert parsed_df is not None, "❌ فشل تحليل HTML"
    assert len(parsed_df) == 4, "❌ عدد الصفوف المحللة غير صحيح"

    # الخطوة 2: حفظ البيانات
    db_for_integration.save_data(parsed_df)

    # الخطوة 3: تحميل البيانات
    latest_data, _ = db_for_integration.load_latest_data()

    assert latest_data is not None, "❌ فشل تحميل البيانات"
    assert len(latest_data) == 4, "❌ عدد الصفوف المحملة غير صحيح"

    # الخطوة 4: تحقق من قيمة لعائد أجل 91
    latest_data["tenor"] = pd.to_numeric(latest_data["tenor"])
    df_91 = latest_data[latest_data["tenor"] == 91]

    assert not df_91.empty, "❌ لم يتم العثور على بيانات لأجل 91 يومًا"
    assert df_91["yield"].iloc[0] == 27.558, "❌ قيمة العائد غير مطابقة"
