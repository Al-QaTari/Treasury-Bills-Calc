import os
import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def prepare_arabic_text(text: str) -> str:
    try:
        return str(text)
    except Exception:
        logger.error(f"Could not convert text to string: {text}", exc_info=True)
        return ""


def load_css(file_path: str) -> None:
    if os.path.exists(file_path):
        logger.debug(f"Loading CSS from {file_path}")
        with open(file_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        logger.warning(f"CSS file not found at path: {file_path}")


def setup_logging(level: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[logging.StreamHandler()],
        )
        logger.info("Logging configured successfully.")


def format_currency(value: Optional[float], currency_symbol: str = "جنيه") -> str:
    if value is None:
        logger.debug("Formatting a None value to default currency string.")
        return f"- {prepare_arabic_text(currency_symbol)}"
    try:
        sign = "-" if value < 0 else ""
        return f"{sign}{abs(value):,.2f} {prepare_arabic_text(currency_symbol)}"
    except (ValueError, TypeError):
        logger.error(f"Could not format value '{value}' as currency.", exc_info=True)
        return str(value)
