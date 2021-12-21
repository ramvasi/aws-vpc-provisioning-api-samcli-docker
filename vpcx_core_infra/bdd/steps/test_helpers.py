# pylint: disable=unnecessary-pass,logging-fstring-interpolation,logging-format-interpolation,raise-missing-from, unused-argument, line-too-long, too-many-arguments, no-self-use,missing-function-docstring,protected-access
"""Common functions used in BDD"""
import json
import boto3
import time
import botocore.exceptions
import logging

LOGGER = logging.getLogger(name="TestHelpers")
LOGGER.setLevel(logging.INFO)

def count_s3_files_at_prefix(bucket, prefix, account_alias, s3_client=boto3.client('s3')):
    """
    Count S3 files in a bucket with a certain prefix

    Args:
        bucket: S3 buckets
        prefix: file prefix
        account_alias: account_alias
        s3_client: s3 boto client

    Returns: num files with prefix
    """
    response = s3_client.list_objects(
        Bucket=bucket,
        Prefix="{}/{}".format(account_alias, prefix)
    )
    if response.get('Contents', None):
        return len(response['Contents'])
    else:
        return 0


def round_down_to_nearest_power_of_2(input_num):
    """
    Round up to nearest power of 2

    Args:
        input_num: input num

    Returns: nearest power of 2
    """
    if input_num > 1:
        last_power = 1
        for i in range(1, int(input_num)):
            if 2 ** i > input_num:
                return int(last_power)
            elif 2 ** i == input_num:
                return int(input_num)
            else:
                last_power = 2 ** i
    else:
        return 1


def delete_existing_vpcs(cf_client, stack_to_delete=None):
    """
    Delete all VPCx stacks in account or a specific stack id specified

    Args:
        cf_client:
        stack_to_delete: optional stack name to limit to single delete. Deletes all vpcx stacks if default

    Returns:

    """
    # List stacks
    response = cf_client.list_stacks()
    LOGGER.info(f"Trying to delete VPC of {stack_to_delete}")
    if not stack_to_delete:
        # Iterate over stacks
        stacks = response.get('StackSummaries', [])
        sorted_stacks = list(filter(lambda x: x.get('DeletionTime', None) is None, stacks))
        sorted_stacks.sort(key=lambda summary: summary.get('CreationTime', ""), reverse=True)
        for stack in sorted_stacks:
            stack_name = stack['StackName']
            # Delete any primary or hpc VPC stacks
            if 'vpc-primary' in stack_name or 'vpc-hpc' in stack_name:
                LOGGER.info(f"Trying to delete stack {stack_name} in status {stack['StackStatus']}")
                # Delete stack
                cf_client.delete_stack(
                    StackName=stack_name
                )
                # Wait for stack to delete
                waiter = cf_client.get_waiter('stack_delete_complete')
                waiter.wait(
                    StackName=stack_name,
                    WaiterConfig={
                        'Delay': 5,
                        'MaxAttempts': 60
                    }
                )
    else:
        for stack in response.get('StackSummaries', None):
            if stack['StackName'] == stack_to_delete and stack['StackStatus'] != "DELETE_COMPLETE":
                LOGGER.info(f"Deleting stack {stack['StackName']} in status {stack['StackStatus']} created {stack['CreationTime']}")
                if stack['StackStatus'] == "DELETE_IN_PROGRESS":
                    LOGGER.info(f"Delete in progress for {stack['StackId']}")
                else:
                    cf_client.delete_stack(StackName=stack_to_delete)
                try:
                    LOGGER.info(f"Waiting on delete of {stack['StackId']}")
                    waiter = cf_client.get_waiter('stack_delete_complete')
                    waiter.wait(
                        StackName=stack_to_delete,
                        WaiterConfig={
                            'Delay': 5,
                            'MaxAttempts': 60
                        }
                    )
                except botocore.exceptions.WaiterError as error:
                    LOGGER.info(f"Failed to delete {stack_to_delete}{stack['StackId']}: {error}")

def mock_log_buckets(credentials, test_account, regions, metadata):
    """
    Create and update mock data for log buckets in Accounts Table

    Args:
        credentials: AWS credentials
        test_account: test account alias
        regions: list of regions to create an S3 bucket
        metadata: current metadata from Accounts Table

    Returns: updated metadata
    """
    # Form new metadata
    new_buckets = {}
    # Init s3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    # List buckets
    buckets = s3_client.list_buckets()
    # Process response
    bucket_list = []
    for item in buckets.get('Buckets'):
        bucket_list.append(item['Name'])
    # Check if target bucket is created in every region
    for region in regions:
        # Form mock bucket name
        log_bucket_name = "{}-temp-log-{}".format(test_account, region)
        new_buckets[region] = log_bucket_name
        # If bucket does not exist, then create it
        if log_bucket_name not in bucket_list:
            s3_client.create_bucket(
                ACL='private',
                Bucket=log_bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': region
                }
            )
    # Set log buckets
    metadata['log_buckets'] = json.dumps(new_buckets)
    return metadata

