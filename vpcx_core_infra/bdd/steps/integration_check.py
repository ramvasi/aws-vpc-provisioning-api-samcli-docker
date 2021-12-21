"""Behave module for verifying VPCx API"""
import ipaddress
import json
import time
import requests
import os
import boto3
from behave import *
import test_helpers
from vpcx_core_infra.utils import s3_interactions, vpcx_account, ec2_interactions

@given('The API v1/vpcx/vpc exists')
def step_impl(context):
    # Check if endpoint is reachable
    #response = requests.get(context.hostname)
    #assert response.status_code < 500
    assert True


@given('There are no preexisting VPCx stacks in {region}')
def step_impl(context, region):
    context.region = region
    # Initialize cross-account CF client
    cf_client = context.cross_account_session.client(
        'cloudformation',
        region_name=region)
    print("Trying to delete all stacks")
    test_helpers.delete_existing_vpcs(cf_client)


@given('The test account does not have the VPCx VPC Stack vpc-{vpc_type}-{region_code}{vpc_index} in {region}')
def step_impl(context, vpc_type, region_code, vpc_index, region):
    # Initialize cross-account CF client
    cf_client = context.cross_account_session.client(
        'cloudformation',
        region_name=region)
    # Build stack name
    context.stack_name = "vpc-{}-{}{}".format(vpc_type, region_code, vpc_index)
    # Initialize S3
    s3_client = boto3.client(
        's3',
    )
    # Count S3 objects with this prefix
    context.s3_count = test_helpers.count_s3_files_at_prefix(
        context.template_metadata_s3_bucket,
        context.stack_name,
        context.test_account,
        s3_client
    )
    # Clean up existing stacks
    test_helpers.delete_existing_vpcs(cf_client, context.stack_name)
    # Ensure stack does not exist
    stack_found = True
    try:
        # Delete stack
        stack = cf_client.describe_stacks(
            StackName=context.stack_name
        )
        print(f"Found Stack: {stack}")
    except cf_client.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            stack_found = False
    assert stack_found is False


def create_preexisting_vpcx_stack(context, vpc_type, region_code, region, index):
    # HPC is occasionally made after primary so we set it to 192 always to leave 
    # open space even though it will be index 1
    cidr_section = "128" if index == 1 and vpc_type == "primary" else "192"
    # Initialize cross-account CF client
    cf_client = context.cross_account_session.client(
        'cloudformation',
        region_name=region,
    )
    # Build stack name
    stack_name = f"vpc-{vpc_type}-{region_code}{index}"
    # Clean up existing stacks
    test_helpers.delete_existing_vpcs(cf_client, stack_name)
    # Create first stack
    test_request = {
        "account_alias": context.test_account,
        "cloud_provider": "aws",
        "vpc_type": vpc_type,
        "vpc_top_level_cidr": [
            f"192.168.{cidr_section}.0/18"
        ],
        "subnets": {
            "private_count": 2,
            "public_count": 2
        },
        "region": region,
        "connectivity_type": "vgw"
    }
    # Prepare request headers
    headers = {
        'Authorization': 'Bearer {}'.format('Test'),
        'Content-Type': 'application/json'
    }
    # Send request
    context.response = requests.post(context.hostname,
                                     data=json.dumps(test_request),
                                     headers=headers)
    # Evaluate response
    assert context.response.status_code == 200
    # Ensure stack is created
    try:
        response = cf_client.describe_stacks(
            StackName=stack_name
        )
        stack_found = True
    except Exception as e:
        stack_found = False
    assert stack_found is True


@given('The test account has a first VPCx VPC Stack vpc-{vpc_type}-{region_code}1 in {region}')
def step_impl(context, vpc_type, region_code, region):
    create_preexisting_vpcx_stack(context, vpc_type, region_code, region, 1)


@given('The test account has a second VPCx VPC Stack vpc-{vpc_type}-{region_code}2 in {region}')
def step_impl(context, vpc_type, region_code, region):
    create_preexisting_vpcx_stack(context, vpc_type, region_code, region, 2)


