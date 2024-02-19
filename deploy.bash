# Global Config
PROJECT_NAME="geode-analytics"
VERSION="2.0.9"

# Check if we should deployed in China or World project
export IS_CHINA=false
for arg in $@; do
    if [ $arg != "--china" ]; then
        echo "Exit : Unknown tag $arg"
        exit 1
    fi
    export IS_CHINA=true
done

export BRANCH_NAME=`git rev-parse --abbrev-ref HEAD`
if [ $BRANCH_NAME = "master" ]; then
    export GEODE_ENVIRONMENT="prod"
    PARAMETER_OVERRIDES="--parameter-overrides SolutionAdminEmailAddress=florent@geode.com KinesisStreamShards=5 SolutionMode=Prod"
elif [ $BRANCH_NAME = "dev" ]; then
    export GEODE_ENVIRONMENT="dev"
    PARAMETER_OVERRIDES="--parameter-overrides SolutionAdminEmailAddress=florent@geode.com"
else
    export GEODE_ENVIRONMENT="sandbox"
    PARAMETER_OVERRIDES=""
fi

echo "Game Analytics Pipeline will deployed project ! (ENVIRONMENT == $GEODE_ENVIRONMENT && CHINA == $IS_CHINA)\n"

export AWS_PROFILE=$GEODE_ENVIRONMENT
if $IS_CHINA; then
    export AWS_PROFILE=$AWS_PROFILE-china
fi

GEODE_AWS_REGION=$(aws configure get region --profile $AWS_PROFILE)

DIST_OUTPUT_BUCKET="$PROJECT_NAME-output-bucket"
STACK_NAME="$PROJECT_NAME-$GEODE_ENVIRONMENT"
SOLUTION_NAME="analytics/$GEODE_ENVIRONMENT"

# Run following command only the first time to create output bucket.
aws s3 mb s3://$DIST_OUTPUT_BUCKET-$GEODE_AWS_REGION --region $GEODE_AWS_REGION 2> /dev/null

cd ./deployment

# Build project (Templates + Lambdas)
./build-s3-dist.sh $DIST_OUTPUT_BUCKET $SOLUTION_NAME $VERSION $PROJECT_NAME

# Store Global Assets to S3 (Templates)
aws s3 cp ./global-s3-assets s3://$DIST_OUTPUT_BUCKET-$GEODE_AWS_REGION/$SOLUTION_NAME/$VERSION --recursive --acl bucket-owner-full-control

# Store Regional Assets to S3 (Lambdas)
aws s3 cp ./regional-s3-assets s3://$DIST_OUTPUT_BUCKET-$GEODE_AWS_REGION/$SOLUTION_NAME/$VERSION --recursive --acl bucket-owner-full-control

# Deploy Backoffce Remote Config API Gateway (Zappa)
./deploy-analytics-backoffice.sh $PROJECT_NAME

# Deploy CloudFormation by creating/updating Stack
aws cloudformation deploy \
    --template-file ./global-s3-assets/game-analytics-pipeline.template \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --s3-bucket $DIST_OUTPUT_BUCKET-$GEODE_AWS_REGION \
    --s3-prefix templates \
    --capabilities CAPABILITY_NAMED_IAM \
    $PARAMETER_OVERRIDES
