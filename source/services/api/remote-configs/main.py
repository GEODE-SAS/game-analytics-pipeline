"""
Lambda handler
"""
import sys
from typing import Any

import boto3

from models.ABTest import ABTest
from models.Audience import Audience
from models.RemoteConfig import RemoteConfig
from models.RemoteConfigOverride import RemoteConfigOverride
from models.UserABTest import UserABTest


dynamodb = boto3.resource("dynamodb")


def handler(event: dict[str, Any], context: dict[str, Any]):
    """
    lambda handler
    """
    print("Attempting to retrieve remote configs.")
    print(f"Event: {event}")
    print(f"Context: {context}")

    result = {}
    application_ID = event["applicationId"]
    user_ID = event["userId"]
    payload = event["payload"] | {"country": event["country"]}

    remote_configs = RemoteConfig.get_all(dynamodb, application_ID)
    if not remote_configs:
        return result

    user_audiences = []
    user_audiences.extend(Audience.event_based_audiences(dynamodb, user_ID))
    user_audiences.extend(Audience.property_based_audiences(dynamodb, payload))

    for remote_config in remote_configs:
        overrides = RemoteConfigOverride.filter_audiences(
            dynamodb, remote_config.remote_config_name, user_audiences
        )

        if not overrides:
            # RemoteConfig has no Override or there is no audience that matches the user
            result[remote_config.remote_config_name] = {
                "value": remote_config.reference_value,
                "value_origin": "reference_value",
            }
            continue

        # If there are several overrides, it is due to an inconsistency in analytical decisions
        # So we take the first override
        override = next(iter(overrides))

        if override.override_type == "fixed":
            result[remote_config.remote_config_name] = {
                "value": override.fixed_value,
                "value_origin": "reference_value",
            }
            continue

        # override_type == abtest
        abtest = ABTest(override.abtest_value)
        user_abtest = UserABTest(dynamodb, user_ID, abtest)

        if not user_abtest.exists:
            user_abtest.set_group(remote_config.reference_value)

        result[remote_config.remote_config_name] = {
            "value": user_abtest.value,
            "value_origin": "abtest" if user_abtest.is_in_test else "reference_value",
        }

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Exit... Missing `applicationId` and `userId`")
        sys.exit(1)

    event = {
        "applicationId": sys.argv[1],
        "country": "FR",
        "payload": {},
        "userId": sys.argv[2],
    }
    print(handler(event, {}))
