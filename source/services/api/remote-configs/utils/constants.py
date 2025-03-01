"""
This module contains constants.
"""

import os


AUDIENCES_TABLE_PROD = os.environ["AUDIENCES_TABLE_PROD"]
AUDIENCES_TABLE_DEV = os.environ["AUDIENCES_TABLE_DEV"]
AUDIENCES_TABLE_SANDBOX = os.environ["AUDIENCES_TABLE_SANDBOX"]
REMOTE_CONFIGS_TABLE = os.environ["REMOTE_CONFIGS_TABLE"]
USERS_ABTESTS_TABLE = os.environ["USERS_ABTESTS_TABLE"]
USERS_AUDIENCES_TABLE = os.environ["USERS_AUDIENCES_TABLE"]
