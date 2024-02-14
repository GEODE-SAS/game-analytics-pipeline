"""
This module contains FlaskApp class.
"""

import contextlib
from decimal import Decimal
import os

import boto3
import flask
from flask import Flask, jsonify, request, wrappers
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from mypy_boto3_athena.client import AthenaClient
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource


class FlaskAppEncoder(DefaultJSONProvider):
    """
    Custom JSONEncoder for Flask app. For example, It uses with jsonify() method
    """

    def default(self, o):
        """default"""
        if isinstance(o, Decimal):
            to_int = int(o)
            to_float = float(o)
            return to_int if to_int == to_float else to_float

        with contextlib.suppress(AttributeError):
            return o.to_dict()

        return super().default(o)


class FlaskApp(Flask):
    """
    This class redefines Flask class.
    """

    def __init__(self, name):
        Flask.__init__(self, name)
        CORS(self)
        self.json_provider_class = FlaskAppEncoder
        self.json = FlaskAppEncoder(self)

        self.config["athena"] = boto3.client("athena")
        self.config["database"] = boto3.resource("dynamodb")
        self.config["prod_database"] = boto3.resource(
            "dynamodb", region_name=os.environ["PROD_REGION"]
        )
        self.config["dev_database"] = boto3.resource(
            "dynamodb", region_name=os.environ["DEV_REGION"]
        )
        self.config["sandbox_database"] = boto3.resource(
            "dynamodb", region_name=os.environ["SANDBOX_REGION"]
        )

        @self.after_request
        def after_request(response: wrappers.Response):
            """after_request"""
            if response.status_code == 308:
                adapter = self.url_map.bind(request.host)
                # pylint: disable=unpacking-non-sequence
                endpoint, _ = adapter.match(
                    path_info=f"{request.path}/", method=request.method
                )
                endpoint_function = self.view_functions[endpoint]
                return endpoint_function()
            return response

        @self.get("/")
        def default():
            """
            Default endpoint.
            """
            return jsonify(), 204

    @property
    def athena(self) -> AthenaClient:
        """
        This property returns instance of database.
        """
        return self.config["athena"]

    @property
    def database(self) -> DynamoDBServiceResource:
        """
        This property returns instance of database.
        """
        return self.config["database"]

    @property
    def dev_database(self) -> DynamoDBServiceResource:
        """
        This property returns instance of dev database.
        """
        return self.config["dev_database"]

    @property
    def prod_database(self) -> DynamoDBServiceResource:
        """
        This property returns instance of prod database.
        """
        return self.config["prod_database"]

    @property
    def sandbox_database(self) -> DynamoDBServiceResource:
        """
        This property returns instance of dev database.
        """
        return self.config["sandbox_database"]


current_app: FlaskApp = flask.current_app
