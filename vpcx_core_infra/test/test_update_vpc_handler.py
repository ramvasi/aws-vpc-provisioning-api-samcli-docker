# pylint: skip-file
from unittest.mock import patch, MagicMock, Mock
import pytest
from .configured_component import (
    ConfiguredComponent,
    MOCK_CREDENTIALS,
    MOCK_APPSYNC_INFO,
    MOCK_PROVISIONING_SECRET,
)

import re
import os
import json

MOCK_ENV_VARS = {
    "ENVIRONMENT": "MockITxEnvironment",
    "METADATA_ACCOUNT_ALIAS": "mock",
    "METADATA_ACCOUNT_BUCKET": "mock",
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

VALID_REQUEST = {
            "account_alias": "alias",
            "vpcx_name": "name",
            "region": "region",
        }

class TestValidation(ConfiguredComponent):
    def test_it_requires_an_account_alias(self):
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        success, response = UpdateVpcHandler.validate_request({})

        assert success == False
        assert re.match("Missing a required field", response.get("body"))

    def test_it_requires_a_vpcx_name(self):
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        success, response = UpdateVpcHandler.validate_request({"account_alias": "alias"})

        assert success == False
        assert re.match("Missing a required field", response.get("body"))

    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.METADATA_TEMPLATE_BUCKET", return_value="BUCKET")
    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.cdk_orchestrator")
    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.VpcContext")
    def test_it_has_no_context_data(self, vpc_context, cdk_orchestrator, template_bucket):
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        cdk_orchestrator.get_context_data_from_metadata_store = Mock(return_value=None)

        success, response = UpdateVpcHandler.validate_request(VALID_REQUEST)

        cdk_orchestrator.get_context_data_from_metadata_store.assert_called_once_with(
            template_bucket,
            VALID_REQUEST.get("account_alias"),
            VALID_REQUEST.get("vpcx_name")
        )
        assert success == False
        assert re.match("No VPCx VPC found", response.get("body"))

    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.METADATA_TEMPLATE_BUCKET", return_value="BUCKET")
    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.cdk_orchestrator")
    @patch("vpcx_core_infra.vpcx_cdk.vpc_update_handler.VpcContext")
    def test_it_is_a_valid_request(self, vpc_context, cdk_orchestrator, template_bucket):
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        cdk_orchestrator.get_context_data_from_metadata_store = Mock()
        vpc_context.init_from_storage = Mock(return_value="OK")
        
        success, _ = UpdateVpcHandler.validate_request(VALID_REQUEST)

        cdk_orchestrator.get_context_data_from_metadata_store.assert_called_once_with(
            template_bucket,
            VALID_REQUEST.get("account_alias"),
            VALID_REQUEST.get("vpcx_name")
        )
        assert success == True

class TestUnauthorizedUpdate(ConfiguredComponent):
    def test_it_is_unauthorized(self):
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        handler = UpdateVpcHandler()

        with patch.object(handler, "auth", return_value="ERROR"):
            assert handler.process({}) == "ERROR"

INVALID_UPDATE_REQUEST = {
    "body": json.dumps({})
}
VALID_UPDATE_REQUEST = {
    "body": json.dumps(VALID_REQUEST),
}
class TestAuthorizedUpdate(ConfiguredComponent):
    def setUp(self):
        super().setUp()
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        self.handler = UpdateVpcHandler()
        authorization = patch.object(self.handler, "auth", return_value=None)
        authorization.start()
        self.addCleanup(authorization.stop)

    def test_it_is_an_invalid_update_request(self):
        with patch.object(self.handler, "validate_request", return_value=(False, "BAD_RESULTS")):
            results = self.handler.process(INVALID_UPDATE_REQUEST)
            assert results == "BAD_RESULTS"

class TestValidAuthorizedUpdate(ConfiguredComponent):
    def setUp(self):
        super().setUp()
        from vpc_core_infra.vpcx_cdk.vpc_update_handler import UpdateVpcHandler

        self.handler = UpdateVpcHandler()
        self.validate_results = Mock()
        self.validate_results.region = VALID_REQUEST.get("region")

        authorization = patch.object(self.handler, "auth", return_value=None)
        validate_result = patch.object(
            self.handler,
            "validate_request",
            return_value=(True, self.validate_results),
        )
        
        authorization.start()
        validate_result.start()

        self.addCleanup(authorization.stop)
        self.addCleanup(validate_result.stop)


    def test_it_requires_a_cross_account_session(self):
        with patch.object(self.handler, "get_cross_account_session", return_value=(False, None)) as fn:
            response = self.handler.process(VALID_UPDATE_REQUEST)

            fn.assert_called_once_with("mock")
            assert response.get("statusCode") == 404
            assert re.match("No metadata account found", response.get("body"))
    
    def test_it_requires_a_account_session(self):
        sessions = [
            (True, "METADATA_ACCOUNT_SESSION"),
            (False, "ACCOUNT_SESSION")
        ]
        with patch.object(self.handler, "get_cross_account_session", side_effect=sessions) as fn:
            response = self.handler.process(VALID_UPDATE_REQUEST)

            assert response.get("statusCode") == 404
            assert re.match("No account found", response.get("body"))
            