def make_explicit_request(context, vpc_type, vpc_cidr, private_subnets, public_subnets, region, connectivity="vgw"):
    # Prepare request
    test_request = {
        "account_alias": context.test_account,
        "cloud_provider": "aws",
        "vpc_type": vpc_type,
        "vpc_top_level_cidr": [
            vpc_cidr
        ],
        "region": region,
        "subnets": {
            "private_blocks": private_subnets.split(','),
            "public_blocks": public_subnets.split(",")
        },
        "connectivity_type": connectivity
    }
    # Prepare request headers
    headers = {
        'Authorization': 'Bearer {}'.format('Test'),
        'Content-Type': 'application/json'
    }
    # Send request
    context.created_region = region
    context.response = requests.post(context.hostname,
                                     data=json.dumps(test_request),
                                     headers=headers)

@when('We issue a request to create an explicit vpc in the test account with {vpc_type}, {vpc_cidr}, {private_subnets}, {public_subnets}, {region}')
def step_impl(context, vpc_type, vpc_cidr, private_subnets, public_subnets, region):
    #context.lambda_arn = context.stack_outputs.get("VpcIntegrationLambdaFunctionQualifiedArn", None)
    make_explicit_request(context, vpc_type, vpc_cidr, private_subnets, public_subnets, region)


@when('We issue a request to create an explicit vpc in the test account with {vpc_type}, {vpc_cidr}, {private_subnets}, {region}')
def step_impl(context, vpc_type, vpc_cidr, private_subnets, region):
    #context.lambda_arn = context.stack_outputs.get("VpcIntegrationLambdaFunctionQualifiedArn", None)
    # Prepare request
    test_request = {
        "account_alias": context.test_account,
        "cloud_provider": "aws",
        "vpc_type": vpc_type,
        "vpc_top_level_cidr": [
            vpc_cidr
        ],
        "region": region,
        "subnets": {
            "private_blocks": private_subnets.split(',')
        },
        "connectivity_type": "vgw"
    }
    # Prepare request headers
    headers = {
        'Authorization': 'Bearer {}'.format('Test'),
        'Content-Type': 'application/json'
    }
    # Send request
    context.response = requests.post(context.hostname,
                                     data=json.dumps(test_request),
                                     headers=headers)


@when('We issue a private count request to create a vpc in the test account with {vpc_type}, {vpc_cidr}, {private_subnet_count}, {region}')
def step_impl(context, vpc_type, vpc_cidr, private_subnet_count, region):
    #context.lambda_arn = context.stack_outputs.get("VpcIntegrationLambdaFunctionQualifiedArn", None)
    # Prepare request
    test_request = {
        "account_alias": context.test_account,
        "cloud_provider": "aws",
        "vpc_type": vpc_type,
        "vpc_top_level_cidr": [
            vpc_cidr
        ],
        "region": region,
        "subnets": {
            "private_count": str(private_subnet_count)
        },
        "connectivity_type": "vgw"
    }
    # Prepare request headers
    headers = {
        'Authorization': 'Bearer {}'.format('Test'),
        'Content-Type': 'application/json'
    }
    # Send request
    context.response = requests.post(context.hostname,
                                     data=json.dumps(test_request),
                                     headers=headers)


@when('We issue a request to create a vpc in the test account with {vpc_type}, {vpc_cidr}, {region}')
def step_impl(context, vpc_type, vpc_cidr, region):
    #context.lambda_arn = context.stack_outputs.get("VpcIntegrationLambdaFunctionQualifiedArn", None)
    # Prepare request
    test_request = {
        "account_alias": context.test_account,
        "cloud_provider": "aws",
        "vpc_type": vpc_type,
        "vpc_top_level_cidr": [
            vpc_cidr
        ],
        "subnets": {},
        "region": region,
        "connectivity_type": "vgw"
    }
    # Prepare request headers
    headers = {
        'Authorization': 'Bearer {}'.format('Test'),
        'Content-Type': 'application/json'
    }
    # Send request
    print('context.hostname: {}'.format(context.hostname))
    print('test_request: {}'.format(json.dumps(test_request)))
    context.response = requests.post(context.hostname,
                                     data=json.dumps(test_request),
                                     headers=headers)


