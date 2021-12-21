"""Unit tests for utils"""
import json
import boto3
from unittest.mock import patch
from utils import cf_interactions


class MockBotoAttributes(object):
    """Used to mock boto3 attributes"""
    def __init__(self):
        self.region_name = "mock"


class MockBoto3Client(object):
    """Used to mock boto3 calls"""

    def __init__(self):
        self.data = None
        self.exceptions = boto3.client().exceptions
        self.exceptions.NoSuchEntityException = Exception
        self.meta = MockBotoAttributes()

    def get_role(self, **kwargs):
        raise self.exceptions.NoSuchEntityException

    def load_mock_data(self, data):
        self.data = data

    def describe_stack_resources(self, **kwargs):
        return self.data

    def create_stack(self, **kwargs):
        return {
            'StackId': '12345'
        }

    def get_waiter(self, id):
        return MockWaiter()


class MockWaiter(object):
    """Used to mock boto3 calls"""
    def __init__(self):
        self.data = None

    def wait(self, **kwargs):
        return None


@patch('boto3.client')
def test_get_stack_arns(mock_boto_client):
    # Mock boto
    mock_boto = MockBoto3Client()
    mock_boto_client.return_value = mock_boto
    # Setup mock data
    mock_data = {
        'StackResources': [
            {
                'LogicalResourceId': 'mocklogic1',
                'PhysicalResourceId': 'mockphysical1',
            },
            {
                'LogicalResourceId': 'mocklogic2',
                'PhysicalResourceId': 'mockphysical2',
            }
        ]
    }
    mock_boto.load_mock_data(mock_data)
    # Call method
    results = cf_interactions.get_stack_arns("mock_id", mock_boto)
    # Evaluate results
    expected_result = {
        "mocklogic1": "mockphysical1",
        "mocklogic2": "mockphysical2"
    }
    assert json.dumps(expected_result) == json.dumps(results)


@patch('boto3.client')
def test_sync_run_template(mock_boto_client):
    # Mock boto
    mock_boto = MockBoto3Client()
    mock_boto_client.return_value = mock_boto
    # Call method
    stack_id = cf_interactions.sync_run_template(
        "mock_template",
        "mock_params",
        "mock_stack_name",
        mock_boto
    )
    # Evaluate
    assert stack_id == '12345'
