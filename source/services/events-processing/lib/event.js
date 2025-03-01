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

const AWS = require('aws-sdk');
const _ = require('underscore');
const moment = require('moment');
const event_schema = require('../config/event_schema.json');
const Ajv2020 = require('ajv/dist/2020');
const { v4: uuidv4 } = require('uuid');

const ajv = new Ajv2020();
var validate = ajv.compile(event_schema);

const creds = new AWS.EnvironmentCredentials('AWS'); // Lambda provided credentials
const dynamoConfig = {
  credentials: creds,
  region: process.env.AWS_REGION
};

console.log(`Loaded event JSON Schema: ${JSON.stringify(event_schema)}`);

class Event {
  
  constructor() {
    this.dynamoConfig = dynamoConfig;
  }

  /**
  * Process an event record sent to the events stream
  * Format processing output in format required by Kinesis Firehose
  * @param {JSON} input - game event input payload
  * @param {string} recordId - recordId from Kinesis
  * @param {JSON} context - AWS Lambda invocation context (https://docs.aws.amazon.com/lambda/latest/dg/nodejs-context.html)
  */
  async processEvent(input, recordId, context) {
    const _self = this;
    try {
      // Extract event object and applicationId string from payload. application_id and event are required or record fails processing
      if(!input.hasOwnProperty('application_id')){
        return Promise.reject({
          recordId: recordId,
          result: 'ProcessingFailed',
          data: new Buffer.from(JSON.stringify(input) + '\n').toString('base64')
        });
      }
      if(!input.hasOwnProperty('event')){
        return Promise.reject({
          recordId: recordId,
          result: 'ProcessingFailed',
          data: new Buffer.from(JSON.stringify(input) + '\n').toString('base64')
        });
      }
      const applicationId = input.application_id;
      const country = input.country;
      const event = input.event;
      
      // Add a processing timestamp and the Lambda Request Id to the event metadata
      let metadata = {
        ingestion_id: context.awsRequestId,
        processing_timestamp: moment().unix()
      };

      // If event came from Solution API, it should have extra metadata
      if (input.aws_ga_api_validated_flag) {
        metadata.api = {};
        if (input.aws_ga_api_requestId) { 
          metadata.api.request_id = input.aws_ga_api_requestId; 
          delete input.aws_ga_api_requestId;
        }
        if (input.aws_ga_api_requestTimeEpoch) {
          metadata.api.request_time_epoch = input.aws_ga_api_requestTimeEpoch;
          delete input.aws_ga_api_requestTimeEpoch;
        }
        delete input.aws_ga_api_validated_flag;
      }

      // Retrieve application config from Applications table
      const application = await _self.getApplication(applicationId);
      if (application !== null) {
        // Validate the input record against solution event schema
        const schemaValid = await _self.validateSchema(input);
        let transformed_event = {};
        if (schemaValid.validation_result == 'schema_mismatch') {
          metadata.processing_result = {
            status: 'schema_mismatch',
            validation_errors: schemaValid.validation_errors
          };
          transformed_event.metadata = metadata;
          //console.log(`Errors processing event: ${JSON.stringify(errors)}`);
        } else {
          metadata.processing_result = {
            status: 'ok'
          };
          transformed_event.metadata = metadata;
        }

        if (await _self.eventAlreadyProcessed(event.event_id, event.event_timestamp)) {
          return Promise.resolve({
            recordId: recordId,
            result: 'Dropped',
            data: new Buffer.from(JSON.stringify(input) + '\n').toString('base64')
          });
        }

        if(event.hasOwnProperty('event_id')){
          transformed_event.event_id = String(event.event_id);
        }
        if(event.hasOwnProperty('event_type')){
          transformed_event.event_type = String(event.event_type);
        }
        if(event.hasOwnProperty('event_name')){
          transformed_event.event_name = String(event.event_name);
        }
        if(event.hasOwnProperty('event_version')){
          transformed_event.event_version = String(event.event_version);
        }
        if(event.hasOwnProperty('event_timestamp')){
          transformed_event.event_timestamp = Number(event.event_timestamp);
        }
        if(event.hasOwnProperty('game_time')){
          transformed_event.game_time = Number(event.game_time);
        }
        if(event.hasOwnProperty('app_info')){
          transformed_event.app_info = event.app_info;
        }
        if(event.hasOwnProperty('user')){
          transformed_event.user = event.user;
          if (transformed_event.event_type != "server") {
            // if event_type == "server", the country is already retrieved in the user app state
            // server events are sent by our servers which are based in the US,
            // so the country will always be equal to US
            transformed_event.user.country = String(country)
          }
        }
        if(event.hasOwnProperty('device')){
          if (!event.device.hasOwnProperty('analytics_installation_id')) {
            // This field exists in UserAppStates for these versions :
            // CoeurDeGem : 3.1.4 and above
            // Dazzly : 1.4.0 and above
            // DazzlyMatch : 1.4.0 and above
            event.device.analytics_installation_id = uuidv4();
          }
          transformed_event.device = event.device;
        }
        if(event.hasOwnProperty('remote_config')){
          transformed_event.remote_config = event.remote_config;
        }
        if(event.hasOwnProperty('attribution')){
          transformed_event.attribution = event.attribution;
        } else {
          // This field not exists in UserAppStates for these versions:
          // CoeurDeGem : 3.1.2 and below
          // Dazzly : 1.2.1 and below
          // DazzlyMatch : 1.4.0 and below
          transformed_event.attribution = {};
        }
        if(event.hasOwnProperty('event_data')){
          transformed_event.event_data = event.event_data;
          if(event.event_data.hasOwnProperty('currency') && event.event_data.hasOwnProperty('revenues')){
            let rate = await _self.getExchangeRate(event.event_data.currency)
            transformed_event.event_data.revenues_usd = event.event_data.revenues / rate
          }
        }
        
        transformed_event.application_name = String(application.application_name);

        if (transformed_event.device.advertising_id == "00000000-0000-0000-0000-000000000000" && transformed_event.attribution.hasOwnProperty("advertising_id")) {
          // Sometimes, device.advertising_id was dummy UID for there versions:
          // CoeurDeGem : 3.1.2 and below
          // Dazzly (only android) : 1.4.0 and below
          // DazzlyMatch : 1.5.1 and below
          // Tenjin never gives a DUMMY UID, when Tenjin doesn't have access to the advertising_id, the field is simply not present in attribution.
          // So if there is the transform_event.attribution.advertising_id field, then Tenjin must have succeeded in recovering it --> We can track user
          transformed_event.device.advertising_id = transformed_event.attribution.advertising_id
          transformed_event.device.is_limiting_ad_tracking = false
        }

        // On older versions of Dazzly iOS, is_limiting_ad_tracking was String
        if (transformed_event.device.is_limiting_ad_tracking === "0") {
          transformed_event.device.is_limiting_ad_tracking = false
        } else if (transformed_event.device.is_limiting_ad_tracking === "1") {
          transformed_event.device.is_limiting_ad_tracking = true
        }

        if (["app_update", "session_start"].includes(transformed_event.event_name)) {
          await _self.setUserAppState(transformed_event, applicationId)
        }

        return Promise.resolve({
          recordId: recordId,
          result: 'Ok',
          data: new Buffer.from(JSON.stringify(transformed_event) + '\n').toString('base64')
        });
      } else {
        /**
         * Handle events from unregistered ("NOT_FOUND") applications
         * Sets processing result as "unregistered"
         * We don't attempt to validate schema of unregistered events, we just coerce the necessary fields into expected format 
         */
        metadata.processing_result = {
          status: 'unregistered'
        };
        let unregistered_format = {};
        unregistered_format.metadata = metadata;
        
        if(event.hasOwnProperty('event_id')){
          unregistered_format.event_id = String(event.event_id);
        }
        if(event.hasOwnProperty('event_type')){
          unregistered_format.event_type = String(event.event_type);
        }
        if(event.hasOwnProperty('event_name')){
          unregistered_format.event_name = String(event.event_name);
        }
        if(event.hasOwnProperty('event_version')){
          unregistered_format.event_version = String(event.event_version);
        }
        if(event.hasOwnProperty('event_timestamp')){
          unregistered_format.event_timestamp = Number(event.event_timestamp);
        }
        if(event.hasOwnProperty('game_time')){
          unregistered_format.game_time = Number(event.game_time);
        }
        if(event.hasOwnProperty('app_info')){
          unregistered_format.app_info = event.app_info;
        }
        if(event.hasOwnProperty('event_data')){
          unregistered_format.event_data = event.event_data;
          if(event.event_data.hasOwnProperty('currency') && event.event_data.hasOwnProperty('revenues')){
            let rate = await _self.getExchangeRate(event.event_data.currency)
            unregistered_format.event_data.revenues_usd = event.event_data.revenues / rate
          }
        }
        if(event.hasOwnProperty('user')){
          unregistered_format.user = event.user;
          unregistered_format.user.country = String(country)
        }
        if(event.hasOwnProperty('device')){
          unregistered_format.device = event.device;
        }
        if(event.hasOwnProperty('remote_config')){
          unregistered_format.remote_config = event.remote_config;
        }
        if(event.hasOwnProperty('attribution')){
          unregistered_format.attribution = event.attribution;
        } else {
          // This field not exists in UserAppStates for these versions :
          // CoeurDeGem : 3.1.3 and below
          // Dazzly : 1.2.1 and below
          // DazzlyMatch : 1.4.0 and below
          unregistered_format.attribution = {};
        }
        
        return Promise.resolve({
          recordId: recordId,
          result: 'Ok',
          data: new Buffer.from(JSON.stringify(unregistered_format) + '\n').toString('base64')
        });
      } 
    } catch (err) {
      console.log(`Error processing record: ${JSON.stringify(err)}`);
      return Promise.reject({
        recordId: recordId,
        result: 'ProcessingFailed',
        data: new Buffer.from(JSON.stringify(input) + '\n').toString('base64')
      });
    }
  }
  

