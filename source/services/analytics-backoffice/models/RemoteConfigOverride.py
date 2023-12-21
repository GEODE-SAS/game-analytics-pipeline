"""
This module contains RemoteConfigOverride class.
"""
from typing import Any, List

from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from models.ABTest import ABTest
from models.Audience import Audience
from utils import constants


class RemoteConfigOverride:
    """
    This class represents a RemoteConfigOverride.
    """

    __override_types = ("abtest", "fixed")

    def __init__(self, database: DynamoDBServiceResource, data: dict[str, Any]):
        self.__database = database
        self.__assert_data(data)
        self.__data = data

    @staticmethod
    def from_audience_name(
        database: DynamoDBServiceResource, audience_name: str
    ) -> List["RemoteConfigOverride"]:
        """
        This method returns a list of RemoteConfigOverride that have <audience_name>.
        """
        response = database.Table(constants.TABLE_REMOTE_CONFIGS_OVERRIDES).query(
            IndexName="audience_name-index",
            KeyConditionExpression=Key("audience_name").eq(audience_name),
        )
        return [
            RemoteConfigOverride(
                database, item | {"activated": item.pop("active") == 1}
            )
            for item in response["Items"]
        ]

    @staticmethod
    def from_remote_config_name(
        database: DynamoDBServiceResource, remote_config_name: str
    ) -> dict[str, "RemoteConfigOverride"]:
        """
        This method returns a dict of RemoteConfigOverride that have <remote_config_name>.
        """
        response = database.Table(constants.TABLE_REMOTE_CONFIGS_OVERRIDES).query(
            IndexName="remote_config_name-index",
            KeyConditionExpression=Key("remote_config_name").eq(remote_config_name),
        )
        return {
            item["audience_name"]: RemoteConfigOverride(
                database, item | {"activated": item.pop("active") == 1}
            )
            for item in response["Items"]
        }

    @staticmethod
    def purge(database: DynamoDBServiceResource, remote_config_name: str):
        """
        This method purges all overrides from remote_config_name.
        """
        overrides = RemoteConfigOverride.from_remote_config_name(
            database, remote_config_name
        )
        table = database.Table(constants.TABLE_REMOTE_CONFIGS_OVERRIDES)

        with table.batch_writer() as batch_writer:
            for override in overrides.values():
                batch_writer.delete_item(
                    Key={
                        "remote_config_name": remote_config_name,
                        "audience_name": override.audience_name,
                    }
                )

    @property
    def activated(self) -> bool:
        """
        This property returns True if RemoteConfigOverride is activated else False.
        """
        return self.__data["activated"]

    @property
    def audience_name(self) -> str:
        """
        This property returns audience_name.
        """
        return self.__data["audience_name"]

    @property
    def override_type(self) -> str:
        """
        This property returns override_type.
        """
        return self.__data["override_type"]

    @property
    def override_value(self) -> Any:
        """
        This property returns override_value.
        """
        return self.__data["override_value"]

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

    def update_database(self):
        """
        This method updates RemoteConfigOverride to database.
        """
        self.__database.Table(constants.TABLE_REMOTE_CONFIGS_OVERRIDES).put_item(
            Item={
                "remote_config_name": self.remote_config_name,
                "audience_name": self.audience_name,
                "active": 1 if self.activated else 0,
                "override_type": self.override_type,
                "override_value": self.override_value,
            }
        )

    def __assert_data(self, data: dict[str, Any]):
        data = data.copy()
        activated = data.pop("activated")
        audience_name = data.pop("audience_name")
        override_type = data.pop("override_type")
        override_value = data.pop("override_value")
        remote_config_name = data.pop("remote_config_name")

        audience = Audience.from_database(self.__database, audience_name)

        assert isinstance(activated, bool), "`activated` should be bool"
        assert (
            isinstance(audience_name, str) and audience_name != ""
        ), "`audience_name` should be a non-empty string"
        assert (
            audience_name == "ALL" or audience and not audience.deleted
        ), f"`audience_name` {audience_name} not exists"
        assert (
            override_type in self.__override_types
        ), f"`override_type` should be in : {self.__override_types}"

        if override_type == "abtest":
            assert isinstance(override_value, dict), "`override_value` should be dict"
            ABTest(override_value)
        else:
            # override_type == "fixed"
            assert (
                isinstance(override_value, str) and override_type != ""
            ), "`override_value` should be non-empty string"

        assert remote_config_name and isinstance(
            audience_name, str
        ), "`remote_config_name` should be a non-empty string"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
