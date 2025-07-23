import os
import streamlit as st
import pandas as pd
import plotly.express as px
import time
from dotenv import load_dotenv
import sentry_sdk
import logging
from pydantic import ValidationError
from datetime import datetime, timedelta
import pytz
from typing import Tuple

# استيراد المكونات
from utils import setup_logging, prepare_arabic_text, load_css, format_currency
from postgres_manager import PostgresDBManager
from treasury_core.ports import HistoricalDataStore
from treasury_core.calculations import calculate_primary_yield, analyze_secondary_sale
from treasury_core.models import PrimaryYieldInput, SecondarySaleInput
from cbe_scraper import CbeScraper, fetch_and_update_data
import constants as C

# تهيئة اللوجينج والتتبع
setup_logging(level=logging.WARNING)
load_dotenv()

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn, traces_sample_rate=1.0, environment="production-streamlit"
    )


@st.cache_resource
def get_db_manager() -> HistoricalDataStore:
    """تهيئة مدير قاعدة البيانات"""
    if os.environ.get("POSTGRES_URI"):
        logging.info("Using PostgresDBManager")
        return PostgresDBManager()
    else:
        from db_manager import SQLiteDBManager

        logging.warning("Falling back to SQLiteDBManager")
        return SQLiteDBManager()


def get_next_auction_date(today: datetime) -> Tuple[datetime, str]:
    """حساب تاريخ ومعلومات العطاء القادم"""
    days_to_thursday = (3 - today.weekday() + 7) % 7
    days_to_sunday = (6 - today.weekday() + 7) % 7

    next_thursday = today + timedelta(days=days_to_thursday)
    next_sunday = today + timedelta(days=days_to_sunday)

    return (
        (next_thursday, "الخميس")
        if next_thursday.date() < next_sunday.date()
        else (next_sunday, "الأحد")
    )


def format_countdown(time_delta: timedelta) -> str:
    """تنسيق الوقت المتبقي للعطاء القادم"""
    parts = []
    days = time_delta.days
    hours = time_delta.seconds // 3600
    minutes = (time_delta.seconds % 3600) // 60

    if days > 0:
        parts.append(f"{days} يوم")
    if hours > 0:
        parts.append(f"{hours} ساعة")
    if minutes > 0 and not parts:  # عرض الدقائق فقط إذا لم تكن هناك أيام أو ساعات
        parts.append(f"{minutes} دقيقة")

    return " و ".join(parts) if parts else "قريباً جداً"


def display_auction_results(
    title: str, info: str, df: pd.DataFrame, expected_tenors: list
):
    """عرض نتائج العطاءات بطريقة منظمة"""
    session_date_str = prepare_arabic_text("تاريخ غير محدد")
    filtered_df = pd.DataFrame()

    if not df.empty and C.TENOR_COLUMN_NAME in df.columns:
        filtered_df = df[df[C.TENOR_COLUMN_NAME].isin(expected_tenors)]
        if not filtered_df.empty:
            # استخدام أحدث تاريخ جلسة متوفر في البيانات المصفاة
            session_date_str = str(filtered_df[C.SESSION_DATE_COLUMN_NAME].iloc[0])

    st.markdown(
        f"<h3 style='text-align: center; color: #ffc107;'>{prepare_arabic_text(f'{title} - {session_date_str}')}</h3>",
        unsafe_allow_html=True,
    )

    info_with_note = f"{info}<br><small>للشراء يتطلب التواجد في البنك قبل الساعة 10 صباحًا في يوم العطاء.</small>"
    st.markdown(
        f"""<div style="text-align: center; padding: 0.75rem; background-color: rgba(38, 39, 48, 0.5); 
            border-radius: 0.5rem; border: 1px solid #3c4049; margin-top: 10px; margin-bottom: 20px;">
            🗓️ {prepare_arabic_text(info_with_note)}
            </div>""",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(expected_tenors))
    for i, tenor in enumerate(expected_tenors):
        with cols[i]:
            label = prepare_arabic_text(f"أجل {tenor} يوم")
            tenor_data = (
                filtered_df[filtered_df[C.TENOR_COLUMN_NAME] == tenor]
                if not filtered_df.empty
                else pd.DataFrame()
            )
            value = (
                f"{tenor_data[C.YIELD_COLUMN_NAME].iloc[0]:.3f}%"
                if not tenor_data.empty
                else prepare_arabic_text("غير متاح")
            )

            st.markdown(
                f"""<div style="background-color: #2c3e50; border: 1px solid #4a6fa5; border-radius: 5px; 
                    padding: 15px; text-align: center; height: 100%; display: flex; flex-direction: column; 
                    justify-content: center;">
                    <p style="font-size: 1.1rem; color: #bdc3c7; margin: 0 0 8px 0;">{label}</p>
                    <p style="font-size: 2rem; font-weight: 700; color: #ffffff; margin: 0;">{value}</p>
                    </div>""",
                unsafe_allow_html=True,
            )