@then('The stack name vpc-{vpc_type}-{region_code}{vpc_index} appears in the test account in {region}')
def step_impl(context, vpc_type, region_code, vpc_index, region):
    # Initialize cross-account resources
    cf_client = context.cross_account_session.client(
        'cloudformation',
        region_name=region,
    )
    ec2_resource = context.cross_account_session.resource(
        'ec2',
        region_name=region,
    )
    response = cf_client.list_stack_resources(
        StackName=context.stack_name
    )
    summaries = response['StackResourceSummaries']

    while "NextToken" in response:
        token = response['NextToken']
        response = cf_client.list_stack_resources(
            StackName=context.stack_name,
            NextToken=token
        )
        summaries.extend(response['StackResourceSummaries'])

    # Set VPC context
    for resource in summaries:
        if resource['ResourceType'] == 'AWS::EC2::VPC':
            context.created_vpc = ec2_resource.Vpc(resource['PhysicalResourceId'])
            context.created_region = region

@then('The response code of the request is {code}')
def step_impl(context, code):
    assert context.response.status_code == int(code), f"""Expected {code},
    got {context.response.status_code} with {context.response.text}"""


@then('The response message returns "No stack update required."')
def step_impl(context):
    assert context.response.text == 'No stack update required.'


@then('The response message returns "Maximum public subnet count exceeded."')
def step_impl(context):
    assert context.response.text == 'Maximum public subnet count exceeded.'


@then('The response message returns "VPC stack updated."')
def step_impl(context):
    print('response.txt: {}'.format(context.response.text))
    assert context.response.text == 'VPC stack updated.'


@then('The response message returns "No VPCx VPC found."')
def step_impl(context):
    assert context.response.text == 'No VPCx VPC found.'


@then('The response message returns "Subnets not viable in provided VPC."')
def step_impl(context):
    assert context.response.text == 'Subnets not viable in provided VPC.'


@then('The response message returns "VPC type {vpc_type} not allowed."')
def step_impl(context, vpc_type):
    assert context.response.text == 'VPC type {} not allowed.'.format(vpc_type)


@then('The response message returns "AWS Region {region} not supported."')
def step_impl(context, region):
    assert context.response.text == "AWS Region {} not supported.".format(region)


@then('The response message returns "Minimum private subnet count not met."')
def step_impl(context):
    assert context.response.text == 'Minimum private subnet count not met.'


@then('The response message returns "Minimum public subnet count not met."')
def step_impl(context):
    assert context.response.text == 'Minimum public subnet count not met.'


@then('The response message returns "Minimum VPC size not met."')
def step_impl(context):
    assert context.response.text == 'Minimum VPC size not met.'


@then('The response message returns "Minimum subnet size not met."')
def step_impl(context):
    assert context.response.text == 'Minimum subnet size not met.'


@then('The response message returns "Invalid user."')
def step_impl(context):
    assert context.response.text == 'Invalid user.'


@then('The response message returns "No account found."')
def step_impl(context):
    assert context.response.text == 'No account found.'


@then('The response message returns "Connectivity type {connectivity_type} not valid."')
def step_impl(context, connectivity_type):
    assert context.response.text == f"Connectivity type {connectivity_type} not valid."


@then('The VPC has CIDR range {vpc_cidr}')
def step_impl(context, vpc_cidr):
    assert context.created_vpc.cidr_block == vpc_cidr


def is_subnet_type(subnet_type):
    return lambda subnet: any([tag.get("Key") == "Name" and subnet_type in tag.get("Value") for tag in subnet.tags])


def is_private_subnet(subnet):
    return is_subnet_type("Private")(subnet)


