# pylint: disable=line-too-long
import logging
import traceback
import os
import boto3

from vpcx_core_infra.vpcx_cdk.cdk_orchestrator import push_to_metadata_store
from vpcx_core_infra.utils import vpcx_account, cf_interactions

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

METADATA_TEMPLATE_BUCKET = os.environ['METADATA_TEMPLATE_BUCKET']
STATIC_CF_TEMPLATE_BUCKET = os.environ.get('STATIC_CF_TEMPLATE_BUCKET')


class VpcHandler(object):

    def get_cross_account_session(self, account_alias, region="us-east-1"):
        credential_result, target_credentials = self.get_target_account_credentials(account_alias)
        if not credential_result:
            return False, None

        return True, boto3.Session(
            region_name=region,
            aws_access_key_id=target_credentials['AccessKeyId'],
            aws_secret_access_key=target_credentials['SecretAccessKey'],
            aws_session_token=target_credentials['SessionToken']
        )

    @staticmethod
    def auth(event):
        """Lambda handler"""
        LOGGER.info("Received infrastructure integration request: %s", event)
        # return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": "Success"}
        # Authorize request
        try:
            pass
        except Exception as e:
            LOGGER.error(e)
            traceback.print_exc()
            return {
                'statusCode': 401,
                'body': 'Invalid user.'
            }
        # Extract account info
        return None

    @staticmethod
    def update_cf_stack(cf_template, stack_name, cf_client, updated_context):
        """
        Update CF stack and metadata file in S3

        Args:
            cf_template: CF template
            stack_name: Stack name
            cf_client: CF boto3 client
            updated_context: updated vpc context object

        Returns: Lambda response
        """
        # Run template in account
        try:
            # Deploy stack
            cf_interactions.sync_run_template(cf_template, [], stack_name, cf_client)
            # Save metadata to S3
            push_to_metadata_store(
                METADATA_TEMPLATE_BUCKET,
                cf_template,
                updated_context
            )
        except cf_interactions.VPCxStackNoUpdateException as e:
            LOGGER.info("No stack update required")
            return {
                'statusCode': 200,
                'body': 'No stack update required.'
            }
        except Exception as e:
            LOGGER.info("Error with operation %s", e)
            traceback.print_exc()
            return {
                'statusCode': 500,
                'body': 'Failed to update stack.'
            }
        # Send response
        return {
            'statusCode': 200,
            'body': 'VPC stack updated.'
        }

