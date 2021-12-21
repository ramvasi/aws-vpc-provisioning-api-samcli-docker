"""Shared functions for account provisioning assume role interactions"""
import logging
import traceback
import boto3

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Define service client
STS_CLIENT = boto3.client('sts')


def assume_cross_account_role(account_number, role_name):
    """
    Assume role in target account

    Args:
        account_number: account number (123456789)
        role_name: IAM role name to assume account

    Returns: tuple.  success (True) / failure (False), credentials
    """
    # Format role string
    role_arn = "arn:aws:iam::{}:role/{}".format(account_number, role_name)
    # Assume cross-account role and extract credentials
    try:
        acct = STS_CLIENT.assume_role(
            RoleArn=role_arn,
            RoleSessionName="cross_account_account_provisioning"
        )
    except Exception as e:
        LOGGER.error(e)
        traceback.print_exc()
        return False, None
    return True, acct['Credentials']
