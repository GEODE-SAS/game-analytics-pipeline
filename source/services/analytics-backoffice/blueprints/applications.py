"""
This module contains applications endpoints.
"""

from flask import Blueprint, jsonify, request

from models.Application import Application


applications_endpoints = Blueprint("applications_endpoints", __name__)


@applications_endpoints.get("/")
def get_applications():
    """
    This endpoint returns applications.
    """
    return jsonify(Application.get_all())


@applications_endpoints.get("/<application_ID>/events")
def get_events_from_application(application_ID: str):
    """
    This endpoint returns applications.
    """
    limit = request.args.get("limit", "50")
    if not limit.isdigit() or int(limit) < 1:
        return jsonify(error="limit should be int and greater than 0"), 400

    if application := Application.from_ID(application_ID):
        return jsonify(application.get_latest_events(int(limit)))
    return jsonify(error=f"There is no application with ID : {application_ID}"), 400