def validate_and_calculate_primary(inputs: dict):
    """التحقق من صحة وحساب العائد الأساسي"""
    try:
        user_inputs = PrimaryYieldInput(**inputs)
        return calculate_primary_yield(user_inputs)
    except ValidationError as e:
        st.error(f"خطأ في المدخلات: {e.errors()[0]['msg']}")
        return None
    except Exception as e:
        st.error(f"حدث خطأ غير متوقع: {str(e)}")
        logging.exception("Error in primary yield calculation")
        return None


def validate_and_calculate_secondary(inputs: dict):
    """التحقق من صحة وحساب البيع الثانوي"""
    try:
        user_inputs = SecondarySaleInput(**inputs)
        return analyze_secondary_sale(user_inputs)
    except ValidationError as e:
        st.error(f"خطأ في المدخلات: {e.errors()[0]['msg']}")
        return None
    except Exception as e:
        st.error(f"حدث خطأ غير متوقع: {str(e)}")
        logging.exception("Error in secondary sale calculation")
        return None


def main():
    # تهيئة الصفحة
    st.set_page_config(
        layout="wide",
        page_title=prepare_arabic_text("حاسبة أذون الخزانة"),
        page_icon="🏦",
    )
    load_css(os.path.join(os.path.dirname(__file__), "css", "style.css"))

    # تهيئة حالة الجلسة
    if "update_successful" not in st.session_state:
        st.session_state.update_successful = False

    db_adapter = get_db_manager()
    scraper_adapter = CbeScraper()

    # --- START: تعديل منطق تحميل البيانات ---
    # تم تغيير هذا الجزء بالكامل لحل مشكلة الاستعلامات المتتالية
    if "historical_df" not in st.session_state:
        # الخطوة 1: استعلام واحد فقط لجلب كل البيانات التاريخية
        historical_data = db_adapter.load_all_historical_data()
        st.session_state.historical_df = historical_data

        # الخطوة 2: استنتاج أحدث البيانات ووقت التحديث من البيانات التي تم جلبها بالفعل
        if not historical_data.empty:
            # التأكد من أن عمود التاريخ من نوع datetime للقيام بالمقارنات
            historical_data[C.DATE_COLUMN_NAME] = pd.to_datetime(
                historical_data[C.DATE_COLUMN_NAME]
            )

            # استخلاص أحدث البيانات لكل أجل باستخدام Pandas
            latest_indices = historical_data.loc[
                historical_data.groupby(C.TENOR_COLUMN_NAME)[
                    C.DATE_COLUMN_NAME
                ].idxmax()
            ]
            st.session_state.df_data = latest_indices.reset_index(drop=True)

            # استخلاص آخر وقت تحديث من البيانات
            last_update_dt_utc = historical_data[C.DATE_COLUMN_NAME].max()
            cairo_tz = pytz.timezone(C.TIMEZONE)

            # التأكد من أن التوقيت معرف قبل تحويله
            if last_update_dt_utc.tzinfo is None:
                last_update_dt_utc = last_update_dt_utc.tz_localize("UTC")

            last_update_dt_cairo = last_update_dt_utc.astimezone(cairo_tz)
            last_update_date = last_update_dt_cairo.strftime("%Y-%m-%d")
            last_update_time = last_update_dt_cairo.strftime("%I:%M %p")
            st.session_state.last_update = (last_update_date, last_update_time)

        else:
            # التعامل مع حالة كون قاعدة البيانات فارغة
            st.session_state.df_data = pd.DataFrame()
            st.session_state.last_update = ("البيانات الأولية", None)

        # تهيئة باقي متغيرات الحالة
        st.session_state.primary_results = None
        st.session_state.secondary_results = None
    # --- END: تعديل منطق تحميل البيانات ---

    # استخراج البيانات من حالة الجلسة
    data_df = st.session_state.df_data
    historical_df = st.session_state.historical_df
    last_update_date, last_update_time = (
        st.session_state.last_update
        if st.session_state.last_update
        else ("البيانات الأولية", None)
    )

    # واجهة المستخدم الرئيسية
    st.markdown(
        f"""<div class="centered-header" style="background-color: #343a40; padding: 20px 10px; 
            border-radius: 15px; margin-bottom: 1rem;">
            <h1 style="color: #ffffff; margin: 0;">{prepare_arabic_text(C.APP_TITLE)}</h1>
            <p style="color: #aab8c2; margin-top: 10px;">{prepare_arabic_text(C.APP_HEADER)}</p>
            <div style="margin-top: 15px; font-size: 0.9rem; color: #adb5bd;">
                صُمم بواسطة <span style="font-weight: bold; color: #00bfff;">{C.AUTHOR_NAME}</span>
            </div>
            </div>""",
        unsafe_allow_html=True,
    )

    # قسم البيانات والعطاءات
    col1, col2 = st.columns([2, 1], gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("📊 أحدث العوائد المعتمدة")
            st.divider()
            display_auction_results(
                "عطاء الخميس", "آجال (6 أشهر و 12 شهر)", data_df, [182, 364]
            )
            st.divider()
            display_auction_results(
                "عطاء الأحد", "آجال (3 أشهر و 9 أشهر)", data_df, [91, 273]
            )
            st.divider()

    with col2:
        with st.container(border=True):
            st.subheader("📡 مركز البيانات")
            now_cairo = datetime.now(pytz.timezone(C.TIMEZONE))
            next_auction_dt, next_auction_day = get_next_auction_date(now_cairo)

            last_update_is_recent = False
            if last_update_date != "البيانات الأولية":
                try:
                    last_update_dt = datetime.strptime(
                        last_update_date, "%Y-%m-%d"
                    ).date()
                    if (now_cairo.date() - last_update_dt).days < 4:
                        last_update_is_recent = True
                except (ValueError, TypeError):
                    pass

            button_placeholder = st.empty()
            update_clicked = False

            if last_update_date == "البيانات الأولية":
                st.warning(
                    "البيانات أولية. يرجى التحديث للحصول على أحدث العوائد.", icon="⚠️"
                )
                update_clicked = button_placeholder.button(
                    "تحديث البيانات الآن 🔄", use_container_width=True, type="primary"
                )
            elif last_update_is_recent:
                st.success(
                    f"البيانات محدثة لآخر عطاء بتاريخ {last_update_date}", icon="✅"
                )
                button_placeholder.button(
                    "محدثة ✅", use_container_width=True, disabled=True
                )

                time_left = next_auction_dt - now_cairo
                countdown_str = format_countdown(time_left)
                st.info(
                    f"في انتظار بيانات عطاء يوم {next_auction_day} القادم. متبقٍ: {countdown_str}",
                    icon="⏳",
                )
            else:
                update_clicked = button_placeholder.button(
                    "محاولة التحديث على أي حال 🔄", use_container_width=True
                )

            if update_clicked:
                progress_bar = st.progress(0, text="...بدء عملية التحديث")
                status_text = st.empty()

                def progress_callback(status: str):
                    progress_map = {
                        "جاري جلب": 25,
                        "جاري التحقق": 60,
                        "جاري الحفظ": 85,
                        "اكتمل": 100,
                        "محدثة بالفعل": 100,
                    }
                    progress_value = next(
                        (v for k, v in progress_map.items() if k in status), 0
                    )
                    status_text.info(f"الحالة: {status}")
                    progress_bar.progress(progress_value, text=status)

                try:
                    updated = fetch_and_update_data(
                        data_source=scraper_adapter,
                        data_store=db_adapter,
                        status_callback=progress_callback,
                    )
                    if updated:
                        st.session_state.update_successful = True
                        st.success("✅ تم تحديث البيانات بنجاح!")
                    else:
                        st.info("ℹ️ البيانات محدثة بالفعل.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    logging.exception("فشل التحديث")
                    st.error("❌ فشل التحديث: تحقق من الاتصال أو سجل الأخطاء.")
                    if sentry_dsn:
                        sentry_sdk.capture_exception(e)
                    st.session_state.update_successful = False

            st.divider()
            st.markdown(
                f"<p style='text-align:center; font-size:0.9rem; color:#adb5bd;'>آخر فحص ناجح: {last_update_date} الساعة {last_update_time or 'N/A'}</p>",
                unsafe_allow_html=True,
            )
            st.link_button(
                "🔗 فتح موقع البنك المركزي", C.CBE_DATA_URL, use_container_width=True
            )

    st.divider()
    st.header(prepare_arabic_text(C.PRIMARY_CALCULATOR_TITLE))
    col_form_main, col_results_main = st.columns(2, gap="large")
    with col_form_main:
        with st.container(border=True):
            st.subheader(prepare_arabic_text("1. أدخل بيانات الاستثمار"), anchor=False)
            investment_amount_main = st.number_input(
                prepare_arabic_text("المبلغ المراد استثماره (القيمة الإسمية)"),
                min_value=C.MIN_T_BILL_AMOUNT,
                value=C.MIN_T_BILL_AMOUNT,
                step=C.T_BILL_AMOUNT_STEP,
            )
            options = (
                sorted(data_df[C.TENOR_COLUMN_NAME].unique())
                if not data_df.empty
                else [91, 182, 273, 364]
            )

            def get_yield_for_tenor(tenor):
                if not data_df.empty:
                    yield_row = data_df[data_df[C.TENOR_COLUMN_NAME] == tenor]
                    if not yield_row.empty:
                        return yield_row[C.YIELD_COLUMN_NAME].iloc[0]
                return 0.0

            formatted_options = [
                (
                    f"{t} {prepare_arabic_text('يوم')} - ({get_yield_for_tenor(t):.3f}%)"
                    if get_yield_for_tenor(t)
                    else f"{t} {prepare_arabic_text('يوم')}"
                )
                for t in options
            ]
            selected_option = st.selectbox(
                prepare_arabic_text("اختر مدة الاستحقاق"),
                formatted_options,
                key="main_tenor_formatted",
            )
            selected_tenor_main = (
                int(selected_option.split(" ")[0]) if selected_option else 0
            )
            tax_rate_main = st.number_input(
                prepare_arabic_text("نسبة الضريبة على الأرباح (%)"),
                min_value=0.0,
                max_value=100.0,
                value=C.DEFAULT_TAX_RATE_PERCENT,
                step=0.5,
                format="%.1f",
            )

            if st.button(
                prepare_arabic_text("احسب العائد الآن"),
                use_container_width=True,
                type="primary",
            ):
                yield_rate = get_yield_for_tenor(selected_tenor_main)
                if yield_rate > 0:
                    try:
                        user_inputs = PrimaryYieldInput(
                            face_value=investment_amount_main,
                            yield_rate=yield_rate,
                            tenor=selected_tenor_main,
                            tax_rate=tax_rate_main,
                        )
                        results = calculate_primary_yield(inputs=user_inputs)
                        st.session_state.primary_results = {
                            "results_obj": results,
                            "tenor": selected_tenor_main,
                            "tax_rate": tax_rate_main,
                        }
                    except ValidationError as e:
                        st.error(f"خطأ في المدخلات: {e}")
                        st.session_state.primary_results = None
                else:
                    st.session_state.primary_results = "error_no_data"

    with col_results_main:
        if st.session_state.primary_results:
            if st.session_state.primary_results == "error_no_data":
                with st.container(border=True):
                    st.error(
                        prepare_arabic_text(
                            "لا توجد بيانات للعائد. يرجى تحديث البيانات أولاً."
                        )
                    )
            else:
                primary_data = st.session_state.primary_results
                results = primary_data["results_obj"]
                with st.container(border=True):
                    st.subheader(
                        prepare_arabic_text(
                            f"✨ ملخص استثمارك لأجل {primary_data['tenor']} يوم"
                        ),
                        anchor=False,
                    )
                    st.markdown(
                        f"""<div style="text-align: center; margin-bottom: 20px;"><p style="font-size: 1.1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("النسبة الفعلية للربح (عن الفترة)")}</p><p style="font-size: 2.8rem; color: #ffc107; font-weight: 700; line-height: 1.2;">{results.real_profit_percentage:.3f}%</p></div>""",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""<div style="text-align: center; background-color: #495057; padding: 10px; border-radius: 10px; margin-bottom: 15px;"><p style="font-size: 1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("💰 صافي الربح المقدم")} </p><p style="font-size: 1.9rem; color: #28a745; font-weight: 600; line-height: 1.2;">{format_currency(results.net_return)}</p></div>""",
                        unsafe_allow_html=True,
                    )

                    final_amount = results.purchase_price + results.net_return
                    st.markdown(
                        f"""<div style="text-align: center; background-color: #212529; padding: 10px; border-radius: 10px; "><p style="font-size: 1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("المبلغ المسترد بعد الضريبة")}</p><p style="font-size: 1.9rem; color: #8ab4f8; font-weight: 600; line-height: 1.2;">{format_currency(final_amount)}</p></div>""",
                        unsafe_allow_html=True,
                    )
                    st.divider()

                    with st.expander(
                        prepare_arabic_text("عرض تفاصيل الحساب الكاملة"), expanded=False
                    ):
                        st.markdown(
                            f"""<div style="padding: 10px; border-radius: 10px; background-color: #212529;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px solid #495057;"><span style="font-size: 1.1rem;">{prepare_arabic_text("سعر الشراء الفعلي (المبلغ المستثمر)")}</span><span style="font-size: 1.2rem; font-weight: 600;">{format_currency(results.purchase_price)}</span></div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px solid #495057;"><span style="font-size: 1.1rem;">{prepare_arabic_text("العائد الإجمالي (قبل الضريبة)")}</span><span style="font-size: 1.2rem; font-weight: 600; color: #8ab4f8;">{format_currency(results.gross_return)}</span></div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px;"><span style="font-size: 1.1rem;">{prepare_arabic_text(f"قيمة الضريبة المستحقة ({primary_data['tax_rate']}%)")}</span><span style="font-size: 1.2rem; font-weight: 600; color: #dc3545;">{format_currency(results.tax_amount)}</span></div>
                                    </div>""",
                            unsafe_allow_html=True,
                        )

                        st.divider()

                    st.markdown(
                        "<div style='margin-top: 15px;'></div>", unsafe_allow_html=True
                    )
                    st.info(
                        prepare_arabic_text(
                            """**💡 آلية صرف العوائد والضريبة:**\n- **صافي الربح** يُضاف إلى حسابك مقدمًا في يوم الشراء (بعد خصم الضريبة مباشرة).\n- في نهاية المدة، تسترد **القيمة الإسمية الكاملة**.\n- تم بالفعل خصم الضريبة من الربح المقدم، لذا لا توجد خصومات مستقبلية متعلقة بهذا الإذن."""
                        ),
                        icon="💡",
                    )
        else:
            with st.container(border=True):
                st.info(
                    "✨ ستظهر نتائج الحساب هنا بعد إدخال البيانات والضغط على زر الحساب.",
                    icon="💡",
                )

    st.divider()
    st.header(prepare_arabic_text(C.SECONDARY_CALCULATOR_TITLE))
    col_secondary_form, col_secondary_results = st.columns(2, gap="large")
    with col_secondary_form:
        with st.container(border=True):
            st.subheader(
                prepare_arabic_text("1. أدخل بيانات الإذن الأصلي"), anchor=False
            )
            face_value_secondary = st.number_input(
                prepare_arabic_text("القيمة الإسمية للإذن"),
                min_value=C.MIN_T_BILL_AMOUNT,
                value=C.MIN_T_BILL_AMOUNT,
                step=C.T_BILL_AMOUNT_STEP,
                key="secondary_face_value",
            )
            original_yield_secondary = st.number_input(
                prepare_arabic_text("عائد الشراء الأصلي (%)"),
                min_value=1.0,
                value=29.0,
                step=0.1,
                key="secondary_original_yield",
                format="%.3f",
            )
            original_tenor_secondary = st.selectbox(
                prepare_arabic_text("أجل الإذن الأصلي (بالأيام)"),
                options,
                key="secondary_tenor",
            )
            tax_rate_secondary = st.number_input(
                prepare_arabic_text("نسبة الضريبة على الأرباح (%)"),
                min_value=0.0,
                max_value=100.0,
                value=C.DEFAULT_TAX_RATE_PERCENT,
                step=0.5,
                format="%.1f",
                key="secondary_tax",
            )
            st.subheader(prepare_arabic_text("2. أدخل تفاصيل البيع"), anchor=False)
            max_holding_days = (
                int(original_tenor_secondary) - 1 if original_tenor_secondary > 1 else 1
            )
            early_sale_days_secondary = st.number_input(
                prepare_arabic_text("أيام الاحتفاظ الفعلية (قبل البيع)"),
                min_value=1,
                value=min(60, max_holding_days),
                max_value=max_holding_days,
                step=1,
            )
            secondary_market_yield = st.number_input(
                prepare_arabic_text("العائد السائد في السوق للمشتري (%)"),
                min_value=1.0,
                value=30.0,
                step=0.1,
                format="%.3f",
            )
            if st.button(
                prepare_arabic_text("حلل سعر البيع الثانوي"),
                use_container_width=True,
                type="primary",
                key="secondary_calc",
            ):
                try:
                    user_inputs = SecondarySaleInput(
                        face_value=face_value_secondary,
                        original_yield=original_yield_secondary,
                        original_tenor=original_tenor_secondary,
                        holding_days=early_sale_days_secondary,
                        secondary_yield=secondary_market_yield,
                        tax_rate=tax_rate_secondary,
                    )
                    results = analyze_secondary_sale(inputs=user_inputs)
                    st.session_state.secondary_results = {
                        "results_obj": results,
                        "tax_rate": tax_rate_secondary,
                    }
                except (ValidationError, ValueError) as e:
                    st.error(f"خطأ في المدخلات: {e}")
                    st.session_state.secondary_results = None
    with col_secondary_results:
        if st.session_state.secondary_results:
            secondary_data = st.session_state.secondary_results
            results = secondary_data["results_obj"]
            with st.container(border=True):
                st.subheader(
                    prepare_arabic_text("✨ تحليل سعر البيع الثانوي"), anchor=False
                )
                if results.net_profit >= 0:
                    st.success(
                        f"البيع الآن يعتبر مربحًا. ستحقق ربحًا صافيًا قدره {format_currency(results.net_profit)}.",
                        icon="✅",
                    )
                else:
                    st.warning(
                        f"البيع الآن سيحقق خسارة. ستبلغ خسارتك الصافية {format_currency(abs(results.net_profit))}.",
                        icon="⚠️",
                    )
                st.divider()
                profit_color = "#0ac135" if results.net_profit >= 0 else "#db2b3c"
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f"""<div style="text-align: center; background-color: #495057; padding: 10px; border-radius: 10px; height: 100%;"><p style="font-size: 1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("🏷️ سعر البيع الفعلي")}</p><p style="font-size: 1.9rem; color: #8ab4f8; font-weight: 600; line-height: 1.2;">{format_currency(results.sale_price)}</p></div>""",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f"""<div style="text-align: center; background-color: #495057; padding: 10px; border-radius: 10px; height: 100%;"><p style="font-size: 1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("💰 صافي الربح / الخسارة")}</p><p style="font-size: 1.9rem; color: {profit_color}; font-weight: 600; line-height: 1.2;">{format_currency(results.net_profit)}</p><p style="font-size: 1rem; color: {profit_color}; margin-top: -5px;">({results.period_yield:.2f}% {prepare_arabic_text("عن فترة الاحتفاظ")})</p></div>""",
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    "<div style='margin-top: 15px;'></div>", unsafe_allow_html=True
                )
                with st.expander(prepare_arabic_text("عرض تفاصيل الحساب")):
                    st.markdown(
                        f"""<div style="padding: 10px; border-radius: 10px; background-color: #212529;"><div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px solid #495057;"><span style="font-size: 1.1rem;">{prepare_arabic_text("سعر الشراء الأصلي")}</span><span style="font-size: 1.2rem; font-weight: 600;">{format_currency(results.original_purchase_price)}</span></div><div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px solid #495057;"><span style="font-size: 1.1rem;">{prepare_arabic_text("إجمالي الربح (قبل الضريبة)")}</span><span style="font-size: 1.2rem; font-weight: 600; color: {'#28a745' if results.gross_profit >= 0 else '#dc3545'};">{format_currency(results.gross_profit)}</span></div><div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 5px;"><span style="font-size: 1.1rem;">{prepare_arabic_text(f"قيمة الضريبة ({secondary_data['tax_rate']}%)")}</span><span style="font-size: 1.2rem; font-weight: 600; color: #dc3545;">-{format_currency(results.tax_amount, currency_symbol='')}</span></div></div>""",
                        unsafe_allow_html=True,
                    )

                    st.divider()

        else:
            with st.container(border=True):
                st.info("📊 ستظهر نتائج تحليل البيع هنا.", icon="💡")

    st.divider()
    st.header(prepare_arabic_text("📈 تطور العائد تاريخيًا"))

    if not historical_df.empty:
        available_tenors = sorted(historical_df[C.TENOR_COLUMN_NAME].unique())
        selected_tenors = st.multiselect(
            label=prepare_arabic_text("اختر الآجال التي تريد عرضها:"),
            options=available_tenors,
            default=available_tenors,
            label_visibility="collapsed",
        )
        if selected_tenors:
            chart_df = historical_df[
                historical_df[C.TENOR_COLUMN_NAME].isin(selected_tenors)
            ]
            fig = px.line(
                chart_df,
                x=C.DATE_COLUMN_NAME,
                y=C.YIELD_COLUMN_NAME,
                color=C.TENOR_COLUMN_NAME,
                markers=True,
                labels={
                    C.DATE_COLUMN_NAME: "تاريخ التحديث",
                    C.YIELD_COLUMN_NAME: "نسبة العائد (%)",
                    C.TENOR_COLUMN_NAME: "الأجل (يوم)",
                },
                title=prepare_arabic_text(
                    "التغير في متوسط العائد المرجح لأذون الخزانة"
                ),
            )
            fig.update_layout(
                legend_title_text=prepare_arabic_text("الأجل"),
                title_x=0.5,
                template="plotly_dark",
                xaxis=dict(tickformat="%d-%m-%Y"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                prepare_arabic_text(
                    "يرجى اختيار أجل واحد على الأقل لعرض الرسم البياني."
                )
            )
    else:
        st.info(
            prepare_arabic_text(
                "لا توجد بيانات تاريخية كافية لعرض الرسم البياني. قم بتحديث البيانات عدة مرات على مدار أيام مختلفة."
            )
        )

    st.divider()
    with st.expander(prepare_arabic_text(C.HELP_TITLE)):
        st.markdown(
            prepare_arabic_text(
                """
        #### **ما الفرق بين "العائد" و "الفائدة"؟**
        - **الفائدة (Interest):** تُحسب على أصل المبلغ وتُضاف إليه دورياً (مثل شهادات الادخار).
        - **العائد (Yield):** في أذون الخزانة، أنت تشتري الإذن بسعر **أقل** من قيمته الإسمية، وربحك هو الفارق الذي ستحصل عليه في نهاية المدة.
        ---
        #### **كيف تعمل حاسبة العائد الأساسية؟**
        1.  **حساب سعر الشراء:** `سعر الشراء = القيمة الإسمية ÷ (1 + (العائد ÷ 100) × (مدة الإذن ÷ 365))`
        2.  **حساب إجمالي الربح:** `إجمالي الربح = القيمة الإسمية - سعر الشراء`
        3.  **حساب الضريبة:** `إجمالي الربح × (نسبة الضريبة ÷ 100)`
        4.  **حساب صافي الربح:** `إجمالي الربح - قيمة الضريبة`
        ---
        #### **كيف تعمل حاسبة البيع في السوق الثانوي؟**
        هذه الحاسبة تجيب على سؤال: "كم سيكون ربحي أو خسارتي إذا بعت الإذن اليوم قبل تاريخ استحقاقه؟". سعر البيع هنا لا يعتمد على سعر شرائك، بل على سعر الفائدة **الحالي** في السوق.
        1.  **حساب سعر شرائك الأصلي:** بنفس طريقة الحاسبة الأساسية.
        2.  **حساب سعر البيع اليوم:** `الأيام المتبقية = الأجل الأصلي - أيام الاحتفاظ`، `سعر البيع = القيمة الإسمية ÷ (1 + (العائد السائد اليوم ÷ 100) × (الأيام المتبقية ÷ 365))`
        3.  **النتيجة النهائية:** `الربح أو الخسارة = سعر البيع - سعر الشراء الأصلي`. يتم حساب الضريبة على هذا الربح إذا كان موجباً.
        """
            )
        )
        st.markdown("---")
        st.subheader(prepare_arabic_text("تقدير رسوم أمين الحفظ"))
        st.markdown(
            prepare_arabic_text(
                """
        تحتفظ البنوك بأذون الخزانة الخاصة بك مقابل رسوم خدمة دورية. تُحسب هذه الرسوم كنسبة مئوية **سنوية** من **القيمة الإسمية** الإجمالية لأذونك، ولكنها تُخصم من حسابك بشكل **ربع سنوي** (كل 3 أشهر).

        تختلف هذه النسبة من بنك لآخر (عادة ما تكون حوالي 0.1% سنوياً). أدخل بياناتك أدناه لتقدير قيمة الخصم الربع سنوي المتوقع.
        """
            )
        )

        fee_col1, fee_col2 = st.columns(2)
        with fee_col1:
            total_face_value = st.number_input(
                prepare_arabic_text("إجمالي القيمة الإسمية لكل أذونك"),
                min_value=C.MIN_T_BILL_AMOUNT,
                value=100000.0,
                step=C.T_BILL_AMOUNT_STEP,
                key="fee_calc_total",
            )
        with fee_col2:
            fee_percentage = st.number_input(
                prepare_arabic_text("نسبة رسوم الحفظ السنوية (%)"),
                min_value=0.0,
                value=0.10,
                step=0.01,
                format="%.2f",
                key="fee_calc_perc",
            )

        annual_fee = total_face_value * (fee_percentage / 100.0)
        quarterly_deduction = annual_fee / 4

        st.markdown(
            f"""<div style='text-align: center; background-color: #212529; padding: 10px; border-radius: 10px; margin-top:10px;'><p style="font-size: 1rem; color: #adb5bd; margin-bottom: 0px;">{prepare_arabic_text("الخصم الربع سنوي التقريبي")}</p><p style="font-size: 1.5rem; color: #ffc107; font-weight: 600; line-height: 1.2;">{format_currency(quarterly_deduction)}</p></div>""",
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown(
            prepare_arabic_text(
                "\n\n***إخلاء مسؤولية:*** *هذا التطبيق هو أداة استرشادية فقط. للحصول على أرقام نهائية ودقيقة، يرجى الرجوع إلى البنك أو المؤسسة المالية التي تتعامل معها.*"
            )
        )


if __name__ == "__main__":
    main()
