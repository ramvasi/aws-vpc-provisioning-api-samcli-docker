"""Module to interact with ec2 / vpc"""
import boto3


def get_availability_zones(ec2_client=boto3.client("ec2")):
    """
    Get availability zones in region of client

    Args:
        ec2_client: boto3 ec2 client

    Returns: list of AZ names
    """
    response = ec2_client.describe_availability_zones()
    return [zone["ZoneName"] for zone in response["AvailabilityZones"]]


def get_ec2_regions(ec2_client=boto3.client("ec2")):
    """
    Get list of regions

    Args:
        ec2_client: boto3 ec2 client

    Returns: list of regions
    """
    response = ec2_client.describe_regions()
    regions = [region['RegionName'] for region in response['Regions']]
    return regions


def derive_operable_regions(ssm_params, regions):
    """
    Given a list of allowed regions from param store, and a list of
    enabled regions in the account, then return a list of regions
    that is in ssm_params AND in regions

    Args:
        ssm_params: dict with region values as keys
        regions: list of regions

    Returns: master list of regions
    """
    return list(set(regions).intersection(list(ssm_params.keys())))


def get_existing_vpcs(ec2_client=boto3.client("ec2")):
    """
    Get other VPCs

    Args:
        ec2_client: boto3 CF client

    Returns: list of vpc_names and vpc_ids
    """
    response = ec2_client.describe_vpcs()
    rt_response = ec2_client.describe_route_tables()
    response.update(rt_response)
    return response
