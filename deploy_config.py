"""Define a desired configuration for the CDKPipeline Stack.

.gitattibutes ensures that the config settings in each branch are
never overridden by another branch, allowing unique config per branch.
This is important for test and deploy into different accounts
from each branch of the repo.
"""
from typing import List

from lib.pipeline_classes import (
    GitHub,
    AWSAccount,
    Tag,
    Repo,
    PipelineApproval
)

from lib.cdk_project_classes import (
    CDKProject,
    CDKEnvPipeline,
    CDKTargetAWSEnv
)

_prj_name = "multipipeline-tgw"
_member_stage = f"{_prj_name}-member-stage"
_pipelines = ["EnvPipeline", "tgw-attachments", "tgw-routes"] # Codepipeline pipelines

"""A list of target AWS Accounts to deploy resources into."""
envs: List[CDKTargetAWSEnv] = [

    CDKTargetAWSEnv(
        name="network",
        pipelines="EnvPipeline,tgw-routes", # pipelines to include this environment on
        next_pipeline="tgw-attachments", # execute this pipeline after this environment is finished with
        aws_acct=AWSAccount(
            account="012345678912", # account number to deploy to e.g. "012345678912"
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com", # email to notify for manual approval
            # permissions=True,   # requires permission boundry permissions
            # release=True        # requires manual approval via email
        ),
        vpc_cidrs="172.16.128.0/24", # vpc cidrs for vpc to add to account
        transit_subnet="28", # subnet mask if contiguous range otherwise use cidr ranges
        contiguous="True", # mark as True if cidr ranges are contiguous
        org_arn_to_share="arn:aws:organizations::233601607584:organization/o-sm87ee7sqc", # arn of organization to share transit gateway with e.g. "arn:aws:organizations::012345678912:organization/o-sm12ee3sqc"
        tags=[
            Tag("environment", "network"),
        ]
    )
    ,
    CDKTargetAWSEnv(
        name="shared-infra-services",
        pipelines="tgw-attachments,tgw-routes",
        wave=_member_stage, # include this on wave so that it is executed at the same time as other environments on this wave
        aws_acct=AWSAccount(
            account="012345678912",
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com"
        ),
        overall_cidr="172.16.128.0/17", # cidr range for overall aws cidr so that route to this range goes through transit gateway
        onprem_cidr = "10.200.0.0/16,10.230.0.0/16,172.21.0.0/16,172.23.0.0/16,172.30.0.0/16", # cidr range for on-premise cidr so that route to this range goes through transit gateway
        vpc_cidrs="172.16.144.0/23",
        public_subnet="27", # first subnet is contiguous so we are using subnet mask
        private_subnet="172.16.144.128/27,172.16.144.160/27,172.16.144.192/27", # because following subnet is not continuous we use full cidr ranges across the 3 AZs
        transit_subnet="172.16.145.0/28,172.16.145.16/28,172.16.145.32/28", # because following subnet is not continuous we use full cidr ranges across the 3 AZs
        tags=[
            Tag("environment", "shared-infra-services"),
        ]
    ),
    CDKTargetAWSEnv(
        name="datalake-dev",
        pipelines="tgw-attachments,tgw-routes",
        wave=_member_stage,
        aws_acct=AWSAccount(
            account="012345678912",
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com"
        ),
        vpc_cidrs="172.16.146.0/24",
        private_subnet="26",
        transit_subnet="28",
        contiguous = "True",
        tags=[
            Tag("environment", "datalake-dev"),
        ]
    ),
    CDKTargetAWSEnv(
        name="datalake-prod",
        pipelines="tgw-attachments,tgw-routes",
        wave=_member_stage,
        aws_acct=AWSAccount(
            account="012345678912",
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com"
        ),
        vpc_cidrs="172.16.147.0/24",
        private_subnet="26",
        transit_subnet="28",
        contiguous = "True",
        tags=[
            Tag("environment", "datalake-prod"),
        ]
    ),
    CDKTargetAWSEnv(
        name="devsecops-tooling",
        pipelines="tgw-attachments,tgw-routes",
        next_pipeline="tgw-routes",
        wave=_member_stage,
        aws_acct=AWSAccount(
            account="012345678912",
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com"
        ),
        vpc_cidrs="172.16.149.0/24",
        private_subnet="26",
        transit_subnet="28",
        contiguous = "True",
        tags=[
            Tag("environment", "devsecops-tooling"),
        ]
    ),
    CDKTargetAWSEnv(
        name="tgw-routes",
        pipelines="tgw-routes",
        inspection_cidr="172.16.144.0/23",
        aws_acct=AWSAccount(
            account="012345678912",
        ),
        approvals=PipelineApproval(
            approver_email="testxxxyyyzzz@gmail.com"
        ),
        tags=[
            Tag("environment", "network"),
        ]
    )
]

"""
The CDK project that has a code pipeline that provisions
stack_resources into each TargetAWSEnv account.
"""
project = CDKProject(
    name=_prj_name,
    pipeline=CDKEnvPipeline(
        github=GitHub(
            org="niftynerd",
            repo=Repo(name="multipipeline-tgw-demo", branch="main"), # specify branch used for pipeline triggers
            connection_id=(
                "arn:aws:codestar-connections:"
                "ap-southeast-2:012345678912:"
                "connection/5e2db7aa-d469-42a4-9cd6-5ad461bc542f" # codestar connection arn created in aws e.g. 
                # "arn:aws:codestar-connections:"
                # "ap-southeast-2:012345678912:"
                # "connection/5e2db7aa-d469-42a4-9cd6-5ad461bc542f"
            )
        ),
        tooling_acct=AWSAccount(
            account="012345678912", # account number of tooling account e.g. "012345678912"
        ),
        slackbot=None
    ),
    envs=envs,
    tags=[
        Tag("project-name", _prj_name),
        Tag("creator", "niftynerd"),
        Tag("owner", "Apps-Services"),
        Tag("owner-email", "testxxxyyyzzz@gmail.com"),
    ]
)
