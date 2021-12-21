"""Unit tests for utils"""
import boto3
from unittest.mock import patch, Mock
from utils import vpcx_params


class MockBoto3Client(object):
    """Used to mock boto3 calls"""

    def __init__(self):
        self.data = None
        self.exceptions = boto3.client().exceptions
        self.exceptions.NoSuchEntityException = Exception

    def get_role(self, **kwargs):
        raise self.exceptions.NoSuchEntityException

    def load_mock_data(self, data):
        self.data = data

    def describe_stack_resources(self, **kwargs):
        return self.data

    def get_parameters_by_path(self, **kwargs):
        return self.data


@patch('boto3.client')
def test_get_ssm_params(mock_boto_client):
    # Set mocks
    mock_data = {
       "Parameters": [
          {
             "Name": "/vpcx/aws/regions/us-mock-1",
             "Type": "String",
             "Value": "{\"master-cidr\": [\"\", \"\"], \"service-accounts\":{\"redshift\":\"ab\",\"alb\":\"cd\"}}"
          },
          {
             "Name": "/vpcx/aws/regions/us-mock-2",
             "Type": "String",
             "Value": "{\"master-cidr\": [\"\", \"\"], \"service-accounts\":{\"redshift\":\"ef\",\"alb\":\"gh\"}}"
          }
       ]
    }
    paginator = Mock()
    paginator.paginate.side_effect = [
        [mock_data]
    ]
    mock_boto_client.get_paginator.return_value = paginator
    # Execute
    ssm_params = vpcx_params.get_ssm_region_params(mock_boto_client)
    # Evaluate results
    expected_result = {
       'us-mock-1': {
           "master-cidr": [
               '',
               ''
           ],
           'service-accounts': {
               'redshift': 'ab',
               'alb': 'cd'
           }
       },
       'us-mock-2': {
            "master-cidr": [
                '',
                ''
            ],
            'service-accounts': {
                'redshift': 'ef',
                'alb': 'gh'
            }
        }
    }
    assert ssm_params == expected_result


