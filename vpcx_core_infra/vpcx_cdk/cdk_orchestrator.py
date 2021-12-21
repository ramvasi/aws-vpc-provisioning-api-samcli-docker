# pylint: disable=line-too-long
"""Module to build CF templates from VPCx configs"""
import json
import logging
from datetime import datetime
from aws_cdk import core
from .vpc_stack import VpcStack
from vpcx_core_infra.vpcx_cdk.vpc_context import VpcContext
from vpcx_core_infra.utils import (
    cf_interactions,
    s3_interactions,
    ec2_interactions,
    vpcx_regions
)
import boto3

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def build_cf_template(vpc_context: VpcContext, external_configs: dict):
    """
    Build a CF template based on VPCx inputs

    Args:
        vpc_context: vpc metadata from request
        external_configs: external configs

    Returns: tuple of app_name, CF template
    """
    # Initialize CDK stack
    app = core.App()
    app_name = vpc_context.vpcx_name
    # Generate and return CF template
    VpcStack(app, app_name, vpc_context, external_configs)
    return app_name, json.dumps(app.synth().get_stack_by_name(app_name).template)


def update_context_from_current_state(vpc_context: VpcContext, session):
    """
    Get details of existing VPCs

    Args:
        vpc_context: VpcContext as built from request body
        session: boto3 session

    Returns: updated VPC context object
    """
    # Grab AZs in
    ec2_client = session.client("ec2", region_name=vpc_context.region)
    zones = ec2_interactions.get_availability_zones(ec2_client)
    existing_vpc_data = ec2_interactions.get_existing_vpcs(ec2_client)
    # Find existing VPCs in region
    existing_stack_names = cf_interactions.get_all_stack_names(session.client("cloudformation", region_name=vpc_context.region))
    # Update VPC context
    vpc_context.set_vpcx_name(stack_names=existing_stack_names)
    vpc_context.availability_zones = zones
    # Return updated context
    return vpc_context


def get_external_configs(region, config_bucket, metadata_account_session):
    """
    Retrieve configs from S3

    Args:
        region: AWS region
        config_bucket: S3 bucket with metadata
        metadata_account_session: Boto session to the metadata acccount

    Returns: networking configs (dict), region configs (dict)
    """
    # region_config = vpcx_regions.get_vpcx_region_parameters(region, boto3.client("ssm"))
    # net_config = s3_interactions.retrieve_json_from_s3(config_bucket, 'networking_config.json')
    # return {
    #     "net_config": net_config,
    #     "region_config": region_config
    # }
    file_reader = open('/var/task/vpcx_core_infra/templates/networking_config.json', 'r')
    net_config = json.loads(file_reader.read())
    file_reader.close()

    if region in ['us-west-1', 'us-west-2']:
        file_reader = open('/var/task/vpcx_core_infra/templates/ssm_region_us_east_1.json', 'r')
        region_config = json.loads(file_reader.read())
        #region_config = vpcx_regions.get_vpcx_region_parameters(region, boto3.client("ssm"))
        file_reader.close()
    else:
        region_config = None

    #net_config = s3_interactions.retrieve_json_from_s3(config_bucket, 'networking_config.json')
    #region_config = vpcx_regions.get_vpcx_region_parameters(region, boto3.client("ssm"))
    return {
        "net_config": net_config,
        "region_config": region_config
    }

def push_to_metadata_store(bucket, template, vpc_context: VpcContext):
    """
    Stores request metadata and stack template in s3

    Args:
        bucket: bucket for storing metadata
        template: CFN template that was deployed
        vpc_context: VpcContext
    """
    # Timestamp stack
    s3_key = f"{vpc_context.account_alias}/{vpc_context.vpcx_name}-{datetime.now().isoformat()}.json"
    # Write data to S3
    metadata_dict = {
        "stack_inputs": vpc_context.output_class_to_dict(),
        "stack_template": template
    }
    s3_interactions.write_json_to_s3(bucket=bucket,
                                     key=s3_key,
                                     contents=metadata_dict)


def get_context_data_from_metadata_store(bucket, account_alias, vpcx_name):
    """
    Retrieves latest request metadata and stack template from s3

    Args:
        bucket: bucket for storing metadata
        account_alias:
        vpcx_name:

    Returns: optional VpcContext
    """
    objects = s3_interactions.list_objects_with_prefix(bucket, f"{account_alias}/{vpcx_name}")
    if not objects:
        return None
    sorted_keys = [o["Key"] for o in objects]
    sorted_keys.sort()
    latest_context_key = sorted_keys.pop()
    response = s3_interactions.retrieve_json_from_s3(bucket, latest_context_key)
    context_json = response.get("stack_inputs")
    return context_json
