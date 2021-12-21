# pylint: skip-file
"""Test request validations"""
import pytest
from vpc_core_infra.request_validation import validate_vpc_request, vpcx_request_validation_exceptions


def test_check_subnet_cidr_overlap_1():
    """Test normal scenario"""
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    subnet_cidrs = [
        "10.0.0.0/24",
        "10.0.1.0/24",
        "10.0.2.0/24",
        "10.0.3.0/24"
    ]
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is True


def test_check_subnet_cidr_overlap_2():
    """Test scenario with multiple top level CIDRs"""
    vpc_cidrs = [
        "192.168.0.0/16",
        "10.0.0.0/16"
    ]
    subnet_cidrs = [
        "10.0.0.0/24",
        "10.0.1.0/24",
        "10.0.2.0/24",
        "10.0.3.0/24",
        "192.168.0.0/24",
        "192.168.1.0/24"
    ]
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is True


def test_check_subnet_cidr_overlap_3():
    """Test scenario with missing top level CIDRs"""
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    subnet_cidrs = [
        "10.0.0.0/24",
        "10.0.1.0/24",
        "10.0.2.0/24",
        "10.0.3.0/24",
        "192.168.0.0/24",
        "192.168.1.0/24"
    ]
    # with pytest.raises(vpcx_request_validation_exceptions.SubnetCidrOverlap):
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is False


def test_check_subnet_cidr_overlap_4():
    """Test scenario with a random CIDR """
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    subnet_cidrs = [
        "10.0.0.0/24",
        "10.0.1.0/24",
        "10.0.2.0/24",
        "10.0.3.0/24",
        "150.134.0.0/24"
    ]
    # with pytest.raises(vpcx_request_validation_exceptions.SubnetCidrOverlap):
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is False


def test_check_subnet_cidr_overlap_5():
    """Test scenario with a overlapping CIDR """
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    subnet_cidrs = [
        "10.0.0.0/24",
        "10.0.1.0/24",
        "10.0.2.0/24",
        "10.0.2.128/32"
    ]
    # with pytest.raises(vpcx_request_validation_exceptions.SubnetCidrOverlap):
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is False


def test_check_subnet_cidr_overlap_empty():
    """Test scenario with a overlapping CIDR """
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    subnet_cidrs = []
    assert validate_vpc_request.is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs) is True


def test_check_cidr_size():
    """Test scenario with a well sized VPC CIDR """
    vpc_cidrs = [
        "10.0.0.0/16"
    ]
    assert validate_vpc_request.cidr_mask_clears_minimum_size(vpc_cidrs, 24) is True


def test_check_cidr_size_too_small():
    """Test scenario with a well sized VPC CIDR """
    vpc_cidrs = [
        "10.0.0.0/28"
    ]
    assert validate_vpc_request.cidr_mask_clears_minimum_size(vpc_cidrs, 24) is False
