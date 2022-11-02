"""Module to define dataclasses for config.py."""

from dataclasses import dataclass, field


@dataclass
class Repo:
    """Define source repository structure."""

    name: str
    branch: str


@dataclass
class GitHub:
    """Define GitHub structure."""

    org: str
    repo: Repo
    connection_id: str


@dataclass
class CodeCommit:
    """Define AWS CodeCommit structure."""

    repo: Repo


@dataclass
class Tag:
    """Define AWS Tag structure."""

    key: str
    value: str


@dataclass
class AWSAccount:
    """Define AWS Account structure."""

    account: str
    region: str = field(default="ap-southeast-2")


@dataclass
class SlackBot:
    """Define Slack AWS Chatbot structure."""

    channel: str
    workspace_id: str
    channel_id: str


@dataclass
class PipelineApproval:
    """Define Pipeline Manual Approval structure."""

    approver_email: str
    release: bool = field(default=False)
    release_description: str = field(default="Manual approval required.")
    permissions: bool = field(default=False)
