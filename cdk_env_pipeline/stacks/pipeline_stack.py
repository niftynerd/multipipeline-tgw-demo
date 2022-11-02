"""Module to create a CDK Environment deployment Codepipeline.

This module provides functionality to define a number of
named deployment environments, and create a separate
codepipeline for each so that one repo branch per env
can be deployed independent of each other.
"""
from aws_cdk import (
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_codestarnotifications as notifications,
    aws_codecommit as codecommit,
    aws_chatbot as chatbot,
    aws_iam as iam,

)
from constructs import Construct
from typing import List

from aws_cdk import (
    Stack,
    Environment,
    Tags
)

from aws_cdk.pipelines import (
    CodeBuildOptions,
    CodePipeline,
    CodePipelineSource,
    ShellStep,
    ManualApprovalStep,
    ConfirmPermissionsBroadening
)

from lib.pipeline_classes import (
    PipelineApproval,
    Tag
)
from ..stages.env_deploy_stage import EnvDeployStage

from deploy_config import (
    project
)


class PipelineStack(Stack):
    """Create a self-mutating environment deployment pipeline."""

    def __init__(self, scope: Construct, id: str, pipeline: str, pipeline_num: int, **kwargs) -> None:
        """Initise the class and construct the pipeline."""
        super().__init__(scope, id, **kwargs)
        self.commands = [
                            "npm install -g aws-cdk",
                            "pip install -r requirements.txt",
                            "cdk synth --ignore-errors"
                        ] # commands to run for synth step
        self.pipeline_env = pipeline
        self.pipeline_num = pipeline_num
        self.pipeline_name = f"{project.name}-{pipeline}"
        self.sns_topic = None
        self.pipeline = self._create_env_pipeline()
        self._add_environments()
        if project.pipeline.slackbot:
            self.pipeline.build_pipeline()
            self._add_notifications()

    def _create_env_pipeline(self) -> CodePipeline:
        """Create a self mutating cdk pipeline."""
        source = self._get_pipeline_source()
        if not source:
            assert("No source config defined for pipeline.")
            exit(1)

        code_build_defaults = CodeBuildOptions(
            role_policy=[
                iam.PolicyStatement(
                    sid="EC2DescribeTransitGateways",
                    actions=["ec2:DescribeTransitGateways",
                        "ec2:DescribeTransitGatewayAttachments",
                        "sts:AssumeRole",
                        "codepipeline:StartPipelineExecution"
                    ],
                    resources=["*"],
                )
            ] # add permissions for cdk synth
        )

        synth = ShellStep(
            "Synth",
            input=source,
            commands=self.commands
            #primary_output_directory="member/cdk.out"
        )

        return CodePipeline(
            self,
            self.pipeline_name,
            pipeline_name=self.pipeline_name,
            synth=synth,
            code_build_defaults=code_build_defaults,
            cross_account_keys=True
        )

    def _add_notifications(self) -> None:
        """Add chatbot notications for Slack."""
        slackbot = project.pipeline.slackbot
        keys = ['channel', 'workspace_id', 'channel_id']
        for key in keys:
            if getattr(slackbot, key) == "":
                return

        target = chatbot.SlackChannelConfiguration(
            self,
            f"{self.pipeline_name}SlackChannel",
            slack_channel_configuration_name=slackbot.channel,
            slack_workspace_id=slackbot.workspace_id,
            slack_channel_id=slackbot.channel_id
        )
        self.pipeline.pipeline.notify_on_execution_state_change(
            id=f"{self.pipeline_name}Notification",
            target=target,
            detail_type=notifications.DetailType.BASIC
        )

    def _add_environments(self):
        """Add each env in config as a deploy stage."""
        waves = []
        wave = None
        print("pipeline:", self.pipeline_env)
        envs = []
        for env_def in project.envs:
            # if not first pipeline, pipeline has to be defined in config file 
            if env_def.skip or env_def.aws_acct.account == "" or \
            (self.pipeline_num != 0 and env_def.pipelines == None) or \
            (env_def.pipelines != None and self.pipeline_env not in env_def.pipelines.split(',')):
                continue
            envs.append(env_def)
        for count,env_def in enumerate(envs):
            env_stage = EnvDeployStage(
                scope=self,
                id=f"{project.name}-{env_def.name}-stage",
                env=Environment(
                    account=env_def.aws_acct.account,
                    region=env_def.aws_acct.region
                ),
                target=env_def
            )
            self._tag_stage(
                stage=env_stage,
                extra_tags=env_def.tags)
            
            pre_app = self._stage_approval(
                        stage_name=env_def.name,
                        approvals=env_def.approvals,
                        stage=env_stage
                      )

            # trigger next pipeline if last step and nextpipeline specified
            if count != len(envs)-1 or env_def.next_pipeline == None: post = None
            else:
                post = [ShellStep(f"execute {env_def.next_pipeline}",
                            commands=[f"aws codepipeline start-pipeline-execution --name {project.name}-{env_def.next_pipeline}"]
                        )]
                
            if env_def.wave == None:
                self.pipeline.add_stage(
                    env_stage,
                    pre=pre_app,
                    post=post
                )
            else:
                if env_def.wave not in waves:
                    waves.append(env_def.wave)
                    wave = self.pipeline.add_wave(env_def.wave)
                wave.add_stage(
                    env_stage,
                    pre=pre_app,
                    post=post
                )

    def _get_pipeline_source(self) -> CodePipelineSource:
        """Return repo source from config."""
        if self.pipeline_num != 0: trigger_on_push = False # trigger on push only if it's the first pipeline
        else: trigger_on_push = True
        if project.pipeline.github:
            github = project.pipeline.github
            return CodePipelineSource.connection(
                repo_string=f"{github.org}/{github.repo.name}",
                branch=github.repo.branch,
                connection_arn=github.connection_id,
                trigger_on_push=trigger_on_push
            )
        if project.pipeline.codecommit:
            code_repo = project.pipeline.codecommit.repo
            repo = codecommit.Repository.from_repository_name(
                self,
                "EnvPLRepo", code_repo.name
            )
            return CodePipelineSource.code_commit(
                repo, code_repo.branch
            )
        return None

    def _tag_stage(
        self,
        stage: EnvDeployStage,
        extra_tags: List[Tag]
    ) -> None:
        """Add tags to deployed resources."""
        tags = project.tags + extra_tags

        for tag in tags:
            Tags.of(stage).add(
                tag.key,
                tag.value
            )

    def _stage_approval(
        self,
        stage_name: str,
        approvals: PipelineApproval,
        stage: EnvDeployStage
    ) -> list:
        """Return pre-approval step."""
        if not (approvals.release and approvals.permissions):
            return None

        pre_step = []
        if approvals.release:
            pre_step.append(
                ManualApprovalStep(
                    f"{stage_name}Approval",
                    comment=approvals.release_description
                )
            )

        if approvals.permissions:
            self._set_sns_topic(approvals.approver_email)
            pre_step.append(
                ConfirmPermissionsBroadening(
                    "CheckPermissions",
                    stage=stage,
                    notification_topic=self.sns_topic
                )
            )

        return pre_step

    def _set_sns_topic(self, email: str) -> None:
        """Create a sns topic."""
        if email != '' and not self.sns_topic:
            self.sns_topic = sns.Topic(
                self,
                f"{project.name}-PipelineApprovals"
            )
            self.sns_topic.add_subscription(
                subscriptions.EmailSubscription(
                    email
                )
            )
