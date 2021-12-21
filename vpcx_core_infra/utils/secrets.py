"""Shared functions for account provisioning secrets"""
import base64
import logging
import json
import traceback
import boto3
import requests


# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Define secrets client
SECRETS_CLIENT = boto3.client('secretsmanager')


def retrieve_ldap_credentials(ldap_credentials_secret_name):
    """
    Retrieve LDAP password from secrets manager

    Args:
        ldap_credentials_secret_name: secret name in Secrets Manager

    Returns: tuple of username, password
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=ldap_credentials_secret_name
    )
    secret = json.loads(secret_response['SecretString'])
    return secret['username'], secret['password']


def retrieve_vpcx_appsync_info(vpcx_appsync_secret_name):
    """
    Retrieve VPCX Appsync url and api keys from Secrets Manager.

    NOTE: this is a shared secret.  This secret does not belong
    to the account provisioning stack.

    Args:
        vpcx_appsync_secret_name: secret name in Secrets Manager

    Returns: tuple of GraphQL URL, and API key
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=vpcx_appsync_secret_name
    )
    secret = json.loads(secret_response['SecretString'])
    return secret['url'], secret['key']


def retrieve_bitbucket_credentials(bitbucket_credentials_secret_name):
    """
    Retrieve bitbucket credentials

    Args:
        bitbucket_credentials_secret_name: secret name in Secrets Manager

    Returns: tuple of username, password
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=bitbucket_credentials_secret_name
    )
    secret = json.loads(secret_response['SecretString'])
    return secret['username'], secret['password']


def retrieve_api_key(cloud_conformity_api_key_secret_name):
    """
    Retrieve API Key from secrets manager

    Args:
        cloud_conformity_api_key_secret_name: secret name in Secrets Manager

    Returns: secret
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=cloud_conformity_api_key_secret_name
    )
    return secret_response['SecretString']


def retrieve_client_secret(client_secret_secret_name):
    """
    Retrieve client secret from secrets manager

    Args:
        client_secret_secret_name: secret name in Secrets Manager

    Returns: secret
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=str(client_secret_secret_name)
    )
    return secret_response['SecretString']


def retrieve_idms_credentials(idms_credentials_secret_name):
    """
    Retrieve IDMS credentials

    Args:
        idms_credentials_secret_name: secret name in Secrets Manager

    Returns: tuple of username, password
    """
    secret_response = SECRETS_CLIENT.get_secret_value(
        SecretId=idms_credentials_secret_name
    )
    secret = json.loads(secret_response['SecretString'])
    return secret['username'], secret['password']


def retrieve_appdevtools_access_token(username, password, auth_endpoint):
    """
    Retrieve access token for appdev tools

    Args:
        username: username
        password: password
        auth_endpoint: authorization endpoint

    Returns: token
    """
    # Form credentials request
    credentials = "{0}:{1}".format(username, password)
    base_encoded_credential = base64.b64encode(bytes(credentials, "utf-8")).decode().replace('\n', '')
    # Form application headers
    headers = {
        "content-type": "application/json",
        "Authorization": "Basic {}".format(base_encoded_credential)
    }
    # Form login request
    login_request = {
        "username": username,
        "password": password
    }
    # Issue request, skip SSL validation
    response = requests.post(url=auth_endpoint, json=login_request,
                             headers=headers, verify=True)
    # Get access token
    return json.loads(response.text)["token"]


def retrieve_idms_session_cookies(idms_username, idms_password, idms_auth_endpoint):
    """
    Retrieve session token to interact with AD endpoint

    Args:
        idms_username: IDMS username
        idms_password: IDMS password
        idms_auth_endpoint: IDMS auth endpoint

    Returns: cookies from IDMS
    """
    # Generate payload
    auth_string = "Module=RoleBasedManualADS;User={};Password={}".format(
        idms_username,
        idms_password
    )
    auth_request = {
        "AuthString": auth_string
    }
    # Prepare headers
    headers = {
        'Content-Type': 'application/json'
    }
    auth_request = json.dumps(auth_request)
    # Issue token call
    response = requests.post(url=idms_auth_endpoint,
                             data=auth_request,
                             headers=headers)
    if response.ok:
        return response.cookies
    else:
        LOGGER.error("Failed to retrieve IDMS session cookies. Error %s, %s",
                     response.status_code,
                     response.text)
        response.raise_for_status()


def get_azure_ad_access_token(client_id, tenant_id, client_secret, scope):
    """
    Get access token via client_credentials grant.

    Args:
        client_id: Azure AD client ID
        tenant_id: J&J Azure tenant ID
        client_secret: Azure AD client secret for this application
        scope: client scope

    Returns: access token
    """
    msft_idp_endpoint = "https://login.microsoftonline.com/"
    # Setup endpoint
    oauth_endpoint = msft_idp_endpoint + tenant_id + "/oauth2/v2.0/token"
    # Generate payload dict
    token_request = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": scope
    }
    # Issue token call
    try:
        LOGGER.info("Retrieving access token for %s", client_id)
        response = requests.post(url=oauth_endpoint, data=token_request)
        if response.ok:
            return json.loads(response.text)["access_token"]
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.error("Failed to retrieve access token: %s", e)
        traceback.print_exc()
