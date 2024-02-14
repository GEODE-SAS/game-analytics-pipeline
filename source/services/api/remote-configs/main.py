"""
Lambda handler
"""

import os
import sys
from typing import Any

import boto3

from models.ABTest import ABTest
from models.Audience import Audience
from models.RemoteConfig import RemoteConfig
from models.UserABTest import UserABTest


dynamodb = boto3.resource("dynamodb")
prod_dynamodb = boto3.resource("dynamodb", region_name=os.environ["PROD_REGION"])
dev_dynamodb = boto3.resource("dynamodb", region_name=os.environ["DEV_REGION"])
sandbox_dynamodb = boto3.resource("dynamodb", region_name=os.environ["SANDBOX_REGION"])

audience_dynamodb = sandbox_dynamodb
if os.environ["GEODE_ENVIRONMENT"] in ("dev", "prod"):
    audience_dynamodb = prod_dynamodb


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

    # Audience Priority : "developer", "property_based", "event_based", "ALL"
    user_audiences: list[Audience] = []
    user_audiences.extend(Audience.developer_audiences(audience_dynamodb, payload))
    user_audiences.extend(Audience.property_based_audiences(audience_dynamodb, payload))
    user_audiences.extend(Audience.event_based_audiences(dynamodb, user_ID))
    user_audience_names = [audience.audience_name for audience in user_audiences] + [
        "ALL"
    ]

    for remote_config in remote_configs:
        # First, we search if there is an active override that matches with user audiences.
        user_audience = None
        user_override = None

        for audience_name in user_audience_names:
            override = remote_config.overrides.get(audience_name)
            if not override:
                continue

            if override.active:
                user_audience = audience_name
                user_override = override
                break

        if not user_audience or not user_override:
            # RemoteConfig has no Override or there is no audience that matches the user
            result[remote_config.remote_config_name] = {
                "value": remote_config.reference_value,
                "value_origin": "reference_value",
            }
            continue

        if user_override.override_type == "fixed":
            result[remote_config.remote_config_name] = {
                "value": user_override.fixed_value,
                "value_origin": "reference_value",
            }
            continue

        # override_type == abtest
        abtest = ABTest(
            remote_config.remote_config_name, user_audience, user_override.abtest_value
        )
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
