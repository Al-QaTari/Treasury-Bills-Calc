# tests/test_cbe_scraper.py
import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cbe_scraper import CbeScraper
import constants as C

# =====================
# 🔧 إعداد HTML وهمي ثابت
# =====================
MOCK_HTML_CONTENT = """
<html><body>
    <h2>النتائج</h2><table><thead><tr><th>البيان</th><th>182</th><th>364</th></tr></thead>
    <tbody><tr><td>تاريخ الجلسة</td><td>10/07/2025</td><td>10/07/2025</td></tr></tbody></table>
    <p><strong>تفاصيل العروض المقبولة</strong></p>
    <table><tbody><tr><td>متوسط العائد المرجح</td><td>27.192</td><td>25.043</td></tr></tbody></table>
    
    <h2>النتائج</h2><table><thead><tr><th>البيان</th><th>91</th><th>273</th></tr></thead>
    <tbody><tr><td>تاريخ الجلسة</td><td>11/07/2025</td><td>11/07/2025</td></tr></tbody></table>
    <p><strong>تفاصيل العروض المقبولة</strong></p>
    <table><tbody><tr><td>متوسط العائد المرجح</td><td>27.558</td><td>26.758</td></tr></tbody></table>
</body></html>
"""


# =====================
# 🧪 Fixtures
# =====================
@pytest.fixture
def scraper() -> CbeScraper:
    """🔧 يُعيد كائن CbeScraper مهيأ للاختبار."""
    return CbeScraper()


# =====================
# 🧪 Tests
# =====================


def test_html_parser_extracts_correct_data(scraper: CbeScraper):
    """🧪 يتأكد من استخراج البيانات وتحويلها إلى DataFrame صالح."""
    df = scraper._parse_cbe_html(MOCK_HTML_CONTENT)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "session_date_dt" in df.columns
    assert C.TENOR_COLUMN_NAME in df.columns
    assert C.YIELD_COLUMN_NAME in df.columns
    assert C.DATE_COLUMN_NAME in df.columns

    assert len(df) == 4  # 4 صفوف (2 تواريخ × 2 عوائد لكل جلسة)

    # التحقق من التاريخ الأحدث
    latest_session = df["session_date_dt"].max().strftime("%d/%m/%Y")
    assert latest_session == "11/07/2025"

    # التحقق من قيمة العائد 364
    yield_364 = df[df[C.TENOR_COLUMN_NAME] == 364][C.YIELD_COLUMN_NAME].iloc[0]
    assert yield_364 == pytest.approx(25.043)


def test_structure_verification_passes(scraper: CbeScraper):
    """🧪 يتأكد من أن HTML صالح يتم قبوله عند التحقق."""
    scraper._verify_page_structure(MOCK_HTML_CONTENT)


def test_structure_verification_fails_on_missing_keyword(scraper: CbeScraper):
    """🧪 يتأكد من أن التحقق من البنية يفشل إذا غابت علامة أساسية."""
    bad_html = MOCK_HTML_CONTENT.replace("متوسط العائد المرجح", "عنصر مفقود")

    with pytest.raises(RuntimeError) as exc_info:
        scraper._verify_page_structure(bad_html)

    assert "متوسط العائد المرجح" in str(exc_info.value)
