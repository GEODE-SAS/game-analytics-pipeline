"""
This module contains ABTest class.
"""
from decimal import Decimal
from typing import Any


class ABTest:
    """
    This class represents an ABTest.
    """

    def __init__(self, data: dict[str, Any]):
        self.__assert_data(data)

    def __assert_data(self, data: dict[str, Any]):
        to_assert = data.copy()
        abtest_name = to_assert.pop("abtest_name")
        target_user_percent = to_assert.pop("target_user_percent")
        variants = to_assert.pop("variants")

        if isinstance(target_user_percent, Decimal):
            target_user_percent = int(target_user_percent)
            data["target_user_percent"] = target_user_percent

        assert (
            isinstance(abtest_name, str) and abtest_name != ""
        ), "`abtest_name` should be non-empty string"
        assert (
            isinstance(target_user_percent, int) and 0 <= target_user_percent <= 100
        ), "`target_user_percent` should be integer between 0 and 100"
        assert (
            isinstance(variants, list) and len(variants) > 0
        ), "`variants` should be a non-empty list of strings"
        for variant in variants:
            assert (
                isinstance(variant, str) and variant != ""
            ), "`variants` should be a non-empty list of non-empty strings"

        assert len(to_assert) == 0, f"Unexpected fields -> {to_assert.keys()}"
