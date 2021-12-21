# pylint: skip-file
from unittest import TestCase
from unittest.mock import patch, MagicMock, Mock

MOCK_CREDENTIALS = ("username", "password",)
MOCK_APPSYNC_INFO = ("endpoint", "api_key",)
MOCK_PROVISIONING_SECRET = "secret"

class ConfiguredComponent(TestCase):
    def setUp(self):
        credentials_patch = patch("utils.secrets.retrieve_ldap_credentials", return_value=MOCK_CREDENTIALS)
        appsync_info_patch = patch("utils.secrets.retrieve_vpcx_appsync_info", return_value=MOCK_APPSYNC_INFO)
        client_secret_patch = patch("utils.secrets.retrieve_client_secret", return_value=MOCK_PROVISIONING_SECRET)
        # azure_access_token_patch = patch("utils.secrets. get_azure_ad_access_token", return_value=MOCK_ACCESS_TOKEN)
        credentials_patch.start()
        appsync_info_patch.start()
        client_secret_patch.start()
        # azure_access_token_patch.start()

        self.addCleanup(credentials_patch.stop)
        self.addCleanup(appsync_info_patch.stop)
        self.addCleanup(client_secret_patch.stop)