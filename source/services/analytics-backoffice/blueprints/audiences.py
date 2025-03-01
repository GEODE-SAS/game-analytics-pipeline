"""
This module contains audiences endpoints.
"""

from flask import Blueprint, jsonify, request

from models.Audience import Audience
from models.RemoteConfig import RemoteConfig


audiences_endpoints = Blueprint("audiences_endpoints", __name__)


@audiences_endpoints.get("/")
def get_audiences():
    """
    This endpoint returns all audiences.
    """
    return jsonify(Audience.get_all())


@audiences_endpoints.post("/<audience_name>")
def set_audience(audience_name: str):
    """
    This endpoint sets an audience.
    """
    payload = request.get_json(force=True) | {"audience_name": audience_name}

    try:
        audience = Audience(payload)
    except AssertionError as e:
        return jsonify(error=str(e)), 400
    except KeyError as e:
        return jsonify(error=f"Invalid payload : missing {e}"), 400

    audience.update_database()
    return jsonify(), 204


@audiences_endpoints.delete("/<audience_name>")
def delete_audience(audience_name: str):
    """
    This endpoint deletes an audience.
    """
    audience = Audience.from_database(audience_name)
    if not audience:
        return (
            jsonify(error=f"There is no audience with {audience_name} audience_name"),
            400,
        )

    try:
        RemoteConfig.purge_from_audience(audience_name)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    audience.delete()
    return jsonify(), 204
