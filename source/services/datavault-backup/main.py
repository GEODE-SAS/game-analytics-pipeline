"""
This lambda backups Datavault every days.
Redshift Documentation : https://docs.aws.amazon.com/redshift/latest/mgmt/python-connect-examples.html
Tenjin Documentation : https://docs.tenjin.com/docs/datavault-introduction
"""
from datetime import datetime, timedelta
import json
import os
from typing import Any

import boto3
import redshift_connector


secrets_manager = boto3.client("secretsmanager")


def handler(event: dict[str, Any], context: dict[str, Any]):
    """
    lambda handler
    """
    print("Datavault backup.")
    print(f"Event: {event}")
    print(f"Context: {context}")

    BUCKET = os.environ["TENJIN_DATAVAULT_BUCKET"]

    datavault_secrets = json.loads(
        secrets_manager.get_secret_value(SecretId="datavault-backup")["SecretString"]
    )

    ACCESS_KEY_ID = datavault_secrets["ACCESS_KEY_ID"]
    SECRET_ACCESS_KEY = datavault_secrets["SECRET_ACCESS_KEY"]

    connection = redshift_connector.connect(
        host=datavault_secrets["HOST"],
        database=datavault_secrets["DATABASE"],
        port=5439,
        user=datavault_secrets["USER"],
        password=datavault_secrets["PASSWORD"],
    )
    cursor = connection.cursor()

    with open("assets/datavault_config.json", encoding="UTF-8") as f:
        datavault_config = json.load(f)

    print(
        f"Will backup Tenjin Datavault database to {BUCKET} s3 bucket using UNLOAD command."
    )

    now = datetime.now()
    now_minus_13_days = (now - timedelta(days=13)).strftime("%Y-%m-%d")
    now_minus_14_days = (now - timedelta(days=14)).strftime("%Y-%m-%d")

    for table, config in datavault_config.items():
        print(f"    • Will backup {table} Table...")
        partitionned = config["partitionned"] is True
        key = "partitioned-tables" if partitionned else "non-partitioned-tables"
        key += f"/{table}"

        SELECT_QUERY = f"""
            SELECT *
            FROM {table}
        """
        if partitionned:
            date_field = config["partition_date_field"]
            SELECT_QUERY = f"""
                SELECT
                    *,
                    TO_CHAR({date_field}, ''YYYY'') AS year,
                    TO_CHAR({date_field}, ''MM'') AS month,
                    TO_CHAR({date_field}, ''DD'') AS day
                FROM {table}
                WHERE ''{now_minus_14_days}'' <= {date_field} AND {date_field} < ''{now_minus_13_days}''
            """

        UNLOAD_QUERY = f"""
            UNLOAD ('{SELECT_QUERY}')
            TO 's3://{BUCKET}/{table}/'
            ACCESS_KEY_ID '{ACCESS_KEY_ID}'
            SECRET_ACCESS_KEY '{SECRET_ACCESS_KEY}'
            FORMAT AS PARQUET
            ALLOWOVERWRITE
        """
        if partitionned:
            UNLOAD_QUERY += "\nPARTITION BY (year, month, day)"

        cursor.execute(UNLOAD_QUERY)


if __name__ == "__main__":
    handler({}, {})
