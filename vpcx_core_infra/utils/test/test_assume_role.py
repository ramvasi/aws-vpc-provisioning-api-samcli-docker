"""Unit tests for utils"""
import json
from utils import assume_role


class MockSTSClient(object):
    """Used to mock STS"""

    def __init__(self, keys, exception):
        self.keys = keys
        self.exception = exception

    def assume_role(self, **kwargs):
        if self.exception:
            raise self.exception
        return self.keys


def test_assume_role():
    # Configure mocks
    mock_credentials = {
        "Credentials": {
            "AccessKeyId": "12345",
            "SecretAccessKey": "12345",
            "SessionToken": "12345"
        }
    }
    assume_role.STS_CLIENT = MockSTSClient(mock_credentials, None)
    # Setup mock data
    mock_account_number = "123456789"
    mock_name = "MOCK"
    # Call method
    result, credentials = assume_role.assume_cross_account_role(mock_account_number, mock_name)
    assert result is True
    assert json.dumps(credentials) == json.dumps(mock_credentials['Credentials'])


def test_assume_role():
    # Configure mocks
    mock_credentials = {
        "Credentials": {
            "AccessKeyId": "12345",
            "SecretAccessKey": "12345",
            "SessionToken": "12345"
        }
    }
    assume_role.STS_CLIENT = MockSTSClient(mock_credentials, None)
    # Setup mock data
    mock_account_number = "123456789"
    mock_name = "MOCK"
    # Call method
    result, credentials = assume_role.assume_cross_account_role(mock_account_number, mock_name)
    assert result is True
    assert json.dumps(credentials) == json.dumps(mock_credentials['Credentials'])


def test_assume_role_negative():
    # Configure mock creds
    mock_credentials = {
        "Credentials": {
            "AccessKeyId": "12345",
            "SecretAccessKey": "12345",
            "SessionToken": "12345"
        }
    }
    assume_role.STS_CLIENT = MockSTSClient(mock_credentials, Exception("Mock Exception"))
    # Setup mock data
    mock_account_number = "123456789"
    mock_name = "MOCK"
    # Call method
    result, credentials = assume_role.assume_cross_account_role(mock_account_number, mock_name)
    assert result is False
    assert credentials is None
