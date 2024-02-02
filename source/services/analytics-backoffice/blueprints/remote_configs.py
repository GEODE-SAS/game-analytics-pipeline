"""
This module contains remote_configs endpoints.
"""
from flask import Blueprint, current_app, jsonify, request

from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from models.Application import Application
from models.RemoteConfig import RemoteConfig


remote_configs_endpoints = Blueprint("remote_configs_endpoints", __name__)


@remote_configs_endpoints.get("/")
def get_remote_configs():
    """
    This endpoint returns all remote configs.
    """
    database = current_app.config["database"]
    remote_configs = RemoteConfig.get_all(database)

    # Dazzly Tools needs audience_name in override format
    result = []
    for remote_config in remote_configs:
        overrides = {}
        for audience_name, override in remote_config.overrides.items():
            overrides[audience_name] = override.to_dict() | {
                "audience_name": audience_name,
                "active": override.active == 1,
            }
        apps = Application.application_IDs_to_tags(
            database, remote_config.application_IDs
        )
        result.append(
            remote_config.to_dict() | {"applications": apps, "overrides": overrides}
        )

    return jsonify(result)


@remote_configs_endpoints.post("/<remote_config_name>")
def set_remote_config(remote_config_name: str):
    """
    This endpoint sets a remote config.
    """
    database: DynamoDBServiceResource = current_app.config["database"]
    payload = request.get_json(force=True)

    try:
        applications = payload["applications"]
        assert isinstance(
            applications, list
        ), "`applications` should be list of non-empty string"
        payload |= {
            "applications": Application.tags_to_application_IDs(database, applications),
            "remote_config_name": remote_config_name,
        }
        remote_config = RemoteConfig(database, payload)
    except AssertionError as e:
        return jsonify(error=str(e)), 400
    except KeyError as e:
        return jsonify(error=f"Invalid payload : missing {e}"), 400

    remote_config.update_database()
    return jsonify(), 204


@remote_configs_endpoints.delete("/<remote_config_name>")
def delete_remote_config(remote_config_name: str):
    """
    This endpoint deletes a remote config.
    """
    database: DynamoDBServiceResource = current_app.config["database"]

    remote_config = RemoteConfig.from_database(database, remote_config_name)
    if not remote_config:
        return jsonify(error=f"Invalid remote_config_name : {remote_config_name}"), 400

    if remote_config.has_active_override:
        return (jsonify(error="Remote config has active overrides"), 400)

    remote_config.delete()
    return jsonify(), 204
