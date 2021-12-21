"""Lambda function to create core VPCx infrastructure"""
import logging
from vpcx_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def create_handler(event, context):
    """
    Handle VPC Create Requests
    Args:
        event: Lambda integration event
        context: Lambda context
    Returns:
        VPC Create Response
    """
    return CreateVpcHandler().process(event)
