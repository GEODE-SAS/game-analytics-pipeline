#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name solution-name version-code
#
# Paramenters:
#  - source-bucket-base-name: Name for the S3 bucket location where the template will source the Lambda
#    code from. The template will append '-[region_name]' to this bucket name.
#    For example: ./build-s3-dist.sh solutions v1.0.0
#    The template will then expect the source code to be located in the solutions-[region_name] bucket
#
#  - solution-name: name of the solution for consistency
#
#  - version-code: version of the package

build_python_lambda() {
    rm -r dist 2>/dev/null
    rsync -av --exclude=.venv/ --exclude=.vscode --exclude=.pylintrc --exclude=local_requirements.txt * dist >/dev/null
    cd dist

    python3.11 -m venv .venv --upgrade-deps
    source .venv/bin/activate
    pip install -r requirements.txt --target . >/dev/null
    deactivate
    rm -r .venv
    rm -r requirements.txt

    zip -r $1.zip . >/dev/null
    cp $1.zip $build_dist_dir/$1.zip
    cd -
}

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "Please provide the base source bucket name, trademark approved solution name and version where the lambda code will eventually reside."
    echo "For example: ./build-s3-dist.sh solutions trademarked-solution-name v1.0.0"
    exit 1
fi

# Get reference for all important folders
template_dir="$PWD"
template_dist_dir="$template_dir/global-s3-assets"
build_dist_dir="$template_dir/regional-s3-assets"
source_dir="$template_dir/../source"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old dist, node_modules and bower_components folders"
echo "------------------------------------------------------------------------------"
echo "rm -rf $template_dist_dir"
rm -rf $template_dist_dir
echo "mkdir -p $template_dist_dir"
mkdir -p $template_dist_dir
echo "rm -rf $build_dist_dir"
rm -rf $build_dist_dir
echo "mkdir -p $build_dist_dir"
mkdir -p $build_dist_dir

echo "------------------------------------------------------------------------------"
echo "[Packing] Templates"
echo "------------------------------------------------------------------------------"
echo "cp $template_dir/*.template $template_dist_dir/"
cp $template_dir/*.template $template_dist_dir/
echo "copy yaml templates and rename"
cp $template_dir/*.yaml $template_dist_dir/
cd $template_dist_dir
# Rename all *.yaml to *.template
for f in *.yaml; do 
    mv -- "$f" "${f%.yaml}.template"
done

cd ..
echo "Updating code source bucket in template with $1"
replace="s|%%BUCKET_NAME%%|$1|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%SOLUTION_NAME%%|$2|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%VERSION%%|$3|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template

PROD_PROFILE="prod"
DEV_PROFILE="dev"
SANDBOX_PROFILE="sandbox"

if $IS_CHINA; then
    PROD_PROFILE="$PROD_PROFILE-china"
    DEV_PROFILE="$DEV_PROFILE-china"
    SANDBOX_PROFILE="$SANDBOX_PROFILE-china"
fi

PROD_AWS_REGION=$(aws configure get region --profile $PROD_PROFILE)
DEV_AWS_REGION=$(aws configure get region --profile $DEV_PROFILE)
SANDBOX_AWS_REGION=$(aws configure get region --profile $SANDBOX_PROFILE)

replace="s|%%PROJECT_NAME%%|$4|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%PROD_REGION%%|$PROD_AWS_REGION|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%DEV_REGION%%|$DEV_AWS_REGION|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%SANDBOX_REGION%%|$SANDBOX_AWS_REGION|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template
replace="s|%%GEODE_ENVIRONMENT%%|$GEODE_ENVIRONMENT|g"
echo "sed -i -e $replace $template_dist_dir/*.template"
sed -i -e $replace $template_dist_dir/*.template

echo "------------------------------------------------------------------------------"
echo "Packaging Lambda Function - Analytics Processing"
echo "------------------------------------------------------------------------------"
cd $source_dir/services/analytics-processing
npm run build
cp dist/analytics-processing.zip $build_dist_dir/analytics-processing.zip

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Events Processing"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/events-processing
npm run build
cp dist/events-processing.zip $build_dist_dir/events-processing.zip

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Applications admin service"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/api/admin
npm run build
cp dist/admin.zip $build_dist_dir/admin.zip

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Lambda Authorizer"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/api/lambda-authorizer
npm run build
cp dist/lambda-authorizer.zip $build_dist_dir/lambda-authorizer.zip

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Glue Partition Creator"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/data-lake/glue-partition-creator
npm run build
cp dist/glue-partition-creator.zip $build_dist_dir/glue-partition-creator.zip

echo "------------------------------------------------------------------------------"
echo "Packaging Lambda Function - Solution Helper"
echo "------------------------------------------------------------------------------"
cd $source_dir/resources/solution-helper
npm run build
cp ./dist/solution-helper.zip $build_dist_dir/solution-helper.zip

echo "------------------------------------------------------------------------------"
echo "Copying Glue ETL Code to regional assets folder"
echo "------------------------------------------------------------------------------"
cd $source_dir/services/data-lake/glue-scripts
cp game_events_etl.py $build_dist_dir/game_events_etl.py

echo "------------------------------------------------------------------------------"
echo "Package AWS SAM template into CloudFormation"
echo "------------------------------------------------------------------------------"
cd $template_dist_dir
aws cloudformation package --template-file ./game-analytics-pipeline.template --s3-bucket $1 --output-template-file ../global-s3-assets/game-analytics-pipeline.template

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Remote Configs service"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/api/remote-configs
build_python_lambda "remote-configs"

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Users Audiences service"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/users-audiences
build_python_lambda "users-audiences"

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Crash Report service"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/crash-report
build_python_lambda "crash-report"

echo "------------------------------------------------------------------------------"  
echo "Packaging Lambda Function - Datavault Backup service"  
echo "------------------------------------------------------------------------------"  
cd $source_dir/services/datavault-backup
build_python_lambda "datavault-backup"

echo "------------------------------------------------------------------------------"  
echo "Completed building distribution"
echo "------------------------------------------------------------------------------" 

ls -laR $build_dist_dir
ls -laR $template_dist_dir


