# pylint: skip-file
"""Test vpc context"""
import pytest
import vpc_core_infra.vpcx_cdk.vpc_context as vpc_con
import vpc_core_infra.request_validation.vpcx_request_validation_exceptions as val_excepts
import json

MOCK_REGION_CONFIG = {
    'master-cidr': ['', ''],
    'tgw-available': False,
    'service-accounts': ['']
}

TEST_LOG_BUCKET_DICT = {"us-east-1": "test-log-bucket"}


def test_context_from_request_with_blocks():
    private_test_blocks = ["192.168.0.0/24", "192.168.1.0/24", "192.168.2.0/24"]
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_blocks": private_test_blocks
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    assert (len(context.vpc_private_subnet_cidrs) == 3)
    for netw in context.vpc_private_subnet_cidrs:
        assert netw in private_test_blocks
    assert context.vpc_type == vpc_con.VpcType.primary


def _get_context():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    return vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_from_request_with_count():
    context = _get_context()
    assert (len(context.vpc_private_subnet_cidrs) == 4)
    assert len(context.vpc_public_subnet_cidrs) == 0
    assert "/19" in context.vpc_private_subnet_cidrs[0]


def test_vpc_context_init_from_store():
    # Simulating S3 storage and then retrieval
    json_data = _get_context().output_class_to_dict()
    context = vpc_con.VpcContext.init_from_storage(json_data)
    assert (len(context.vpc_private_subnet_cidrs) == 4)
    assert "/19" in context.vpc_private_subnet_cidrs[0]


