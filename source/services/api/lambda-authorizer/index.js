/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
 
'use strict';

/**
 * Lib
 */
const AWS = require('aws-sdk');
console.log('Loading function');
const CHINA_REGIONS = ["cn-north-1", "cn-northwest-1"]


/**
 * AuthPolicy receives a set of allowed and denied methods and generates a valid
 * AWS policy for the API Gateway authorizer. The constructor receives the calling
 * user principal, the AWS account ID of the API owner, and an apiOptions object.
 * The apiOptions can contain an API Gateway RestApi Id, a region for the RestApi, and a
 * stage that calls should be allowed/denied for. For example
 * {
 *   restApiId: 'xxxxxxxxxx,
 *   region: 'us-east-1,
 *   stage: 'dev',
 * }
 *
 * const testPolicy = new AuthPolicy("[principal user identifier]", "[AWS account id]", apiOptions);
 * testPolicy.allowMethod(AuthPolicy.HttpVerb.GET, "/users/username");
 * testPolicy.denyMethod(AuthPolicy.HttpVerb.POST, "/pets");
 * callback(null, testPolicy.build());
 *
 * @class AuthPolicy
 * @constructor
 */
function AuthPolicy(principal, awsAccountId, apiOptions) {
    /**
     * The AWS account id the policy will be generated for. This is used to create
     * the method ARNs.
     *
     * @property awsAccountId
     * @type {String}
     */
    this.awsAccountId = awsAccountId;

    /**
     * The principal used for the policy, this should be a unique identifier for
     * the end user.
     *
     * @property principalId
     * @type {String}
     */
    this.principalId = principal;

    /**
     * The policy version used for the evaluation. This should always be "2012-10-17"
     *
     * @property version
     * @type {String}
     * @default "2012-10-17"
     */
    this.version = '2012-10-17';

    /**
     * The regular expression used to validate resource paths for the policy
     *
     * @property pathRegex
     * @type {RegExp}
     * @default '^\/[/.a-zA-Z0-9-\*]+$'
     */
    this.pathRegex = new RegExp('^[/.a-zA-Z0-9-\*]+$');

    // These are the internal lists of allowed and denied methods. These are lists
    // of objects and each object has two properties: a resource ARN and a nullable
    // conditions statement. The build method processes these lists and generates
    // the appropriate statements for the final policy.
    this.allowMethods = [];
    this.denyMethods = [];

    if (!apiOptions || !apiOptions.restApiId) {
        this.restApiId = '*';
    } else {
        this.restApiId = apiOptions.restApiId;
    }
    if (!apiOptions || !apiOptions.region) {
        this.region = '*';
    } else {
        this.region = apiOptions.region;
    }
    if (!apiOptions || !apiOptions.stage) {
        this.stage = '*';
    } else {
        this.stage = apiOptions.stage;
    }
}

/**
 * A set of existing HTTP verbs supported by API Gateway. This property is here
 * only to avoid spelling mistakes in the policy.
 *
 * @property HttpVerb
 * @type {Object}
 */
AuthPolicy.HttpVerb = {
    GET: 'GET',
    POST: 'POST',
    PUT: 'PUT',
    PATCH: 'PATCH',
    HEAD: 'HEAD',
    DELETE: 'DELETE',
    OPTIONS: 'OPTIONS',
    ALL: '*',
};