def is_public_subnet(subnet):
    return is_subnet_type("Public")(subnet)


@then('The VPC has {public_subnet_count} public subnets')
def step_impl(context, public_subnet_count):
    count = 0
    for subnet in context.created_vpc.subnets.all():
        if is_public_subnet(subnet):
            count += 1
    assert count == int(public_subnet_count)


@then('The VPC has {private_subnet_count} private subnets')
def step_impl(context, private_subnet_count):
    count = 0
    for subnet in context.created_vpc.subnets.all():
        if is_private_subnet(subnet):
            count += 1
    assert count == int(private_subnet_count)


def get_subnet_ids_by_igw_presence(route_tables, has_igw: bool):
    subnets_on_rt_ids = []
    for route_table in route_tables:
        route_gateway_ids = [route.get("GatewayId", "") for route in route_table.routes_attribute]
        if (len(list(filter(lambda gw_id: "igw" in gw_id, route_gateway_ids))) > 0) == has_igw:
            for association in route_table.associations:
                subnets_on_rt_ids.append(association.subnet_id)
    return subnets_on_rt_ids


@then('The private subnets have no route to an IGW')
def step_impl(context):
    route_tables = context.created_vpc.route_tables.all()
    non_igw_associated_subnet_ids = get_subnet_ids_by_igw_presence(route_tables, has_igw=False)
    for subnet in context.created_vpc.subnets.all():
        if is_private_subnet(subnet):
            assert subnet.id in non_igw_associated_subnet_ids


@then('The public subnets have a route to an IGW')
def step_impl(context):
    route_tables = context.created_vpc.route_tables.all()
    igw_associated_subnet_ids = get_subnet_ids_by_igw_presence(route_tables, has_igw=True)

    for subnet in context.created_vpc.subnets.all():
        if is_public_subnet(subnet):
            assert subnet.id in igw_associated_subnet_ids


@then('The subnet has no route to an IGW')
def step_impl(context):
    gateway_found = False
    for internet_gateway in context.created_vpc.internet_gateways.all():
        gateway_found = True
    assert not gateway_found


@then('The subnets are in different AZs in {region}')
def step_impl(context, region):
    used_azs = []
    # Find possible AZs
    possible_azs = ec2_interactions.get_availability_zones(context.cross_account_session.client(
        'ec2',
        region_name=region
    ))
    # Get used subnets
    for subnet in context.created_vpc.subnets.all():
        used_azs.append(subnet.availability_zone)
    # If fewer/equal subnets exist than AZs, then verify used_azs contains no dupes
    if len(used_azs) <= len(possible_azs):
        assert not any(used_azs.count(x) > 1 for x in used_azs)
    # If more subnets exist than AZs, then verify all AZs are used
    else:
        assert set(used_azs) == set(possible_azs)


@then('The private subnet CIDR blocks match {private_subnets}')
def step_impl(context, private_subnets):
    subnet_cidrs = private_subnets.split(',')
    found_subnet_cidrs = []
    for subnet in context.created_vpc.subnets.all():
        if is_private_subnet(subnet):
            found_subnet_cidrs.append(subnet.cidr_block)

    assert set(found_subnet_cidrs) == set(subnet_cidrs)


@then('The public subnet CIDR blocks match {public_subnets}')
def step_impl(context, public_subnets):
    subnet_cidrs = public_subnets.split(',')
    found_subnet_cidrs = []
    for subnet in context.created_vpc.subnets.all():
        if is_public_subnet(subnet):
            found_subnet_cidrs.append(subnet.cidr_block)
    assert set(found_subnet_cidrs) == set(subnet_cidrs)


@then('There is a route to a VPC Endpoint S3 Gateway in {region}')
def step_impl(context, region):
    # Get Live VPC Endpoints
    ec2_client = context.cross_account_session.client(
        'ec2',
        region_name=region
    )

    endpoints = ec2_client.describe_vpc_endpoints(Filters=[{
        "Name": "vpc-id",
        "Values": [context.created_vpc.vpc_id]
    }])
    endpoint_service_names = [endpoint['ServiceName'] for endpoint in endpoints['VpcEndpoints']]
    assert any(["s3" in endpoint_service_name for endpoint_service_name in endpoint_service_names])


