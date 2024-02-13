"""
This module contains constants.
"""

import os


__project_name = os.environ["PROJECT_NAME"]
__geode_environment = os.environ["GEODE_ENVIRONMENT"]

__table_prefix = f"{__project_name}-{__geode_environment}"
__prod_table_prefix = (
    f"{__project_name}-prod"
    if __geode_environment != "sandbox"
    else f"{__project_name}-sandbox"
)

ANALYTICS_BUCKET = f"{__table_prefix}-analyticsbucket"
ANALYTICS_DATABASE = __table_prefix
ANALYTICS_TABLE = "raw_events"

TABLE_ABTESTS = f"{__table_prefix}-abtests"
TABLE_AUDIENCES = f"{__prod_table_prefix}-audiences"
TABLE_APPLICATIONS = f"{__table_prefix}-applications"
TABLE_REMOTE_CONFIGS = f"{__table_prefix}-remote-configs"
TABLE_USERS_ABTESTS = f"{__table_prefix}-users-abtests"
