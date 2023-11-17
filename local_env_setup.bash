# This script setups local environment for local development
# You can run this script when you update Python requirements


refresh_venv() {
    cd $1
    if [ ! -d .venv ]; then
        python3.11 -m venv .venv --upgrade-deps
    fi
    if ! cmp -s requirements.txt .venv/requirements.txt; then
        source .venv/bin/activate
        pip install -r requirements.txt
        deactivate
        cp requirements.txt .venv/requirements.txt
    fi
    cd - >/dev/null
}


cd source/services
refresh_venv "api/remote-configs"
refresh_venv "crash-report"
refresh_venv "users-audiences"