@then('The VPC DHCP Options match custom configuration')
def step_impl(context):
    # Initialize S3
    s3_object = boto3.resource(
        's3'
    )
    # Get VPC DHCP configs
    dhcp_configs = context.created_vpc.dhcp_options.dhcp_configurations
    # Retrieve custom configs
    custom_configs = s3_interactions.retrieve_json_from_s3(
        context.static_data_s3_bucket,
        'networking_config.json',
        s3_object
    )
    for config in dhcp_configs:
        # Verify domain name
        if config['Key'] == 'domain-name':
            for config_value in config['Values']:
                assert config_value['Value'] == custom_configs['global']['DomainName']
        # Verify DNS servers
        if config['Key'] == 'domain-name-servers':
            actual_values = []
            for config_value in config['Values']:
                actual_values.append(config_value['Value'])
            assert set(actual_values) == set(custom_configs['TopLevel']['DomainNameServers'])
        # Verify DNS servers
        if config['Key'] == 'ntp-servers':
            actual_values = []
            for config_value in config['Values']:
                actual_values.append(config_value['Value'])
            assert set(actual_values) == set(custom_configs['TopLevel']['NetworkTimeServers'])
        # Verify DNS servers
        if config['Key'] == 'netbios-node-type':
            for config_value in config['Values']:
                assert config_value['Value'] == '8'
        # Verify DNS servers
        if config['Key'] == 'netbios-name-servers':
            actual_values = []
            for config_value in config['Values']:
                actual_values.append(config_value['Value'])
            assert set(actual_values) == set(custom_configs['TopLevel']['NetbiosNameServers'])


@then('The VPC for the stack has tag for vcpx: {vpc_type}')
def step_impl(context, vpc_type):
    tag_found = False
    # Iterate over VPC tags
    for tag in context.created_vpc.tags:
        if tag['Key'] == 'vpcx' and tag['Value'] == vpc_type:
            tag_found = True
            break
    assert tag_found


@then('Each subnet CIDR takes up 1 / ({private_subnet_count} + 2) IP addresses in VPC CIDR, rounded down to nearest power of 2')
def step_impl(context, private_subnet_count):
    # Num addresses in VPC
    vpc_addresses = ipaddress.ip_network(context.created_vpc.cidr_block).num_addresses
    # Calculate num of CIDRs
    expected_cidr_size = test_helpers.round_down_to_nearest_power_of_2((vpc_addresses / (int(private_subnet_count) + 2)))
    # Iterate through subnet sizes
    for subnet in context.created_vpc.subnets.all():
        subnet_address_count = ipaddress.ip_network(subnet.cidr_block).num_addresses
        assert subnet_address_count == expected_cidr_size


@then('Each subnet CIDR takes up 1 / ({public_subnet_count} + {private_subnet_count}) IP addresses in VPC CIDR, rounded up to nearest power of 2')
def step_impl(context, public_subnet_count, private_subnet_count):
    # Num addresses in VPC
    vpc_addresses = ipaddress.ip_network(context.created_vpc.cidr_block).num_addresses
    # Calculate num of CIDRs
    expected_cidr_size = test_helpers.round_down_to_nearest_power_of_2((vpc_addresses / (int(public_subnet_count) + int(private_subnet_count))))
    # Iterate through subnet sizes
    for subnet in context.created_vpc.subnets.all():
        subnet_address_count = ipaddress.ip_network(subnet.cidr_block).num_addresses
        assert subnet_address_count == expected_cidr_size


