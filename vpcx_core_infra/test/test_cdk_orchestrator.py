# pylint: skip-file
"""Test cdk orchestrator"""
import pytest
from unittest.mock import Mock, patch

import vpc_core_infra.vpcx_cdk.cdk_orchestrator as cdk_orchestrator
from vpc_core_infra.vpcx_cdk.vpc_context import VpcContext
from vpc_core_infra.test.test_cdk_orch_mocks import MOCK_EXTERNAL_CONFIG


def test_build_cf_template_private_only():
    private_blocks = ["192.168.0.0/24", "192.168.1.0/24"]
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="primary",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/16"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=private_blocks,
                         vpc_public_subnet_cidrs=[],
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[],
                         connectivity_type="vgw",
                         transit_gateway=None)

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "AWS::EC2::VPC" in stack
    # The route table associations will match without the escaped quotes
    assert stack.count("\"AWS::EC2::Subnet\"") == len(private_blocks)
    assert "AWS::EC2::DHCPOptions" in stack


def test_build_cf_template_multi_vpc_cidr():
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="primary",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/17", "192.168.128.0/17"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=["192.168.0.0/24", "192.168.1.0/24"],
                         vpc_public_subnet_cidrs=[],
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[],
                         connectivity_type="vgw",
                         transit_gateway=None)

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "AWS::EC2::VPCCidrBlock" in stack


def test_build_cf_template_public_cidr():
    priv_blocks = ["192.168.0.0/24", "192.168.1.0/24"]
    pub_blocks = ["192.168.2.0/24", "192.168.3.0/24"]
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="primary",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/17", "192.168.128.0/17"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=priv_blocks,
                         vpc_public_subnet_cidrs=pub_blocks,
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[],
                         connectivity_type="vgw",
                         transit_gateway=None)

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "AWS::EC2::VPCEndpoint" in stack
    assert "S3Gateway" in stack
    assert "AWS::EC2::InternetGateway" in stack
    assert "AWS::EC2::NatGateway" not in stack
    assert stack.count("\"AWS::EC2::Subnet\"") == len(pub_blocks) + len(priv_blocks)
    print(stack)


def test_build_cf_template_hpc():
    priv_blocks = ["192.168.0.0/24", "192.168.1.0/24"]
    pub_blocks = ["192.168.2.0/24", "192.168.3.0/24"]
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="hpc",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/17", "192.168.128.0/17"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=priv_blocks,
                         vpc_public_subnet_cidrs=pub_blocks,
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[{"vpc_id": "vpc-123",
                                       "vpc_cidrs": ["10.0.0.0/16"],
                                       "route_tables": [{"id": "rt-pub12",
                                                         "name": "primary1PublicRt"},
                                                        {"id": "rt-pri34",
                                                         "name": "primary1PrivateRt"}]
                                       }, {
                                          "vpc_id": "vpc-456",
                                          "vpc_cidrs": ["10.1.0.0/16"],
                                          "route_tables": [{"id": "rt-pri56",
                                                            "name": "primary2PrivateRt"}]
                                      }
                                      ],
                         connectivity_type="vgw",
                         transit_gateway=None)

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "AWS::EC2::VPCEndpoint" in stack
    assert "S3Gateway" in stack
    assert "AWS::EC2::InternetGateway" in stack
    assert "AWS::EC2::NatGateway" in stack
    assert "AWS::EC2::DHCPOptions" not in stack
    assert stack.count("AWS::EC2::VPCPeeringConnection") == 2


def test_build_cf_template_tgw():
    priv_blocks = ["192.168.0.0/24", "192.168.1.0/24"]
    pub_blocks = ["192.168.2.0/24", "192.168.3.0/24"]
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="primary",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/17"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=priv_blocks,
                         vpc_public_subnet_cidrs=pub_blocks,
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[],
                         connectivity_type="tgw",
                         transit_gateway="tgw-123")

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "AWS::EC2::TransitGatewayAttachment" in stack


def test_build_cf_template_primary_peer_hpc():
    priv_blocks = ["192.168.0.0/24", "192.168.1.0/24"]
    pub_blocks = ["192.168.2.0/24", "192.168.3.0/24"]
    context = VpcContext(account_alias="alias",
                         log_bucket="test-log-bucket",
                         vpc_type="primary",
                         vpcx_name="name",
                         vpc_top_level_cidr=["192.168.0.0/17"],
                         region="us-east-1",
                         availability_zones=["us-east-1a", "us-east-1b"],
                         cloud_provider="AWS",
                         vpc_private_subnet_cidrs=priv_blocks,
                         vpc_public_subnet_cidrs=pub_blocks,
                         allocated_public_subnet_cidrs=[],
                         owned_peers=[{
                             "vpc_id": "vpc-123",
                             "vpc_cidrs": "10.0.0.0/24",
                             "route_tables": [{
                                 "id": "rt-123SHOULDBEPRESENT",
                                 "name": "hpcPrivateRt"
                             }, {
                                 "id": "rt-456NOTROUTED",
                                 "name": "hpcPublicRt"
                             }
                             ]
                         }],
                         connectivity_type="vgw",
                         transit_gateway=None)

    n, stack = cdk_orchestrator.build_cf_template(context, MOCK_EXTERNAL_CONFIG)
    assert "rt-123SHOULDBEPRESENT" in stack
    assert "rt-456NOTROUTED" not in stack
