import json
import boto3

print("Getting secret...")
AUTH_SECRET = retrieve_secret()
print(AUTH_SECRET)

def retrieve_secret():
    client = boto3.client('secretsmanager')
    return client.get_secret_value(
        SecretId="app/okta-to-aws-sso"
    )

def lambda_handler(event, context):
    print(json.dumps(event))
    return None