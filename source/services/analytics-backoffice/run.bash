# This script is used to run analytics-backoffice REST API locally

BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`
export PROJECT_NAME="geode-analytics"

if [ $BRANCH_NAME = "master" ]; then
    export AWS_PROFILE_NAME="prod"
    export GEODE_ENVIRONMENT="prod"
elif [ $BRANCH_NAME = "dev" ]; then
    export AWS_PROFILE_NAME="dev"
    export GEODE_ENVIRONMENT="dev"
else
    export AWS_PROFILE_NAME="sandbox"
    export GEODE_ENVIRONMENT="sandbox"
fi

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

python main.py
