"""
This module contains RemoteConfig class.
"""
from typing import Any, List

from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from models.Application import Application
from models.Audience import Audience
from models.RemoteConfigOverride import RemoteConfigOverride
from utils import constants


class RemoteConfig:
    """
    This class represents a mobile application configuration that we can manage remotely.
    """

    def __init__(self, database: DynamoDBServiceResource, data: dict[str, Any]):
        self.__database = database
        self.__assert_data(data)
        self.__data = data
        self.__data["overrides"] = {
            audience_name: RemoteConfigOverride(override)
            for audience_name, override in self.__data["overrides"].items()
        }

    @staticmethod
    def get_all(database: DynamoDBServiceResource) -> List["RemoteConfig"]:
        """
        This static method returns all remote configs.
        """
        response = database.Table(constants.TABLE_REMOTE_CONFIGS).scan()
        return [RemoteConfig(database, item) for item in response["Items"]]

    @staticmethod
    def purge_from_audience(database: DynamoDBServiceResource, audience_name: str):
        """
        This static method purges all overrides related to <audience_name>.
        It raises ValueError if there are active overrides with this audience.
        """
        remote_configs = RemoteConfig.get_all(database)

        # Fisrt, check if there are active overrides with this audience.
        for remote_config in remote_configs:
            override = remote_config.overrides.get(audience_name)
            if not override:
                continue

            if override.active:
                raise ValueError(
                    f"The audience is active on {remote_config.remote_config_name}"
                )

        # Now we purge this audience from all overrides.
        for remote_config in remote_configs:
            override = remote_config.overrides.get(audience_name)
            if not override:
                continue

            database.Table(constants.TABLE_REMOTE_CONFIGS).update_item(
                Key={"remote_config_name": remote_config.remote_config_name},
                UpdateExpression=f"REMOVE overrides.{audience_name}",
            )

    @property
    def application_IDs(self) -> list[str]:
        """
        This method returns application_IDs.
        """
        return self.__data["applications"]

    @property
    def description(self) -> str:
        """
        This method returns description.
        """
        return self.__data["description"]

    @property
    def overrides(self) -> dict[str, RemoteConfigOverride]:
        """
        This method returns overrides.
        """
        return self.__data["overrides"]

    @property
    def reference_value(self) -> str:
        """
        This method returns reference_value.
        """
        return self.__data["reference_value"]

    @property
    def remote_config_name(self) -> str:
        """
        This method returns remote_config_name.
        """
        return self.__data["remote_config_name"]

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the RemoteConfig.
        """
        return self.__data

    def update_database(self):
        """
        This method creates RemoteConfig in database.
        """
        self.__database.Table(constants.TABLE_REMOTE_CONFIGS).put_item(
            Item={
                "remote_config_name": self.remote_config_name,
                "applications": self.application_IDs,
                "description": self.description,
                "reference_value": self.reference_value,
                "overrides": {
                    audience_name: override.to_dict()
                    for audience_name, override in self.overrides.items()
                },
            }
        )

    def __assert_data(self, data: dict[str, Any]):
        data = data.copy()
        application_IDs = data.pop("applications")
        description = data.pop("description")
        overrides = data.pop("overrides")
        reference_value = data.pop("reference_value")
        remote_config_name = data.pop("remote_config_name")

        assert isinstance(
            application_IDs, list
        ), "`applications` should be a list of non-empty string"
        assert isinstance(description, str), "`description` should be string"
        assert isinstance(overrides, dict), "`overrides` should be dict[str, dict]"
        assert isinstance(reference_value, str), "`reference_value` should be string"
        assert (
            isinstance(remote_config_name, str) and remote_config_name != ""
        ), "`remote_config_name` should be non-empty string"

        for application_ID in application_IDs:
            assert (
                application_ID != ""
            ), "`application_IDs` should be a list of non-empty string"
            assert Application.exists(
                self.__database, application_ID
            ), f"`There is no application with ID : {application_ID}`"

        for audience_name, override in overrides.items():
            assert audience_name == "ALL" or Audience.from_database(
                self.__database, audience_name
            ), f"`audience_name` {audience_name} NOT exists"
            assert isinstance(override, dict), "`overrides` should be dict[str, dict]"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
