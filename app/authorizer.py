import json
import boto3

EFFECT_DENY = 'Deny'
EFFECT_ALLOW = 'Allow'

def retrieve_auth_token():
    client = boto3.client('secretsmanager')
    secret =  client.get_secret_value(
        SecretId="app/okta-to-aws-sso"
    )
    return json.loads(secret['SecretString'])['auth_token_for_okta']

AUTH_TOKEN = retrieve_auth_token()

def lambda_handler(event, context):
    print(json.dumps(event))
    provided_token = event['headers']['Authorization']
    principal_id = event['headers']['x-api-key']
    resource = event['methodArn']

    policy = generate_policy(principal_id, EFFECT_DENY, resource)
    if provided_token == AUTH_TOKEN:
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