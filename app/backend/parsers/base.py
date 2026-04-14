"""Base parser interface."""
from abc import ABC, abstractmethod
import pandas as pd


class BaseParser(ABC):
    """All bank parsers implement this interface."""

    @abstractmethod
    def parse(self, text: str) -> pd.DataFrame:
        """
        Parse extracted PDF text into a normalised DataFrame with columns:
            Date (datetime), Description (str), Amount (float), Balance (float)
        """
