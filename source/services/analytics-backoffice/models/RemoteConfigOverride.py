"""
This module contains RemoteConfigOverride class.
"""
from decimal import Decimal
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
        return [RemoteConfigOverride(database, item) for item in response["Items"]]

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
            item["audience_name"]: RemoteConfigOverride(database, item)
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

    def update_database(self):
        """
        This method updates RemoteConfigOverride to database.
        """
        item = {
            "remote_config_name": self.remote_config_name,
            "audience_name": self.audience_name,
            "active": self.active,
            "override_type": self.override_type,
        }

        match self.override_type:
            case "abtest":
                item["abtest_value"] = self.abtest_value
            case "fixed":
                item["fixed_value"] = self.fixed_value

        self.__database.Table(constants.TABLE_REMOTE_CONFIGS_OVERRIDES).put_item(
            Item=item
        )

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
        audience_name = data.pop("audience_name")
        override_type = data.pop("override_type")
        remote_config_name = data.pop("remote_config_name")

        audience = Audience.from_database(self.__database, audience_name)

        assert isinstance(active, int), "`active` should be int"
        assert (
            isinstance(audience_name, str) and audience_name != ""
        ), "`audience_name` should be a non-empty string"
        assert (
            audience_name == "ALL" or audience and not audience.deleted
        ), f"`audience_name` {audience_name} not exists"
        assert (
            override_type in self.__override_types
        ), f"`override_type` should be in : {self.__override_types}"

        match override_type:
            case "abtest":
                abtest_value = data.pop("abtest_value")
                assert isinstance(abtest_value, dict), "`abtest_value` should be dict"
                ABTest(abtest_value)
            case "fixed":
                fixed_value = data.pop("fixed_value")
                assert (
                    isinstance(fixed_value, str) and override_type != ""
                ), "`fixed_value` should be non-empty string"

        assert remote_config_name and isinstance(
            audience_name, str
        ), "`remote_config_name` should be a non-empty string"

        data.pop("override_value", None)
        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
