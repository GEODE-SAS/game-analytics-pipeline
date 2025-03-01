"""
This module contains Application class.
"""

from datetime import datetime
from time import sleep
from typing import Any, List

from boto3.dynamodb.conditions import Attr

from FlaskApp import current_app
from utils import constants


class Application:
    """
    This class represents an analytical application.
    """

    def __init__(self, application_ID: str, application_data: dict[str, Any]):
        self.__application_ID = application_ID
        self.__data = application_data

    @classmethod
    def from_ID(cls, application_ID: str):
        """
        This method creates an instance of RemoteConfig from ID. It fetches database.
        It returns None if there is no RemoteConfig with this ID.
        """
        response = Application.__table_applications().get_item(
            Key={"application_id": application_ID}
        )
        if item := response.get("Item"):
            return cls(item.pop("application_id"), item)

    @staticmethod
    def application_IDs_to_tags(application_IDs: list[str]) -> list[str]:
        """
        This staticmethod returns a list of Application that match the <tags>.
        """
        if not application_IDs:
            return []

        response = Application.__table_applications().scan(
            FilterExpression=Attr("application_id").is_in(application_IDs)
        )
        return sorted(set(item["tag"] for item in response["Items"]))

    @staticmethod
    def exists(application_ID: str) -> bool:
        """
        This property returns True if Application exists, else False.
        """
        response = Application.__table_applications().get_item(
            Key={"application_id": application_ID}
        )
        return "Item" in response

    @staticmethod
    def get_all() -> List["Application"]:
        """
        This static method returns all applications.
        """
        response = Application.__table_applications().scan()
        return [
            Application(item.pop("application_id"), item) for item in response["Items"]
        ]

    @staticmethod
    def tags_to_application_IDs(tags: list[str]) -> list[str]:
        """
        This staticmethod returns a list of Application that match the <tags>.
        """
        if not tags:
            return []

        response = Application.__table_applications().scan(
            FilterExpression=Attr("tag").is_in(tags)
        )
        return [item["application_id"] for item in response["Items"]]

    @property
    def application_name(self) -> str:
        """
        This method returns name of application.
        """
        return self.__data["application_name"]

    def get_latest_events(self, limit: int) -> list[dict[str, Any]]:
        """
        This method returns latest events of application.
        """
        now = datetime.now()
        # Start Athena Query
        response = current_app.athena.start_query_execution(
            QueryString=f"""
                SELECT *
                FROM {constants.ANALYTICS_TABLE}
                WHERE application_name='{self.application_name}' AND year='{now.year}' AND month='{now.month}' AND day='{now.day}'
                ORDER BY event_timestamp DESC
                LIMIT {limit}
            """,
            QueryExecutionContext={"Database": constants.ANALYTICS_DATABASE},
            ResultConfiguration={
                "OutputLocation": f"s3://{constants.ANALYTICS_BUCKET}/athena_query_results/"
            },
        )
        query_execution_id = response["QueryExecutionId"]
        while True:
            # Wait for the query to be executed
            sleep(0.5)  # To avoid spamming requests
            query_status = current_app.athena.get_query_execution(
                QueryExecutionId=query_execution_id
            )["QueryExecution"]["Status"]
            if query_status["State"] not in ("QUEUED", "RUNNING"):
                break

        if query_status == "FAILED":
            raise ValueError(
                f"Error during Athena query execution : {query_status['StateChangeReason']}"
            )

        # Get Athena Query Results
        query_results = current_app.athena.get_query_results(
            QueryExecutionId=response["QueryExecutionId"]
        )
        result_set = query_results["ResultSet"]

        # Events Formatting
        columns = [
            column["Label"] for column in result_set["ResultSetMetadata"]["ColumnInfo"]
        ]
        return [
            {
                column: value["VarCharValue"]
                for column, value in zip(columns, row["Data"])
            }
            for row in result_set["Rows"][1:]
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        This method returns a dict that represents the Application.
        """
        return self.__data | {"application_id": self.__application_ID}

    @staticmethod
    def __table_applications():
        return current_app.database.Table(constants.TABLE_APPLICATIONS)
