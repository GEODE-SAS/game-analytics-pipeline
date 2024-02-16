"""
This module contains constants.
"""

import os


__project_name = os.environ["PROJECT_NAME"]
__geode_environment = os.environ["GEODE_ENVIRONMENT"]

__table_prefix = f"{__project_name}-{__geode_environment}"
__table_prefix_prod = f"{__project_name}-prod"
__table_prefix_dev = f"{__project_name}-dev"
__table_prefix_sandbox = f"{__project_name}-sandbox"

ANALYTICS_BUCKET = f"{__table_prefix}-analyticsbucket"
ANALYTICS_DATABASE = __table_prefix
ANALYTICS_TABLE = "raw_events"

TABLE_ABTESTS = f"{__table_prefix}-abtests"
TABLE_APPLICATIONS = f"{__table_prefix}-applications"
TABLE_HISTORY = f"{__table_prefix}-history"
TABLE_REMOTE_CONFIGS = f"{__table_prefix}-remote-configs"
TABLE_USERS_ABTESTS = f"{__table_prefix}-users-abtests"

TABLE_AUDIENCES_PROD = f"{__table_prefix_prod}-audiences"
TABLE_AUDIENCES_SANDBOX = f"{__table_prefix_sandbox}-audiences"

TABLE_REMOTE_CONFIGS_PROD = f"{__table_prefix_prod}-remote-configs"
TABLE_REMOTE_CONFIGS_DEV = f"{__table_prefix_dev}-remote-configs"
TABLE_REMOTE_CONFIGS_SANDBOX = f"{__table_prefix_sandbox}-remote-configs"

TABLE_HISTORY_PROD = f"{__table_prefix_prod}-history"
TABLE_HISTORY_DEV = f"{__table_prefix_dev}-history"
TABLE_HISTORY_SANDBOX = f"{__table_prefix_sandbox}-history"
