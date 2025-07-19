import os
import logging
import re
from typing import Optional, Union, Any
import streamlit as st
import constants as C

logger = logging.getLogger(__name__)


def prepare_arabic_text(text: Union[str, Any]) -> str:
    """
    تحضير النص العربي للتطبيق مع معالجة محسنة للأخطاء.
    
    Args:
        text: النص المراد تحضيره
        
    Returns:
        النص المحضر كسلسلة نصية
    """
    try:
        if text is None:
            return ""
        
        # تحويل إلى سلسلة نصية
        text_str = str(text)
        
        # تنظيف النص من الأحرف غير المرغوبة
        text_str = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\w\s\-\.\,\!\?\(\)\[\]\{\}]', '', text_str)
        
        # إزالة المسافات الزائدة
        text_str = re.sub(r'\s+', ' ', text_str).strip()
        
        return text_str
    except Exception as e:
        logger.error(f"Could not prepare Arabic text: {text}, Error: {e}", exc_info=True)
        return str(text) if text is not None else ""


def load_css(file_path: str) -> None:
    """
    تحميل ملف CSS مع معالجة محسنة للأخطاء.
    
    Args:
        file_path: مسار ملف CSS
    """
    try:
        if os.path.exists(file_path):
            logger.debug(f"Loading CSS from {file_path}")
            with open(file_path, encoding="utf-8") as f:
                css_content = f.read()
                # تحسين CSS للتحميل
                css_content = _optimize_css(css_content)
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
                logger.info(f"CSS loaded successfully from {file_path}")
        else:
            logger.warning(f"CSS file not found at path: {file_path}")
            # تحميل CSS افتراضي
            _load_default_css()
    except Exception as e:
        logger.error(f"Error loading CSS from {file_path}: {e}", exc_info=True)
        _load_default_css()


def _optimize_css(css_content: str) -> str:
    """
    تحسين محتوى CSS للأداء.
    
    Args:
        css_content: محتوى CSS الأصلي
        
    Returns:
        محتوى CSS المحسن
    """
    try:
        # إزالة التعليقات
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # إزالة المسافات الزائدة
        css_content = re.sub(r'\s+', ' ', css_content)
        
        # إزالة المسافات حول علامات الترقيم
        css_content = re.sub(r'\s*([{}:;,])\s*', r'\1', css_content)
        
        return css_content.strip()
    except Exception as e:
        logger.error(f"Error optimizing CSS: {e}", exc_info=True)
        return css_content


