import requests
import json

def lambda_handler(event, context):
    print(json.dumps(event))
    body = json.loads(event['body'])
    print(json.dumps(body))
    