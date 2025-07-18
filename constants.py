# constants.py (النسخة النهائية مع علامات التحقق)
"""
Centralized constants for the Treasury Calculator application.
This file consolidates all magic strings, column names, URLs, and default values
to improve maintainability and prevent errors.
"""

# --- Column Names ---
TENOR_COLUMN_NAME = "tenor"
YIELD_COLUMN_NAME = "yield"
DATE_COLUMN_NAME = "scrape_date"
SESSION_DATE_COLUMN_NAME = "session_date"

# --- Database ---
DB_FILENAME = "cbe_historical_data.db"
TABLE_NAME = "cbe_t_bills"

# --- Web Scraping ---
CBE_DATA_URL = "https://www.cbe.org.eg/ar/auctions/egp-t-bills"
YIELD_ANCHOR_TEXT = "متوسط العائد المرجح"
ACCEPTED_BIDS_KEYWORD = "المقبولة"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

# --- Web Scraping Controls ---
SCRAPER_RETRIES = 3
SCRAPER_RETRY_DELAY_SECONDS = 10
SCRAPER_TIMEOUT_SECONDS = 60

# --- Financial ---
DAYS_IN_YEAR = 365.0
DEFAULT_TAX_RATE_PERCENT = 20.0
MIN_T_BILL_AMOUNT = 25000.0
T_BILL_AMOUNT_STEP = 25000.0

# --- Localization ---
TIMEZONE = "Africa/Cairo"

# --- Initial Data (Fallback) ---
INITIAL_DATA = {
    TENOR_COLUMN_NAME: [91, 182, 273, 364],
    YIELD_COLUMN_NAME: [26.0, 26.5, 27.0, 27.5],
    SESSION_DATE_COLUMN_NAME: ["N/A", "N/A", "N/A", "N/A"],
}

# --- UI Constants ---
APP_TITLE = "🏦 حاسبة أذون الخزانة المصرية"
APP_HEADER = "تطبيق تفاعلي لحساب وتحليل عوائد أذون الخزانة المصرية"
PRIMARY_CALCULATOR_TITLE = "🧮 حاسبة العائد الأساسية (الشراء والاحتفاظ)"
SECONDARY_CALCULATOR_TITLE = "⚖️ حاسبة تحليل البيع في السوق الثانوي"
HELP_TITLE = "💡 شرح ومساعدة (أسئلة شائعة)"
AUTHOR_NAME = "Mohamed AL-QaTri"

# --- Paths ---
CSS_FILE_PATH = "css/style.css"

# --- START OF NEW CODE FOR TASK 3 ---
# قائمة بالنصوص الأساسية التي يجب أن تكون موجودة في الصفحة لضمان عمل الكود
ESSENTIAL_TEXT_MARKERS = [
    "النتائج",
    "تاريخ الجلسة",
    YIELD_ANCHOR_TEXT,  # "متوسط العائد المرجح"
    ACCEPTED_BIDS_KEYWORD,  # "المقبولة"
]
# --- END OF NEW CODE FOR TASK 3 ---
