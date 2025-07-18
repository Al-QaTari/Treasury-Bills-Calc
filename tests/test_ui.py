import sys
import os
import pytest
from playwright.async_api import async_playwright, expect

# إضافة المسار الرئيسي للمشروع للسماح بالاستيراد
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# هذا يفترض أن تطبيق ستريمليت يعمل على الرابط التالي:
STREAMLIT_APP_URL = "http://localhost:8501"


# --- 🔧 Fixture لإعادة استخدام المتصفح في كل اختبار ---
@pytest.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        yield page
        await browser.close()


# --- 🧪 اختبار عنوان التطبيق الرئيسي ---
@pytest.mark.ui
@pytest.mark.asyncio
async def test_app_main_title(browser_page):
    """يتحقق من أن عنوان التطبيق الرئيسي يظهر بشكل صحيح."""
    await browser_page.goto(STREAMLIT_APP_URL, timeout=20000)

    # نتحقق من وجود عنوان h1 يحتوي على اسم التطبيق
    title_element = browser_page.locator("h1").first
    await expect(title_element).to_contain_text(
        "حاسبة أذون الخزانة المصرية", timeout=10000
    )


# --- 🧪 اختبار وجود زر تحديث البيانات ---
@pytest.mark.ui
@pytest.mark.asyncio
async def test_update_data_button_exists(browser_page):
    """يتحقق من أن زر 'تحديث البيانات الآن 🔄' موجود ومرئي."""
    await browser_page.goto(STREAMLIT_APP_URL, timeout=20000)

    # نبحث عن الزر باستخدام role accessibility (الأفضل لـ Playwright)
    update_button = browser_page.get_by_role("button", name="تحديث البيانات الآن 🔄")
    await expect(update_button).to_be_visible(timeout=10000)
