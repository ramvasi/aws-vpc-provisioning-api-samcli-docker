"""Module to interact with S3"""
import logging
import boto3
import json

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def list_objects_with_prefix(bucket, prefix, s3_client=boto3.client("s3")):
    """
    List obejcts at prefix in S3

    Args:
        bucket: name of S3 bucket thats stores account metadata
        prefix: key prefix to use in search
        s3_client: s3 client (e.g., boto3.client('s3'))

    Returns: list
    """
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = response.get('Contents', [])
    while 'NextContinuationToken' in response:
        token = response['NextToken']
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, ContinuationToken=token)
        objects.extend(response['Contents'])
    return objects


def retrieve_json_from_s3(bucket, key, s3_resource=boto3.resource('s3')):
    """
    Retrieve json from S3

    Args:
        bucket: name of S3 bucket thats stores account metadata
        key: key for account metadata file in S3
        s3_resource: s3 resource (e.g., boto3.resource('s3'))

    Returns: json
    """
    LOGGER.info('Retrieving JSON file %s/%s', bucket, key)
    # Define object
    content_object = s3_resource.Object(bucket, key)
    # Read object
    file_content = content_object.get()['Body'].read().decode('utf-8')
    # Load JSON
    LOGGER.info('Retrieved file: %s', str(file_content))
    return json.loads(str(file_content))


def write_json_to_s3(bucket, key, contents, s3_resource=boto3.resource('s3')):
    """
    Write JSON to S3

    Args:
        bucket: name of S3 bucket that stores account metadata
        key: key for account metadata file in S3
        contents: json contents
        s3_resource: s3 resource (e.g., boto3.resource('s3'))
    """
    LOGGER.info('Writing JSON file %s from %s.  Contents %s', bucket, key, contents)
    # Define object
    content_object = s3_resource.Object(bucket, key)
    # Write object
    content_object.put(
        Body=(bytes(json.dumps(contents).encode('UTF-8'))),
        ServerSideEncryption='AES256'
    )


def retrieve_file_from_s3(bucket, key, s3_resource=boto3.resource('s3')):
    """
    Retrieve file from S3

    Args:
        bucket: name of S3 bucket thats stores account metadata
        key: key for account metadata file in S3
        s3_resource: s3 resource (e.g., boto3.resource('s3'))

    Returns: json
    """
    LOGGER.info('Retrieving JSON file %s/%s', bucket, key)
    # Define object
    content_object = s3_resource.Object(bucket, key)
    # Read object
    file_content = content_object.get()['Body'].read().decode('utf-8')
    # Load JSON
    LOGGER.info('Retrieved file: %s', str(file_content))
    return str(file_content)


def write_file_to_s3(bucket, key, contents, s3_resource=boto3.resource('s3')):
    """
    Write block data S3

    Args:
        bucket: name of S3 bucket that stores account metadata
        key: key for account metadata file in S3
        contents: json contents
        s3_resource: s3 resource (e.g., boto3.resource('s3'))
    """
    LOGGER.info('Writing JSON file %s from %s.  Contents %s', bucket, key, contents)
    # Define object
    content_object = s3_resource.Object(bucket, key)
    # Write object
    content_object.put(
        Body=(bytes(str(contents).encode('UTF-8')))
    )
