# This script is used to run remote-configs lambda locally

BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`
export PROJECT_NAME="geode-analytics"

if [ $BRANCH_NAME = "master" ]; then
    export AWS_PROFILE="prod"
    export GEODE_ENVIRONMENT="prod"
elif [ $BRANCH_NAME = "dev" ]; then
    export AWS_PROFILE="dev"
    export GEODE_ENVIRONMENT="dev"
else
    export AWS_PROFILE="sandbox"
    export GEODE_ENVIRONMENT="sandbox"
fi

export AUDIENCES_TABLE="$PROJECT_NAME-$GEODE_ENVIRONMENT-audiences"
export REMOTE_CONFIGS_TABLE="$PROJECT_NAME-$GEODE_ENVIRONMENT-remote-configs"
export REMOTE_CONFIGS_OVERRIDES_TABLE="$PROJECT_NAME-$GEODE_ENVIRONMENT-remote-configs-overrides"
export USERS_ABTESTS_TABLE="$PROJECT_NAME-$GEODE_ENVIRONMENT-users-abtests"
export USERS_AUDIENCES_TABLE="$PROJECT_NAME-$GEODE_ENVIRONMENT-users-audiences"

if [ ! -d .venv ]; then
    echo "Virtual environment creation processing...\n"
    python3.11 -m venv .venv --upgrade-deps
fi

source .venv/bin/activate

if ! cmp -s requirements.txt .venv/requirements.txt; then
    echo "Updating local dependencies...\n"
    pip install --upgrade pip
    pip install -r requirements.txt >/dev/null
    cp requirements.txt .venv/requirements.txt
fi

python main.py $@
