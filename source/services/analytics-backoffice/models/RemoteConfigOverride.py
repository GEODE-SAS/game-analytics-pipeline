"""
This module contains RemoteConfigOverride class.
"""
from decimal import Decimal
from typing import Any

from models.ABTest import ABTest


class RemoteConfigOverride:
    """
    This class represents a RemoteConfigOverride.
    """

    __override_types = ("abtest", "fixed")

    def __init__(self, data: dict[str, Any]):
        self.__assert_data(data)
        self.__data = data

    @property
    def abtest_value(self) -> dict[str, Any] | None:
        """
        This property returns abtest_value.
        """
        return self.__data.get("abtest_value")

    @property
    def active(self) -> int:
        """
        This property returns 1 if RemoteConfigOverride is activated else 0.
        """
        return self.__data["active"]

    @property
    def audience_name(self) -> str:
        """
        This property returns audience_name.
        """
        return self.__data["audience_name"]

    @property
    def fixed_value(self) -> str | None:
        """
        This property returns fixed_value.
        """
        return self.__data.get("fixed_value")

    @property
    def override_type(self) -> str:
        """
        This property returns override_type.
        """
        return self.__data["override_type"]

    @property
    def remote_config_name(self) -> str:
        """
        This property returns remote_config_name.
        """
        return self.__data["remote_config_name"]

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the RemoteConfigOverride.
        """
        return self.__data

    def __assert_data(self, data: dict[str, Any]):
        active = data.get("active")
        if isinstance(active, bool):
            # The field comes from payload
            data["active"] = 1 if active else 0
        elif isinstance(active, Decimal):
            # The field comes from database
            data["active"] = int(active)

        data = data.copy()
        active = data.pop("active")
        override_type = data.pop("override_type")

        assert isinstance(active, int), "`active` should be int"
        assert (
            override_type in self.__override_types
        ), f"`override_type` should be in : {self.__override_types}"

        match override_type:
            case "abtest":
                abtest_value = data.pop("abtest_value")
                assert isinstance(abtest_value, dict), "`abtest_value` should be dict"
                ABTest(abtest_value)  # There is an assertion
            case "fixed":
                fixed_value = data.pop("fixed_value")
                assert (
                    isinstance(fixed_value, str) and override_type != ""
                ), "`fixed_value` should be non-empty string"

        data.pop("override_value", None)
        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
