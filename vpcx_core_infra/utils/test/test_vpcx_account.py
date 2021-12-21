# pylint: skip-file
"""Unit tests for utils"""
import os
import json
import pytest
from unittest.mock import patch
from utils import vpcx_account

BASE_PATH = os.path.dirname(os.path.realpath(__file__))


# Used to mock request responses
class MockRequestResponse(object):

    def __init__(self, status, text, ok):
        self.status = status
        self.text = text
        self.ok = ok


@patch('requests.get')
def test_get_vpcx_account_admin_credentials(mock_request):
    # Setup mock data
    mock_creds = 'mock_creds'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'credentials': mock_creds
    })
    # Call method
    response = vpcx_account.get_vpcx_account_admin_credentials(
        'mock',
        'mock',
        'mock',
        'mock'
    )
    # Evaluate results
    assert response == mock_creds


@patch('requests.post')
def test_translate_account_alias_to_account_number(mock_request):
    # Setup mock data
    mock_account_num = '123456789'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': '',
                'items': [
                    {
                        'aws_number': mock_account_num
                    }
                ]
            }
        }
    })
    # Call method
    response = vpcx_account.translate_account_alias_to_account_number(
        'mock',
        'mock',
        'mock'
    )
    # Evaluate results
    assert response == mock_account_num


@patch('requests.post')
def test_translate_account_alias_to_account_number_multiple_accounts(mock_request):
    # Setup mock data
    mock_account_num = '123456789'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': '',
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
    with pytest.raises(vpcx_account.AccountNumberException):
        vpcx_account.translate_account_alias_to_account_number(
            'mock',
            'mock',
            'mock'
        )


@patch('requests.post')
def test_translate_account_alias_to_account_number_next_token(mock_request):
    # Setup mock data
    mock_account_num = '123456789'
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': 'mock',
                'items': [
                    {
                        'aws_number': mock_account_num,
                    }
                ]
            }
        }
    })
    # Call method
    with pytest.raises(vpcx_account.AccountNumberException):
        vpcx_account.translate_account_alias_to_account_number(
            'mock',
            'mock',
            'mock'
        )


@patch('requests.post')
def test_translate_account_alias_to_account_number_no_accounts(mock_request):
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'GetAccountByProjectId': {
                'nextToken': 'mock',
                'items': []
            }
        }
    })
    # Call method
    with pytest.raises(vpcx_account.AccountNumberException):
        vpcx_account.translate_account_alias_to_account_number(
            'mock',
            'mock',
            'mock'
        )


@patch('requests.post')
def test_get_all_accounts_in_env(mock_request):
    # Mock response
    mock_request.return_value.status_code = 200
    mock_request.return_value.text = json.dumps({
        'data': {
            'listAccounts': {
                'nextToken': None,
                'items': [
                    {'project_id': 'itx-123'},
                    {'project_id': 'itx-456'}
                ]
            }
        }
    })
    # Call method
    response = vpcx_account.get_all_accounts_in_env('mock',  'mock')
    # Evaluate response
    assert set(response) == {'itx-123', 'itx-456'}


@patch('requests.post')
def test_get_all_accounts_in_env_with_next_token(mock_request):
    # Mock responses
    mock_first_response = json.dumps({
        'data': {
            'listAccounts': {
                'nextToken': '123456',
                'items': [
                    {'project_id': 'itx-123'},
                    {'project_id': 'itx-456'}
                ]
            }
        }
    })
    mock_second_response = json.dumps({
        'data': {
            'listAccounts': {
                'nextToken': '7890123',
                'items': [
                    {'project_id': 'itx-abc'},
                    {'project_id': 'itx-def'}
                ]
            }
        }
    })
    mock_third_response = json.dumps({
        'data': {
            'listAccounts': {
                'nextToken': None,
                'items': [
                    {'project_id': 'itx-789'},
                    {'project_id': 'itx-456'}
                ]
            }
        }
    })
    mock_request.side_effect = [
        MockRequestResponse(200, mock_first_response, True),
        MockRequestResponse(200, mock_second_response, True),
        MockRequestResponse(200, mock_third_response, True)
    ]
    # Call method
    response = vpcx_account.get_all_accounts_in_env('mock',  'mock')
    # Evaluate response
    assert set(response) == {'itx-123', 'itx-456', 'itx-789', 'itx-abc', 'itx-def'}