AuthPolicy.prototype = (function AuthPolicyClass() {
    /**
     * Adds a method to the internal lists of allowed or denied methods. Each object in
     * the internal list contains a resource ARN and a condition statement. The condition
     * statement can be null.
     *
     * @method addMethod
     * @param {String} The effect for the policy. This can only be "Allow" or "Deny".
     * @param {String} The HTTP verb for the method, this should ideally come from the
     *                 AuthPolicy.HttpVerb object to avoid spelling mistakes
     * @param {String} The resource path. For example "/pets"
     * @param {Object} The conditions object in the format specified by the AWS docs.
     * @return {void}
     */
    function addMethod(effect, verb, resource, conditions) {
        if (verb !== '*' && !Object.prototype.hasOwnProperty.call(AuthPolicy.HttpVerb, verb)) {
            throw new Error(`Invalid HTTP verb ${verb}. Allowed verbs in AuthPolicy.HttpVerb`);
        }

        if (!this.pathRegex.test(resource)) {
            throw new Error(`Invalid resource path: ${resource}. Path should match ${this.pathRegex}`);
        }

        let cleanedResource = resource;
        if (resource.substring(0, 1) === '/') {
            cleanedResource = resource.substring(1, resource.length);
        }
        const awsPartition = CHINA_REGIONS.includes(this.region) ? "aws-cn" : "aws"
        const resourceArn = `arn:${awsPartition}:execute-api:${this.region}:${this.awsAccountId}:${this.restApiId}/${this.stage}/${verb}/${cleanedResource}`;

        if (effect.toLowerCase() === 'allow') {
            this.allowMethods.push({
                resourceArn,
                conditions,
            });
        } else if (effect.toLowerCase() === 'deny') {
            this.denyMethods.push({
                resourceArn,
                conditions,
            });
        }
    }

    /**
     * Returns an empty statement object prepopulated with the correct action and the
     * desired effect.
     *
     * @method getEmptyStatement
     * @param {String} The effect of the statement, this can be "Allow" or "Deny"
     * @return {Object} An empty statement object with the Action, Effect, and Resource
     *                  properties prepopulated.
     */
    function getEmptyStatement(effect) {
        const statement = {};
        statement.Action = 'execute-api:Invoke';
        statement.Effect = effect.substring(0, 1).toUpperCase() + effect.substring(1, effect.length).toLowerCase();
        statement.Resource = [];

        return statement;
    }

    /**
     * This function loops over an array of objects containing a resourceArn and
     * conditions statement and generates the array of statements for the policy.
     *
     * @method getStatementsForEffect
     * @param {String} The desired effect. This can be "Allow" or "Deny"
     * @param {Array} An array of method objects containing the ARN of the resource
     *                and the conditions for the policy
     * @return {Array} an array of formatted statements for the policy.
     */
    function getStatementsForEffect(effect, methods) {
        const statements = [];

        if (methods.length > 0) {
            const statement = getEmptyStatement(effect);

            for (let i = 0; i < methods.length; i++) {
                const curMethod = methods[i];
                if (curMethod.conditions === null || curMethod.conditions.length === 0) {
                    statement.Resource.push(curMethod.resourceArn);
                } else {
                    const conditionalStatement = getEmptyStatement(effect);
                    conditionalStatement.Resource.push(curMethod.resourceArn);
                    conditionalStatement.Condition = curMethod.conditions;
                    statements.push(conditionalStatement);
                }
            }

            if (statement.Resource !== null && statement.Resource.length > 0) {
                statements.push(statement);
            }
        }

        return statements;
    }

    return {
        constructor: AuthPolicy,

        /**
         * Adds an allow "*" statement to the policy.
         *
         * @method allowAllMethods
         */
        allowAllMethods() {
            addMethod.call(this, 'allow', '*', '*', null);
        },

        /**
         * Adds a deny "*" statement to the policy.
         *
         * @method denyAllMethods
         */
        denyAllMethods() {
            addMethod.call(this, 'deny', '*', '*', null);
        },

        /**
         * Adds an API Gateway method (Http verb + Resource path) to the list of allowed
         * methods for the policy
         *
         * @method allowMethod
         * @param {String} The HTTP verb for the method, this should ideally come from the
         *                 AuthPolicy.HttpVerb object to avoid spelling mistakes
         * @param {string} The resource path. For example "/pets"
         * @return {void}
         */
        allowMethod(verb, resource) {
            addMethod.call(this, 'allow', verb, resource, null);
        },

        /**
         * Adds an API Gateway method (Http verb + Resource path) to the list of denied
         * methods for the policy
         *
         * @method denyMethod
         * @param {String} The HTTP verb for the method, this should ideally come from the
         *                 AuthPolicy.HttpVerb object to avoid spelling mistakes
         * @param {string} The resource path. For example "/pets"
         * @return {void}
         */
        denyMethod(verb, resource) {
            addMethod.call(this, 'deny', verb, resource, null);
        },

        /**
         * Adds an API Gateway method (Http verb + Resource path) to the list of allowed
         * methods and includes a condition for the policy statement. More on AWS policy
         * conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition
         *
         * @method allowMethodWithConditions
         * @param {String} The HTTP verb for the method, this should ideally come from the
         *                 AuthPolicy.HttpVerb object to avoid spelling mistakes
         * @param {string} The resource path. For example "/pets"
         * @param {Object} The conditions object in the format specified by the AWS docs
         * @return {void}
         */
        allowMethodWithConditions(verb, resource, conditions) {
            addMethod.call(this, 'allow', verb, resource, conditions);
        },

        /**
         * Adds an API Gateway method (Http verb + Resource path) to the list of denied
         * methods and includes a condition for the policy statement. More on AWS policy
         * conditions here: http://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html#Condition
         *
         * @method denyMethodWithConditions
         * @param {String} The HTTP verb for the method, this should ideally come from the
         *                 AuthPolicy.HttpVerb object to avoid spelling mistakes
         * @param {string} The resource path. For example "/pets"
         * @param {Object} The conditions object in the format specified by the AWS docs
         * @return {void}
         */
        denyMethodWithConditions(verb, resource, conditions) {
            addMethod.call(this, 'deny', verb, resource, conditions);
        },

        /**
         * Generates the policy document based on the internal lists of allowed and denied
         * conditions. This will generate a policy with two main statements for the effect:
         * one statement for Allow and one statement for Deny.
         * Methods that includes conditions will have their own statement in the policy.
         *
         * @method build
         * @return {Object} The policy object that can be serialized to JSON.
         */
        build() {
            if ((!this.allowMethods || this.allowMethods.length === 0) &&
                    (!this.denyMethods || this.denyMethods.length === 0)) {
                throw new Error('No statements defined for the policy');
            }

            const policy = {};
            policy.principalId = this.principalId;
            const doc = {};
            doc.Version = this.version;
            doc.Statement = [];

            doc.Statement = doc.Statement.concat(getStatementsForEffect.call(this, 'Allow', this.allowMethods));
            doc.Statement = doc.Statement.concat(getStatementsForEffect.call(this, 'Deny', this.denyMethods));

            policy.policyDocument = doc;

            return policy;
        },
    };
}());


