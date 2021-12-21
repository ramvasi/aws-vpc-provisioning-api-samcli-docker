# pylint: skip-file
"""Test update context from current state"""
from unittest.mock import Mock, patch

import vpc_core_infra.vpcx_cdk.cdk_orchestrator as cdk_orchestrator

MOCK_AVAILABILIY_ZONES = ["us-east-1a", "us-east-1b"]
MOCK_EXISTING_VPCS = {
    "Vpcs": [
        {
            "CidrBlock": "CidrBlock",
            "VpcId": "VpcId",
        }
    ],
    "RouteTables": [
        {
            "Associations": [],
            "Routes": [],
            "RouteTableId": "RouteTableId",
            "PropagatingVgws": [],
            "VicId": "VpcId",
        }
    ]
}

MOCK_TRANSIT_GATEWAY_IDS = ["TgwId1", "TgwId2"]
MOCK_STACK_NAMES = ["StackName1", "StackName2"]
@patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.ec2_interactions")
@patch("vpcx_core_infra.vpcx_cdk.cdk_orchestrator.cf_interactions")
def test_update_context_from_current_state(_cf_interactions, _ec2_interactions):
    _ec2_interactions.get_availability_zones = Mock(return_value=MOCK_AVAILABILIY_ZONES)
    _ec2_interactions.get_existing_vpcs = Mock(return_value=MOCK_EXISTING_VPCS)
    _ec2_interactions.get_active_transit_gateway_ids = Mock(return_value=MOCK_TRANSIT_GATEWAY_IDS)

    _cf_interactions.get_all_stack_names = Mock(return_value=MOCK_STACK_NAMES)

    vpc_context = Mock()

    ec2_client = Mock()
    cf_client = Mock()
    session = Mock()
    session.client.side_effect = [ec2_client, cf_client]

    cdk_orchestrator.update_context_from_current_state(vpc_context, session)

    _ec2_interactions.get_availability_zones.assert_called_once_with(ec2_client)
    _ec2_interactions.get_existing_vpcs.assert_called_once_with(ec2_client)
    _ec2_interactions.get_active_transit_gateway_ids.assert_called_once_with(ec2_client)
    _cf_interactions.get_all_stack_names.assert_called_once_with(cf_client)

    vpc_context.set_vpcx_name.assert_called_once_with(stack_names=MOCK_STACK_NAMES)
    vpc_context.set_owned_peers.assert_called_once_with(current_state=MOCK_EXISTING_VPCS)
    vpc_context.set_transit_gateway.assert_called_once_with(tgw_ids=MOCK_TRANSIT_GATEWAY_IDS)
    