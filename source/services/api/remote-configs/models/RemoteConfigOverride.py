"""
This module contains RemoteConfigOverride class.
"""
from typing import Any


class RemoteConfigOverride:
    """
    This class represents a remote config override.
    """

    def __init__(self, data: dict[str, Any]):
        self.__data = data

    @property
    def abtest_value(self) -> dict[str, Any] | None:
        """
        This property returns abtest_value.
        """
        return self.__data.get("abtest_value")

    @property
    def active(self) -> bool:
        """
        This property returns True if Override is active, else False.
        """
        return int(self.__data["active"]) == 1

    @property
    def fixed_value(self) -> str | None:
        """
        This property returns fixed_value.
        """
        return self.__data.get("fixed_value")

    @property
    def override_type(self) -> str:
        """
        This property retus override_type.
        """
        return self.__data["override_type"]
