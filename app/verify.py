import json

def lambda_handler(event, context):

    response = {
        "statusCode": 200,
        "headers": {
            "content-type": "application/json"
        }
    }

    response_body = {
        "verification": event['headers']['X-Okta-Verification-Challenge']
    }

    response['body'] = json.dumps(response_body)
    print(json.dumps(response))

    return response
