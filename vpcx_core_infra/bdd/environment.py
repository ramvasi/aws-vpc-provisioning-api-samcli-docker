# pylint: disable=unnecessary-pass,logging-fstring-interpolation,logging-format-interpolation,raise-missing-from, unused-argument, line-too-long, too-many-arguments, no-self-use,missing-function-docstring,protected-access
"""Set up proper configurations for VPC infrastructure"""
import json
import logging
import os

import boto3

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def before_all(context):
    """
    Prepare BDD testing environment

    Args:
        context: behave framework default args
    """
    # Set BDD test vars
    with open('vpcx_core_infra/config/config.{}.json'.format(os.environ['ENV'])) as env_config_file:
        env_configs = json.load(env_config_file)
        context.deployment_account = env_configs['DEPLOYMENT']['ACCOUNT']
        context.test_account = env_configs['TESTING']['TEST_ACCOUNT']
        context.static_data_s3_bucket = env_configs['DEPLOYMENT']['STATIC_CF_TEMPLATE_BUCKET']
        context.template_metadata_s3_bucket = env_configs['DEPLOYMENT']['METADATA_TEMPLATE_BUCKET']
        context.creds_hostname = 'Test'
    # Set BDD test vars
    with open('vpcx_core_infra/config/config.common.json') as common_config_file:
        env_configs = json.load(common_config_file)

    context.hostname =  "http://sam-d-LoadB-EXCX02EPHOA9-701236970.us-west-2.elb.amazonaws.com" #context.stack_outputs['ServiceEndpoint'] + "/v1/vpcx/vpc"
    context.cross_account_session = boto3.session.Session(profile_name='i6_uswest2')
