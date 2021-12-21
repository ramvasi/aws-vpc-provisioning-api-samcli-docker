# pylint: disable=line-too-long
"""
VPC Context Class for storing incoming metadata from either API call or S3 Bucket to be used when generating a
CFN template for VPC Creation.
"""
import json
import logging
from datetime import datetime
from enum import Enum, auto
import math
from netaddr import (
    IPNetwork
)

from vpcx_core_infra.request_validation import (
    vpcx_request_validation_exceptions as val_excepts,
    validate_vpc_request as net_validation
)

# Initialize Logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class VpcType(Enum):
    hpc = auto()
    primary = auto()

    def __str__(self):
        return str(self.name)

    def get_peer_type(self):
        if self == VpcType.hpc:
            return VpcType.primary
        else:
            return VpcType.hpc


class VpcConnectivity(Enum):
    vgw = auto()
    tgw = auto()

    def __str__(self):
        return str(self.name)


class VpcContext(object):
    """
    Class used to generate VPCx VPC
    """
    # Define smallest allowed size for a subnet
    MIN_SUBNET_CIDR_MASK = 28
    # Define smallest allowed size for a vpc
    MIN_VPC_CIDR_MASK = 26
    # Define smallest allowed size for a subnet
    MIN_SUBNET_COUNT = 2
    # Minimum / default sizes if none provided
    DEFAULT_PRIVATE_COUNT = 2
    DEFAULT_PUBLIC_COUNT = 0
    ALLOCATED_PUBLIC_COUNT = 2

    # Max HPC Public Count
    MAX_HPC_PUBLIC_COUNT = 2

    def __init__(self,
                 account_alias,
                 log_bucket,
                 vpc_type,
                 vpcx_name,
                 vpc_top_level_cidr,
                 region,
                 availability_zones,
                 cloud_provider,
                 vpc_private_subnet_cidrs,
                 vpc_public_subnet_cidrs,
                 allocated_public_subnet_cidrs,
                 owned_peers,
                 connectivity_type,
                 transit_gateway):

        self.account_alias = account_alias
        self.log_bucket = log_bucket
        self.vpc_type = VpcType[vpc_type.lower()]
        self.vpcx_name = vpcx_name
        self.vpc_top_level_cidr = vpc_top_level_cidr
        self.region = region
        self.availability_zones = availability_zones
        self.cloud_provider = cloud_provider
        self.vpc_private_subnet_cidrs = vpc_private_subnet_cidrs
        self.vpc_public_subnet_cidrs = vpc_public_subnet_cidrs
        self.allocated_public_subnet_cidrs = allocated_public_subnet_cidrs
        self.owned_peers = owned_peers
        self.transit_gateway = transit_gateway
        # Connectivity type is always effectively None for HPC so reflecting that here
        self.connectivity_type = None if not connectivity_type or self.vpc_type == VpcType.hpc \
            else VpcConnectivity[connectivity_type.lower()]

    @classmethod
    def init_from_storage(cls, json_data):
        """
        Class method to init VpcContext object from JSON metadata retrieved from S3

        Args:
            json_data: JSON metadata object from S3

        Returns: VpcContext Object
        """
        # Unpack JSON
        account_alias = json_data['account_alias']
        log_bucket = json_data['log_bucket']
        vpc_type = json_data['vpc_type']
        vpcx_name = json_data['vpcx_name']
        vpc_top_level_cidr = json_data['vpc_top_level_cidr']
        region = json_data['region']
        availability_zones = json_data['availability_zones']
        cloud_provider = json_data['cloud_provider']
        vpc_private_subnet_cidrs = json_data['subnets']['private']
        vpc_public_subnet_cidrs = json_data['subnets']['public']
        allocated_public_subnet_cidrs = json_data['subnets']['allocated_public']
        owned_peers = json_data['owned_peers']
        connectivity_type = json_data['connectivity_type']
        transit_gateway = json_data['transit_gateway']

        # Return object
        return cls(
            account_alias=account_alias,
            log_bucket=log_bucket,
            vpc_type=vpc_type,
            vpcx_name=vpcx_name,
            vpc_top_level_cidr=vpc_top_level_cidr,
            region=region,
            availability_zones=availability_zones,
            cloud_provider=cloud_provider,
            vpc_private_subnet_cidrs=vpc_private_subnet_cidrs,
            vpc_public_subnet_cidrs=vpc_public_subnet_cidrs,
            allocated_public_subnet_cidrs=allocated_public_subnet_cidrs,
            owned_peers=owned_peers,
            connectivity_type=connectivity_type,
            transit_gateway=transit_gateway
        )

    @classmethod
    def init_from_request_body(cls, request_body, region_config, region_to_log_bucket_dict):
        """
        Class method to init VpcContext object from API request body. Verifies incoming request input
        and returns a VpcContext object if valid or raises an exception otherwise

        Args:
            request_body: JSON request body
            region_config: aws region config, None if unsupported region
            region_to_log_bucket_dict: dictionary that maps region to its log bucket for account

        Returns: VpcContext Object
        """
        # Unpack requests
        account_alias = request_body.get('account_alias', None)
        vpc_type = request_body.get('vpc_type', None)
        vpcx_name = None
        vpc_top_level_cidr = request_body.get('vpc_top_level_cidr', None)
        subnets = request_body.get('subnets', {})
        cloud_provider = request_body.get('cloud_provider', 'aws')
        region = request_body.get('region', None)
        availability_zones = None
        owned_peers = []
        connectivity_type = request_body.get('connectivity_type', None)
        transit_gateway = None

        # Format inputs
        if not isinstance(vpc_top_level_cidr, list):
            vpc_top_level_cidr = list(vpc_top_level_cidr)
        # Validate incoming request
        cls.validate_incoming_vpc_request(
            account_alias, vpc_type, vpc_top_level_cidr, subnets,
            cloud_provider, region, region_config, connectivity_type, region_to_log_bucket_dict
        )
        # Generate CIDR blocks
        vpc_private_subnet_cidrs, vpc_public_subnet_cidrs, allocated_public_subnet_cidrs = \
            cls.generate_subnet_cidrs(vpc_top_level_cidr, subnets)

        # Return constructor
        return cls(
            account_alias=account_alias,
            log_bucket=region_to_log_bucket_dict[region],
            vpc_type=vpc_type,
            vpcx_name=vpcx_name,
            vpc_top_level_cidr=vpc_top_level_cidr,
            region=region,
            availability_zones=availability_zones,
            cloud_provider=cloud_provider,
            vpc_private_subnet_cidrs=vpc_private_subnet_cidrs,
            vpc_public_subnet_cidrs=vpc_public_subnet_cidrs,
            allocated_public_subnet_cidrs=allocated_public_subnet_cidrs,
            owned_peers=owned_peers,
            connectivity_type=connectivity_type,
            transit_gateway=transit_gateway
        )

    @staticmethod
    def _get_public_and_allocated_count(subnet_dict):
        """
        Static method to determine public subnet and associated allocated count to reserve but not create subnets

        Args:
            subnet_dict: subnet information being passed in

        Returns: tuple of public subnet count, allocated subnet count
        """
        if "public_count" not in subnet_dict.keys():
            public_subnets_requested = VpcContext.DEFAULT_PUBLIC_COUNT
            allocated_subnets_count = VpcContext.ALLOCATED_PUBLIC_COUNT
        else:
            public_subnets_requested = int(subnet_dict["public_count"])
            allocated_subnets_count = 0
        return public_subnets_requested, allocated_subnets_count

    @classmethod
    def generate_subnet_cidrs(cls, vpc_cidrs, subnet_dict: dict):
        """
        Class method to generate subnet CIDRs based on VPC

        Args:
            vpc_cidrs: array of VPC CIDRs
            subnet_dict: subnet information being apssed in

        Returns: tuple of private/public subnets
        """
        # Handle explicitly declared CIDRs
        if "private_blocks" in subnet_dict.keys():
            # No subnets allocated when private / public blocks are explicit
            return subnet_dict['private_blocks'], subnet_dict.get('public_blocks', []), []
        # Assign CIDRs up based on VPC availability
        else:
            private_subnets_requested = int(subnet_dict.get("private_count", VpcContext.DEFAULT_PRIVATE_COUNT))
            public_subnets_requested, allocated_subnets_needed = cls._get_public_and_allocated_count(subnet_dict)
            equal_sized_subnets_to_make = cls._get_total_subnet_count(private_subnets_requested +
                                                                      public_subnets_requested +
                                                                      allocated_subnets_needed)
            subnets_available = cls.calculate_subnet_division(vpc_cidrs, equal_sized_subnets_to_make)
            cidr_blocks_available = [str(subnet) for subnet in subnets_available]

            # We will have at least 2 subnets allocated if no public count is made.
            # The entire remaining block is considered allocated however if there are
            #  additional subnets due to equally sizing divisions
            return (cidr_blocks_available[:private_subnets_requested],
                    cidr_blocks_available[private_subnets_requested:private_subnets_requested+public_subnets_requested],
                    cidr_blocks_available[private_subnets_requested+public_subnets_requested:])


    @staticmethod
    def _get_total_subnet_count(subnets_requested):
        """
        Static method to convert the requested number of subnets into the amount that will be needed total
        e.g. Requesting 5 subnets will need 8 equally sized subnets to make them all

        Args:
            subnets_requested: requested amount of subnets

        Returns: int total subnets
        """
        return 2 ** (subnets_requested - 1).bit_length()

    def set_vpcx_name(self, stack_names):
        """
        Generate the stack name

        Args:
            stack_names: Other found stack names

        Returns: nothing
        """
        # Translate region to code name, e.g. "us-east-1" will become "USEA1"
        region_to_name = "".join([token[0:2].upper() for token in self.region.split("-")])
        # Find other VPCs in region with same naming convention
        vpcx_name_no_index = f"vpc-{self.vpc_type}-{region_to_name}"
        filtered_list = list(filter(lambda stack_name: vpcx_name_no_index in stack_name, stack_names))
        # Generate stack name
        self.vpcx_name = f"{vpcx_name_no_index}{len(filtered_list)+1}"

    def set_owned_peers(self, current_state: dict):
        """
        Generate the stack name

        Args:
            current_state: dict containing current Vpcs and RouteTables

        Returns: nothing
        """
        # Generate vpc_ids filtered by type via vpcx tag
        peer_vpcs = []
        for vpc in current_state["Vpcs"]:
            for tag in vpc.get("Tags", []):
                if tag["Key"] == "vpcx":
                    # Only one HPC type is allowed, so if request is for one and one already exists raise error
                    if self.vpc_type == VpcType.hpc and tag.get("Value", "") == str(VpcType.hpc):
                        raise val_excepts.VpcTypeAlreadyPresentException(str(self.vpc_type))
                    if tag.get("Value", "") == str(self.vpc_type.get_peer_type()):
                        cidrs = [associated_block["CidrBlock"] for associated_block in vpc.get("CidrBlockAssociationSet", [])]
                        vpc_id = vpc["VpcId"]

                        rt_items = []
                        for route_table in current_state["RouteTables"]:
                            if route_table["VpcId"] == vpc_id:
                                for rt_tag in route_table.get("Tags", []):
                                    if rt_tag.get("Key", "") == "Name":
                                        rt_items.append({
                                            "id": route_table["RouteTableId"],
                                            "name": rt_tag.get("Value")
                                        })
                                        break
                        peer_vpcs.append({
                            "vpc_id": vpc_id,
                            "vpc_cidrs": cidrs,
                            "route_tables": rt_items
                        })
                        break
        self.owned_peers = peer_vpcs

    def set_transit_gateway(self, tgw_ids):
        """
        Set the available transit gateway

        Args:
            tgw_ids: list of the available transit gateway ids

        Returns: nothing
        """
        if self.connectivity_type == VpcConnectivity.tgw:
            if not tgw_ids:
                raise val_excepts.VpcTgwConnectivityException()
            elif len(tgw_ids) > 1:
                raise val_excepts.VpcMultipleTgwException()
            else:
                self.transit_gateway = tgw_ids[0]

    @classmethod
    def calculate_subnet_division(cls, cidr_list, subnet_count):
        """
        Calculate subnet size based on VPC CIDRs and subnet count

        Args:
            cidr_list: List of VPC CIDRs
            subnet_count: Desired subnet count

        Returns: list of subnet assignments
        """
        # First check that subnet length is a power of 2, round up to the nearest valid number if not
        if len(cidr_list) > 1:
            # TODO: Handle VPC CIDR extensions
            LOGGER.info("Only using first CIDR for calculations")
            return cls.generate_single_cidr_subnets(cidr_list, subnet_count)

        return cls.generate_single_cidr_subnets(cidr_list, subnet_count)

    @classmethod
    def generate_single_cidr_subnets(cls, cidr_list, subnet_count):
        """
        Generate subnet for a single top-level CIDR

        Args:
            cidr_list: top-level CIDR
            subnet_count: Desired subnet count

        Returns: list of subnet assignments
        """
        top_level_ip = IPNetwork(cidr_list[0])
        cidr_suffix = int(cidr_list[0].split('/')[1])
        cidr_shift_amount = int(math.log(subnet_count, 2))
        subnet_cidr = cidr_suffix + cidr_shift_amount
        if subnet_cidr > cls.MIN_SUBNET_CIDR_MASK:
            raise val_excepts.SubnetCidrSizeException()
        return list(top_level_ip.subnet(int(subnet_cidr)))

    @classmethod
    def validate_incoming_vpc_request(cls, account_alias, vpc_type,
                                      vpc_top_level_cidr, subnets,
                                      cloud_provider, region, region_config, connectivity_type,
                                      region_to_log_bucket_dict):
        """
        Wrapper method to validate incoming requests

        Args:
            account_alias: account alias
            vpc_type: vpc type (e.g., primary)
            vpc_top_level_cidr: array of top level CIDRs for VPC
            subnets: VPC subnet spec, if applicable
            cloud_provider: cloud provider
            region: cloud provider region
            region_config: list of valid regions
            connectivity_type: connectivity type
            region_to_log_bucket_dict: log bucket by region dict
        """
        # Check if request body values are none
        cls._validate_request_body_fields_not_none(
            account_alias, vpc_type, vpc_top_level_cidr, subnets, cloud_provider, region
        )

        # Check if request body values are invalid
        cls._validate_request_body_fields_validity(
            account_alias, vpc_type, vpc_top_level_cidr, subnets,
            cloud_provider, region, region_config, connectivity_type, region_to_log_bucket_dict
        )

    @staticmethod
    def _validate_request_body_fields_not_none(account_alias, vpc_type, vpc_top_level_cidr,
                                               subnets, cloud_provider, region):
        """
        Validate any required incoming request params are not missing

        Args:
            account_alias: account alias
            vpc_type: vpc type (e.g., primary)
            vpc_top_level_cidr: array of top level CIDRs for VPC
            subnets: VPC subnet spec, if applicable
            cloud_provider: cloud provider
            region: cloud provider region
            connectivity_type: connectivity type, vgw or tgw
        """
        if account_alias is None:
            raise val_excepts.VpcMissingFieldException("account_alias")
        if vpc_type is None:
            raise val_excepts.VpcMissingFieldException("vpc_type")
        if not vpc_top_level_cidr:
            raise val_excepts.VpcMissingFieldException("vpc_top_level_cidr")
        if region is None:
            raise val_excepts.VpcMissingFieldException("region")
        if cloud_provider is None:
            raise val_excepts.VpcMissingFieldException("cloud_provider")
        if subnets:
            if ("private_blocks" in subnets.keys() or "public_blocks" in subnets.keys()) \
                    and ("private_count" in subnets.keys() or "public_count" in subnets.keys()):
                raise val_excepts.SubnetBlocksCountCombinationException()
            if "private_count" not in subnets.keys() and "private_blocks" not in subnets.keys():
                raise val_excepts.VpcMissingFieldException("subnets.private_count OR subnets.private_blocks")
            if "private_count" in subnets.keys() and not str(subnets["private_count"]).isdigit():
                raise val_excepts.VpcMissingFieldException("subnets.private_count (must be integer)")
            if "public_count" in subnets.keys() and not str(subnets["public_count"]).isdigit():
                raise val_excepts.VpcMissingFieldException("subnets.public_count (must be integer)")

    @classmethod
    def _validate_request_body_fields_validity(cls, account_alias, vpc_type_str,
                                               vpc_top_level_cidr, subnets: dict,
                                               cloud_provider, region, region_config, connectivity,
                                               region_to_log_bucket_dict):
        """
        Validate incoming request params according to business rules

        Args:
            account_alias: account alias
            vpc_type_str: vpc type string (e.g., primary)
            vpc_top_level_cidr: array of top level CIDRs for VPC
            subnets: VPC subnet spec, if applicable
            cloud_provider: cloud provider
            region: cloud provider region
            region_config: param store config for region, None if region not supported
            connectivity: tgw/vgw
            region_to_log_bucket_dict: log bucket by region dict
        """
        # Handles no value provided and region not supported as only supported regions have configs
        if region is None or region_config is None:
            raise val_excepts.InvalidAwsRegionException(region)
        # Validate region is represented in the log bucket dict
        # if region not in region_to_log_bucket_dict:
        #     raise val_excepts.MissingConfiguredLogBucketException()
        # Validate VPC is of min size
        if not net_validation.cidr_mask_clears_minimum_size(vpc_top_level_cidr, cls.MIN_VPC_CIDR_MASK):
            raise val_excepts.VpcCidrSizeException()
        # Validate VPC is of allowed type
        if vpc_type_str.lower() not in [t.name for t in VpcType]:
            raise val_excepts.VpcTypeException(vpc_type_str)
        # Cast to VpcType now that is is valid
        vpc_type = VpcType[vpc_type_str.lower()]
        # Connectivity is not required for HPC type, but is for others
        if vpc_type is not VpcType.hpc and not connectivity:
            raise val_excepts.VpcMissingFieldException("connectivity_type")
        # Validate provided connectivity is allowed
        if isinstance(connectivity, str):
            if connectivity.lower() not in [c.name for c in VpcConnectivity]:
                raise val_excepts.VpcConnectivityException(connectivity)
            # TGW is only enabled in certain regions
            elif VpcConnectivity[connectivity] is VpcConnectivity.tgw and not region_config.get("tgw-available", False):
                raise val_excepts.VpcTgwConnectivityException()
        # Validate min subnet count is met
        if subnets and "private_count" in subnets.keys() \
                and int(subnets["private_count"]) < cls.MIN_SUBNET_COUNT:
            raise val_excepts.VpcMinSubnetCountException("private")
        if subnets and "public_count" in subnets.keys():
            if int(subnets["public_count"]) < cls.MIN_SUBNET_COUNT and int(subnets["public_count"]) != 0:
                raise val_excepts.VpcMinSubnetCountException("public")
            if vpc_type == VpcType.hpc and int(subnets["public_count"]) > cls.MAX_HPC_PUBLIC_COUNT:
                raise val_excepts.MaxPublicSubnetCountException()

        all_blocks = subnets.get("private_blocks", []) + subnets.get("public_blocks", [])
        # Validate min subnet size is met
        if not net_validation.cidr_mask_clears_minimum_size(all_blocks, cls.MIN_SUBNET_CIDR_MASK):
            raise val_excepts.SubnetCidrSizeException()
        # Validate subnets do not overlap
        if not net_validation.is_vpc_subnet_cidr_viable(vpc_top_level_cidr, all_blocks):
            raise val_excepts.SubnetCidrOverlapException()

    def output_class_to_dict(self):
        """
        Return class data to dict

        Return: class data
        """
        return {
            "account_alias": self.account_alias,
            "log_bucket": self.log_bucket,
            "vpc_type": str(self.vpc_type),
            "vpcx_name": self.vpcx_name,
            "vpc_top_level_cidr": self.vpc_top_level_cidr,
            "subnets": {
                "private": self.vpc_private_subnet_cidrs,
                "public": self.vpc_public_subnet_cidrs,
                "allocated_public": self.allocated_public_subnet_cidrs
            },
            "region": self.region,
            "availability_zones": self.availability_zones,
            "owned_peers": self.owned_peers,
            "connectivity_type": str(self.connectivity_type) if self.connectivity_type else None,
            "transit_gateway": self.transit_gateway,
            "cloud_provider": self.cloud_provider,
            "timestamp": datetime.now().isoformat()
        }
