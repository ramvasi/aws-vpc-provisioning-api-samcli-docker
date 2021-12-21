"""Used to get information from VPCx accounts"""
import logging
import json
import traceback
import requests

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class AccountMetadataException(Exception):
    """
    Exception raised when failed to retrieve account number

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="AppSync API returned error"):
        self.message = message
        super().__init__(self.message)


def get_current_account_metadata(account_alias, appsync_endpoint, appsync_api_key):
    """
        Check if row already exists in Accounts table or not

        Args:
            account_alias: account alias
            appsync_endpoint: AppSync API endpoint
            appsync_api_key: API Key

        Returns: account number and id
    """
    LOGGER.info('Sending get account metadata request for account %s', account_alias)
    # Setup query
    query = '''
                query GetAccountByProjectId($project_id: String) {
                GetAccountByProjectId(project_id: $project_id) {
                    items {
                    id
                    aws_number
                    project_id
                    owner
                    log_buckets
                    regions  
                    },
                    nextToken
                }
                }
                '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': appsync_api_key,
        "Authorization": appsync_api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        'project_id': account_alias
    }
    # Send request
    try:
        response = requests.post(appsync_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from get account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            next_token = response_body['data']['GetAccountByProjectId']['nextToken']
            items = response_body['data']['GetAccountByProjectId']['items']
            # Ensure only 1 result was found
            if not items:
                return None
            elif len(items) != 1 or next_token:
                LOGGER.info("Multiple entries found for account %s", account_alias)
                return None
            else:
                return items[0]
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to retrieve account metadata")
        LOGGER.exception(str(e))
        raise e


def insert_account_metadata(input_data, appsync_endpoint, appsync_api_key):
    """
    Insert data in accounts table

    Args:
        input_data: data dictionary
        appsync_endpoint: AppSync API endpoint
        appsync_api_key: API Key

    Returns: inserted data
    """
    LOGGER.info('Sending insert account metadata request for account %s', input_data["project_id"])
    # Setup query
    query = '''
            mutation CreateAccount($input: CreateAccountInput!) {
              createAccount(input: $input) {
                  id
                  aws_number 
                  project_id
                  owner 
                  regions
                  log_buckets
              }
            }
            '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': appsync_api_key,
        "Authorization": appsync_api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        "input": input_data
    }
    # Send request
    try:
        response = requests.post(appsync_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from insert account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            if response_body.get('errors'):
                LOGGER.error(json.dumps(response_body))
                raise AccountMetadataException()
            elif response_body['data']:
                result = response_body['data']['createAccount']
                return result
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to insert account metadata ")
        raise e


def update_account_metadata(input_data, appsync_endpoint, appsync_api_key):
    """
        Update table for a pre existing row

        Args:
            input_data: data dictionary
            appsync_endpoint: GraphQL endpoint
            appsync_api_key:  API Key for AppSync API

        Returns: updated data
    """
    LOGGER.info('Sending update account metadata request for account %s', input_data["project_id"])
    # Setup query
    query = '''
            mutation UpdateAccount($input: UpdateAccountInput!) {
            updateAccount(input: $input) {
                id
                aws_number
                project_id
                owner
                log_buckets
                regions 
            }
            }
            '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': appsync_api_key,
        "Authorization": appsync_api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        'input': input_data
    }
    # Send request
    try:
        response = requests.post(appsync_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from update account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            if response_body.get('errors'):
                LOGGER.error(json.dumps(response_body))
                raise AccountMetadataException()
            elif response_body['data']:
                result = response_body['data']['updateAccount']
                return result
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to update account metadata ")
        raise e


def delete_account_metadata(input_data, appsync_endpoint, appsync_api_key):
    """
        Delete row from table

        Args:
            input_data: data dictionary
            appsync_endpoint: GraphQL endpoint
            appsync_api_key:  API Key for AppSync API

        Returns: updated data
    """
    LOGGER.info('Sending delete account metadata request for id %s', input_data["id"])
    # Setup query
    query = '''
            mutation DeleteAccount($input: DeleteAccountInput!) {
              deleteAccount(input: $input){
                id
                project_id
              }
            }
            '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': appsync_api_key,
        "Authorization": appsync_api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        'input': input_data
    }
    # Send request
    try:
        response = requests.post(appsync_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from delete account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            if response_body.get('errors'):
                LOGGER.error(json.dumps(response_body))
                raise AccountMetadataException()
            elif response_body['data']:
                result = response_body['data']['deleteAccount']
                return result
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to delete account metadata")
        raise e

def get_account_by_aws_number(aws_number, appsync_endpoint, appsync_api_key):
    """
        Check if row already exists in Accounts table or not

        Args:
            aws_number: account number
            appsync_endpoint: AppSync API endpoint
            appsync_api_key: API Key

        Returns: account number and id

    """
    LOGGER.info('Getting account by aws number for account %s', aws_number)
    # Setup query
    query = '''
                query GetAccountByAWSNumber($aws_number: String) {
                  GetAccountByAWSNumber(aws_number: $aws_number) {
                    items {
                      aws_number
                      project_id
                    }
                    nextToken
                  }
                }
                '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': appsync_api_key,
        "Authorization": appsync_api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        'aws_number': aws_number
    }
    # Send request
    try:
        response = requests.post(appsync_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from get account by aws number %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            next_token = response_body['data']['GetAccountByAWSNumber']['nextToken']
            items = response_body['data']['GetAccountByAWSNumber']['items']
            # Ensure only 1 result was found
            if not items:
                return None
            elif len(items) != 1 or next_token:
                LOGGER.info("Multiple entries found for account %s", aws_number)
                return None
            else:
                return items[0]
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to retrieve account by aws_number")
        LOGGER.exception(str(e))
        raise e

