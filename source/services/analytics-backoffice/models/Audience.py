"""
This module contains Audience class.
"""

from typing import Any, List

from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from utils import constants


class Audience:
    """
    This class represents an Audience.
    """

    __types = ("developer", "event_based", "property_based")

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
        response = database.Table(constants.TABLE_AUDIENCES).scan()
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
    def created_by(self) -> str:
        """
        This method returns created_by.
        """
        return self.__data["created_by"]

    @property
    def type(self) -> str:
        """
        This method returns type.
        """
        return self.__data["type"]

    def delete(self):
        """
        This method deletes audience from database.
        """
        self.__database.Table(constants.TABLE_AUDIENCES).delete_item(
            Key={"audience_name": self.audience_name}
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
                "created_by": self.created_by,
                "type": self.type,
            }
        )

    def __assert_data(self, data: dict[str, Any]):
        data = data.copy()
        audience_name = data.pop("audience_name")
        condition = data.pop("condition")
        created_by = data.pop("created_by")
        audience_type = data.pop("type")

        assert (
            isinstance(audience_name, str) and audience_name != ""
        ), "`audience_name` should be non-empty string"
        assert (
            isinstance(condition, str) and audience_name != ""
        ), "`condition_value` should be non-empty string"
        assert isinstance(created_by, str), "`created_by` should be non-empty string"
        assert audience_type in self.__types, f"`type` should be in {self.__types}"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
