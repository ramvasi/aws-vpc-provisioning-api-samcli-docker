"""Module for validating VPC request"""
import ipaddress
from vpcx_core_infra.request_validation import vpcx_request_validation_exceptions


def cidr_mask_clears_minimum_size(cidrs: list, min_size: int):
    """
    Verify all subnet masks in a list of CIDR blocks are larger than a minimum

    Args:
        cidrs: list of CIDR block strings
        min_size: smallest size allowed for mask

    Returns: bool
    """
    return all([int(cidr.split("/")[1]) <= min_size for cidr in cidrs])


def is_subnet(a, b):
    """
    Return if "a" is a subnet of "b".

    Note: this functionality is built into the default ip address library
    starting at Python 3.7.  This project uses Python 3.6.
    
    Args:
        a: CIDR
        b: CIDR

    Returns: bool
    """
    # Get CIDR prefix
    a_len = a.prefixlen
    b_len = b.prefixlen
    # Compare prefix lengths
    return a_len >= b_len and a.supernet(a_len - b_len) == b


def is_vpc_subnet_cidr_viable(vpc_cidrs, subnet_cidrs):
    """
    Verify subnets are viable in provided VPCs

    Args:
        vpc_cidrs: top-level VPC CIDR
        subnet_cidrs: subnet CIDRs

    Return: bool if settings are valid
    """
    # Iterate over subnet CIDRs
    for subnet_index, subnet_cidr in enumerate(subnet_cidrs):
        # Initialize subnet CIDR
        subnet_cidr = ipaddress.ip_network(subnet_cidr)
        # Verify subnet CIDR is a subnet of one of the VPC CIDRs
        vpc_overlap_found = False
        for vpc_cidr in vpc_cidrs:
            # Initialize VPC CIDR
            vpc_cidr = ipaddress.ip_network(vpc_cidr)
            # Check if subnet is within CIDR
            if is_subnet(subnet_cidr, vpc_cidr):
                vpc_overlap_found = True
                break
        # Check if VPC overlap was found
        if not vpc_overlap_found:
            return False
        # Verify subnet CIDR does not overlap one of the other subnets
        for compare_index, compare_cidr in enumerate(subnet_cidrs):
            # Skip compare to self
            if compare_index == subnet_index:
                continue
            # Initialize compare subnet CIDR
            compare_cidr = ipaddress.ip_network(compare_cidr)
            # Verify no subnet overlap
            if subnet_cidr.overlaps(compare_cidr):
                return False
    return True
