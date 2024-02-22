"""
This module contains RemoteConfig class.
"""

from decimal import Decimal
import os
from typing import Any, List

from FlaskApp import current_app
from models.ABTest import ABTest
from models.Audience import Audience
from models.History import HistoryItem
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
    def new_users_threshold(self) -> int:
        """
        This method returns new_users_threshold.
        """
        return self.__data["new_users_threshold"]

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
        table = RemoteConfig.__table_remote_configs()

        self.__purge_users_abtests(all_abtests=True)
        table.delete_item(Key={"remote_config_name": self.remote_config_name})

        history_item = HistoryItem(
            method="DELETE", old_item=self.__item, table_name=table.table_name
        )
        history_item.update_database()

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
        RemoteConfig.__table_remote_configs().put_item(Item=self.__item)

    @property
    def __item(self) -> dict[str, Any]:
        return {
            "remote_config_name": self.remote_config_name,
            "applications": self.application_IDs,
            "description": self.description,
            "new_users_threshold": self.new_users_threshold,
            "reference_value": self.reference_value,
            "overrides": {
                audience_name: override.to_dict()
                for audience_name, override in self.overrides.items()
            },
        }

    def __assert_data(self, data: dict[str, Any]):
        to_assert = data.copy()
        application_IDs = to_assert.pop("applications")
        description = to_assert.pop("description")
        new_users_threshold = to_assert.pop("new_users_threshold")
        overrides = to_assert.pop("overrides")
        reference_value = to_assert.pop("reference_value")
        remote_config_name = to_assert.pop("remote_config_name")

        if isinstance(new_users_threshold, Decimal):
            new_users_threshold = int(new_users_threshold)
            data["new_users_threshold"] = new_users_threshold

        assert isinstance(
            application_IDs, list
        ), "`applications` should be a list of non-empty string"
        assert isinstance(description, str), "`description` should be string"
        assert (
            isinstance(new_users_threshold, int) and new_users_threshold >= 0
        ), "`new_users_threshold` should be int greater than or equal to 0"
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

        assert len(to_assert) == 0, f"Unexpected fields -> {to_assert.keys()}"

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
        match environment:
            case "prod":
                return current_app.prod_database.Table(
                    constants.TABLE_REMOTE_CONFIGS_PROD
                )
            case "dev":
                return current_app.dev_database.Table(
                    constants.TABLE_REMOTE_CONFIGS_DEV
                )
            case "sandbox":
                return current_app.sandbox_database.Table(
                    constants.TABLE_REMOTE_CONFIGS_SANDBOX
                )
        return current_app.database.Table(constants.TABLE_REMOTE_CONFIGS)
