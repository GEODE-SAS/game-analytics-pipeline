analytics_backoffice_dist_dir="$PWD/analytics-backoffice-assets"
source_dir="$PWD/../source"

GEODE_AWS_REGION=$(aws configure get region --profile $AWS_PROFILE)

if [ $GEODE_ENVIRONMENT = "prod" ]; then
    GEODE_DOMAIN_NAME="api.geode.com"
elif [ $GEODE_ENVIRONMENT = "dev" ]; then
    GEODE_DOMAIN_NAME="apidev.geode.com"
fi

PROD_PROFILE="prod"
DEV_PROFILE="dev"
SANDBOX_PROFILE="sandbox"

if $IS_CHINA; then
    GEODE_DOMAIN_NAME="cn-$GEODE_DOMAIN_NAME"
    PROD_PROFILE="$PROD_PROFILE-china"
    DEV_PROFILE="$DEV_PROFILE-china"
    SANDBOX_PROFILE="$SANDBOX_PROFILE-china"
fi

PROD_AWS_REGION=$(aws configure get region --profile $PROD_PROFILE)
DEV_AWS_REGION=$(aws configure get region --profile $DEV_PROFILE)
SANDBOX_AWS_REGION=$(aws configure get region --profile $SANDBOX_PROFILE)

echo "------------------------------------------------------------------------------"
echo "Copying Analytics Backoffice project"
echo "------------------------------------------------------------------------------"
echo "rm -rf $analytics_backoffice_dist_dir"
rm -rf $analytics_backoffice_dist_dir
echo "mkdir -p $analytics_backoffice_dist_dir"
mkdir -p $analytics_backoffice_dist_dir

rsync -av --exclude='.venv/' $source_dir/services/analytics-backoffice/* $analytics_backoffice_dist_dir >/dev/null
sed -i '' s/%%AWS_REGION%%/$GEODE_AWS_REGION/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%PROJECT_NAME%%/$1/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%GEODE_DOMAIN_NAME%%/$GEODE_DOMAIN_NAME/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%PROD_REGION%%/$PROD_AWS_REGION/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%DEV_REGION%%/$DEV_AWS_REGION/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%SANDBOX_REGION%%/$SANDBOX_AWS_REGION/g $analytics_backoffice_dist_dir/zappa_settings.json
sed -i '' s/%%PROFILE_NAME%%/$AWS_PROFILE/g $analytics_backoffice_dist_dir/zappa_settings.json

echo "------------------------------------------------------------------------------"
echo "Build Analytics Backoffice project"
echo "------------------------------------------------------------------------------"

cd $analytics_backoffice_dist_dir
rm -r .venv 2>/dev/null
python3 -m venv .venv --upgrade-deps
source .venv/bin/activate
pip install -r requirements.txt >/dev/null
zappa update $GEODE_ENVIRONMENT
if [[ $? == 1 ]]; then
    echo "Applicaton not exists, will create it"
    zappa deploy $GEODE_ENVIRONMENT
fi
cd -
