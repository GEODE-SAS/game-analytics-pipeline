"""
This module contains RemoteConfig class.
"""
from typing import Any, List

from boto3.dynamodb.conditions import Attr
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from models.RemoteConfigOverride import RemoteConfigOverride
from utils import constants


class RemoteConfig:
    """
    This class represents a RemoteConfig.
    """

    def __init__(self, data: dict[str, Any]):
        self.__data = data
        self.__data["overrides"] = {
            audience_name: RemoteConfigOverride(override)
            for audience_name, override in self.__data["overrides"].items()
        }

    @staticmethod
    def get_all(
        dynamodb: DynamoDBServiceResource, application_ID: str
    ) -> List["RemoteConfig"]:
        """
        This method returns all RemoteConfigs.
        """
        response = dynamodb.Table(constants.REMOTE_CONFIGS_TABLE).scan(
            FilterExpression=Attr("applications").contains(application_ID),
        )
        return [RemoteConfig(item) for item in response["Items"]]

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
