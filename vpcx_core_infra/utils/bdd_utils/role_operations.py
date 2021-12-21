"""Shared BDD utils"""
import json
import time
import boto3


def verify_trusted_role_exists_in_account(role_name, account_number,
                                          iam_client=boto3.client('iam'),
                                          path='/'):
    """
    Check if trusted role exists.  If not, create it

    Args:
        role_name: role name
        account_number: account number for trust policy
        iam_client: boto3 iam client
        path: role path
    """
    # Define trust policy
    trust_policy = {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::{}:root".format(account_number)
          },
          "Action": "sts:AssumeRole",
          "Condition": {}
        }
      ]
    }
    # Check for role existence. If no role, then create
    try:
        iam_client.get_role(
            RoleName=role_name
        )
    except iam_client.exceptions.NoSuchEntityException:
        iam_client.create_role(
            RoleName=role_name,
            Path=path,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
        )
        # Sleep to prevent AccessDenied error
        time.sleep(30)


def delete_role_if_exists(role_name, iam_client=boto3.client('iam')):
    """
    Delete role if exists.  If not, throw exception

    Args:
        role_name: role name
        iam_client: boto3 client for IAM
    """
    # Check for role existence. If role exists, then delete
    try:
        iam_client.get_role(
            RoleName=role_name
        )
        # Role found. Delete role
        try:
            # Remove inline policies
            role = iam_client.list_role_policies(
                RoleName=role_name
            )
            for policy in role['PolicyNames']:
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy
                )
            # Remove managed policies
            role = iam_client.list_attached_role_policies(
                RoleName=role_name
            )
            for attached_policy in role['AttachedPolicies']:
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=attached_policy['PolicyArn']
                )
            # Delete role
            iam_client.delete_role(
                RoleName=role_name
            )
            # Ensure role is deleted
            time.sleep(30)
            try:
                iam_client.get_role(
                    RoleName=role_name
                )
            except iam_client.exceptions.NoSuchEntityException:
                return
            # If role still exists, throw exception
            raise Exception('Role still exists.')
        except iam_client.exceptions.NoSuchEntityException:
            pass
    except iam_client.exceptions.NoSuchEntityException:
        pass
