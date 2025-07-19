# constants.py (النسخة النهائية المحسنة)
"""
Centralized constants for the Treasury Calculator application.
This file consolidates all magic strings, column names, URLs, and default values
to improve maintainability and prevent errors.

تحسينات النسخة الجديدة:
- إضافة ثوابت جديدة للتحكم في الأداء
- تحسين تنظيم الثوابت
- إضافة تعليقات توضيحية باللغة العربية
- إضافة ثوابت للتحكم في التخزين المؤقت
- إضافة ثوابت للتحكم في الأمان
"""

# ==================================================
# 📊 Column Names (أسماء الأعمدة)
# ==================================================
TENOR_COLUMN_NAME = "tenor"
YIELD_COLUMN_NAME = "yield"
DATE_COLUMN_NAME = "scrape_date"
SESSION_DATE_COLUMN_NAME = "session_date"

# ==================================================
# 🗄️ Database (قاعدة البيانات)
# ==================================================
DB_FILENAME = "cbe_historical_data.db"
TABLE_NAME = "cbe_t_bills"

# ==================================================
# 🌐 Web Scraping (جلب البيانات من الويب)
# ==================================================
CBE_DATA_URL = "https://www.cbe.org.eg/ar/auctions/egp-t-bills"
YIELD_ANCHOR_TEXT = "متوسط العائد المرجح"
ACCEPTED_BIDS_KEYWORD = "المقبولة"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

# ==================================================
# ⚙️ Web Scraping Controls (التحكم في جلب البيانات)
# ==================================================
SCRAPER_RETRIES = 3
SCRAPER_RETRY_DELAY_SECONDS = 10
SCRAPER_TIMEOUT_SECONDS = 60
SCRAPER_MAX_WAIT_TIME = 30  # أقصى وقت انتظار للعناصر

# ==================================================
# 💰 Financial (المالية)
# ==================================================
DAYS_IN_YEAR = 365.0
DEFAULT_TAX_RATE_PERCENT = 20.0
MIN_T_BILL_AMOUNT = 25000.0
T_BILL_AMOUNT_STEP = 25000.0
MAX_T_BILL_AMOUNT = 10000000.0  # 10 مليون جنيه كحد أقصى

# ==================================================
# 🌍 Localization (التوطين)
# ==================================================
TIMEZONE = "Africa/Cairo"
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================================================
# 📈 Initial Data (البيانات الأولية)
# ==================================================
INITIAL_DATA = {
    TENOR_COLUMN_NAME: [91, 182, 273, 364],
    YIELD_COLUMN_NAME: [26.0, 26.5, 27.0, 27.5],
    SESSION_DATE_COLUMN_NAME: ["N/A", "N/A", "N/A", "N/A"],
}

# ==================================================
# 🎨 UI Constants (ثوابت واجهة المستخدم)
# ==================================================
APP_TITLE = "🏦 حاسبة أذون الخزانة المصرية"
APP_HEADER = "تطبيق تفاعلي لحساب وتحليل عوائد أذون الخزانة المصرية"
PRIMARY_CALCULATOR_TITLE = "🧮 حاسبة العائد الأساسية (الشراء والاحتفاظ)"
SECONDARY_CALCULATOR_TITLE = "⚖️ حاسبة تحليل البيع في السوق الثانوي"
HELP_TITLE = "💡 شرح ومساعدة (أسئلة شائعة)"
AUTHOR_NAME = "Mohamed AL-QaTri"

# ==================================================
# 📁 Paths (المسارات)
# ==================================================
CSS_FILE_PATH = "css/style.css"
DATA_DIR = "data"
LOGS_DIR = "logs"

# ==================================================
# 🔧 Performance & Caching (الأداء والتخزين المؤقت)
# ==================================================
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 ساعات
REDIS_CACHE_KEY = "cbe_latest_yields_cache"
MAX_CACHE_SIZE = 1000  # أقصى عدد من العناصر في التخزين المؤقت

# ==================================================
# 🛡️ Security & Validation (الأمان والتحقق)
# ==================================================
MAX_YIELD_RATE = 100.0  # أقصى معدل عائد مسموح
MIN_YIELD_RATE = 0.1    # أدنى معدل عائد مسموح
MAX_TENOR_DAYS = 365    # أقصى مدة مسموحة
MIN_TENOR_DAYS = 1      # أدنى مدة مسموحة

# ==================================================
# 📊 Chart Configuration (إعدادات الرسوم البيانية)
# ==================================================
CHART_HEIGHT = 500
CHART_TEMPLATE = "plotly_dark"
CHART_MARKERS = True
CHART_LINE_WIDTH = 2

