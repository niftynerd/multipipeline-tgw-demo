"""Module to define CDKResource definition."""

from dataclasses import dataclass, field
from typing import List
import aws_cdk as cdk


@dataclass
class CDKResourceDef:
    """Data class defining a resource parameters."""
    type: str               # noqa: E501 The resource type EG: Bucket
    module: str             # noqa: E501 The CDK module that provisions this resource.
    name_ref: str           # noqa: E501 The CDK name attribute of the created resource EG: bucket_name.
    permissions: List[str]  # noqa: E501 Permission methods the resource will apply to a supplied role.
    kargs: dict             # noqa: E501 The keyword arguments used by the CDK resource module.
    karg_name: bool = field(default=False)  # noqa: E501 Add a resource name karg if True
    removal_policy: cdk.RemovalPolicy = field(default=cdk.RemovalPolicy.DESTROY)  # noqa: E501
