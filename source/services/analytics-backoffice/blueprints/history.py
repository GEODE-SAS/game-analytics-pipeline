"""
This module contains history endpoints
"""

from flask import Blueprint, jsonify, request

from models.History import HistoryItem

history_endpoints = Blueprint("history_endpoints", __name__)


@history_endpoints.get("/")
def get_history():
    """
    This method returns history.
    """
    return jsonify(HistoryItem.get_all())


@history_endpoints.post("/<history_item_ID>/restore")
def restore_history_item(history_item_ID: str):
    """
    This method restores HistoryItem.
    """
    history_item = HistoryItem.from_database(history_item_ID)
    if not history_item:
        return jsonify(), 400

    history_item.restore()
    return jsonify(), 204
