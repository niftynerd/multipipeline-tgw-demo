"""Module to create a Parameter Stack.

CDKStack has a _provison_resources() method called from
__init__(). This uses naming conventions and references
to CDKResource definitions to create the actual CDK resources.

Much of the functionality is generic rinse and repeat that
doesn't need a specific class to execute, when it's only the
names of things that change, or pointing to another resource.

This class can be inherited and the _provision_resources method
overridden to provision resources that need a lot of cross
referencing to other objects like buckets, roles etc.

These references can be made by referencing the scope passed
to this class from it's parent, which is a CDKStage.

"""
from typing import List
from lib.cdk_classes import (
    CDKStack,
    CDKStage,
)
from lib.cdk_resource import CDKResourceDef

from aws_cdk import aws_ssm as ssm

import boto3
ec2 = boto3.client('ec2')


class ParameterStack(CDKStack):
    """Creates a stack for transit gateway parameters"""
    def __init__(
            self,
            stage: CDKStage,
            id: str,
            stack = None,
            **kwargs,
    ) -> None:
        self.resource_names = []
        
        self.tgw_id = None
        try:
            tgw = ec2.describe_transit_gateways()['TransitGateways'][0]
            self.tgw_id = tgw['TransitGatewayId']
        except:
            pass
        
        if stack != None:
            self.tgw_attach = None
            self.tgw_attach = ssm.StringParameter.value_from_lookup(scope=stack,parameter_name="demo-tgw-attach")
        
        super().__init__(stage, id, **kwargs)
