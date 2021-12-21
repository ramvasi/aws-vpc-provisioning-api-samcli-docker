# pylint: disable=line-too-long
"""VPC Update handler"""
import json
from vpcx_core_infra.vpcx_cdk.vpc_base import VpcHandler, METADATA_TEMPLATE_BUCKET, STATIC_CF_TEMPLATE_BUCKET
from vpcx_core_infra.vpcx_cdk import cdk_orchestrator
from vpcx_core_infra.vpcx_cdk.vpc_context import VpcContext


class UpdateVpcHandler(VpcHandler):
    @staticmethod
    def validate_request(request_body):
        account_alias = request_body.get('account_alias', None)
        vpcx_name = request_body.get('vpcx_name', None)
        if account_alias is None or vpcx_name is None:
            return False, {
                'statusCode': 400,
                'body': "Missing a required field"
            }

        context_data = cdk_orchestrator.get_context_data_from_metadata_store(METADATA_TEMPLATE_BUCKET,
                                                                             account_alias,
                                                                             vpcx_name)
        if context_data is None:
            return False, {
                'statusCode': 404,
                'body': "No VPCx VPC found."
            }
        return True, VpcContext.init_from_storage(context_data)

    def process(self, event):
        auth_error = self.auth(event)
        if auth_error:
            return auth_error

        request_body = json.loads(event['body'])
        validate_success, validate_results = self.validate_request(request_body)
        if not validate_success:
            return validate_results
        vpc_context = validate_results

        metadata_account_result, metadata_account_session = self.get_cross_account_session('METADATA_ACCOUNT_ALIAS')
        if not metadata_account_result:
            return {
                'statusCode': 404,
                'body': 'No metadata account found.'
            }
        target_result, target_account_session = self.get_cross_account_session(request_body["account_alias"], vpc_context.region)
        if not target_result:
            return {
                'statusCode': 404,
                'body': 'No account found.'
            }
        # Get external configs
        external_configs = cdk_orchestrator.get_external_configs(request_body.get('region'),
                                                                 STATIC_CF_TEMPLATE_BUCKET,
                                                                 metadata_account_session)
        # Generate CF template
        stack_name, cf_template = cdk_orchestrator.build_cf_template(vpc_context, external_configs)
        # Kickoff stack update
        return self.update_cf_stack(
            cf_template,
            stack_name,
            target_account_session.client('cloudformation'),
            vpc_context
        )