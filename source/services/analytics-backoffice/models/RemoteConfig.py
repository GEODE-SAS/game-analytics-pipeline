"""
This module contains RemoteConfig class.
"""
from typing import Any, List

from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from models.Application import Application
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
        overrides = [
            RemoteConfigOverride(
                database,
                override
                | {
                    "audience_name": audience_name,
                    "remote_config_name": self.remote_config_name,
                },
            )
            for audience_name, override in data["overrides"].items()
        ]
        self.__data |= {"overrides": overrides}

    @staticmethod
    def get_all(database: DynamoDBServiceResource) -> List["RemoteConfig"]:
        """
        This static method returns all remote configs.
        """
        response = database.Table(constants.TABLE_REMOTE_CONFIGS).scan()
        remote_configs = []
        for item in response["Items"]:
            overrides = RemoteConfigOverride.from_remote_config_name(
                database, item["remote_config_name"]
            )
            overrides_dict = {
                audience_name: override.to_dict()
                for audience_name, override in overrides.items()
            }
            remote_configs.append(
                RemoteConfig(database, item | {"overrides": overrides_dict})
            )

        return remote_configs

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
    def overrides(self) -> list[RemoteConfigOverride]:
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
        overrides = {override.audience_name: override for override in self.overrides}
        return self.__data.copy() | {"overrides": overrides}

    def update_database(self):
        """
        This method creates RemoteConfig in database.
        """
        self.__database.Table(constants.TABLE_REMOTE_CONFIGS).put_item(
            Item={
                "remote_config_name": self.remote_config_name,
                "description": self.description,
                "reference_value": self.reference_value,
                "applications": self.application_IDs,
            }
        )
        RemoteConfigOverride.purge(self.__database, self.remote_config_name)
        for override in self.overrides:
            override.update_database()

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

        for override in overrides.values():
            assert isinstance(override, dict), "`overrides` should be dict[str, dict]"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"
