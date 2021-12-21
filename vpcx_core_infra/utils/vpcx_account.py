"""Used to get information from VPCx accounts"""
import logging
import requests
import json
import traceback

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


# Define exception for failure to find account ID
class AccountNumberException(Exception):
    """
    Exception raised when failed to retrieve account number

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="Failed to retrieve account number."):
        self.message = message
        super().__init__(self.message)


def get_vpcx_account_admin_credentials(vpc_endpoint_hostname, creds_hostname,
                                       access_token, account_alias):
    """
    Get VPCx account admin credentials.

    Args:
        vpc_endpoint_hostname: Hostname to call creds endpoint
        creds_hostname: API GW hostname needed in header
        access_token: Access token
        account_alias: account alias

    Returns: account credentials (access key, secret access key, session)
    """
    # Replace account in URL
    url = vpc_endpoint_hostname.replace('<ACCOUNT_ALIAS>', account_alias)
    # Set additional headers
    headers = {
        'Host': creds_hostname,
        'Authorization': 'Bearer {}'.format(access_token)
    }
    # Request credentials
    LOGGER.info('Requesting credentials from %s', url)
    try:
        response = requests.get(url, headers=headers)
        if response.ok:
            response_body = json.loads(response.text)
            return response_body['credentials']
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to retrieve creds %s", e)
        raise e


def translate_account_alias_to_account_number(account_alias, gql_endpoint, api_key):
    """
    Translate account alias to account number

    Args:
        account_alias: account alias
        gql_endpoint: AppSync GraphQL endpoint
        api_key: API Key for GraphQL endpoint

    Returns: account number
    """
    LOGGER.info('Sending account metadata request for account %s', account_alias)
    # Setup query
    query = '''
        query GetAccountByProjectId($project_id: String) {
        GetAccountByProjectId(project_id: $project_id) {
            items {
            aws_number   
            },
            nextToken
        }
        }
        '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': api_key,
        "Authorization": api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Setup variables
    variables = {
        'project_id': account_alias
    }
    # Send request
    try:
        response = requests.post(gql_endpoint,
                                 json={
                                     'query': query,
                                     'variables': variables
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            next_token = response_body['data']['GetAccountByProjectId']['nextToken']
            items = response_body['data']['GetAccountByProjectId']['items']
            # Ensure only 1 result was found
            if not items:
                raise AccountNumberException('No response found.')
            elif len(items) != 1 or next_token:
                raise AccountNumberException('More than one account found.')
            else:
                return items[0]['aws_number']
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to retrieve account metadata %s", e)
        raise e


def get_all_accounts_in_env(gql_endpoint, api_key):
    """
    Get all accounts in an environment

    Args:
        gql_endpoint: AppSync GraphQL endpoint
        api_key: API Key for GraphQL endpoint

    Returns: list of all accounts in an environment
    """
    LOGGER.info('Retrieving all account aliases')
    # Setup query
    query = '''
        query getAllAccounts($next_token: String) {
            listAccounts(nextToken: $next_token) {
                items {
                    project_id
                    aws_number
                },
                nextToken
            }
        }
        '''
    # Setup headers
    headers = {
        'Content-Type': "application/json",
        'x-api-key': api_key,
        "Authorization": api_key,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
    }
    # Collect all accounts
    accounts = set()
    try:
        response = requests.post(gql_endpoint,
                                 json={
                                     'query': query
                                 },
                                 headers=headers)
        # Evaluate response
        if response.ok:
            LOGGER.info('Received response from account metadata request %s', response.text)
            # Unpack results
            response_body = json.loads(response.text)
            next_token = response_body['data']['listAccounts']['nextToken']
            items = response_body['data']['listAccounts']['items']
            # Add accounts to list of accounts
            for item in items:
                accounts.add(item.get('project_id'))
            # Check next token
            while next_token:
                # Set variables
                variables = {
                    '$next_token': next_token
                }
                response = requests.post(gql_endpoint,
                                         json={
                                             'query': query,
                                             'variables': variables
                                         },
                                         headers=headers)
                LOGGER.info('Received response from account metadata request %s', response.text)
                if response.ok:
                    # Unpack results
                    response_body = json.loads(response.text)
                    next_token = response_body['data']['listAccounts']['nextToken']
                    items = response_body['data']['listAccounts']['items']
                    # Add accounts to list of accounts
                    for item in items:
                        accounts.add(item.get('project_id'))
                else:
                    response.raise_for_status()
        else:
            response.raise_for_status()
    except Exception as e:
        LOGGER.exception("Failed to retrieve account metadata %s", e)
        raise e
    # Remove any accounts with "test" in them
    LOGGER.info("Retrieved accounts list %s", accounts)
    accounts_list = [account for account in list(accounts) if 'test' not in account]
    # Return filtered accounts
    LOGGER.info("Filtered accounts list %s", accounts_list)
    return accounts_list


def derive_new_account_alias(current_account_aliases, lower_bound, upper_bound, exception_list):
    """
    Given a list of current account aliases, return the next alphanumeric account alias

    Args:
        current_account_aliases: sorted list of current account aliases
        lower_bound: lower bound account alias for env
        upper_bound: upper bound account alias for env
        exception_list: exception list of accounts

    Returns: new account alias
    """
    LOGGER.info("Deriving new account alias based on %s", current_account_aliases)
    # Verify boundary conditions
    if min(lower_bound, upper_bound) != lower_bound:
        raise AccountNumberException('Lower bound must be less than upper bound.')
    elif not (lower_bound.startswith('itx-') and upper_bound.startswith('itx-')):
        raise AccountNumberException('Invalid boundary condition format.')
    # Check base case
    if not current_account_aliases:
        LOGGER.info("Empty current account alias list found.")
        if lower_bound not in exception_list:
            LOGGER.info("Returning lower bound as account alias.")
            return lower_bound
    # Start at lower bound and iterate through until appropriate alias is found (or upper bound is reached)
    current_alias = lower_bound
    while current_alias != upper_bound:
        # Generate next alias
        next_account_alias = generate_next_alphanumeric(current_alias)
        # Check if used or in exception list
        if (next_account_alias in exception_list) or (next_account_alias in current_account_aliases):
            current_alias = next_account_alias
        # Else, this account alias is acceptable
        else:
            LOGGER.info("Account alias found: %s", next_account_alias)
            return next_account_alias
    # Upper bound reached and no alias found
    raise AccountNumberException('Account alias beyond upper bound.')


def generate_next_alphanumeric(s):
    """
    Generate the next alphanumeric account alias

    Args:
        s: sorted list of current account aliases

    Returns: next account alias
    """
    strip_zs = s.lower().rstrip('z')
    if strip_zs:
        return strip_zs[:-1] + chr(ord(strip_zs[-1]) + 1) + 'a' * (len(s) - len(strip_zs))
    return 'a' * (len(s) + 1)