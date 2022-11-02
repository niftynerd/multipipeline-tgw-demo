"""Module to create a Transit Gateway Routes Stack.

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
    CDKResource,
    CDKStack,
    CDKStage,
)
from lib.cdk_resource import CDKResourceDef
from aws_cdk import (
    aws_ec2,
    aws_ram,
)
import aws_cdk as cdk


class TgwRoutesStack(CDKStack):
    """Create a stack for transit gateway routes"""
    def __init__(
            self,
            stage: CDKStage,
            id: str,
            inspection_cidr: str,
            shared_infra_tgw_attach : List[str],
            **kwargs,
    ) -> None:
        self.resource_names = []
        self.inspection_cidr = inspection_cidr
        self.shared_infra_tgw_attach = shared_infra_tgw_attach
      
        super().__init__(stage, id, **kwargs)


    def _provision_resources(self) -> None:
        super()._provision_resources()
        
        egress_rt_id = cdk.Fn.import_value("egress-rt-id")
        inspection_rt_id = cdk.Fn.import_value("inspection-rt-id")
        print("egress_rt_id:", egress_rt_id)
        print("inspection_rt_id:", inspection_rt_id)

        for attach in self.shared_infra_tgw_attach:
            try:
                attach_id = attach.split(',')[0].strip()
                vpc_cidr = attach.split(',')[1].strip()
                global_cidr = "0.0.0.0/0"
                
                if vpc_cidr == self.inspection_cidr: # create association on inspection vpc route table and route to inspection vpc on egress route table
                    self._provision_tgw_rt_ass(attach_id=attach_id, ass_table_id=inspection_rt_id)
                    self._provision_tgw_rt_route(attach_id=attach_id, vpc_cidr=global_cidr, rt_table_id=egress_rt_id)
                else: # create association on egress route table for spoke vpcs and route to vpc on inspection vpc route table
                    self._provision_tgw_rt_ass(attach_id=attach_id, ass_table_id=egress_rt_id)
                    self._provision_tgw_rt_route(attach_id=attach_id, vpc_cidr=vpc_cidr, rt_table_id=inspection_rt_id)
            except IndexError:
                pass

    
    def _provision_tgw_rt_ass(self, attach_id, ass_table_id):
        cdk_def_rtass = self._get_cdk_def(type="CfnTransitGatewayRouteTableAssociation", module="aws_ec2", name_ref="logical_id",
            kargs = {
                "transit_gateway_attachment_id" : attach_id,
                "transit_gateway_route_table_id" : ass_table_id # associate vpc to tgw route table
            }
        )
        self._provision_resource(f"{attach_id}-rtass", cdk_def_rtass)


    def _provision_tgw_rt_route(self, attach_id, vpc_cidr, rt_table_id):
        cdk_def_rtroute = self._get_cdk_def(type="CfnTransitGatewayRoute", module="aws_ec2", name_ref="logical_id",
            kargs = {
                "transit_gateway_attachment_id" : attach_id,
                "destination_cidr_block" : vpc_cidr,
                "transit_gateway_route_table_id" : rt_table_id # add route to tgw route table
            }
        )
        self._provision_resource(f"{attach_id}-rtroute", cdk_def_rtroute)
