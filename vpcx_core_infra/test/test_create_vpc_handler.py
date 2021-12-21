# pylint: skip-file
from unittest.mock import patch, MagicMock, Mock
import pytest
from .configured_component import (
    ConfiguredComponent,
    MOCK_CREDENTIALS,
    MOCK_APPSYNC_INFO,
    MOCK_PROVISIONING_SECRET,
)
from vpc_core_infra.request_validation import vpcx_request_validation_exceptions

import re
import os
import json

MOCK_ENV_VARS = {
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


class TestProcessRequestValidation(ConfiguredComponent):
    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.VpcContext")
    def test_it_cannot_initalize_vpc_context(self, vpc_context):
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler
        from vpc_core_infra.request_validation import vpcx_request_validation_exceptions
        vpc_context.init_from_request_body = Mock(
            side_effect=vpcx_request_validation_exceptions.VpcRequestException("Error"),
        )
        success, response = CreateVpcHandler.process_request_validation(
            "request_body",
            "region_config",
            "region_to_log_bucket_dict",
        )
        assert success == False
        assert re.match("Error", response.get("body"))

    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.VpcContext")
    def test_it_fails_unexpectedly(self, vpc_context):
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler
        vpc_context.init_from_request_body = Mock(
            side_effect=Exception("Error"),
        )

        success, response = CreateVpcHandler.process_request_validation(
            "request_body",
            "region_config",
            "region_to_log_bucket_dict",
        )
        assert success == False
        assert response.get("statusCode") == 500
        assert re.match("Error occurred processing request", response.get("body"))

    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.VpcContext")
    def test_it_initializes_vpc_context(self, vpc_context):
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler
        vpc_context.init_from_request_body = Mock(return_value="vpc_context")

        success, response = CreateVpcHandler.process_request_validation(
            "request_body",
            "region_config",
            "region_to_log_bucket_dict",
        )

        assert success == True
        assert response == "vpc_context"

class TestProcessUpdateContextValidation(ConfiguredComponent):
    def setUp(self):
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler

        self.handler = CreateVpcHandler
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.update_context_from_current_state",
        side_effect=vpcx_request_validation_exceptions.VpcRequestException("Error"),
    )
    def test_it_cannot_validate(self, validator):
        success, response = self.handler.process_update_context_validation(Mock(), Mock())

        assert success == False
        assert response.get("body") == "Error"

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.update_context_from_current_state",
        side_effect=Exception("Error"),
    )
    def test_it_fails_unexpectedly(self, validator):
        success, response = self.handler.process_update_context_validation(Mock(), Mock())

        assert success == False
        assert re.match("Error occurred processing request", response.get("body"))

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.update_context_from_current_state",
        return_value=(True, "Anything"),
    )
    def test_it_works(self, validator):
        success, response = self.handler.process_update_context_validation(Mock(), Mock())

        assert success == True

class TestUnauthorizedRequest(ConfiguredComponent):
    def setUp(self):
        super().setUp()
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler
        self.handler = CreateVpcHandler()
        authorization = patch.object(self.handler, "auth", return_value="Error")
        authorization.start()
        self.addCleanup(authorization.stop)
    
    def test_it_is_unauthorized(self):
        response = self.handler.process("Event")
        assert response == "Error"

VALID_BODY = {
    "region": "region",
    "account_alias": "account_alias",
}
VALID_CREATE_EVENT = {
    "body": json.dumps(VALID_BODY),
}
class AuthorizedTestCase(ConfiguredComponent):
    def setUp(self):
        super().setUp()
        from vpc_core_infra.vpcx_cdk.vpc_create_handler import CreateVpcHandler
        self.handler = CreateVpcHandler()
        authorization = patch.object(self.handler, "auth", return_value=None)
        authorization.start()
        self.addCleanup(authorization.stop)

class TestAuthorizedRequest(AuthorizedTestCase):

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=None,
    )
    def test_it_has_no_log_bucket_configuration(self, rx_account_log_buckets):
        response = self.handler.process(VALID_CREATE_EVENT)
        assert response.get("statusCode") == 404
        assert re.match("No account found", response.get("body"))

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=True,
    )
    def test_it_has_no_metadata_account(self, rx_account_log_buckets):
        mock_session = (False, "Session")
        with patch.object(self.handler, "get_cross_account_session", return_value=mock_session) as fn:
            response = self.handler.process(VALID_CREATE_EVENT)
            fn.assert_called_once_with("mock")
            assert response.get("statusCode") == 404
            assert re.match("No metadata account found", response.get("body"))

EXTERNAL_CONFIGS = {"region_config": "region_config"}
class TestAuthorizedInvalidRequest(AuthorizedTestCase):
    def setUp(self):
        super().setUp()
        process_request_validation = patch.object(
            self.handler,
            "process_request_validation",
            return_value=(False, "ValidateResults")
        )

        process_request_validation.start()
        self.addCleanup(process_request_validation.stop)

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=True,
    )
    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.get_external_configs", return_value=EXTERNAL_CONFIGS)
    def test_it_cannot_validate_the_request(self, get_external_configs, rx_account_log_buckets):
        with patch.object(self.handler, "get_cross_account_session", return_value=VALID_SESSION):
            response = self.handler.process(VALID_CREATE_EVENT)
            assert response == "ValidateResults"


VALID_SESSION = (True, "Session")
INVALID_SESSION = (False, "Session")
class TestValidCreate(AuthorizedTestCase):
    def setUp(self):
        super().setUp()
        self.process_request_validation = Mock()
        self.process_request_validation.cloud_provider = "Google"
        process_request_validation = patch.object(
            self.handler,
            "process_request_validation",
            return_value=(True, self.process_request_validation),
        )

        process_request_validation.start()
        
        self.addCleanup(process_request_validation.stop)
    
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=True,
    )
    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.get_external_configs", return_value=EXTERNAL_CONFIGS)
    def test_it_is_not_cloud_provider_aws(self, external_configs, rx_account_log_buckets):
        with patch.object(self.handler, "get_cross_account_session", return_value=VALID_SESSION):
            response = self.handler.process(VALID_CREATE_EVENT)

            assert response.get("statusCode") == 400
            assert re.match("Cloud provider not supported", response.get("body"))

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=True,
    )
    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.get_external_configs", return_value=EXTERNAL_CONFIGS)
    def test_it_is_cloud_provider_aws_and_has_no_account(self, external_configs, rx_account_log_buckets):
        self.process_request_validation.cloud_provider = "AWS"
        sessions = [VALID_SESSION, INVALID_SESSION]
        with patch.object(self.handler, "get_cross_account_session", side_effect=sessions):
            response = self.handler.process(VALID_CREATE_EVENT)
            assert response.get("statusCode") == 404
            assert re.match("No account found", response.get("body"))

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.retrieve_account_log_buckets",
        return_value=True,
    )
    @patch("vpcx_core_infra.vpcx_cdk.vpc_create_handler.cdk_orchestrator.get_external_configs", return_value=EXTERNAL_CONFIGS)
    def test_it_is_cloud_provider_aws_and_has_an_account(self, external_configs, rx_account_log_buckets):
        
        self.process_request_validation.cloud_provider = "AWS"
        validation = (False, "UpdateResult")
        sessions = [VALID_SESSION, VALID_SESSION]

        with patch.object(self.handler, "process_update_context_validation", return_value=validation):
            with patch.object(self.handler, "get_cross_account_session", side_effect=sessions):
                response = self.handler.process(VALID_CREATE_EVENT)
                assert response == "UpdateResult"