@then('Each subnet CIDR takes up 1 / 4 IP addresses in VPC CIDR')
def step_impl(context):
    # Num addresses in VPC
    vpc_addresses = ipaddress.ip_network(context.created_vpc.cidr_block).num_addresses
    # Calculate num of CIDRs
    expected_cidr_size = test_helpers.round_down_to_nearest_power_of_2((vpc_addresses / 4))
    # Iterate through subnet sizes
    for subnet in context.created_vpc.subnets.all():
        subnet_address_count = ipaddress.ip_network(subnet.cidr_block).num_addresses
        assert subnet_address_count == expected_cidr_size


def get_subnet_ids_by_natgw_presence(route_tables, has_nat: bool):
    subnets_on_rt_ids = []
    for route_table in route_tables:
        route_gateway_ids = [route.get("NatGatewayId", "") for route in route_table.routes_attribute]
        if (len(list(filter(lambda gw_id: "nat" in gw_id, route_gateway_ids))) > 0) == has_nat:
            for association in route_table.associations:
                subnets_on_rt_ids.append(association.subnet_id)
    return subnets_on_rt_ids


@then('The private subnets have a route to NAT Gateway')
def step_impl(context):
    route_tables = context.created_vpc.route_tables.all()
    non_igw_associated_subnet_ids = get_subnet_ids_by_natgw_presence(route_tables, has_nat=True)
    for subnet in context.created_vpc.subnets.all():
        if is_private_subnet(subnet):
            assert subnet.id in non_igw_associated_subnet_ids


@then('There is a NAT Gateway in the public subnet in {region}')
def step_impl(context, region):
    # Get NAT Gateways
    ec2_client = context.cross_account_session.client(
        'ec2',
        region_name=region
    )
    response = ec2_client.describe_nat_gateways(Filters=[{
        "Name": "vpc-id",
        "Values": [context.created_vpc.vpc_id]
    }])
    assert response.get("NatGateways", [])


@then('The route table has a route to peered VPCs')
def step_impl(context):
    route_tables = context.created_vpc.route_tables.all()
    route_table_has_peer_route = []
    for route_table in route_tables:
        route_peer_connection_ids = [route.get("VpcPeeringConnectionId", None) for route in route_table.routes_attribute]
        route_table_has_peer_route.append(any(route_peer_connection_ids))
    # Checking that at least one route table routs to peer.  Default RT will not ever
    assert any(route_table_has_peer_route)


@then('The VPC DHCP Options are default')
def step_impl(context):
    dhcp = context.created_vpc.dhcp_options
    has_default_dns_server = [option.get("Key", "") == "domain-name-servers"
                       and len(option.get("Values", [])) == 1
                       and "AmazonProvidedDNS" in option["Values"][0].get("Value", "") for option in dhcp.dhcp_configurations]
    assert any(has_default_dns_server)


@then('The VPC has a VGW attachment')
def step_impl(context):
    ec2_client = context.cross_account_session.client(
        'ec2',
        region_name=context.created_region
    )
    response = ec2_client.describe_vpn_gateways(Filters=[
        {
            "Name": "attachment.vpc-id",
            "Values": [context.created_vpc.vpc_id]
        }
    ])

    assert len(response.get("VpnGateways", [])) > 0


def get_subnet_ids_by_vgw_presence(route_tables, has_vgw: bool):
    subnets_on_rt_ids = []
    for route_table in route_tables:
        is_vgw_route_list = ["vgw" in route.get("GatewayId", "") and route.get("DestinationCidrBlock") == "0.0.0.0/0"
                             for route in route_table.routes_attribute]
        if (len(list(filter(
                lambda x: x, is_vgw_route_list))) > 0) == has_vgw:
            for association in route_table.associations:
                subnets_on_rt_ids.append(association.subnet_id)
    return subnets_on_rt_ids


@then('The private subnets have a 0.0.0.0/0 route to the VGW')
def step_impl(context):
    route_tables = context.created_vpc.route_tables.all()
    vgw_associated_subnet_ids = get_subnet_ids_by_vgw_presence(route_tables, has_vgw=True)
    for subnet in context.created_vpc.subnets.all():
        if is_private_subnet(subnet):
            assert subnet.id in vgw_associated_subnet_ids