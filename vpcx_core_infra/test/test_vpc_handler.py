# pylint: skip-file
"""Test Handler"""
from unittest.mock import patch, MagicMock, Mock
import pytest
from .configured_component import (
    ConfiguredComponent,
    MOCK_CREDENTIALS,
    MOCK_APPSYNC_INFO,
    MOCK_PROVISIONING_SECRET,
)
import os
import json

MOCK_ENV_VARS = {
    "ACCOUNT_PROVISIONING_METADATA_BUCKET": "mock",
    "ENVIRONMENT": "MockITxEnvironment",
    "METADATA_ACCOUNT_ALIAS": "mock",
    "METADATA_ACCOUNT_BUCKET": "mock",
    "METADATA_TEMPLATE_BUCKET": "mock",
    "STATIC_CF_TEMPLATE_BUCKET": "mock",
    "ITX_IAM_STACK_NAME": "mock",
    "AWS_ORG_EXECUTION_ROLE_NAME": "mock",
    "ITX_IAM_TEMPLATE_NAME": "mock",
    "XBOT_ACCOUNT_NUMBER": "MockXbotAccountNumber",
    "LOGGING_TRUST_ACCOUNT_NUMBER": "MockLoggingTrustAccountNumber",
    "CLOUD_HEALTH_TRUST_ACCOUNT_NUMBER": "MockCloudHealthTrustAccountNumber",
    "ORGANIZATION_ID": "MockOrganizationId",
    "ACCOUNTS_CLOUD_HEALTH_READ_DATA_FROM_BILLING": "mock,mock1,mock2",
    "ACCOUNTS_TURBONOMICS_READ_FROM_S3": "mock,mock1,mock2",
    "ACCOUNTS_ORG_TAGS_ROLE": "mock,mock1,mock2",
    "LDAP_SERVER": "mock",
    "LDAP_USERNAME": "mock",
    "LDAP_GROUP_LOOKUP_ATTRIBUTE": "mock",
    "LDAP_CREDENTIALS_SECRET_NAME": "mock",
    "LDAP_SEARCH_BASE": "mock",
    "LDAP_OBJECT_CLASS": "mock",
    "LDAP_GROUP_NAME": "mock",
    "LDAP_USER_LOOKUP_ATTRIBUTE": "mock",
    "MSFT_IDP_TENANT_ID": "mock",
    "MSFT_IDP_APP_ID": "mock",
    "MSFT_IDP_CLIENT_ROLES": "mock",
    "CREDS_API_HOSTNAME": "mock",
    "CREDS_API_VPCE_ENDPOINT": "mock",
    "CREDS_API_SCOPE": "mock",
    "APPSYNC_INFO_SECRET_NAME": "mock",
    "ACCOUNT_PROVISIONING_CLIENT_SECRET_NAME": "mock"
}

@pytest.fixture(autouse=True)
def mock_settings_env_vars():
    with patch.dict(os.environ, MOCK_ENV_VARS):
        yield


ACCOUNT_ALIAS = "itx-999"
MOCK_ACCESS_TOKEN = "header.claims.sig"
class TestVpcHandler(ConfiguredComponent):

    @patch("vpcx_core_infra.index.lambda_auth.authorize_lambda_request", side_effect=Exception("Unauthorized"))
    def test_it_requires_authorization(self, _auth):
        from vpc_core_infra.index import handler

        event = {"body": json.dumps({})}
        context = {}
        response = handler(event, context)

        assert response.get("statusCode") == 401

    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.retrieve_account_log_buckets", return_value=False)
    @patch("vpcx_core_infra.index.lambda_auth.authorize_lambda_request", return_value=True)
    def test_it_requires_an_account_alias(self, _auth, _account_log_buckets):
        from vpc_core_infra.index import handler

        event = {"body": json.dumps({})}
        context = {}
        response = handler(event, context)

        assert response.get("statusCode") == 404
        assert response.get("body") == "No account found."

    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.retrieve_account_log_buckets", return_value=True)
    @patch("vpcx_core_infra.index.lambda_auth.authorize_lambda_request", return_value=True)
    @patch("vpcx_core_infra.index.get_cross_account_session", return_value=(False, Mock()))
    def test_it_requires_a_metadata_account(self, _session, _auth, _account_log_buckets):
        from vpc_core_infra.index import handler

        event = {"body": json.dumps({})}
        context = {}
        response = handler(event, context)

        assert response.get("statusCode") == 404
        assert response.get("body") == "No metadata account found."

    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.retrieve_account_log_buckets", return_value=True)
    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.get_external_configs", return_value={"region_config": None})
    @patch("vpcx_core_infra.index.lambda_auth.authorize_lambda_request", return_value=True)
    @patch("vpcx_core_infra.index.get_cross_account_session", return_value=(True, Mock()))
    @patch("vpcx_core_infra.index.process_request_validation", return_value=(False, {}))
    def test_it_requires_a_region(self, _process_request, _get_session, _auth, _external_configs, _account_log_buckets):
        from vpc_core_infra.index import handler

        event = {"body": json.dumps({})}
        context = {}
        _ = handler(event, context)
        _get_session.assert_called_once_with("mock")
        _process_request.assert_called_once()

    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.retrieve_account_log_buckets", return_value=True)
    @patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.get_external_configs", return_value={"region_config": None})
    @patch("vpcx_core_infra.index.lambda_auth.authorize_lambda_request", return_value=True)
    @patch("vpcx_core_infra.index.get_cross_account_session", return_value=(True, Mock()))
    @patch("vpcx_core_infra.index.process_request_validation", return_value=(True, Mock()))
    def test_it_only_works_on_aws(self, _process_request, _get_session, _auth, _external_configs, _account_log_buckets):
        from vpc_core_infra.index import handler

        validate_results = _process_request[1]
        validate_results.cloud_provider.return_value = "Google"

        event = {"body": json.dumps({})}
        context = {}
        response = handler(event, context)

        assert response.get("statusCode") == 400
        assert response.get("body") == "Cloud provider not supported."