"""
This module contains ABTest class.
"""

from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key

from FlaskApp import current_app
from utils import constants


class ABTest:
    """
    This class represents an ABTest.
    """

    def __init__(self, data: dict[str, Any]):
        self.__assert_data(data)

    @staticmethod
    def purge_users_abtests(remote_config_name: str, audience_name: str):
        """
        This method purges all UsersABTests links to <remote_config_name> and <audience_name>.
        """
        # table = current_app.database.Table(constants.TABLE_USERS_ABTESTS)
        response = ABTest.__table_users_abtests().query(
            IndexName="abtest_ID-index",
            KeyConditionExpression=Key("abtest_ID").eq(
                f"{remote_config_name}-{audience_name}"
            ),
        )

        with ABTest.__table_users_abtests().batch_writer() as batch:
            for item in response["Items"]:
                batch.delete_item(
                    Key={"uid": item["uid"], "abtest_ID": item["abtest_ID"]}
                )

    def __assert_data(self, data: dict[str, Any]):
        to_assert = data.copy()
        target_user_percent = to_assert.pop("target_user_percent")
        variants = to_assert.pop("variants")

        if isinstance(target_user_percent, Decimal):
            target_user_percent = int(target_user_percent)
            data["target_user_percent"] = target_user_percent

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

    @staticmethod
    def __table_users_abtests():
        return current_app.database.Table(constants.TABLE_USERS_ABTESTS)
