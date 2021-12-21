# pylint: disable=line-too-long
import json
import traceback

import boto3
from boto3 import Session
from botocore.exceptions import ClientError

from vpcx_core_infra.vpcx_cdk.vpc_base import VpcHandler, LOGGER, STATIC_CF_TEMPLATE_BUCKET
from vpcx_core_infra.vpcx_cdk import cdk_orchestrator
from vpcx_core_infra.vpcx_cdk.vpc_context import VpcContext
from vpcx_core_infra.request_validation import vpcx_request_validation_exceptions


class CreateVpcHandler(VpcHandler):
    @staticmethod
    def process_request_validation(request_body, region_config, region_to_log_bucket_dict):
        """
        Validate input request and return results to user

        Args:
            request_body: request body
            region_config: region configuration from params
            region_to_log_bucket_dict: dictionary that maps region to its log bucket for account

        Returns: tuple of success, VPC context or failure, error
        """
        try:
            vpc_context = VpcContext.init_from_request_body(request_body, region_config, region_to_log_bucket_dict)
            return True, vpc_context
        except vpcx_request_validation_exceptions.VpcRequestException as e:
            LOGGER.error("Error validating request: %s", str(e.message))
            traceback.print_exc()
            return False, {
                'statusCode': e.status_code,
                'body': e.message
            }
        except Exception as e:
            LOGGER.error(f"Error processing request {e}")
            traceback.print_exc()
            return False, {
                'statusCode': 500,
                'body': "Error occurred processing request"
            }

    @staticmethod
    def process_update_context_validation(context: VpcContext, session):
        """
        Validate input request and return results to user

        Args:
            context: base context from request
            session: AWS session for target account

        Returns: tuple of success, updated VPC context or failure, error response
        """
        try:
            updated_context = cdk_orchestrator.update_context_from_current_state(context, session)
            return True, updated_context
        except vpcx_request_validation_exceptions.VpcRequestException as e:
            LOGGER.error("Error validating request: %s", str(e.message))
            traceback.print_exc()
            return False, {
                'statusCode': e.status_code,
                'body': e.message
            }
        except Exception as e:
            LOGGER.error(f"Error processing request {e}")
            traceback.print_exc()
            return False, {
                'statusCode': 500,
                'body': "Error occurred processing request"
            }

    @staticmethod
    def assume_role_session(region, sts_client_source_account, destination_account, role_name, service):
        """Assume a role and return a session for a service in the account

        Args:
            region: The region for the session
            sts_client_source_account: The authenticated STS client for the account from which the role is being assumed
            destination_account: The account, role from which is being assumed
            role_name: Name of the role to be assumed
            service: The service for which an authenticated session will be returned

        Returns:
            new_session: The authenticated client for the service in the destination account

        Raises:
            ClientError: Boto3 error
        """
        try:
            session = sts_client_source_account.assume_role(
                RoleArn='arn:aws:iam::' + str(destination_account) + ':role/' + role_name,
                RoleSessionName='BDDAssumeRoleSession'
            )
            sts_session = Session(
                aws_access_key_id=session['Credentials']['AccessKeyId'],
                aws_secret_access_key=session['Credentials']['SecretAccessKey'],
                aws_session_token=session['Credentials']['SessionToken']
            )
            #new_session = sts_session.client(service, region_name=region)
            return sts_session
        except ClientError:
            raise

    def process(self, event):
        LOGGER.info("VPC_Create_handler - Received infrastructure integration request: %s", event)
        auth_error = self.auth(event)
        if auth_error:
            return auth_error

        # return {"statusCode": 200, "body": "Success"}

        LOGGER.info("VPC_Create_handler - Received infrastructure integration request: %s", event)
        request_body = json.loads(event['body'])
        account_alias = request_body.get('account_alias', None)
        request_region = request_body.get('region')
        # Get external configs
        external_configs = cdk_orchestrator.get_external_configs(request_body.get('region'),
                                                                 STATIC_CF_TEMPLATE_BUCKET,
                                                                 metadata_account_session=None)
        # Validate input
        validate_success, validate_results = self.process_request_validation(request_body,
                                                                             external_configs["region_config"],
                                                                             {request_region: 'vpcx-vpc-flow-logs-us-west-2'})
        if not validate_success:
            return validate_results

        #print('validate results:{}'.format(json.dumps(validate_results)))


        vpc_context = validate_results
        # Begin request processing
        if vpc_context.cloud_provider.upper() == "AWS":
            # Get cross-account session
            try:
                target_account_session = self.assume_role_session(request_region, boto3.client('sts'), account_alias, 'vpcx_admin_role', 'lambda')
            except Exception as e:
                LOGGER.exception("Error while getting target account session")
                return {
                    'statusCode': 404,
                    'body': 'No account found.'
                }
            # Get current state data
            update_success, update_result = self.process_update_context_validation(vpc_context, target_account_session)
            if not update_success:
                return update_result
            updated_context = update_result
            # Generate CF template
            stack_name, cf_template = cdk_orchestrator.build_cf_template(updated_context, external_configs)
            # Kickoff stack update
            print('cf_template', json.dumps(cf_template))
            #return {"statusCode": 200, "body": str(cf_template)}
            return self.update_cf_stack(
                cf_template,
                stack_name,
                target_account_session.client('cloudformation', region_name=updated_context.region),
                updated_context
            )
        else:
            return {
                'statusCode': 400,
                'body': 'Cloud provider not supported.'
            }