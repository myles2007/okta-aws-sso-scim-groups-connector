import datetime
import json

import boto3

CACHED_AUTH_TOKEN = None # Once set, wait at least TOKEN_CACHE_TIME to look up.
TOKEN_CACHE_TIME = 300 # seconds
LAST_CACHE_TIME = None

# Possible policy effects
EFFECT_DENY = 'Deny'
EFFECT_ALLOW = 'Allow'

def retrieve_auth_token():
    global CACHED_AUTH_TOKEN, LAST_CACHE_TIME

    # If there is no cache time, use the min possible date
    LAST_CACHE_TIME = LAST_CACHE_TIME or datetime.datetime.min
    token_cache_delta = datetime.datetime.now() - LAST_CACHE_TIME
    token_cache_delta_in_seconds = token_cache_delta.total_seconds()
    token_cache_expired = token_cache_delta_in_seconds > TOKEN_CACHE_TIME

    if not CACHED_AUTH_TOKEN or token_cache_expired:
        client = boto3.client('secretsmanager')
        secret =  client.get_secret_value(
            SecretId="app/okta-to-aws-sso"
        )
        secret_string = json.loads(secret['SecretString'])
        CACHED_AUTH_TOKEN = secret_string['auth_token_for_okta']
        LAST_CACHE_TIME = datetime.datetime.now()

    return CACHED_AUTH_TOKEN

def lambda_handler(event, context):
    provided_token = event['headers']['Authorization']
    principal_id = event['headers']['x-api-key']
    resource = event['methodArn']
    expected_token = retrieve_auth_token()

    policy = generate_policy(principal_id, EFFECT_DENY, resource)
    if provided_token == expected_token:
        policy = generate_policy(principal_id, EFFECT_ALLOW, resource)

    print(json.dumps(policy))

    return policy

def generate_policy(principal_id, effect, resource):
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }

    }