def _load_default_css() -> None:
    """تحميل CSS افتراضي في حالة فشل تحميل الملف الأصلي."""
    default_css = """
    :root {
        --primary-font: 'Cairo', sans-serif;
        --color-background: #0e1117;
        --color-container-bg: #1a1a2e;
        --color-text-primary: #f0f2f5;
        --color-text-secondary: #e8e8e8;
        --color-accent: #3b82f6;
        --color-border: #495057;
    }
    
    html, body {
        direction: rtl;
        font-family: var(--primary-font);
        background-color: var(--color-background);
        color: var(--color-text-primary);
    }
    
    [class*="st-"], button, input, textarea, select {
        direction: rtl !important;
        font-family: var(--primary-font) !important;
    }
    """
    st.markdown(f"<style>{default_css}</style>", unsafe_allow_html=True)
    logger.info("Default CSS loaded")


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    إعداد نظام التسجيل مع خيارات محسنة.
    
    Args:
        level: مستوى التسجيل
        log_file: مسار ملف التسجيل (اختياري)
    """
    try:
        if not logging.getLogger().handlers:
            # إنشاء مجلد السجلات إذا لم يكن موجوداً
            if log_file and not os.path.exists(os.path.dirname(log_file)):
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # إعداد التنسيق
            formatter = logging.Formatter(
                C.LOG_FORMAT,
                datefmt=C.LOG_DATE_FORMAT
            )
            
            # إعداد معالج وحدة التحكم
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(level)
            
            # إعداد معالج الملف (إذا تم تحديده)
            handlers = [console_handler]
            if log_file:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(formatter)
                file_handler.setLevel(level)
                handlers.append(file_handler)
            
            # إعداد التسجيل الأساسي
            logging.basicConfig(
                level=level,
                handlers=handlers,
                force=True
            )
            
            logger.info("Logging configured successfully.")
            logger.info(f"Log level set to: {logging.getLevelName(level)}")
            if log_file:
                logger.info(f"Log file: {log_file}")
                
    except Exception as e:
        print(f"Failed to setup logging: {e}")
        # إعداد تسجيل بسيط كبديل
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def format_currency(value: Optional[float], currency_symbol: str = "جنيه") -> str:
    """
    تنسيق القيم المالية مع معالجة محسنة للأخطاء.
    
    Args:
        value: القيمة المراد تنسيقها
        currency_symbol: رمز العملة
        
    Returns:
        القيمة المنسقة كسلسلة نصية
    """
    try:
        if value is None:
            return f"- {prepare_arabic_text(currency_symbol)}"
        
        # التحقق من أن القيمة رقمية
        if not isinstance(value, (int, float)):
            value = float(value)
        
        # تنسيق الرقم
        sign = "-" if value < 0 else ""
        formatted_value = f"{abs(value):,.2f}"
        
        # إضافة رمز العملة
        currency_text = prepare_arabic_text(currency_symbol)
        
        return f"{sign}{formatted_value} {currency_text}"
        
    except (ValueError, TypeError) as e:
        logger.error(f"Could not format value '{value}' as currency: {e}", exc_info=True)
        return str(value) if value is not None else f"- {prepare_arabic_text(currency_symbol)}"


def format_percentage(value: Optional[float], decimal_places: int = 3) -> str:
    """
    تنسيق النسب المئوية.
    
    Args:
        value: القيمة المراد تنسيقها
        decimal_places: عدد الخانات العشرية
        
    Returns:
        النسبة المنسقة كسلسلة نصية
    """
    try:
        if value is None:
            return "0.000%"
        
        if not isinstance(value, (int, float)):
            value = float(value)
        
        return f"{value:.{decimal_places}f}%"
        
    except (ValueError, TypeError) as e:
        logger.error(f"Could not format value '{value}' as percentage: {e}", exc_info=True)
        return "0.000%"


def validate_numeric_input(value: Any, min_value: Optional[float] = None, 
                          max_value: Optional[float] = None) -> Optional[float]:
    """
    التحقق من صحة المدخلات الرقمية.
    
    Args:
        value: القيمة المراد التحقق منها
        min_value: الحد الأدنى المسموح
        max_value: الحد الأقصى المسموح
        
    Returns:
        القيمة المحققة أو None إذا كانت غير صالحة
    """
    try:
        if value is None:
            return None
        
        # تحويل إلى رقم
        numeric_value = float(value)
        
        # التحقق من الحدود
        if min_value is not None and numeric_value < min_value:
            logger.warning(f"Value {numeric_value} is below minimum {min_value}")
            return None
            
        if max_value is not None and numeric_value > max_value:
            logger.warning(f"Value {numeric_value} is above maximum {max_value}")
            return None
        
        return numeric_value
        
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid numeric input: {value}, Error: {e}", exc_info=True)
        return None


def sanitize_filename(filename: str) -> str:
    """
    تنظيف اسم الملف من الأحرف غير المرغوبة.
    
    Args:
        filename: اسم الملف الأصلي
        
    Returns:
        اسم الملف المنظف
    """
    try:
        # إزالة الأحرف غير المسموحة
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # إزالة المسافات الزائدة
        sanitized = re.sub(r'\s+', '_', sanitized)
        
        # إزالة النقاط المتتالية
        sanitized = re.sub(r'\.+', '.', sanitized)
        
        return sanitized.strip('._')
        
    except Exception as e:
        logger.error(f"Error sanitizing filename '{filename}': {e}", exc_info=True)
        return "sanitized_file"


def create_directory_if_not_exists(directory_path: str) -> bool:
    """
    إنشاء مجلد إذا لم يكن موجوداً.
    
    Args:
        directory_path: مسار المجلد
        
    Returns:
        True إذا تم الإنشاء بنجاح أو كان موجوداً، False خلاف ذلك
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            logger.info(f"Created directory: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory '{directory_path}': {e}", exc_info=True)
        return False


