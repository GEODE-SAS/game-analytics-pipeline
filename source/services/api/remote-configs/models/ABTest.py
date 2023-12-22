"""
This module contains ABTest class.
"""
from typing import Any


class ABTest:
    """
    This class represents an ABTest.
    """

    def __init__(self, data: dict[str, Any]):
        self.__data = data

    @property
    def abtest_name(self) -> str:
        """
        This property returns abtest_name.
        """
        return self.__data["abtest_name"]

    @property
    def target_user_percent(self) -> int:
        """
        This property returns target_user_percent.
        """
        return self.__data["target_user_percent"]

    @property
    def variants(self) -> list[str]:
        """
        This property returns variants.
        """
        return self.__data["variants"]
