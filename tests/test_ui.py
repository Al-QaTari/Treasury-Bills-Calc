import pytest

# ✅ التخطي على مستوى الملف إذا لم تتوفر المكتبات المطلوبة
try:
    import pytest_asyncio
    from playwright.async_api import async_playwright, expect
except ImportError:
    pytest.skip("تخطي test_ui.py لأن المكتبات غير مثبتة", allow_module_level=True)

STREAMLIT_APP_URL = "http://localhost:8501"


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        # في بيئات التشغيل الآلي (CI)، قد تحتاج لإضافة --no-sandbox
        # browser = await p.chromium.launch(args=["--no-sandbox"])
        browser = await p.chromium.launch()
        page = await browser.new_page()
        yield page
        await browser.close()


@pytest.mark.ui
@pytest.mark.asyncio
async def test_app_main_title_is_visible(browser_page):
    """
    يتحقق من أن عنوان التطبيق الرئيسي يظهر بشكل صحيح خلال فترة زمنية معقولة.
    """
    await browser_page.goto(STREAMLIT_APP_URL, timeout=30000)

    # استخدام محدد أكثر دقة للوصول إلى العنوان داخل الهيدر
    title_element = browser_page.locator(".centered-header h1")

    # زيادة مهلة الانتظار والتأكد من أن النص المتوقع موجود
    await expect(title_element).to_contain_text(
        "حاسبة أذون الخزانة المصرية", timeout=20000
    )
    await expect(title_element).to_be_visible()


@pytest.mark.ui
@pytest.mark.asyncio
async def test_data_center_buttons_exist(browser_page):
    """
    يتحقق من وجود أي من الأزرار الممكنة في 'مركز البيانات'.
    هذا الاختبار ينجح إذا وجد زر التحديث، أو الزر المعطل، أو زر المحاولة.
    """
    await browser_page.goto(STREAMLIT_APP_URL, timeout=30000)

    # تعريف المحددات لجميع الأزرار الممكنة
    update_now_button = browser_page.get_by_role(
        "button", name="تحديث البيانات الآن 🔄"
    )
    updated_disabled_button = browser_page.get_by_role("button", name="محدثة ✅")
    try_anyway_button = browser_page.get_by_role(
        "button", name="محاولة التحديث على أي حال 🔄"
    )

    # استخدام .or_() للبحث عن أي من المحددات الثلاثة
    # ينجح الاختبار إذا كان أي واحد منهم ظاهرًا
    combined_locator = update_now_button.or_(updated_disabled_button).or_(
        try_anyway_button
    )

    await expect(combined_locator).to_be_visible(timeout=15000)