exports.handler = async (event, context, callback) => {        
    console.log(`Received event: ${JSON.stringify(event)}`);
    // Retrieve request parameters from the Lambda function input:
    const headers = event.headers;
    const queryStringParameters = event.queryStringParameters;
    const pathParameters = event.pathParameters;
    const stageVariables = event.stageVariables;
        
    // Parse the input for the parameter values
    const apiOptions = {};
    const tmp = event.methodArn.split(':');
    const apiGatewayArnTmp = tmp[5].split('/');
    const awsAccountId = tmp[4];
    apiOptions.region = tmp[3];
    apiOptions.restApiId = apiGatewayArnTmp[0];
    apiOptions.stage = apiGatewayArnTmp[1];
    
    /**
     * Extract authorization header
     * Use Api Key to check if authorizations exist in Authorizations Table
     * Generate Allow POST /events associated with key
     */
    if (!headers.Authorization) {
        callback('Unauthorized');
    }
    
    const apiKeyValue = headers.Authorization;
    let policy = new AuthPolicy(apiKeyValue, awsAccountId, apiOptions);
    let authResponse = {};
    // Returns array of authorizations or false if no authorizations are found for key
    const authorizations = await getAuthorizations(apiKeyValue);
    
    // If api key is valid and authorizations are found, use them to build and return an allow policy
    // If api key not found, "false" is returned and a "deny all" policy is set for the unknown key value so it gets cached
    if (authorizations.authorizations) {
        console.log(JSON.stringify(authorizations));
        authorizations.authorizations.forEach(function(item) {
            policy.allowMethod(AuthPolicy.HttpVerb.POST, `/applications/${item.application_id}/events`);
        });
        
        authResponse = policy.build();
        authResponse.usageIdentifierKey = apiKeyValue;
        console.log(JSON.stringify(authResponse));
        callback(null, authResponse);
    } else {
        console.log(`No authorizations found for api key. Setting policy to deny all so that it can be cached`);
        policy.denyAllMethods(); // return deny all if api key invalid/no authZ found
        authResponse = policy.build();
        callback(null, authResponse);
    }
};

/**
 * Retrieve registrations for an api key
 */
const getAuthorizations = async (apiKeyValue) => {
    console.log(`Attempting to get authorizations`);
    try {
        const result = await _queryDDBAuthorizations(apiKeyValue);
        return result;
    } catch (err) {
        console.log(JSON.stringify(err));
        if (err.error === 'NoAuthorizationsFound') {
            return false;
        }
        return err;
    }
};


// Queries the ApiKeyValues index and only returns enabled keys
// If needed, admins can update the records directly in DynamoDB to disable (but not delete) a key to deactivate it
const _queryDDBAuthorizations = async (apiKeyValue, lastevalkey) => {
    let authorizations = [];
    let params = {
        TableName: process.env.AUTHORIZATIONS_TABLE,
        IndexName: 'ApiKeyValues',
        KeyConditionExpression: 'api_key_value = :apiKeyValue',
        ExpressionAttributeValues: {
            ':apiKeyValue': apiKeyValue,
            ':enabled': true
        },
        FilterExpression : 'enabled = :enabled',
        Limit: 500
    };
    this.creds = new AWS.EnvironmentCredentials('AWS'); // Lambda provided credentials
    this.config = {
      credentials: this.creds,
      region: process.env.AWS_REGION,
    };
    
    if (lastevalkey) {
        params.ExclusiveStartKey = lastevalkey;
    }
    let docClient = new AWS.DynamoDB.DocumentClient(this.config);
    try {
        let result = await docClient.query(params).promise();
        if (result.Items.length < 1){
            console.log(`No authorizations found for api key`);
            return Promise.reject({
                code: 400,
                error: 'NoAuthorizationsFound',
                message: 'No authorizations found for api key'
            });
        }
        result.Items.forEach(function(item) {
            authorizations.push({
                'api_key_id': item.api_key_id,
                'api_key_value': item.api_key_value,
                'application_id': item.application_id,
                'enabled': item.enabled
            });  
        });
        if (result.LastEvaluatedKey) {
            let moreResult = await this._queryDDBAuthorizations(apiKeyValue, lastevalkey);
            moreResult.Items.forEach(function(item) {
                authorizations.push({
                    'api_key_id': item.api_key_id,
                    'api_key_value': item.api_key_value,
                    'application_id': item.application_id,
                    'enabled': item.enabled
                }); 
            });
        }
        return Promise.resolve({
            'authorizations': authorizations,
            'count': authorizations.length
        });
    } catch (err) {
        console.log(JSON.stringify(err));
        return Promise.reject(err);
    }
};