def test_context_from_request_with_blocks_outside_vpc():
    private_test_blocks = ["192.168.0.0/24", "192.169.1.0/24", "192.168.2.0/24"]
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_blocks": private_test_blocks
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }

    with pytest.raises(val_excepts.SubnetCidrOverlapException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_from_request_with_blocks_overlapping():
    private_test_blocks = ["192.168.0.0/24", "192.168.0.0/25"]
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/18"],
        'subnets': {
            "private_blocks": private_test_blocks
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }

    with pytest.raises(val_excepts.SubnetCidrOverlapException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_from_count_too_large():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/25"],
        'subnets': {
            "private_count": "1000"
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.SubnetCidrSizeException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_from_count_too_small():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 1
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.VpcMinSubnetCountException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_from_count_too_small_public():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4,
            "public_count": 1
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.VpcMinSubnetCountException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_vpc_too_small():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/30"],
        'subnets': {
            "private_count": 1
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.VpcCidrSizeException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_public_blocks():
    private_test_blocks = ["192.168.0.0/24", "192.168.1.0/24", "192.168.2.0/24"]
    public_test_blocks = ["192.168.3.0/24", "192.168.4.0/24"]
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_blocks": private_test_blocks,
            "public_blocks": public_test_blocks
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    assert (len(context.vpc_private_subnet_cidrs) == 3)
    for netw in context.vpc_private_subnet_cidrs:
        assert netw in private_test_blocks

    assert (len(context.vpc_public_subnet_cidrs) == 2)
    for netw in context.vpc_public_subnet_cidrs:
        assert netw in public_test_blocks

    assert context.vpc_type == vpc_con.VpcType.primary


def test_context_public_from_count():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4,
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    assert len(context.vpc_public_subnet_cidrs) == 2
    assert len(context.vpc_private_subnet_cidrs) == 4


def test_context_public_from_count_zero():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4,
            "public_count": 0
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    assert len(context.vpc_public_subnet_cidrs) == 0
    assert len(context.vpc_private_subnet_cidrs) == 4
    assert len(context.allocated_public_subnet_cidrs) == 0


def test_context_public_from_count_too_small():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": "4",
            "public_count": "1"
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.VpcMinSubnetCountException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_mix_count_blocks():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_blocks": ["192.168.0.0/18"],
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "vgw"
    }
    with pytest.raises(val_excepts.SubnetBlocksCountCombinationException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_primary_bad_connectivity():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 7,
            "public_count": 3
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "badtype"
    }
    with pytest.raises(val_excepts.VpcConnectivityException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_primary_no_connectivity():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4
        },
        'cloud_provider': "AWS",
        'region': "us-east-1"
    }
    with pytest.raises(val_excepts.VpcMissingFieldException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


# Even though connectivity is not required for HPC, passing a bad value is still not allowed
def test_context_hpc_bad_connectivity():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 2,
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "badtype"
    }
    with pytest.raises(val_excepts.VpcConnectivityException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_hpc_no_connectivity():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 8,
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1"
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    assert context.vpc_type == vpc_con.VpcType.hpc
    assert context.connectivity_type is None


def test_context_hpc_max_public_count():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": "2",
            "public_count": 4
        },
        'cloud_provider': "AWS",
        'region': "us-east-1"
    }
    with pytest.raises(val_excepts.MaxPublicSubnetCountException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_owned_peers():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'cloud_provider': "AWS",
        'subnets': {
            "private_count": 2,
            "public_count": 2
        },
        'region': "us-east-1"
    }
    expected_owned_peers = [{
            "vpc_id": "vpc-123",
            "vpc_cidrs": ["10.20.0.0/16"],
            "route_tables": [{"id": "rt-priabc", "name": "primary1PublicRT"},
                             {"id": "rt-pubjkl", "name": "primary1PrivateRT"}]
        },
        {
            "vpc_id": "vpc-456",
            "vpc_cidrs": ["10.21.0.0/16"],
            "route_tables": [{"id": "rt-pridef", "name": "primary2PrivateRT"}]
        }]

    mock_describe_vpc = {
        "Vpcs": [{
            "VpcId": expected_owned_peers[0]["vpc_id"],
            "CidrBlock": expected_owned_peers[0]["vpc_cidrs"][0],
            "CidrBlockAssociationSet": [
                {
                    "CidrBlock": expected_owned_peers[0]["vpc_cidrs"][0]
                }
            ],
            "Tags": [{
                "Key": "vpcx",
                "Value": "primary"
            },
                {
                    "Key": "Name",
                    "Value": "primary-USEA11"
                }
            ]
        },
            {
                "VpcId": expected_owned_peers[1]["vpc_id"],
                "CidrBlock": expected_owned_peers[1]["vpc_cidrs"][0],
                "CidrBlockAssociationSet": [
                    {
                        "CidrBlock": expected_owned_peers[1]["vpc_cidrs"][0]
                    }
                ],
                "Tags": [{
                    "Key": "vpcx",
                    "Value": "primary"
                },
                {
                    "Key": "Name",
                    "Value": "primary-USEA12"
                }
                ]
            }
        ],
        "RouteTables": [
            {
                "VpcId": expected_owned_peers[0]["vpc_id"],
                "RouteTableId": expected_owned_peers[0]["route_tables"][0]["id"],
                "Tags": [{
                    "Key": "Name",
                    "Value": expected_owned_peers[0]["route_tables"][0]["name"]
                }]
            },
            {
                "VpcId": expected_owned_peers[0]["vpc_id"],
                "RouteTableId": expected_owned_peers[0]["route_tables"][1]["id"],
                "Tags": [{
                    "Key": "Name",
                    "Value": expected_owned_peers[0]["route_tables"][1]["name"]
                }]
            },
            {
                "VpcId": expected_owned_peers[1]["vpc_id"],
                "RouteTableId": expected_owned_peers[1]["route_tables"][0]["id"],
                "Tags": [{
                    "Key": "Name",
                    "Value": expected_owned_peers[1]["route_tables"][0]["name"]
                }]
            }
        ]
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    context.set_owned_peers(mock_describe_vpc)
    assert context.owned_peers == expected_owned_peers


def test_hpc_already_exists():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/18"],
        'cloud_provider': "AWS",
        'subnets': {
            "private_count": 2,
            "public_count": 2
        },
        'region': "us-east-1"
    }
    mock_describe_vpc = {
        "Vpcs": [{
            "VpcId": "vpc-123",
            "CidrBlock": "192.168.0.0/18",
            "CidrBlockAssociationSet": [
                {
                    "CidrBlock": "192.168.0.0/18"
                }
            ],
            "Tags": [{
                    "Key": "vpcx",
                    "Value": "hpc"
                },
                {
                    "Key": "Name",
                    "Value": "hpc-USEA11"
                }
            ]
        }
        ],
        "RouteTables": [
            {
                "VpcId": "vpc-123",
                "RouteTableId": "rt-456",
                "Tags": [{
                    "Key": "Name",
                    "Value": "hpcPrivateRouteTable"
                }]
            },
            {
                "VpcId": "vpc-123",
                "RouteTableId": "rt-789",
                "Tags": [{
                    "Key": "Name",
                    "Value": "hpcPublicRouteTable"
                }]
            }
        ]
    }
    context = vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
    with pytest.raises(val_excepts.VpcTypeAlreadyPresentException):
        context.set_owned_peers(mock_describe_vpc)


def test_context_tgw_not_available():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4,
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "tgw"
    }
    with pytest.raises(val_excepts.VpcTgwConnectivityException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)


def test_context_tgw_is_available():
    request_body = {
        "account_alias": "something",
        'vpc_type': "primary",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": 4,
            "public_count": 2
        },
        'cloud_provider': "AWS",
        'region': "us-east-1",
        'connectivity_type': "tgw"
    }
    tgw_true_config = MOCK_REGION_CONFIG.copy()
    tgw_true_config["tgw-available"] = True
    context = vpc_con.VpcContext.init_from_request_body(request_body, tgw_true_config, TEST_LOG_BUCKET_DICT)
    assert context.connectivity_type == vpc_con.VpcConnectivity.tgw

def test_context_no_log_bucket_for_region():
    request_body = {
        "account_alias": "something",
        'vpc_type': "hpc",
        'vpc_top_level_cidr': ["192.168.0.0/16"],
        'subnets': {
            "private_count": "2",
            "public_count": 4
        },
        'cloud_provider': "AWS",
        'region': "us-west-1"
    }
    with pytest.raises(val_excepts.MissingConfiguredLogBucketException):
        vpc_con.VpcContext.init_from_request_body(request_body, MOCK_REGION_CONFIG, TEST_LOG_BUCKET_DICT)
