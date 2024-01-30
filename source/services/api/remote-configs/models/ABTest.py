"""
This module contains ABTest class.
"""
from typing import Any


class ABTest:
    """
    This class represents an ABTest.
    """

    def __init__(
        self, remote_config_name: str, audience_name: str, data: dict[str, Any]
    ):
        self.__data = data
        self.__ID = f"{remote_config_name}-{audience_name}"

    @property
    def ID(self) -> str:
        """
        This property returns ABTest ID.
        It's the concatenation of remote_config_name and audience_name.
        """
        return self.__ID

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
