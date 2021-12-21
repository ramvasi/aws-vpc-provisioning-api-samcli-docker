"""VPCx VPC request validation exceptions"""


class VpcRequestException(Exception):
    """
   Base Exception raised for errors in request

   Attributes:
       message: Description of this error
   """

    def __init__(self, message="Error processing VPC request", status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidAwsRegionException(VpcRequestException):
    """
    Exception raised for an unsupported AWS region

    Attributes:
        message: Description of this error
    """

    def __init__(self, message=""):
        self.message = f"AWS Region {message} not supported."
        super().__init__(self.message)


class VpcMissingFieldException(VpcRequestException):
    """
    Exception raised for missing required field

    Attributes:
        message: Description of this error
    """

    def __init__(self, message=""):
        self.message = "Required field missing: {}.".format(message)
        super().__init__(self.message)


class SubnetBlocksCountCombinationException(VpcRequestException):
    """
    Exception raised for a CIDR block being too small for a given subnet

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="May not use a CIDR block and a count in same request."):
        self.message = message
        super().__init__(self.message)


class SubnetCidrSizeException(VpcRequestException):
    """
    Exception raised for a CIDR block being too small for a given subnet

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="Minimum subnet size not met."):
        self.message = message
        super().__init__(self.message)


class VpcCidrSizeException(VpcRequestException):
    """
    Exception raised for a CIDR block being too small for a given vpc

    Attributes:
        message: Description of this error
    """

    def __init__(self, message="Minimum VPC size not met."):
        self.message = message
        super().__init__(self.message)


class VpcMinSubnetCountException(VpcRequestException):
    """
    Exception raised for too small a requested number of private subnet

    Attributes:
        message: Description of this error
    """

    def __init__(self, subnet_type):
        self.message = f"Minimum {subnet_type} subnet count not met."
        super().__init__(self.message)


class VpcTypeException(VpcRequestException):
    """
    Exception raised for inappropriate VPC name

    Attributes:
        message: Description of this error
    """

    def __init__(self, message=""):
        self.message = "VPC type {} not allowed.".format(message)
        super().__init__(self.message)


class VpcConnectivityException(VpcRequestException):
    """
    Exception raised for inappropriate VPC connectivity name

    Attributes:
        message: Description of this error
    """

    def __init__(self, message=""):
        self.message = "Connectivity type {} not valid.".format(message)
        super().__init__(self.message)


class VpcTgwConnectivityException(VpcRequestException):
    """
    Exception raised for region without TGW support

    Attributes:
        message: Description of this error
    """

    def __init__(self):
        self.message = f"No TGW found."
        self.status_code = 404
        super().__init__(self.message, self.status_code)


class VpcMultipleTgwException(VpcRequestException):
    """
    Exception raised for multiple TGW in region

    Attributes:
        message: Description of this error
    """

    def __init__(self):
        self.message = f"Multiple TGWs found."
        self.status_code = 409
        super().__init__(self.message, self.status_code)


class VpcTypeAlreadyPresentException(VpcRequestException):
    """
    Exception raised for Vpc type which is already present and does not allow multiples

    Attributes:
        message: Description of this error
    """

    def __init__(self, vpc_type):
        self.message = f"{vpc_type.upper()} VPC already present."
        super().__init__(self.message)


class SubnetCidrOverlapException(VpcRequestException):
    """
    Exception raised for invalid CIDRs

    Attributes:
        message: Description of this error
    """

    def __init__(self):
        self.message = "Subnets not viable in provided VPC."
        super().__init__(self.message)


class MaxPublicSubnetCountException(VpcRequestException):
    """
    Exception raised when a public subnet count exceeds maximum

    Attributes:
        message: Description of this error
    """

    def __init__(self):
        self.message = "Maximum public subnet count exceeded."
        super().__init__(self.message)


class MissingConfiguredLogBucketException(VpcRequestException):
    """
    Exception raised there is no mapping to a log bucket for the region

    Attributes:
        message: Description of this error
    """

    def __init__(self):
        self.message = "No log buckets assigned for account in region."
        self.status_code = 404
        super().__init__(self.message, self.status_code)
