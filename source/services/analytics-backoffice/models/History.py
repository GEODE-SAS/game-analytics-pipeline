"""
This module contains HistoryItem Table.
"""

from datetime import datetime
import json
from time import time
from typing import Any, List
from uuid import uuid4

import pytz

from FlaskApp import current_app
from utils import constants


class HistoryItem:
    """
    This class represents an Item of History.
    """

    __available_methods = ["DELETE"]

    def __init__(self, **kwargs):
        """
        Required params :
        - `method`: enum("DELETE")
        - `old_item`: dict
        - `table_name`: str
        """
        self.__assert_data(kwargs)
        self.__data = kwargs

    @classmethod
    def from_database(cls, history_item_ID: str):
        """
        This method creates an instance of Audience from audience_name by fetching database.
        It returns None if there is no Audience with this audience_name.
        """
        response = HistoryItem.__table_history().get_item(Key={"ID": history_item_ID})
        if item := response.get("Item"):
            item["old_item"] = json.loads(item["old_item"])
            return cls(**item)

    @staticmethod
    def get_all() -> List["HistoryItem"]:
        """
        This static method returns all HistoryItems sorted by timestamp ASCENDING.
        """
        table = HistoryItem.__table_history()
        response = table.scan()
        items = response["Items"]

        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response["Items"])

        result = []
        for item in sorted(items, key=lambda i: i["timestamp"]):
            item["old_item"] = json.loads(item["old_item"])
            result.append(HistoryItem(**item))

        return result

    @property
    def ID(self) -> str:
        """
        This method returns ID.
        """
        return self.__data["ID"]

    @property
    def method(self) -> str:
        """
        This method returns method.
        """
        return self.__data["method"]

    @property
    def old_item(self) -> str:
        """
        This method returns old_item.
        """
        return self.__data["old_item"]

    @property
    def table_name(self) -> str:
        """
        This method returns table_name.
        """
        return self.__data["table_name"]

    @property
    def timestamp(self) -> int:
        """
        This method returns timestamp.
        """
        return self.__data["timestamp"]

    def __assert_data(self, data: dict[str:Any]):
        assert (
            data.get("method") in self.__available_methods
        ), f"`method` should in {self.__available_methods}"
        assert isinstance(data.get("old_item"), dict), "`old_item` should be dict"
        assert isinstance(data.get("table_name"), str), "`table_name` should be str"

    def restore(self):
        """
        This method retores HistoryItem.
        """
        current_app.database.Table(self.table_name).put_item(Item=self.old_item)

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the HistoryItem.
        """
        return self.__data

    def update_database(self, environment: str = ""):
        """
        This method updates HistoryItem to database.
        """
        HistoryItem.__table_history(environment).put_item(
            Item={
                "ID": uuid4().hex,
                "expires_timestamp": int(time()) + 60 * 60 * 24 * 30,  # 30 days
                "method": self.method,
                "old_item": json.dumps(self.old_item),
                "table_name": self.table_name,
                "timestamp": int(
                    datetime.now(pytz.timezone("Europe/Paris")).timestamp()
                ),
            }
        )

    @staticmethod
    def __table_history(environment: str = ""):
        match environment:
            case "prod":
                return current_app.prod_database.Table(constants.TABLE_HISTORY_PROD)
            case "dev":
                return current_app.dev_database.Table(constants.TABLE_HISTORY_DEV)
            case "sandbox":
                return current_app.sandbox_database.Table(
                    constants.TABLE_HISTORY_SANDBOX
                )
        return current_app.database.Table(constants.TABLE_HISTORY)
