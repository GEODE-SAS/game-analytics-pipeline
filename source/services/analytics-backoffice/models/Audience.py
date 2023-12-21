"""
This module contains Audience class.
"""
from typing import Any, List

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from utils import constants


class Audience:
    """
    This class represents an Audience.
    """

    __types = ("event_based", "property_based")

    def __init__(self, database: DynamoDBServiceResource, data: dict[str, Any]):
        self.__database = database
        self.__assert_data(data)
        self.__data = data

    @classmethod
    def from_database(cls, database: DynamoDBServiceResource, audience_name: str):
        """
        This method creates an instance of Audience from audience_name by fetching database.
        It returns None if there is no Audience with this audience_name.
        """
        response = database.Table(constants.TABLE_AUDIENCES).get_item(
            Key={"audience_name": audience_name}
        )
        if item := response.get("Item"):
            return cls(database, item)

    @staticmethod
    def get_all(database: DynamoDBServiceResource) -> List["Audience"]:
        """
        This static method returns all audiences.
        """
        response = database.Table(constants.TABLE_AUDIENCES).query(
            IndexName="deleted-index", KeyConditionExpression=Key("deleted").eq(0)
        )
        return [Audience(database, item) for item in response["Items"]]

    @property
    def audience_name(self) -> str:
        """
        This method returns audience_name.
        """
        return self.__data["audience_name"]

    @property
    def condition(self) -> str:
        """
        This method returns condition.
        """
        return self.__data["condition"]

    @property
    def deleted(self) -> bool:
        """
        This method returns True if Audience is soft deleted, else False.
        """
        return self.__data["deleted"]

    @property
    def description(self) -> str:
        """
        This method returns description.
        """
        return self.__data["description"]

    @property
    def type(self) -> str:
        """
        This method returns type.
        """
        return self.__data["type"]

    def soft_delete(self):
        """
        This method soft deletes audience from database.
        """
        self.__database.Table(constants.TABLE_AUDIENCES).update_item(
            Key={"audience_name": self.audience_name},
            AttributeUpdates={
                "deleted": {"Value": 1, "Action": "PUT"},
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the Audience.
        """
        return self.__data

    def update_database(self):
        """
        This method updates RemoteConfigCondition to database.
        """
        self.__database.Table(constants.TABLE_AUDIENCES).put_item(
            Item={
                "audience_name": self.audience_name,
                "condition": self.condition,
                "deleted": 0,
                "description": self.description,
                "type": self.type,
            }
        )

    def __assert_data(self, data: dict[str, Any]):
        data = data.copy()
        data.pop("deleted", None)
        audience_name = data.pop("audience_name")
        condition = data.pop("condition")
        description = data.pop("description")
        audience_type = data.pop("type")

        assert (
            isinstance(audience_name, str) and audience_name != ""
        ), "`audience_name` should be non-empty string"
        assert (
            isinstance(condition, str) and audience_name != ""
        ), "`condition_value` should be non-empty string"
        assert isinstance(description, str), "`description` should be string"
        assert audience_type in self.__types, f"`type` should be in {self.__types}"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
