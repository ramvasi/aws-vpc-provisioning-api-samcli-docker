"""Used to get information about VPCx regions"""
import logging
import json
import boto3

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

# Define constant param path
PARAM_PATH = '/vpcx/aws/regions/'


# Define constant param path
PARAM_PATH = '/vpcx/aws/regions/'


def get_ssm_region_params(ssm_client=boto3.client('ssm')):
    """
    Retrieve all regional params from param store.

    Returns a dict of params by region.  Example:
    {
      "us-east-1": "... param value ...",
      "us-east-1": "... param value ..."
    }

    Args:
        ssm_client: SSM client for param store

    Returns: dict of param
    """
    parameters = []
    paginator = ssm_client.get_paginator('get_parameters_by_path')
    pages = paginator.paginate(
        Path=PARAM_PATH,
        Recursive=False,
        WithDecryption=True
    )
    for page in pages:
        parameters.extend(page["Parameters"])

    LOGGER.info("Retrieved parameters %s", parameters)
    # Format response
    active_regions = {}
    for parameter in parameters:
        region_name = parameter['Name'].replace(PARAM_PATH, "")
        active_regions[region_name] = json.loads(parameter['Value'])
    LOGGER.info("Returning formatted response %s", active_regions)
    # Return response
    return active_regions
