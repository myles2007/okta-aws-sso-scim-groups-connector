import collections
import requests
import json
import os

import boto3

GroupMemberPatch = collections.namedtuple('GroupMemberPatch', ['targetGoperation', 'display', 'id'])
TARGET_TYPE_GROUP = "UserGroup"
TARGET_TYPE_USER = "User"

AWS_GROUP_PREFIX = os.environ['GROUP_PREFIX']
SCIM_URL = os.environ['SCIM_URL']

PATCH_OPERATION_FOR_OKTA_EVENT = {
    "group.user_membership.add": "add",
    "group.user_membership.remove": "remove"
}


def lambda_handler(event, context):
    okta_event = json.loads(event['body'])
    print(json.dumps(okta_event))
    process_events(okta_event['data']['events'])

def get_event_target_by_type(target, target_type):
    # Currently assumes there is only one entity of each type. This is unverified.
    for entity in target:
        if entity['type'] == target_type:
            return entity

def aws_group_change_events(events):
    # TODO: Consider ordering? Okta's document says ordering isn't guaranteed.
    #       https://developer.okta.com/docs/concepts/event-hooks/#ongoing-event-delivery
    for event in events:
        target_group = get_event_target_by_type(event['target'], TARGET_TYPE_GROUP)
        if target_group['displayName'].startswith(AWS_GROUP_PREFIX):
            yield event

def process_events(events):
    users, groups = None, None

    patches = []
    for event in aws_group_change_events(events):
        scim_key = retrieve_scim_key()
        users = users or get_aws_sso_users(scim_key)
        groups = groups or get_aws_sso_groups(scim_key)

        target = event['target']
        user_target = get_event_target_by_type(target, TARGET_TYPE_USER)
        group_target = get_event_target_by_type(target, TARGET_TYPE_GROUP)

        # The user/group object reachable via the key represents the AWS SSO
        # user knowleddge. The key is the common link.
        user = users[user_target['id']]
        group_id = groups[group_target['displayName']]['id']

        patches.append(
            {
                "resource": f"{SCIM_URL}/Groups/{group_id}",
                "patch": generate_scim_group_member_patch(
                    operation=PATCH_OPERATION_FOR_OKTA_EVENT[event["eventType"]],
                    display=user["displayName"],
                    value=user["id"]
                )
            }
        )

    print(json.dumps(patches))

    # TODO: Probably send to SQS in case there are a lot (or load test with Okta)
    #       I'm not sure how this will complete in Okta's 3 second window if there
    #       are too many events.
    for patch in patches:
        patch_aws_sso_group_membership(scim_key, patch)

def generate_scim_group_member_patch(operation, display, value):
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": operation,
                "path": "members",
                "value": [
                    {
                        "display": display,
                        "value": value
                    }
                ]
            }
        ]
    }

def get_aws_sso_users(scim_key):
    # NOTE: Assumes 1000 or fewer users and that AWS will return
    #       this many users (and in a timely manner).
    number_of_results = 1000
    url = f"{SCIM_URL}/Users?startIndex=1&count={number_of_results}"
    response = requests.get(url, headers={'Authorization': f'Bearer {scim_key}'})
    response.raise_for_status()

    users = {
        user['externalId']: user for user in response.json()["Resources"]
    }

    return users

def patch_aws_sso_group_membership(scim_key, patch):
    response = requests.patch(
        patch['resource'],
        json=patch['patch'],
        headers={'Authorization': f'Bearer {scim_key}'}
    )
    response.raise_for_status()

def get_aws_sso_groups(scim_key):
    # NOTE: Assumes 1000 or fewer groups and that AWS will return
    #       this many users (and in a timely manner).
    number_of_results = 1000
    url = f"{SCIM_URL}/Groups?startIndex=1&count={number_of_results}"
    response = requests.get(url, headers={'Authorization': f'Bearer {scim_key}'})
    response.raise_for_status()

    groups = {
        group['displayName']: group for group in response.json()["Resources"]
    }

    return groups

def retrieve_scim_key():
    client = boto3.client('secretsmanager')
    secret =  client.get_secret_value(
        SecretId="app/okta-to-aws-sso"
    )
    secret_string = json.loads(secret['SecretString'])
    scim_key = secret_string['aws_sso_scim_key']
    return scim_key
