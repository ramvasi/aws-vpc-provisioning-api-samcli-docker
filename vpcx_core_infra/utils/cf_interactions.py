"""Module to interact with CF"""
import time
import boto3
from botocore.exceptions import WaiterError
import logging

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def debug_failed_stack(client: boto3.client, stack_name:str) -> None:
    """
    Debug what happened in a stack
    Args:
        client: Boto3 client authorized to investigate stacks
        stack_name: Name of the stack to debug
    Returns: None
    """
    try:
        debug_stack(client, stack_name)
    except Exception as exception:
        LOGGER.exception("While debugging stack {}: {}".format(
            stack_name,
            exception,
        ))

    try:
        debug_stack_resources(client, stack_name)
    except Exception as exception:
        LOGGER.exception("While deubbing stack resources {}: {}".format(
            stack_name,
            exception,
        ))

def debug_stack(client, stack_name:str):
    """
    Debug Cloud Formation Stack events
    Args:
        client: Boto3 client authorized to investigate stacks
        stack_name: Name of the stack to debug
    """
    paginator = client.get_paginator('describe_stack_events')
    pages = paginator.paginate(StackName=stack_name)
    for page in pages:
        for event in page.get("StackEvents", []):
            LOGGER.info(event)


def debug_stack_resources(client, stack_name:str):
    """
    Debug Cloud Formation Stack resources
    Args:
        client: Boto3 client authorized to investigate stacks
        stack_name: Name of the stack to debug
    Returns: None
    """
    LOGGER.info(f"Debugging stack deletion of {stack_name}")
    paginator = client.get_paginator('list_stack_resources')

    pages = paginator.paginate(
        StackName=stack_name,
    )

    for page in pages:
        for resource in page.get("StackResourceSummaries", []):
            resource_state = resource.get("ResourceStatus", "")
            resource_id = resource.get('LogicalResourceId', "NoLogicalId")
            physical_resource_id = resource.get("PhysicalResourceId", "NoPhysicalID")
            if resource_state.endswith("_IN_PROGRESS") or resource_state.endswith("FAILED"):
                reason = resource.get("ResourceStatusReason", "Unknown")
                LOGGER.info(f"Warning: Resource {resource_id}({physical_resource_id}) is in state {resource_state}:\n\t{reason}")


# Define exception for stack deploy failures
class VPCxStackDeployException(Exception):
    """
    Exception raised when a VPCx stack fails to stabilize

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="Failed to deploy stack."):
        self.message = message
        super().__init__(self.message)


# Define exception for no updates
class VPCxStackNoUpdateException(Exception):
    """
    Exception raised when a VPCx has redundant updates

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="No updates found stack."):
        self.message = message
        super().__init__(self.message)


def get_stack_arns(stack_id, cf_client=boto3.client('cloudformation')):
    """
    Get resources in a stack

    Args:
        stack_id: CF template stack ID
        cf_client: boto3 CF client

    Returns: dict of { "LogicalId": "PhysicalId" }
    """
    # Describe stack resources
    response = cf_client.describe_stack_resources(
        StackName=stack_id
    )
    LOGGER.info("Stack resources {}".format(str(response)))
    # Iterate over stack resources
    results = {}
    for stack in response['StackResources']:
        logical_resource_id = stack['LogicalResourceId']
        physical_resource_id = stack['PhysicalResourceId']
        results[logical_resource_id] = physical_resource_id
    return results


def sync_run_template(cf_template, params,
                      stack_name, cf_client=boto3.client('cloudformation')):
    """
    Deploy CF template in cross-account

    Args:
        cf_template: template body
        params: CF param overrides
        stack_name: name of CF stack
        cf_client: boto3 CF client

    Returns: stack ID
    """
    LOGGER.info('Deploying with stack params: {}'.format(str(params)))
    LOGGER.info('Deploying with stack name: {} in region {}'.format(str(stack_name), cf_client.meta.region_name))
    # Kickoff stack create and extract stack ID
    is_new_stack = True
    try:
        stack_create_response = cf_client.create_stack(
            StackName=stack_name,
            TemplateBody=cf_template,
            Capabilities=[
                'CAPABILITY_NAMED_IAM'
            ],
            Parameters=params,
            OnFailure='DELETE'
        )
    # If stack exists, then update it
    except cf_client.exceptions.AlreadyExistsException:
        LOGGER.info("Stack %s already exists in region %s. Updating stack.", stack_name, cf_client.meta.region_name)
        try:
            is_new_stack = False
            stack_create_response = cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=cf_template,
                Capabilities=[
                    'CAPABILITY_NAMED_IAM'
                ],
                Parameters=params
            )
        # If stack exists, and no updates, raise custom exception
        except cf_client.exceptions.ClientError as e:
            if 'No updates are to be performed' in str(e):
                raise VPCxStackNoUpdateException()
            else:
                raise e
    LOGGER.info('Deployed stack {} with parameters {}'.format(str(stack_create_response), params))
    stack_id = stack_create_response['StackId']
    # Wait for stack to stabilize
    if is_new_stack:
        waiter = cf_client.get_waiter('stack_create_complete')
    else:
        waiter = cf_client.get_waiter('stack_update_complete')
    try:
        waiter.wait(
            StackName=stack_id,
            WaiterConfig={
                'Delay': 12,
                'MaxAttempts': 25
            }
        )
    except WaiterError as e:
        LOGGER.error("Stack {} failed to stabilize {}".format(stack_name, e))
        debug_stack(cf_client, stack_name)
        raise VPCxStackDeployException('Stack {} failed to stabilize.'.format(
            stack_name
        ))
    LOGGER.info('Completed stack deploy. Region {} Stack ID {}'.format(cf_client.meta.region_name, str(stack_id)))
    # Return stack ID
    return stack_id


def get_all_stack_names(cf_client=boto3.client("cloudformation")):
    """
    Get all stack names

    Args:
        cf_client: boto3 CF client

    Returns: list of StackName
    """
    LOGGER.info("Attempting to retrieve stack information")
    response = cf_client.describe_stacks()
    LOGGER.info("Retrieved stack information: %s", response)
    return [stack["StackName"] for stack in response["Stacks"]]

def get_stack_events(cf_client, stack_name:str):
    """
    Get stack events for a stack
    Args:
        cf_client: CloudFormation Boto3 Client
        stack_name: Name of the stack to debug
    Returns:
        Stack Events iterator
    """
    paginator = cf_client.get_paginator("describe_stack_events")
    return paginator.paginate(StackName=stack_name)

def debug_stack_events(stack_event_pages):
    """
    Display message from all stack events
    Args:
        stack_event_pages: Iterator
    """
    log_line = """[{Timestamp}] StackName: {StackName}
        Stack: {StackId}
        Event: {EventId}
        Status: {ResourceStatus}
        {ResourceStatusReason}
        {ResourceProperties}
    """

    for page in stack_event_pages:
        for stack_event in page.get("StackEvents", []):
            LOGGER.info(log_line.format(**stack_event))