# ==================================================
# 🔄 Update Configuration (إعدادات التحديث)
# ==================================================
UPDATE_CHECK_INTERVAL_HOURS = 4  # فحص التحديث كل 4 ساعات
FORCE_UPDATE_THRESHOLD_DAYS = 7  # إجبار التحديث بعد 7 أيام
MAX_UPDATE_RETRIES = 3

# ==================================================
# 📝 Logging Configuration (إعدادات التسجيل)
# ==================================================
LOG_LEVEL = "WARNING"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==================================================
# 🎯 Essential Text Markers (علامات النص الأساسية)
# ==================================================
ESSENTIAL_TEXT_MARKERS = [
    "النتائج",
    "تاريخ الجلسة",
    YIELD_ANCHOR_TEXT,  # "متوسط العائد المرجح"
    ACCEPTED_BIDS_KEYWORD,  # "المقبولة"
]

# ==================================================
# 🚨 Error Messages (رسائل الأخطاء)
# ==================================================
ERROR_MESSAGES = {
    "database_connection": "فشل في الاتصال بقاعدة البيانات",
    "data_loading": "فشل في تحميل البيانات",
    "scraping_failed": "فشل في جلب البيانات من الموقع",
    "validation_error": "خطأ في التحقق من صحة المدخلات",
    "calculation_error": "خطأ في الحسابات",
    "network_error": "خطأ في الاتصال بالشبكة",
    "timeout_error": "انتهت مهلة الاتصال",
}

# ==================================================
# ✅ Success Messages (رسائل النجاح)
# ==================================================
SUCCESS_MESSAGES = {
    "data_updated": "تم تحديث البيانات بنجاح",
    "calculation_complete": "تم إكمال الحسابات بنجاح",
    "data_saved": "تم حفظ البيانات بنجاح",
    "cache_updated": "تم تحديث التخزين المؤقت",
}

# ==================================================
# ℹ️ Info Messages (رسائل المعلومات)
# ==================================================
INFO_MESSAGES = {
    "data_already_updated": "البيانات محدثة بالفعل",
    "using_cached_data": "جاري استخدام البيانات المخزنة مؤقتاً",
    "checking_for_updates": "جاري فحص التحديثات",
    "processing_data": "جاري معالجة البيانات",
}

# ==================================================
# ⚠️ Warning Messages (رسائل التحذير)
# ==================================================
WARNING_MESSAGES = {
    "fallback_to_sqlite": "الرجوع إلى SQLite كبديل",
    "cache_unavailable": "التخزين المؤقت غير متاح",
    "partial_data": "البيانات غير مكتملة",
    "old_data": "البيانات قديمة",
}

# ==================================================
# 🎨 Color Scheme (نظام الألوان)
# ==================================================
COLORS = {
    "primary": "#3b82f6",
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#343a40",
    "white": "#ffffff",
    "black": "#000000",
    "gray": "#6c757d",
    "gray_light": "#adb5bd",
    "gray_dark": "#495057",
}

# ==================================================
# 📱 Responsive Breakpoints (نقاط التوقف المتجاوبة)
# ==================================================
BREAKPOINTS = {
    "mobile": 768,
    "tablet": 1024,
    "desktop": 1200,
    "large_desktop": 1400,
}

# ==================================================
# 🔧 Feature Flags (علامات الميزات)
# ==================================================
FEATURES = {
    "redis_caching": True,
    "sentry_monitoring": True,
    "auto_update": True,
    "historical_charts": True,
    "secondary_market": True,
    "fee_calculator": True,
    "dark_mode": True,
    "rtl_support": True,
}

# ==================================================
# 📊 Data Validation Rules (قواعد التحقق من البيانات)
# ==================================================
VALIDATION_RULES = {
    "min_face_value": MIN_T_BILL_AMOUNT,
    "max_face_value": MAX_T_BILL_AMOUNT,
    "min_yield_rate": MIN_YIELD_RATE,
    "max_yield_rate": MAX_YIELD_RATE,
    "min_tenor": MIN_TENOR_DAYS,
    "max_tenor": MAX_TENOR_DAYS,
    "min_tax_rate": 0.0,
    "max_tax_rate": 100.0,
}

# ==================================================
# 🎯 Application States (حالات التطبيق)
# ==================================================
APP_STATES = {
    "initial": "initial",
    "loading": "loading",
    "ready": "ready",
    "error": "error",
    "updating": "updating",
    "calculating": "calculating",
}

# ==================================================
# 📈 Chart Types (أنواع الرسوم البيانية)
# ==================================================
CHART_TYPES = {
    "line": "line",
    "bar": "bar",
    "scatter": "scatter",
    "area": "area",
}

# ==================================================
# 🔄 Update Statuses (حالات التحديث)
# ==================================================
UPDATE_STATUSES = {
    "idle": "idle",
    "checking": "checking",
    "downloading": "downloading",
    "processing": "processing",
    "saving": "saving",
    "complete": "complete",
    "failed": "failed",
}
