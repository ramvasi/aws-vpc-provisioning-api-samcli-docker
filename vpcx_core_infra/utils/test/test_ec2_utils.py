"""Unit tests for utils"""
import boto3
import json
from unittest.mock import patch
from utils import ec2_interactions


class MockBoto3Client(object):
    """Used to mock boto3 calls"""
    def __init__(self):
        self.data = None
        self.exceptions = boto3.client().exceptions
        self.exceptions.NoSuchEntityException = Exception

    def load_mock_data(self, data):
        self.data = data

    def describe_regions(self, **kwargs):
        return self.data


@patch('boto3.client')
def test_ec2_get_active_regions(mock_boto_client):
    # Setup mocks
    mock_boto = MockBoto3Client()
    mock_boto_client.return_value = mock_boto
    mock_data = {
        'Regions': [
            {
                'RegionName': 'mock1',
            },
            {
                'RegionName': 'mock2',
            },
            {
                'RegionName': 'mock3',
            }
        ]
    }
    mock_boto.load_mock_data(mock_data)
    # Execute
    results = ec2_interactions.get_ec2_regions(mock_boto)
    # Evaluate results
    expected_result = ["mock1", "mock2", "mock3"]
    assert json.dumps(expected_result) == json.dumps(results)


def test_derive_operable_regions():
    # Setup mocks
    mock_ssm_params = {
        'us-east-1': {},
        'us-east-2': {},
        'us-west-1': {},
        'us-west-2': {}
    }
    mock_regions = ['us-east-2', 'us-west-2', 'af-south-1']
    # Execute
    result = ec2_interactions.derive_operable_regions(mock_ssm_params, mock_regions)
    # Evaluate results
    assert set(result) == {'us-west-2', 'us-east-2'}
