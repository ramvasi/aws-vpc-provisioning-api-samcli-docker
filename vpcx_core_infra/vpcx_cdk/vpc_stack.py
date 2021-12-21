# pylint: disable=line-too-long
"""Class to handle the Cloudformatiom stack template creation"""
from aws_cdk import (
    aws_ec2 as ec2,
    core
)
from typing import List
from .vpc_context import VpcContext, VpcType, VpcConnectivity


class VpcStack(core.Stack):
    """
    VPC generated using the CDK
    """
    # These are used in Subnet / RouteTable names.  This is the only way to determine
    #   what the intended usage is other than inferring from configuration
    PRIVATE_TYPE_NAME = "Private"
    PUBLIC_TYPE_NAME = "Public"

    def __init__(self, scope: core.Construct, construct_id: str,
                 vpc_context: VpcContext, external_configs: dict, **kwargs) -> None:
        # Initialize VPC
        super().__init__(scope, construct_id, **kwargs)
        # Collect input args
        self.net_config = external_configs["net_config"]
        self.vpc_context = vpc_context

        vpc = self.make_vpc()
        #self.make_vpc_flow_logs(vpc.ref)

        private_route_table, private_subnets = self.make_subnets(vpc.ref,
                                                                 vpc_context.vpc_private_subnet_cidrs,
                                                                 self.PRIVATE_TYPE_NAME)
        public_route_table, public_subnets = self.make_subnets(vpc.ref,
                                                               vpc_context.vpc_public_subnet_cidrs,
                                                               self.PUBLIC_TYPE_NAME,
                                                               len(private_subnets))
        self.make_s3_vpc_gateway_endpoint(vpc.ref, private_route_table.ref)

        #self.make_vpc_peering(vpc.ref, private_route_table, public_route_table)

        has_public_setup = (public_route_table and public_subnets)
        # Public Specific Config
        if has_public_setup:
            self.make_internet_gateway(vpc.ref, public_route_table.ref)

        # Non-HPC Specific Config
        if vpc_context.vpc_type != VpcType.hpc:
            self.add_dhcp_options(vpc.ref)

            # No provided connectivity will create a VGW in addition to explicit request
            if vpc_context.connectivity_type == VpcConnectivity.vgw:
                self.make_vgw(vpc.ref, private_route_table.ref)

        # HPC Specific Config (HPC should always have public set up)
        # if vpc_context.vpc_type == VpcType.hpc and has_public_setup:
        #     self.make_nat_gateway(public_subnets[0].ref, private_route_table.ref)

    @classmethod
    def _get_subnet_id_per_az(cls, subnets: List[ec2.CfnSubnet]):
        """
        Returns one subnet from each AZ that is in use

        Args:
            subnets: list of CfnSubnets

        Returns: of CfnSubnets ids by ref
        """
        one_subnet_per_az = []
        used_azs = []
        for subnet in subnets:
            if subnet.availability_zone not in used_azs:
                one_subnet_per_az.append(subnet.ref)
                used_azs.append(subnet.availability_zone)
        return one_subnet_per_az

    def make_vgw(self, vpc_id, private_route_table_id):
        """
        Generate VGW connection which will be manually connected elsewhere to a DCG

        Args:
            vpc_id: VPC CDK ID
            private_route_table_id: Private route table id

        Returns: nothing
        """
        name = f"{self.vpc_context.vpcx_name}VGW"
        vgw = ec2.CfnVPNGateway(self, id=name, type="ipsec.1", tags=self.make_tags(("Name", name)))
        vgw_attach = ec2.CfnVPCGatewayAttachment(self, id=f"{name}Attachment", vpc_id=vpc_id, vpn_gateway_id=vgw.ref)
        vgw_route = ec2.CfnRoute(self,
                                 id=f"{name}Route",
                                 route_table_id=private_route_table_id,
                                 destination_cidr_block=self.net_config["global"]["InternetCidr"],
                                 gateway_id=vgw.ref)

        # Needs depends on or will be created prematurely in Cloudformation
        vgw_route.add_depends_on(target=vgw_attach)

    def make_s3_vpc_gateway_endpoint(self, vpc_id, private_route_table_id):
        """
        Generate VPC endpoint

        Args:
            vpc_id: VPC CDK ID
            private_route_table_id: Private route table id

        Returns: nothing
        """
        ec2.CfnVPCEndpoint(self,
                           id=f"{self.vpc_context.vpcx_name}S3Gateway",
                           vpc_id=vpc_id,
                           route_table_ids=[private_route_table_id],
                           service_name=f"com.amazonaws.{self.vpc_context.region}.s3")

    def make_internet_gateway(self, vpc_id, public_rt_id):
        """
        Generate IGW resources

        Args:
            vpc_id: VPC CDK ID
            public_rt_id: public route table id to add IGW routes to

        Returns: nothing
        """
        igw_name = f"{self.vpc_context.vpcx_name}IGW"
        igw = ec2.CfnInternetGateway(self,
                                     id=igw_name,
                                     tags=self.make_tags(("Name", igw_name)))

        ec2.CfnVPCGatewayAttachment(self,
                                    id=f"{igw_name}Attachment",
                                    vpc_id=vpc_id,
                                    internet_gateway_id=igw.ref)
        ec2.CfnRoute(self,
                     id=f"{igw_name}Route",
                     route_table_id=public_rt_id,
                     destination_cidr_block=self.net_config["global"]["InternetCidr"],
                     gateway_id=igw.ref)

    def make_nat_gateway(self, public_subnet_id, private_rt_id):
        """
        Generate NAT GW resources

        Args:
            public_subnet_id: a public subnet id to use for hosting NAT
            private_rt_id: private route table id to add NAT routes to

        Returns: nothing
        """
        nat_name = f"{self.vpc_context.vpcx_name}NatGW"
        eip_name = f"{nat_name}EIP"
        eip = ec2.CfnEIP(self, id=eip_name, domain="vpc", tags=self.make_tags(("Name", eip_name)))
        nat_gw = ec2.CfnNatGateway(self,
                                   id=nat_name,
                                   allocation_id=eip.attr_allocation_id,
                                   subnet_id=public_subnet_id,
                                   tags=self.make_tags(("Name", nat_name)))

        ec2.CfnRoute(self,
                     id=f"{nat_name}Route",
                     route_table_id=private_rt_id,
                     destination_cidr_block=self.net_config["global"]["InternetCidr"],
                     nat_gateway_id=nat_gw.ref)

    @staticmethod
    def make_tags(*specific_tags):
        """
        Make tags

        Args:
            specific_tags: specific tags as tuples of key values to be added to resource

        Returns: cfnTag list containing all common tags plus any specific tags added
        """
        common_tags = []
        tags_all = list(specific_tags) + common_tags
        return [core.CfnTag(key=key, value=val) for key, val in tags_all]

    def make_vpc(self):
        """
        Generate a VPC template

        Returns: CDK VPC object
        """
        # Create initial VPC
        vpc = ec2.CfnVPC(self,
                         id=self.vpc_context.vpcx_name,
                         cidr_block=self.vpc_context.vpc_top_level_cidr[0],
                         tags=self.make_tags(("Name", self.vpc_context.vpcx_name),
                                             ("vpcx", str(self.vpc_context.vpc_type)))
                         )
        # Extend VPC top-level CIDR
        if len(self.vpc_context.vpc_top_level_cidr) > 1:
            for i, additional_cidr in enumerate(self.vpc_context.vpc_top_level_cidr[1:]):
                name = f"{self.vpc_context.vpcx_name}AddtionalVpcCidr{i + 1}"
                ec2.CfnVPCCidrBlock(self,
                                    id=name,
                                    vpc_id=vpc.ref,
                                    cidr_block=additional_cidr)

        return vpc

    def make_subnets(self, vpc_id, subnet_cidrs, subnet_type, subnet_count_offset=0):
        """
        Generate VPC subnets

        Args:
            vpc_id: VPC CDK ID
            subnet_cidrs: block of subnets cidrs to create
            subnet_type: type of subnet created (for naming, eg Private / Public)
            subnet_count_offset: number of subnets to offset during AZ allocation

        Returns: list of CDK subnet objects
        """
        subnets = list()
        route_table = None
        # Grab AZs in region
        az_length = len(self.vpc_context.availability_zones)
        # Generate subnet in alternating AZs
        if subnet_cidrs:
            name = f"{self.vpc_context.vpcx_name}{subnet_type}RouteTable"
            route_table = ec2.CfnRouteTable(self,
                                            id=name,
                                            vpc_id=vpc_id,
                                            tags=self.make_tags(("Name", name)))

            for i, cidr in enumerate(subnet_cidrs):
                name = f"{self.vpc_context.vpcx_name}{subnet_type}Subnet{i + 1}"
                subnet = ec2.CfnSubnet(self,
                                       id=name,
                                       vpc_id=vpc_id,
                                       cidr_block=cidr,
                                       availability_zone=self.vpc_context.availability_zones[
                                           (subnet_count_offset + i) % az_length],
                                       tags=self.make_tags(("Name", name)))
                # Associate route table
                ec2.CfnSubnetRouteTableAssociation(self,
                                                   id=f"{name}RouteTableAssoc",
                                                   route_table_id=route_table.ref,
                                                   subnet_id=subnet.ref)
                subnets.append(subnet)
        return route_table, subnets

    def add_dhcp_options(self, vpc_id):
        """
        Generate VPC DHCP options

        Args:
            vpc_id: VPC CDK ID

        Returns: CDK DHCP objects
        """
        # Generate DHCP options
        dhcp_options = ec2.CfnDHCPOptions(self,
                                          id=f"{self.vpc_context.vpcx_name}DHCPOptions",
                                          domain_name=self.net_config["global"]["DomainName"],
                                          domain_name_servers=self.net_config["TopLevel"]["DomainNameServers"],
                                          netbios_name_servers=self.net_config["TopLevel"]["NetbiosNameServers"],
                                          netbios_node_type=8,
                                          ntp_servers=self.net_config["TopLevel"]["NetworkTimeServers"])
        # Associate route table
        ec2.CfnVPCDHCPOptionsAssociation(self,
                                         id=f"{self.vpc_context.vpcx_name}DHCPOptionsAssoc",
                                         dhcp_options_id=dhcp_options.ref,
                                         vpc_id=vpc_id)

    def make_vpc_flow_logs(self, vpc_id):
        """
        Generate VPC endpoint

        Args:
            vpc_id: vpc_id: VPC CDK ID

        Returns: nothing
        """
        ec2.CfnFlowLog(self,
                       id=f"{self.vpc_context.vpcx_name}FlowLog",
                       resource_id=vpc_id,
                       resource_type="VPC",
                       traffic_type="ALL",
                       log_destination=f"arn:aws:s3:::{self.vpc_context.log_bucket}/vpc-flow-log/{vpc_id}/",
                       log_destination_type="s3")