  /**
   * Retrieve event_id from DynamoDB
   * If not in Dynamo Table, add it
   * Returns bool
   */
  async eventAlreadyProcessed(eventID, eventTimestamp) {
    const params = {
      TableName: process.env.IDEMPOTENCY_TABLE,
      Key: {
        event_id: eventID
      }
    };
    
    // get from DynamoDB
    const docClient = new AWS.DynamoDB.DocumentClient(this.dynamoConfig);
    try {
      let data = await docClient.get(params).promise();
      if (!_.isEmpty(data)) {
        // This event has already been processed
        return Promise.resolve(true);
      } else {
        // This event has never been processed
        // There is 86400 seconds in one day
        const putParams = {
          TableName: process.env.IDEMPOTENCY_TABLE,
          Item: {
            event_id: eventID,
            expires_timestamp: eventTimestamp + 86400 * 7
          }
        };
        await docClient.put(putParams).promise();
        return Promise.resolve(false);
      }
    } catch (err) {
      console.log(JSON.stringify(err));
      return Promise.reject(err);
    }
  }

  /**
   * Retrieve application from DynamoDB
   * Fetches from and updates the local registered applications cache with results
   */
  async getApplication(applicationId) {
    const params = {
      TableName: process.env.APPLICATIONS_TABLE,
      Key: {
        application_id: applicationId
      }
    };
    
    // first try to fetch from cache
    let applicationsCacheResult = global.applicationsCache.get(applicationId);
    if (applicationsCacheResult == 'NOT_FOUND') {
      // if already marked not found, skip processing. Applications will remain "NOT_FOUND" until the cache refresh
      return Promise.resolve(null);
    } else if (applicationsCacheResult == undefined) {
      // get from DynamoDB and set in Applications cache
      const docClient = new AWS.DynamoDB.DocumentClient(this.dynamoConfig);
      try {
        let data = await docClient.get(params).promise();
        if (!_.isEmpty(data)) {
          // if found in ddb, set in cache and return it
          global.applicationsCache.set(applicationId, data.Item);
          return Promise.resolve(data.Item);
        } else {
          // if application isn't registered in dynamodb, set not found in cache
          console.log(`Application ${applicationId} not found in DynamoDB`);
          global.applicationsCache.set(applicationId, 'NOT_FOUND');
          return Promise.resolve(null);
        }
      } catch (err) {
        console.log(JSON.stringify(err));
        return Promise.reject(err);
      }
    } else {
      // if in cache, return it
      return Promise.resolve(applicationsCacheResult);
    }
  }

