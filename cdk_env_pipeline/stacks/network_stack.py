"""Module to create a Network Stack.

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
    aws_iam,
)
import aws_cdk as cdk


class NetworkStack(CDKStack):
    """Creates a stack for vpc network resources"""
    def __init__(
            self,
            stage: CDKStage,
            id: str,
            overall_cidr: str,
            onprem_cidr: str,
            vpc_cidrs: str,
            transit_subnet: str,
            private_subnet: str,
            public_subnet: str,
            contiguous: str,
            org_arn_to_share: str,
            tgw_id: str,
            **kwargs,
    ) -> None:
        self.resource_names = []
        self.overall_cidr = overall_cidr
        self.onprem_cidr = onprem_cidr
        self.vpc_cidrs = vpc_cidrs
        self.transit_subnet = transit_subnet
        self.private_subnet = private_subnet
        self.public_subnet = public_subnet
        self.contiguous = contiguous
        self.org_arn_to_share = org_arn_to_share
        self.tgw_id = tgw_id
        self.subnet_config_list = []
        super().__init__(stage, id, **kwargs)


    def _provision_resources(self) -> None:
        super()._provision_resources()        

        for n,vpc_cidr in enumerate(self.vpc_cidrs.split(',')):
            # provision vpc
            v_name = f"ctvpc-{n}"
            cdk_def = self._get_cdk_def(type="Vpc", module="aws_ec2", name_ref="vpc_id",
                kargs = {
                    "cidr": vpc_cidr.strip(),
                    "vpc_name": v_name,
                }
            )

            # provision contiguous subnets
            if self.public_subnet != None:
                self._append_subnet_config_list(name="public-subnet",
                    sub_type=aws_ec2.SubnetType.PUBLIC,
                    mask=int(self.public_subnet)
                )
            if self.private_subnet != None and (len(self.subnet_config_list) == 0 or self.contiguous == "True"):               
                self._append_subnet_config_list(name="private-subnet",
                    sub_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
                    mask=int(self.private_subnet)
                )
            if self.transit_subnet != None and (len(self.subnet_config_list) == 0 or self.contiguous == "True"):
                self._append_subnet_config_list(name="transit-subnet",
                    sub_type=aws_ec2.SubnetType.PRIVATE_ISOLATED,
                    mask=int(self.transit_subnet)
                )
            if len(self.subnet_config_list) > 0:
                cdk_def.kargs["subnet_configuration"] = self.subnet_config_list            

            self._provision_resource(f"{v_name}", cdk_def)
            self.resources[f"{v_name}{cdk_def.type}"].resource.add_flow_log("flow_log",
                destination=aws_ec2.FlowLogDestination.to_cloud_watch_logs()) # add vpc flow logs

            vpc_resource = self.resources[f"{v_name}{cdk_def.type}"].resource
            self._tag_subnets(subnets=vpc_resource.public_subnets, name="public-subnet")
            self._tag_subnets(subnets=vpc_resource.isolated_subnets[:-3], name="private-subnet")
            self._tag_subnets(subnets=vpc_resource.isolated_subnets[-3:], name="transit-subnet")
            vpc_id = vpc_resource.vpc_id
            # cfn output for vpc id
            cdk.CfnOutput(
                self,
                "vpc_id_output",
                value = vpc_id,
                export_name = f"vpc-{n}-id"
            )

            private_subnet_ids=[]
            if self.private_subnet != None and (len(self.subnet_config_list) == 0 or self.contiguous == "True"):
                private_subnet_ids += [ps.subnet_id for ps in vpc_resource.isolated_subnets[:-3]]
            transit_subnet_ids=[]
            private_route_table_ids = []
            if self.contiguous != "True":  # provision subnets for non-contiguous subnets
                if self.private_subnet.find(",") != -1:
                    self._provision_subnets(subnet_name="private-subnet",subnet_cidrs=self.private_subnet.split(','), vpc_id=vpc_id,subnet_ids=private_subnet_ids,private_route_table_ids=private_route_table_ids)
                if self.transit_subnet.find(",") != -1:
                    self._provision_subnets(subnet_name="transit-subnet",subnet_cidrs=self.transit_subnet.split(','), vpc_id=vpc_id,subnet_ids=transit_subnet_ids,private_route_table_ids=private_route_table_ids)

            # transit gateway
            if self.org_arn_to_share != None: # if network vpc
                tgw_name = "Demo-tgw"
                cdk_def_tgw = self._get_cdk_def(type="CfnTransitGateway", module="aws_ec2", name_ref="attr_id",
                    kargs={
                        "auto_accept_shared_attachments": "enable",
                        "description": tgw_name,
                        "default_route_table_association": "disable",
                        "default_route_table_propagation": "disable",
                        "tags": [cdk.CfnTag(
                            key="Name",
                            value=tgw_name
                        )]
                    }
                )
                self._provision_resource(tgw_name, cdk_def_tgw)
                tgw = self.resources[f"{tgw_name}{cdk_def_tgw.type}"].resource
                self.tgw_id = tgw.attr_id
                # store tgw id in ssm parameter
                tgw_ssm_name = "demo-tgw"
                cdk_def_ssm = self._get_cdk_def(type="StringParameter", module="aws_ssm", name_ref="parameter_name", 
                    kargs={
                        "string_value": self.tgw_id,
                        "parameter_name": tgw_ssm_name
                    }
                )
                self._provision_resource(tgw_ssm_name, cdk_def_ssm)
                # tgw flow logs
                # log group for tgw flow logs
                log_group_name = "tgw-log-group"
                cdk_def_tgw_log_group = self._get_cdk_def(type="LogGroup", module="aws_logs", name_ref="log_group_name", kargs={})
                self._provision_resource(log_group_name, cdk_def_tgw_log_group)
                cdk_def_tgw_log_group_res=self.resources[f"{log_group_name}{cdk_def_tgw_log_group.type}"].resource
                # role for tgw flow logs
                role_name = "cw-role"
                cdk_def_cw_role = self._get_cdk_def(type="Role", module="aws_iam", name_ref="role_name",
                    kargs={
                        "assumed_by": aws_iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
                        "inline_policies": {
                            "EnableCloudWatchPolicy" : aws_iam.PolicyDocument(
                                statements=[
                                    aws_iam.PolicyStatement(
                                        actions=[
                                            "logs:CreateLogStream",
                                            "logs:PutLogEvents",
                                            "logs:DescribeLogStreams"
                                        ],
                                        resources=[cdk_def_tgw_log_group_res.log_group_arn],
                                    ),
                                ]
                            )
                        }
                    }
                )
                self._provision_resource(role_name, cdk_def_cw_role)
                cdk_def_cw_role_res=self.resources[f"{role_name}{cdk_def_cw_role.type}"].resource
                
                # transit gateway route tables
                rt_names = ["egress-rt","inspection-rt"]
                for rt in rt_names:
                    cdk_def_tgw_rt = self._get_cdk_def(type="CfnTransitGatewayRouteTable", module="aws_ec2", name_ref="logical_id", 
                        kargs={
                            "transit_gateway_id": self.tgw_id,
                            "tags": [cdk.CfnTag(
                                key="Name",
                                value=rt
                            )]
                        }
                    )
                    self._provision_resource(rt, cdk_def_tgw_rt)
                    tgw_rt = self.resources[f"{rt}{cdk_def_tgw_rt.type}"].resource
                    # cfn output for tgw route table ids
                    cdk.CfnOutput(
                        self,
                        f"{rt}-id-output",
                        value = tgw_rt.ref,
                        export_name = f"{rt}-id"
                    )

                # share tgw
                tgw_arn = f"arn:aws:ec2:{cdk.Stack.of(self).region}:{self.account}:transit-gateway/{self.tgw_id}"
                cdk_def_ram = self._get_cdk_def(type="CfnResourceShare", module="aws_ram", name_ref="name",
                    kargs={
                        "name": "tgw-share",
                        "allow_external_principals": False,
                        "principals": [self.org_arn_to_share],
                        "resource_arns": [tgw_arn]
                    }
                )
                self._provision_resource("tgw-share", cdk_def_ram)

            # nat gateways
            if vpc_resource.public_subnets != None:
                nat_gateway_ids = []
                for ps in vpc_resource.public_subnets:
                    eip_name = f"Demo-eip-{ps.availability_zone}"
                    cdk_def_eip = self._get_cdk_def(type="CfnEIP", module="aws_ec2", name_ref="attr_allocation_id",
                        kargs={
                            "tags": [cdk.CfnTag(
                                key="Name",
                                value=eip_name
                            )]
                        }
                    )
                    self._provision_resource(eip_name, cdk_def_eip)
                    nat_name = f"Demo-nat-{ps.availability_zone}"
                    cdk_def_nat = self._get_cdk_def(type="CfnNatGateway", module="aws_ec2", name_ref="attr_nat_gateway_id",
                        kargs={
                            "subnet_id": ps.subnet_id,
                            "connectivity_type": "public",
                            "allocation_id": self.resources[f"{eip_name}{cdk_def_eip.type}"].resource.attr_allocation_id,
                            "tags": [cdk.CfnTag(
                                key="Name",
                                value=nat_name
                            )]
                        }
                    )
                    self._provision_resource(nat_name, cdk_def_nat)
                    nat_gateway_ids.append(self.resources[f"{nat_name}{cdk_def_nat.type}"].resource.attr_nat_gateway_id)

            if self.tgw_id != None:
                # tgw attachment
                for ps in vpc_resource.isolated_subnets[-3:]:
                    transit_subnet_ids.append(ps.subnet_id)
                tgw_attach_name = "Demo-tgw-attach"
                appliance_mode_support = "disable"
                if self.public_subnet != None: appliance_mode_support = "enable" # if inspection vpc then enable appliance mode
                cdk_def_tgw_attach = self._get_cdk_def(type="CfnTransitGatewayAttachment", module="aws_ec2", name_ref="attr_id",
                    kargs={
                        "subnet_ids": transit_subnet_ids,
                        "transit_gateway_id": self.tgw_id,
                        "vpc_id": vpc_id,
                        "options": { "ApplianceModeSupport" : appliance_mode_support },
                        "tags": [cdk.CfnTag(
                            key="Name",
                            value=tgw_attach_name
                        )]
                    }
                )
                self._provision_resource(tgw_attach_name, cdk_def_tgw_attach)
                cdk_def_tgw_attach_res=self.resources[f"{tgw_attach_name}{cdk_def_tgw_attach.type}"].resource
                # store tgw attachment id in ssm parameter
                tgw_attach_id = cdk_def_tgw_attach_res.attr_id
                tgw_attach_ssm_name = "demo-tgw-attach"
                cdk_def_ssm = self._get_cdk_def(type="StringParameter", module="aws_ssm", name_ref="parameter_name", 
                    kargs={
                        "string_value": f"{tgw_attach_id},{vpc_cidr}",
                        "parameter_name": tgw_attach_ssm_name
                    }
                )
                self._provision_resource(tgw_attach_ssm_name, cdk_def_ssm)

                # routes
                private_route_table_ids += [i.route_table.route_table_id for i in vpc_resource.isolated_subnets]
                public_route_table_ids = [i.route_table.route_table_id for i in vpc_resource.public_subnets]
               
                if self.public_subnet != None: # if inspection vpc
                    # cfn output for route table ids
                    for n,i in enumerate(private_route_table_ids[:-3]):
                        cdk.CfnOutput(
                            self,
                            f"private_rt_id_output_{n}",
                            value = i.strip(),
                            export_name = f"private-rt-id-{n}"
                        )
                    for n,i in enumerate(private_route_table_ids[-3:]):
                        cdk.CfnOutput(
                            self,
                            f"transit_rt_id_output_{n}",
                            value = i.strip(),
                            export_name = f"transit-rt-id-{n}"
                        )
                    for n,i in enumerate(public_route_table_ids):
                        cdk.CfnOutput(
                            self,
                            f"public_rt_id_output_{n}",
                            value = i.strip(),
                            export_name = f"public-rt-id-{n}"
                        )
                    # cfn output for subnet ids
                    for n,i in enumerate(private_subnet_ids):
                        cdk.CfnOutput(
                            self,
                            f"private_subnet_id_output_{n}",
                            value = i.strip(),
                            export_name = f"private-subnet-id-{n}"
                        )
                    for n,i in enumerate(transit_subnet_ids):    
                        cdk.CfnOutput(
                            self,
                            f"transit_subnet_id_output_{n}",
                            value = i.strip(),
                            export_name = f"transit-subnet-id-{n}"
                        )
                    for n,i in enumerate([i.subnet_id for i in vpc_resource.public_subnets]):
                        cdk.CfnOutput(
                            self,
                            f"public_subnet_id_output_{n}",
                            value = i.strip(),
                            export_name = f"public-subnet-id-{n}"
                        )

                # routes
                global_cidr = "0.0.0.0/0"
                if self.public_subnet != None: # if inspection vpc
                    tgw_dests = [self.overall_cidr] + [c.strip() for c in self.onprem_cidr.split(',')] # route to tgw for overall aws cidr and on-premises cidr
                    for n,r in enumerate(private_route_table_ids+public_route_table_ids): # route on for private and public route tables
                        for d in tgw_dests:
                            cdk_def_route = self._get_cdk_def(type="CfnRoute", module="aws_ec2", name_ref="logical_id",
                                kargs={
                                    "route_table_id": r,
                                    "destination_cidr_block": d,
                                    "transit_gateway_id": self.tgw_id # route to transit gateway for overall aws cidr and on-premises cidr
                                }
                            )
                            self._provision_resource(f"tgw{n}-{d}", cdk_def_route)
                            self.resources[f"tgw{n}-{d}{cdk_def_route.type}"].resource.add_depends_on(cdk_def_tgw_attach_res)
                    for az,pr in enumerate(private_route_table_ids):  # route on for private route tables
                        cdk_def_route = self._get_cdk_def(type="CfnRoute", module="aws_ec2", name_ref="logical_id",
                            kargs={
                                "route_table_id": pr,
                                "destination_cidr_block": global_cidr,
                                "nat_gateway_id": nat_gateway_ids[az%len(nat_gateway_ids)] # route to nat gateway for global cidr
                            }
                        )
                        self._provision_resource(f"nat{az}", cdk_def_route)
                else:
                    for n,r in enumerate(private_route_table_ids): # route to transit gateway for all other vpcs that aren't inspection vpc
                        cdk_def_route = self._get_cdk_def(type="CfnRoute", module="aws_ec2", name_ref="logical_id",
                            kargs={
                                "route_table_id": r,
                                "destination_cidr_block": global_cidr,
                                "transit_gateway_id": self.tgw_id
                            }
                        )
                        self._provision_resource(f"tgw{n}-{global_cidr}", cdk_def_route)
                        self.resources[f"tgw{n}-{global_cidr}{cdk_def_route.type}"].resource.add_depends_on(cdk_def_tgw_attach_res)


    def _append_subnet_config_list(self, name: str, sub_type, mask):
        self.subnet_config_list.append(aws_ec2.SubnetConfiguration(
                name=name,
                subnet_type=sub_type,
                cidr_mask=mask
            )
        )


    def _provision_subnets(self, subnet_name, subnet_cidrs, vpc_id: str, subnet_ids, private_route_table_ids):
        for az,s in zip(["a","b","c"],subnet_cidrs):
            cdk_def = self._get_cdk_def(type="PrivateSubnet", module="aws_ec2", name_ref="subnet_id",
                kargs={
                    "availability_zone": f"{cdk.Stack.of(self).region}{az}",
                    "cidr_block": s.strip(),
                    "vpc_id": vpc_id
                }
            )
            name = f"{subnet_name}-{az}"
            self._provision_resource(name, cdk_def)
            subnet = self.resources[f"{name}{cdk_def.type}"].resource
            cdk.Tags.of(subnet).add("Name", name)
            subnet_ids.append(subnet.subnet_id)
            private_route_table_ids.append(subnet.route_table.route_table_id)


    def _tag_subnets(self, subnets, name):
        for s in subnets:
            cdk.Tags.of(s).add("Name", f"{name}-{s.availability_zone}")
