"""Class that provides a Pipeline Environment Stage."""

from lib.cdk_classes import (
    CDKStage
)
from lib.cdk_classes import (
    CDKTargetAWSEnv
)

from ..stacks.resource_stack import ResourceStack
from ..stacks.network_stack import NetworkStack
from ..stacks.tgw_routes_stack import TgwRoutesStack
from ..stacks.parameter_stack import ParameterStack


class EnvDeployStage(CDKStage):
    """Deploy CDK Resources into the target AWS environment."""
    shared_infra_tgw_attach = []

    def __init__(self, scope, id, target: CDKTargetAWSEnv, **kwargs):
        """Create an instance of the class."""
        super().__init__(scope, id, target, **kwargs)
        print("target name:",target.name)
    
        # network stack
        if target.vpc_cidrs != None:
            # check for existing tgw
            self.tgw_and_tgwrt_stack = ParameterStack(
                stage=self,
                id="parameters",
            )
            tgw_id = self.tgw_and_tgwrt_stack.tgw_id
            print("tgw_id:", tgw_id)
            
            self.network = NetworkStack(
                stage=self,
                id="networking",
                overall_cidr=target.overall_cidr,
                onprem_cidr=target.onprem_cidr,
                vpc_cidrs=target.vpc_cidrs,
                transit_subnet=target.transit_subnet,
                private_subnet=target.private_subnet,
                public_subnet=target.public_subnet,
                contiguous=target.contiguous,
                org_arn_to_share=target.org_arn_to_share,
                tgw_id=tgw_id,
            )

            self.shared_infra_tgwattach_stack = ParameterStack(
                stage=self,
                id="parameters-attach",
                stack=self.network,
            )
            self.shared_infra_tgwattach_stack.add_dependency(self.network)
            tgw_attach = self.shared_infra_tgwattach_stack.tgw_attach
            if tgw_attach not in EnvDeployStage.shared_infra_tgw_attach:
                EnvDeployStage.shared_infra_tgw_attach.append(tgw_attach) # add tgw attachment to list
            print("shared_infra_tgw_attach:", tgw_attach)
        
        # tgw routes stack
        if target.name == "tgw-routes": # if network account, happens after all accounts have been attached to tgw
            if len(EnvDeployStage.shared_infra_tgw_attach) > 0:
                self.tgwroutes = TgwRoutesStack(
                    stage=self,
                    id="tgw-routes",
                    inspection_cidr=target.inspection_cidr,
                    shared_infra_tgw_attach=EnvDeployStage.shared_infra_tgw_attach,
                )
            else: # empty stack if no tgw attachment id or tgw route table id
                self.tgwroutes = ResourceStack(
                    stage=self,
                    id="empty",
                    cdk_def=None,
                    resource_names=[]
                )
