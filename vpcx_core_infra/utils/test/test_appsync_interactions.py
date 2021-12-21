# pylint: skip-file
"""Unit tests for utils"""
import os
import json
import pytest
from unittest.mock import patch
from vpcx_core_infra.utils import appsync_interactions

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


@patch('requests.post')
def test_get_current_account_metadata(mock_request):
    # Setup mock data
    mock_account_num = '123456789'
    mock_id = "1"
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': '',
                'items': [
                    {
                        'aws_number': mock_account_num,
                        'id': mock_id
                    }
                ]
            }
        }
    })
    # Call method
    response = appsync_interactions.get_current_account_metadata(
        'mock',
        'mock',
        'mock'
    )
    # Evaluate results
    assert response['aws_number'] == mock_account_num
    assert response['id'] == mock_id


@patch('requests.post')
def test_get_current_account_metadata_with_no_items(mock_request):
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': '',
                'items': []
            }
        }
    })
    # Call method
    response = appsync_interactions.get_current_account_metadata(
        'mock',
        'mock',
        'mock'
    )
    # Evaluate results
    assert response is None


@patch('requests.post')
def test_get_current_account_metadata_with_multiple_items(mock_request):
    mock_account_num = '12345678890'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': 'mock',
                'items': [
                    {
                        'aws_number': mock_account_num,
                    },
                    {
                        'aws_number': mock_account_num,
                    }
                ]
            }
        }
    })
    # Call method
    response = appsync_interactions.get_current_account_metadata(
        'mock',
        'mock',
        'mock'
    )
    # Evaluate results
    assert response is None


@patch('requests.post')
def test_update_account_metadata(mock_request):
    # Set up mock data
    mock_data = {
        "id": "1",
        "aws_number": "1234567890",
        "project_id": "itx-abc",
        "owner": "mock",
        "log_buckets": "mock",
        "regions": ["mock"]
    }
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'updateAccount': mock_data
        }
    })
    # Call method
    response = appsync_interactions.update_account_metadata(
        mock_data,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response == mock_data


@patch('requests.post')
def test_update_account_metadata_error(mock_request):
    # Set up mock data
    mock_data = {
        "id": "1",
        "aws_number": "1234567890",
        "project_id": "itx-abc",
        "owner": "mock",
        "log_buckets": "mock",
        "regions": ["mock"]
    }
    # Mock response
    mock_request.return_value.status_code = 400
    mock_request.return_value.text = json.dumps({
        'data': {},
        'errors': [{
            'errorType': 'MockException',
            'message':' MockMessage'
        }]
    })
    # Call method
    with pytest.raises(appsync_interactions.AccountMetadataException) as error:
        appsync_interactions.update_account_metadata(
            mock_data,
            'mock',
            'mock'
        )


@patch('requests.post')
def test_insert_account_metadata(mock_request):
    mock_data = {
        "aws_number": "1234567890",
        "project_id": "itx-abc",
        "owner": "mock",
        "log_buckets": "mock",
        "regions": ["mock"]
    }
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'createAccount': mock_data
        }
    })
    # Call method
    response = appsync_interactions.insert_account_metadata(
        mock_data,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response == mock_data


@patch('requests.post')
def test_insert_account_metadata_error(mock_request):
    mock_data = {
        "aws_number": "1234567890",
        "project_id": "itx-abc",
        "owner": "mock",
        "log_buckets": "mock",
        "regions": ["mock"]
    }
    # Mock response
    mock_request.return_value.status_code = 400
    mock_request.return_value.text = json.dumps({
        'data': {},
        'errors': [{
            'errorType': 'MockException',
            'message': ' MockMessage'
        }]
    })
    # Call method
    with pytest.raises(appsync_interactions.AccountMetadataException) as error:
        appsync_interactions.insert_account_metadata(
            mock_data,
            'mock',
            'mock'
        )


@patch('requests.post')
def test_delete_account_metadata(mock_request):
    mock_request_data = {
        "id": "mock"
    }
    mock_response_data = {
        "id": "mock",
        "project_id": "mock"
    }
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'deleteAccount': mock_response_data
        }
    })
    # Call method
    response = appsync_interactions.delete_account_metadata(
        mock_request_data,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response == mock_response_data


@patch('requests.post')
def test_delete_account_metadata_error(mock_request):
    mock_data = {
        "id": "mock"
    }
    # Mock response
    mock_request.return_value.status_code = 400
    mock_request.return_value.text = json.dumps({
        'data': {},
        'errors': [{
            'errorType': 'MockException',
            'message': ' MockMessage'
        }]
    })
    # Call method
    with pytest.raises(appsync_interactions.AccountMetadataException) as error:
        appsync_interactions.delete_account_metadata(
            mock_data,
            'mock',
            'mock'
        )

@patch('requests.post')
def test_get_account_by_aws_number(mock_request):
    # Setup mock data
    mock_account_num = '123456789'
    mock_project_id = "itx-mock"
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByAWSNumber': {
                'nextToken': '',
                'items': [
                    {
                        'aws_number': mock_account_num,
                        'project_id': mock_project_id
                    }
                ]
            }
        }
    })
    # Call method
    response = appsync_interactions.get_account_by_aws_number(
        mock_account_num,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response['aws_number'] == mock_account_num
    assert response['project_id'] == mock_project_id

@patch('requests.post')
def test_get_account_by_aws_number_with_no_items(mock_request):
    mock_account_num = '12345678890'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByAWSNumber': {
                'nextToken': '',
                'items': []
            }
        }
    })
    # Call method
    response = appsync_interactions.get_account_by_aws_number(
        mock_account_num,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response is None

@patch('requests.post')
def test_get_account_by_aws_number_with_multiple_items(mock_request):
    mock_account_num = '12345678890'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByAWSNumber': {
                'nextToken': 'mock',
                'items': [
                    {
                        'aws_number': mock_account_num,
                        'project_id': '1234567890'
                    },
                    {
                        'aws_number': mock_account_num,
                        'project_id': '0987654321'
                    }
                ]
            }
        }
    })
    # Call method
    response = appsync_interactions.get_account_by_aws_number(
        mock_account_num,
        'mock',
        'mock'
    )
    # Evaluate results
    assert response is None
