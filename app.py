"""Application to create CDK Environment Pipeline Stack."""

import aws_cdk as cdk

from cdk_env_pipeline.stacks.pipeline_stack import PipelineStack
from deploy_config import project, _pipelines


app = cdk.App()
region = app.node.try_get_context("region")

print("pipelines:", _pipelines)
for n,p in enumerate(_pipelines): # create pipeline stack for each pipeline
    pipeline_stack = PipelineStack(
        app,
        f"{project.name}-{p}Stack",
        p,
        n,
        env=cdk.Environment(
            account=project.pipeline.tooling_acct.account,
            region=project.pipeline.tooling_acct.region
        )
    )
    print()

for tag in project.tags:
    cdk.Tags.of(pipeline_stack).add(
        tag.key,
        tag.value
    )

app.synth()