  /**
   * Retrieve exchange rate from DynamoDB
   * The base currency is USD.
   */
  async getExchangeRate(currency) {
    const params = {
      TableName: process.env.EXCHANGE_RATES_TABLE,
      Key: {
        currency: currency.toUpperCase()
      }
    };
    
    // first try to fetch from cache
    let currencyCacheResult = global.currencyCache.get(currency)
    if (currencyCacheResult == undefined) {
      // get from DynamoDB and set in Applications cache
      const docClient = new AWS.DynamoDB.DocumentClient(this.dynamoConfig);
      try {
        let data = await docClient.get(params).promise();
        // if found in ddb, set in cache and return it
        const { rate } = data.Item;
        global.currencyCache.set(currency, rate);
        return Promise.resolve(rate);
      } catch (err) {
        console.log(JSON.stringify(err));
        return Promise.reject(err);
      }
    } else {
      // if in cache, return it
      return Promise.resolve(currencyCacheResult);
    }
  }

  /**
   * Set User App State in DynamoDB.
   */
  async setUserAppState(event, applicationId) {
    const params = {
      TableName: process.env.USER_APP_STATES_TABLE,
      Item: {
        user_id: event.user.user_id,
        application_id: applicationId,
        app_info: JSON.stringify(event.app_info),
        attribution: JSON.stringify(event.attribution),
        device: JSON.stringify(event.device),
        game_time: event.game_time,
        remote_config: JSON.stringify(event.remote_config),
        user: JSON.stringify(event.user)
      }
    };

    const docClient = new AWS.DynamoDB.DocumentClient(this.dynamoConfig);
    try {
      const data = await docClient.put(params).promise();
      console.log(data)
      return Promise.resolve()
    } catch (err) {
      console.log(JSON.stringify(err));
      return Promise.reject(err);
    }
  }

  /**
   * Validate input data against JSON schema
   */
  async validateSchema(data) {
    try {
      let valid = validate(data);
      if (!valid) {
        let errors = validate.errors;
        return Promise.resolve({
          validation_result: 'schema_mismatch',
          validation_errors: errors
        });
      } else {
        return Promise.resolve({
          validation_result: 'ok'
        });
      }
    } catch (err) {
      console.log(`There was an error validating the schema ${JSON.stringify(err)}`);
      return Promise.reject(err);
    }
  }
}


module.exports = Event;