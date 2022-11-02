"""Module to define some CDK Project Classes."""

from dataclasses import dataclass, field
from typing import List

import aws_cdk as cdk


from lib.pipeline_classes import (
    AWSAccount,
    PipelineApproval,
    SlackBot,
    GitHub,
    CodeCommit,
    Tag
)


@dataclass
class CDKTargetAWSEnv:
    """Define Target AWS Environment structure."""

    name: str
    aws_acct: AWSAccount
    approvals: PipelineApproval
    tags: List[Tag]
    skip: bool = field(default=False)
    removal_policy: cdk.RemovalPolicy = field(
        default=cdk.RemovalPolicy.DESTROY
    )
    trusted_accounts : str = field(default=None)
    overall_cidr : str = field(default=None)
    onprem_cidr : str = field(default=None)
    vpc_cidrs : str = field(default=None)
    public_subnet : str = field(default=None)
    private_subnet : str = field(default=None)
    transit_subnet : str = field(default=None)
    contiguous : str = field(default=None)
    org_arn_to_share : str = field(default=None)
    wave : str = field(default=None)
    next_pipeline : str = field(default=None)
    pipelines : str = field(default=None)
    inspection_cidr : str = field(default=None)


@dataclass
class CDKEnvPipeline:
    """Define CDKEnvPipeline structure."""

    tooling_acct: AWSAccount
    slackbot: SlackBot = field(default=None)
    github: GitHub = field(default=None)
    codecommit: CodeCommit = field(default=None)


@dataclass
class CDKProject:
    """Define CDKProject structure."""

    name: str
    pipeline: CDKEnvPipeline
    envs: List[CDKTargetAWSEnv]
    tags: List[Tag]
