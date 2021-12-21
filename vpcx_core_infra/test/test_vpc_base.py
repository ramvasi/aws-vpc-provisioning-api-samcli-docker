# pylint: skip-file
from unittest.mock import patch, MagicMock, Mock

from .configured_component import (
    ConfiguredComponent,
    MOCK_CREDENTIALS,
    MOCK_APPSYNC_INFO,
    MOCK_PROVISIONING_SECRET,
)

import re
import os
import json

class TestVpcHandler(ConfiguredComponent):
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.secrets.get_azure_ad_access_token",
        side_effect=Exception("No access token"),
    )
    def test_it_cannot_get_an_azure_token(self, get_access_token):
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler

        success, _ = VpcHandler.get_target_account_credentials(
            "account_alias"
        )

        assert success == False

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.secrets.get_azure_ad_access_token",
        return_value=None,
    )
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.vpcx_account.get_vpcx_account_admin_credentials",
        side_effect=Exception("No admin credentials"),
    )
    def test_it_cannot_get_an_azure_token(self, get_admin_credentials, get_access_token):
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler

        success, _ = VpcHandler.get_target_account_credentials(
            "account_alias"
        )

        assert success == False

    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.secrets.get_azure_ad_access_token",
        return_value=None,
    )
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.vpcx_account.get_vpcx_account_admin_credentials",
        return_value=None
    )
    def test_it_gets_target_credentials(self, get_admin_credentials, get_access_token):
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler

        success, _ = VpcHandler.get_target_account_credentials(
            "account_alias"
        )

        assert success == True

VALID_CREDENTIALS = {
    "AccessKeyId": "AccessKeyId",
    "SecretAccessKey": "SecretAccessKey",
    "SessionToken": "SessionToken",
}
class TestGetCrossAccountCredentials(ConfiguredComponent):
    def setUp(self):
        super().setUp()
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler

        self.handler = VpcHandler()
    def test_it_cannot_get_credentials(self):
        with patch.object(
            self.handler,
            "get_target_account_credentials",
            return_value=(False, None),
            ) as fn:
            success, response = self.handler.get_cross_account_session("account_alias")
            fn.assert_called_once_with("account_alias")
            assert success == False

    @patch("boto3.Session", return_value="Boto3Session")
    def test_it_gets_credentials(self, boto3_session):
        self.target_account_credentials = Mock(return_value=(True, VALID_CREDENTIALS))

        with patch.object(
            self.handler,
            "get_target_account_credentials",
            return_value=(True, VALID_CREDENTIALS),
            ) as fn:

            success, session = self.handler.get_cross_account_session("account_alias")

            assert session == "Boto3Session"
            assert success == True
            assert session == "Boto3Session"

class TestAuth(ConfiguredComponent):

    def test_it_fails_to_authorize(self):
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler
        response = VpcHandler.auth({})
        assert response.get("statusCode") == 401
        assert re.match("Invalid user", response.get("body"))
    @patch(
        "vpcx_core_infra.vpcx_cdk.vpc_base.lambda_auth.authorize_lambda_request",
        side_effet=Exception("Error"),
    )
    def test_it_authorizes(self, authorize_lambda_request):
        from vpc_core_infra.vpcx_cdk.vpc_base import VpcHandler

        response = VpcHandler.auth({})
        assert response == None
        