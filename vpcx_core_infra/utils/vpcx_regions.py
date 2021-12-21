"""Used to get information about VPCx regions"""
import logging
import re
import boto3
import json

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def get_vpcx_active_regions(ssm_client=boto3.client('ssm')):
    """
    Retrieve regions currently active for VPCx from param store
    Returns: array of AWS regions
    """
    """
    get_parameters_by_path returns a maximum of 10 results in single API call. 
    Use NextToken to get complete list of regions. 
    """
    response = ssm_client.get_parameters_by_path(
        Path='/vpcx/aws/regions/',
        Recursive=False,
        WithDecryption=True
    )
    parameters = response['Parameters']

    while "NextToken" in response:
        token = response['NextToken']
        response = ssm_client.get_parameters_by_path(
            Path='/vpcx/aws/regions',
            Recursive=False,
            WithDecryption=True,
            NextToken=token
        )
        parameters.extend(response['Parameters'])

    """
    Parameter name e.g. - /vpcx/aws/regions/us-east-1
    Split the parameter name from /vpcx/aws/regions/
    """
    active_regions = []
    for parameter in parameters:
        active_regions.append((re.split('/vpcx/aws/regions/', parameter['Name'])[1]))
    return active_regions


def get_vpcx_region_parameters(region, ssm_client=boto3.client('ssm')):
    """
    Retrieve regions currently active for VPCx from param store

    Args:
        region: AWS Region to look up params for
        ssm_client: SSM boto3 client
    Returns: optional dict of parameter value
    """
    """
    get_parameters_by_path returns a maximum of 10 results in single API call. 
    Use NextToken to get complete list of regions. 
    """
    if not region:
        LOGGER.warning("No region provided.")
        return None
    try:
        response = ssm_client.get_parameter(Name=f'/vpcx/aws/regions/{region.lower()}')
        return json.loads(response.get("Parameter", {}).get("Value", "{}"))
    except ssm_client.exceptions.ParameterNotFound:
        LOGGER.warning(f"Region parameter not found for {region}")
        return None