def test_generate_next_alphanumeric_1():
    # Setup mock data
    mock_account = "itx-456"
    assert "itx-457" == vpcx_account.generate_next_alphanumeric(mock_account)


def test_generate_next_alphanumeric_2():
    # Setup mock data
    mock_account = "itx-abd"
    assert "itx-abe" == vpcx_account.generate_next_alphanumeric(mock_account)


def test_generate_next_alphanumeric_3():
    # Setup mock data
    mock_account = "itx-abz"
    assert "itx-aca" == vpcx_account.generate_next_alphanumeric(mock_account)


def test_derive_new_account_alias_mismatched_upper_and_lower():
    # Setup mock data
    current_account_aliases = []
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abb'
    exception_list = []
    with pytest.raises(vpcx_account.AccountNumberException) as e:
        vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                              upper_bound, exception_list)
    # Evaluate results
    assert "Lower bound must be less than upper bound." == str(e.value)


def test_derive_new_account_alias_bad_lower_boundary():
    # Setup mock data
    current_account_aliases = []
    lower_bound = 'abc'
    upper_bound = 'itx-abe'
    exception_list = []
    with pytest.raises(vpcx_account.AccountNumberException) as e:
        vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                              upper_bound, exception_list)
    # Evaluate results
    assert "Invalid boundary condition format." == str(e.value)


def test_derive_new_account_alias_bad_upper_boundary():
    # Setup mock data
    current_account_aliases = []
    lower_bound = 'itx-abc'
    upper_bound = 'jkl'
    exception_list = []
    with pytest.raises(vpcx_account.AccountNumberException) as e:
        vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                              upper_bound, exception_list)
    # Evaluate results
    assert "Invalid boundary condition format." == str(e.value)


def test_derive_new_account_alias_return_lower_bound():
    # Setup mock data
    current_account_aliases = []
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abe'
    exception_list = []
    # Execute
    result = vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                                   upper_bound, exception_list)
    # Evaluate
    assert result == 'itx-abc'


def test_derive_new_account_alias_return_good():
    # Setup mock data
    current_account_aliases = ['itx-abc']
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abe'
    exception_list = []
    # Execute
    result = vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                                   upper_bound, exception_list)
    # Evaluate
    assert result == 'itx-abd'


def test_derive_new_account_alias_return_good_with_exception():
    # Setup mock data
    current_account_aliases = ['itx-abc']
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abe'
    exception_list = ['itx-abd']
    # Execute
    result = vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                                   upper_bound, exception_list)
    # Evaluate
    assert result == 'itx-abe'


def test_derive_new_account_alias_return_good_complex():
    # Setup mock data
    current_account_aliases = ['itx-abc', 'itx-abe', 'itx-abg']
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abj'
    exception_list = ['itx-abd']
    # Execute
    result = vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                                   upper_bound, exception_list)
    # Evaluate
    assert result == 'itx-abf'


def test_derive_new_account_alias_beyond_upper_bound():
    # Setup mock data
    current_account_aliases = ['itx-abc']
    lower_bound = 'itx-abc'
    upper_bound = 'itx-abe'
    exception_list = ['itx-abd', 'itx-abe']
    with pytest.raises(vpcx_account.AccountNumberException) as e:
        vpcx_account.derive_new_account_alias(current_account_aliases, lower_bound,
                                              upper_bound, exception_list)
    # Evaluate results
    assert "Account alias beyond upper bound." == str(e.value)