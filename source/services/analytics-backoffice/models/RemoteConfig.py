"""
This module contains RemoteConfig class.
"""

import os
from typing import Any, List

from FlaskApp import current_app
from models.ABTest import ABTest
from models.Audience import Audience
from models.RemoteConfigOverride import RemoteConfigOverride
from utils import constants


class RemoteConfig:
    """
    This class represents a mobile application configuration that we can manage remotely.
    """

    def __init__(self, data: dict[str, Any]):
        self.__assert_data(data)
        self.__data = data
        self.__data["overrides"] = {
            audience_name: RemoteConfigOverride(override)
            for audience_name, override in self.__data["overrides"].items()
        }

    @classmethod
    def from_database(cls, remote_config_name: str):
        """
        This method creates an instance of RemoteConfig by fetching database.
        It returns None if there is no RemoteConfig with <remote_config_name> in database.
        """
        response = RemoteConfig.__table_remote_configs().get_item(
            Key={"remote_config_name": remote_config_name}
        )
        if item := response.get("Item"):
            return cls(item)

    @staticmethod
    def get_all(environment: str = "") -> List["RemoteConfig"]:
        """
        This static method returns all remote configs.
        """
        response = RemoteConfig.__table_remote_configs(environment).scan()
        return [RemoteConfig(item) for item in response["Items"]]

    @staticmethod
    def purge_from_audience(audience_name: str):
        """
        This static method purges all overrides related to <audience_name>.
        It raises ValueError if there are active overrides with this audience.
        """
        environments = (
            ["dev", "prod"]
            if os.environ["GEODE_ENVIRONMENT"] in ("dev", "prod")
            else ["sandbox"]
        )

        for environment in environments:
            remote_configs = RemoteConfig.get_all(environment)

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

                RemoteConfig.__table_remote_configs(environment).update_item(
                    ExpressionAttributeNames={"#audience": audience_name},
                    Key={"remote_config_name": remote_config.remote_config_name},
                    UpdateExpression="REMOVE overrides.#audience",
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
    def has_active_override(self) -> bool:
        """
        This method returns True if RemoteConfig has active override else False.
        """
        for override in self.overrides.values():
            if override.active:
                return True
        return False

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

    def delete(self):
        """
        This method deletes remote config from database.
        """
        self.__purge_users_abtests(all_abtests=True)
        RemoteConfig.__table_remote_configs().delete_item(
            Key={"remote_config_name": self.remote_config_name}
        )

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the RemoteConfig.
        """
        return self.__data

    def update_database(self):
        """
        This method creates RemoteConfig in database.
        """
        self.__purge_users_abtests()
        RemoteConfig.__table_remote_configs().put_item(
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
            ), "`applications` should be a list of non-empty string"

        for audience_name, override in overrides.items():
            assert audience_name == "ALL" or Audience.from_database(
                audience_name
            ), f"`audience_name` {audience_name} NOT exists"
            assert isinstance(override, dict), "`overrides` should be dict[str, dict]"

        assert len(data) == 0, f"Unexpected fields -> {data.keys()}"

    def __purge_users_abtests(self, all_abtests: bool = False):
        """
        `all_abtests` should be True if the remote config will be entierly deleted.
        """
        # Check if an ABTest override has been deleted
        if remote_config := RemoteConfig.from_database(self.remote_config_name):
            for audience_name, override in remote_config.overrides.items():
                if override.override_type != "abtest":
                    continue
                if all_abtests or audience_name not in self.overrides:
                    # This ABTest has been deleted
                    ABTest.purge_users_abtests(self.remote_config_name, audience_name)

    @staticmethod
    def __table_remote_configs(environment: str = ""):
        """
        By default we work on the deployed environment. \n
        We leave the possibility of switching environments if necessary.
        """
        database = current_app.database
        match environment:
            case "prod":
                database = current_app.prod_database
            case "dev":
                database = current_app.dev_database
            case "sandbox":
                database = current_app.sandbox_database
        return database.Table(constants.TABLE_REMOTE_CONFIGS)
