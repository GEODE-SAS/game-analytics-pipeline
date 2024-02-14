# This script is used to run analytics-backoffice REST API locally

BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`
export PROJECT_NAME="geode-analytics"

export PROD_REGION=$(aws configure get region --profile prod)
export DEV_REGION=$(aws configure get region --profile dev)
export SANDBOX_REGION=$(aws configure get region --profile sandbox)

if [ $BRANCH_NAME = "master" ]; then
    export GEODE_ENVIRONMENT="prod"
elif [ $BRANCH_NAME = "dev" ]; then
    export GEODE_ENVIRONMENT="prod"
else
    export GEODE_ENVIRONMENT="sandbox"
fi

export AWS_PROFILE=$GEODE_ENVIRONMENT

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
