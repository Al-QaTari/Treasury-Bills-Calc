# treasury_core/ports.py
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import pandas as pd


class YieldDataSource(ABC):
    """منفذ يمثل أي مصدر يمكنه جلب أحدث بيانات العوائد."""

    @abstractmethod
    def get_latest_yields(self) -> Optional[pd.DataFrame]:
        """
        يجلب أحدث بيانات العوائد.
        """
        pass


class HistoricalDataStore(ABC):
    """منفذ يمثل أي مكان يمكن فيه تخزين وتحميل بيانات العوائد."""

    @abstractmethod
    def save_data(self, df: pd.DataFrame) -> None:
        """
        يحفظ بيانات العوائد الجديدة.
        """
        pass

    @abstractmethod
    def load_latest_data(
        self,
    ) -> Tuple[pd.DataFrame, Tuple[Optional[str], Optional[str]]]:
        """
        يقوم بتحميل أحدث البيانات المتاحة لكل أجل.
        """
        pass

    @abstractmethod
    def load_all_historical_data(self) -> pd.DataFrame:
        """
        يقوم بتحميل جميع البيانات التاريخية.
        """
        pass

    @abstractmethod
    def get_latest_session_date(self) -> Optional[str]:
        """
        يجلب أحدث تاريخ جلسة مسجل في قاعدة البيانات.
        """
        pass
