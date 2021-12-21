@integration_test
Feature: Test basic VPC deploy

@ready
Scenario Outline:  Positive Scenario - Successful creation of base VPC with defaults
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
    And The test account does not have the VPCx VPC Stack vpc-<vpc_type>-<region_code><vpc_index> in <region>
  When We issue a request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <region>
  Then The response code of the request is 200
  And The response message returns "VPC stack updated."

      Examples: VPC requests
        | region    |  vpc_type   |  vpc_cidr         |  region_code   | vpc_index | private_subnet_count |
        | us-west-2 |  primary    |  192.168.0.0/18   |  USWE2         | 1         | 2                    |


Scenario Outline:  Positive Scenario - Successful creation of base VPC with specified subnet count
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
    And The test account does not have the VPCx VPC Stack vpc-<vpc_type>-<region_code><vpc_index> in <region>
  When We issue a private count request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnet_count>, <region>
  Then The response code of the request is 200
    And The response message returns "VPC stack updated."

    Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnet_count       | region_code   | vpc_index |
      | us-west-2 | primary    | 192.168.0.0/18   | 4                          | USWE2         | 1         |


Scenario Outline: Positive Scenario - Basic primary VPC creation with explicit subnets
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
    And The test account does not have the VPCx VPC Stack vpc-<vpc_type>-<region_code><vpc_index> in <region>
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 200
    And The response message returns "VPC stack updated."

    Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                                  | region_code | vpc_index | private_subnet_count |
      | us-west-2 | primary    | 192.168.0.0/18   | 192.168.0.0/24,192.168.1.0/24                    | USWE2       | 1         | 2                    |


Scenario Outline: Positive Scenario - Basic multiple primary VPC creation with explicit subnets
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
    And The test account does not have the VPCx VPC Stack vpc-<vpc_type>-<region_code><vpc_index> in <region>
    And The test account has a first VPCx VPC Stack vpc-<vpc_type>-<region_code>1 in <region>
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 200
    And The response message returns "VPC stack updated."

    Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                                 | region_code   | vpc_index | private_subnet_count |
      | us-west-2 | primary    | 192.168.64.0/18  | 192.168.64.0/24,192.168.65.0/24,192.168.66.0/24 | USWE2         | 2         | 3                    |


Scenario Outline: Positive Scenario - Basic primary VPC + public subnet creation with explicit subnets and VGW verification
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
    And The test account does not have the VPCx VPC Stack vpc-<vpc_type>-<region_code><vpc_index> in <region>
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <public_subnets>, <region>
  Then The response code of the request is 200
    And The response message returns "VPC stack updated."
    And The stack name vpc-<vpc_type>-<region_code><vpc_index> appears in the test account in <region>
    And The private subnets have no route to an IGW
    And The VPC has a VGW attachment
    And The private subnets have a 0.0.0.0/0 route to the VGW
    And The public subnets have a route to an IGW

    Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                | public_subnets                                   | region_code | vpc_index | public_subnet_count | private_subnet_count |
      | us-west-2 | primary    | 192.168.0.0/18   | 192.168.0.0/24,192.168.1.0/24  | 192.168.2.0/24,192.168.3.0/24                    | USWE2       | 1         | 2                   | 2                    |


Scenario Outline: Negative Scenario - Bad CIDR ranges (out of range)
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 400
    And The response message returns "Subnets not viable in provided VPC."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                                  |
      | us-west-2 | primary    | 192.168.128.0/18 | 192.168.64.0/24,192.168.65.0/24,192.168.66.0/24  |


Scenario Outline: Negative Scenario - Overlapping CIDR ranges
  Given The API v1/vpcx/vpc exists
    And There are no preexisting VPCx stacks in <region>
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 400
    And The response message returns "Subnets not viable in provided VPC."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                  |
      | us-west-2 | primary    | 192.168.128.0/18 | 192.168.0.0/24,192.168.128.0/24  |


Scenario Outline: Negative Scenario - Bad VPC Type
  Given The API v1/vpcx/vpc exists
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 400
    And The response message returns "VPC type <vpc_type> not allowed."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                  |
      | us-west-2 | secondary  | 192.168.0.0/18   | 192.168.0.0/24,192.168.1.0/24    |


Scenario Outline: Negative Scenario - Bad Region
  Given The API v1/vpcx/vpc exists
  When We issue a private count request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnet_count>, <region>
  Then The response code of the request is 400
    And The response message returns "AWS Region <region> not supported."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnet_count       |
      | us-mock-1 | primary    | 192.168.0.0/18   | 2                          |


Scenario Outline: Negative Scenario - Bad Subnet Count
  Given The API v1/vpcx/vpc exists
  When We issue a private count request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnet_count>, <region>
  Then The response code of the request is 400
    And The response message returns "Minimum private subnet count not met."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnet_count       |
      | us-west-2 | primary    | 192.168.0.0/18   | 1                          |


Scenario Outline: Negative Scenario - Minimum VPC Size
  Given The API v1/vpcx/vpc exists
  When We issue a private count request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnet_count>, <region>
  Then The response code of the request is 400
    And The response message returns "Minimum VPC size not met."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnet_count       |
      | us-west-2 | primary    | 192.168.0.0/29   | 2                          |


Scenario Outline: Negative Scenario - Minimum Subnet Size from count
  Given The API v1/vpcx/vpc exists
  When We issue a private count request to create a vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnet_count>, <region>
  Then The response code of the request is 400
    And The response message returns "Minimum subnet size not met."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnet_count       |
      | us-west-2 | primary    | 192.168.0.0/26   | 20                         |


Scenario Outline: Negative Scenario - Minimum subnet size
  Given The API v1/vpcx/vpc exists
  When We issue a request to create an explicit vpc in the test account with <vpc_type>, <vpc_cidr>, <private_subnets>, <region>
  Then The response code of the request is 400
    And The response message returns "Minimum subnet size not met."

  Examples: VPC requests
      | region    | vpc_type   | vpc_cidr         | private_subnets                  |
      | us-west-2 | primary    | 192.168.0.0/18   | 192.168.0.0/24,192.168.1.0/31    |
