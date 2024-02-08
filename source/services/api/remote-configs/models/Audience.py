"""
This module contains Audience class.
"""

import contextlib
from typing import Any, List

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

# Warning : packaging is used by eval()
from packaging.version import Version  # pylint: disable = unused-import

from utils import constants


class Audience:
    """
    This class represents an audience.
    """

    def __init__(self, audience_name: str):
        self.__audience_name = audience_name

    @staticmethod
    def developer_audiences(
        dynamodb: DynamoDBServiceResource, user_data: dict[str, Any]
    ) -> List["Audience"]:
        """
        This static method returns a list of all property_based Audiences for uid.
        """
        response = dynamodb.Table(constants.AUDIENCES_TABLE).query(
            IndexName="type-index",
            KeyConditionExpression=Key("type").eq("developer"),
        )
        return Audience.__extract_audience_from_condition(response["Items"], user_data)

    @staticmethod
    def event_based_audiences(
        dynamodb: DynamoDBServiceResource, uid: str
    ) -> List["Audience"]:
        """
        This static method returns a list of all event_based Audiences for uid.
        """
        response = dynamodb.Table(constants.USERS_AUDIENCES_TABLE).query(
            IndexName="uid-index",
            KeyConditionExpression=Key("uid").eq(uid),
        )

        return [Audience(item["audience_name"]) for item in response["Items"]]

    @staticmethod
    def property_based_audiences(
        dynamodb: DynamoDBServiceResource, user_data: dict[str, Any]
    ) -> List["Audience"]:
        """
        This static method returns a list of all property_based Audiences for uid.
        """
        response = dynamodb.Table(constants.AUDIENCES_TABLE).query(
            IndexName="type-index",
            KeyConditionExpression=Key("type").eq("property_based"),
        )

        return Audience.__extract_audience_from_condition(response["Items"], user_data)

    @property
    def audience_name(self) -> str:
        """
        This property returns audience_name.
        """
        return self.__audience_name

    @staticmethod
    def __extract_audience_from_condition(
        items: list[dict[str, Any]], user_data: dict[str, Any]
    ):
        audiences = []
        for item in items:
            expression: str = item["condition"]

            for parameter_name, parameter_value in user_data.items():
                expression = expression.replace(parameter_name, f"'{parameter_value}'")

            with contextlib.suppress(NameError):
                # eval() raises NameError if parameter in expression not in user_data
                if eval(expression) is True:  # pylint: disable=eval-used
                    audiences.append(Audience(item["audience_name"]))

        return audiences