def get_file_size_mb(file_path: str) -> Optional[float]:
    """
    الحصول على حجم الملف بالميجابايت.
    
    Args:
        file_path: مسار الملف
        
    Returns:
        حجم الملف بالميجابايت أو None إذا فشل
    """
    try:
        if os.path.exists(file_path):
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)  # تحويل إلى ميجابايت
        return None
    except Exception as e:
        logger.error(f"Error getting file size for '{file_path}': {e}", exc_info=True)
        return None


def is_valid_date(date_string: str, date_format: str = C.DATE_FORMAT) -> bool:
    """
    التحقق من صحة تنسيق التاريخ.
    
    Args:
        date_string: سلسلة التاريخ
        date_format: تنسيق التاريخ المتوقع
        
    Returns:
        True إذا كان التاريخ صحيحاً، False خلاف ذلك
    """
    try:
        from datetime import datetime
        datetime.strptime(date_string, date_format)
        return True
    except (ValueError, TypeError):
        return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    تقصير النص إذا تجاوز الحد الأقصى.
    
    Args:
        text: النص الأصلي
        max_length: الحد الأقصى للطول
        suffix: النص المضاف في النهاية
        
    Returns:
        النص المقصوص
    """
    try:
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
        
    except Exception as e:
        logger.error(f"Error truncating text: {e}", exc_info=True)
        return text


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    قسمة آمنة مع معالجة القسمة على صفر.
    
    Args:
        numerator: البسط
        denominator: المقام
        default: القيمة الافتراضية في حالة القسمة على صفر
        
    Returns:
        نتيجة القسمة أو القيمة الافتراضية
    """
    try:
        if denominator == 0:
            logger.warning(f"Division by zero: {numerator} / {denominator}")
            return default
        return numerator / denominator
    except Exception as e:
        logger.error(f"Error in safe division: {e}", exc_info=True)
        return default


def format_file_size(size_bytes: int) -> str:
    """
    تنسيق حجم الملف بالوحدات المناسبة.
    
    Args:
        size_bytes: حجم الملف بالبايت
        
    Returns:
        حجم الملف المنسق
    """
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"
        
    except Exception as e:
        logger.error(f"Error formatting file size: {e}", exc_info=True)
        return "Unknown size"


def get_environment_info() -> dict:
    """
    الحصول على معلومات البيئة التشغيلية.
    
    Returns:
        قاموس يحتوي على معلومات البيئة
    """
    try:
        import platform
        import sys
        
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "working_directory": os.getcwd(),
            "environment_variables": {
                "POSTGRES_URI": bool(os.environ.get("POSTGRES_URI")),
                "SENTRY_DSN": bool(os.environ.get("SENTRY_DSN")),
                "AIVEN_REDIS_URI": bool(os.environ.get("AIVEN_REDIS_URI")),
            }
        }
    except Exception as e:
        logger.error(f"Error getting environment info: {e}", exc_info=True)
        return {"error": str(e)}


def log_performance_metrics(func_name: str, start_time: float, 
                           additional_info: Optional[dict] = None) -> None:
    """
    تسجيل مقاييس الأداء للدوال.
    
    Args:
        func_name: اسم الدالة
        start_time: وقت البداية
        additional_info: معلومات إضافية
    """
    try:
        import time
        execution_time = time.time() - start_time
        
        log_data = {
            "function": func_name,
            "execution_time_seconds": execution_time,
            "timestamp": time.time()
        }
        
        if additional_info:
            log_data.update(additional_info)
        
        if execution_time > 1.0:  # تسجيل الدوال البطيئة
            logger.warning(f"Slow function execution: {log_data}")
        else:
            logger.debug(f"Performance metrics: {log_data}")
            
    except Exception as e:
        logger.error(f"Error logging performance metrics: {e}", exc_info=True)
