"""
This module contains abtests endpoints.
"""
from flask import Blueprint, current_app, jsonify, request

from models.RemoteConfig import RemoteConfig


remote_configs_endpoints = Blueprint("remote_configs_endpoints", __name__)


@remote_configs_endpoints.get("/<uid>")
def get_uid_slot(uid: str):
    """
    This endpoint returns all remote configs.
    """
    if application_ID := request.args.get("application_ID"):
        remote_configs = RemoteConfig.get_all_from_uid(
            current_app.config["database"], uid, application_ID
        )
        return jsonify(remote_configs)
    return jsonify(error="Invalid payload : application_ID"), 400
