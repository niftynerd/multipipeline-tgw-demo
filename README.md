
# Multi-pipeline solution for VPCs with AWS transit gateway - Network Pipelines


Once initially deployed via the cdk CLI into the tooling account, three AWS Codepipelines are created
to deploy network resouces into all target AWS Accounts defined as environments in the deploy_config.py file.
1. EnvPipeline - hub vpc on network account, contains transit gateway
2. tgw-attachments - attach all spoke vpcs to transit gateway
3. tgw-routes - create transit gateway routes to and from inspection vpc

Once deployed via CLI, commits to the repo cause the environment pipeline (1st one) to update,
self mutate, and create CloudFormation changesets for the target AWS accounts (environments).
The 2nd and 3rd pipelines are triggered by the successful completions of the previous pipelines.

The tooling account and target AWS Accounts must be [bootstrapped](#cdk-bootstrapping) with the cdk toolkit
before deployment and updates can occur.

## Contents

[CICD Overview](#cicd-overview)

[Pipeline Architecture](#pipeline-architecture)

[Pipeline Application Design](#pipeline-application-design)

[Pipeline Configuration](#pipeline-configuration)

[Resource Definition](#resource-definition)

[AWS Glue ETL Jobs](#aws-glue-etl-jobs)

[AWS DMS Provisioning](#aws-dms-provisioning)

[CDK Basics](#cdk-basics)

<div class="page"/>

## CICD Overview

Prerequisites for pipeline deployment are:
1. AWS CLI tools [installed locally](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. Latest [AWS CDK 2.*](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) installed locally.
3. AWS Admin rights to Tooling account.
4. AWS Admin rights to each target AWS Account.
5. The tooling account and target AWS Accounts must be [bootstrapped](#cdk-bootstrapping)
6. Create a Codestar connection in the tooling account to the Bitbucket repo. (Bitbucket admin rights required)
7. Clone the pipeline repo from Bitbucket.
8. pip install -r requirements.txt
9. cdk synth (to ensure the project builds locally)
10. Configure aws cli access EG: "aws configure sso"
11. Set default profile to data tooling account: export AWS_PROFILE='tooling'
12. Obtain new temporary credentials: "aws sso login --profile tooling"
13. Deploy cdk app: cdk deploy

When the app is initially deployed you will be granted to allow the creation of AWS Resources including IAM Roles.

## Pipeline Architecture

The CDK pipeline is designed to be a highly configurable, modular IaC application developed in Python 3 using the AWS cdk framework.
The key objective of the design is being easy to expand and maintain. The project uses python data classes to infer typing which assists with code completion
in various IDEs.

At the core of the pipeline is deploy-config.py. This contains primary configuration items such as the project name and defines which AWS accounts the pipeline should target.

## Pipeline Application Design

1. Running 'cdk deploy' on the CLI runs 'python app.py' with the context from cdk.json
2. app.py provisions a CloudFormation stack in the data tooling account.
3. The CloudFormation stack creates a self-mutating CodePipeline with source from the Bitbucket repo.
4. EnvDeployStage imports NetworkStack, ParameterStack and TgwRoutesStack. Resources defined in these respective stacks are provisioned by these CDK Stack classes.

## Pipeline Configuration

The following sections outline key attributes that can be defined in the top level config files.

### deploy-config

Application level parameters that define project name and target AWS accounts.
Item names in bold text are required. Others are optional.

| Item | Purpose | Values |
|----|----|----|
| **_prj_name** | Prefix for all resources created by the stack. | String |
| **envs** | List of Target accounts the data lake should be deployed to. | List[CDKTargetAWSEnv] |
| **project** | Defines the tooling account and repo to deploy from. | CDKProject |

### CDKTargetAWSEnv 

Python dataclass that defines the AWS accounts that the env pipeline will target for deployment. These must be bootstrapped with cdk *before* they can be used. See: [CDK Boot strapping](#cdk-bootstrapping)

| Item | Purpose | Values |
|----|----|----|
| **name** | Prefix for this environment. (dev,uat,prod) | "[a-z0-9]" |
| **aws_acct** | AWS Account number of this environment. | "[1-9]" |
| **region** | Region in AWS Account to target | Valid AWS Region name. |
| removal_policy | Environment specific override for resources when CloudFormation stack is deleted. See: [CDK Removal Policy](https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.core/RemovalPolicy.html) | Default: cdk.RemovalPolicy.DESTROY |
| approvals.release | When true, forces manual approval in the pipeline to release into this environment. | bool |
| approvals.release_description | Message could be "Production release approval required." | string |
| approvals.permissions | When True, requires manual approval when permission bounderies would be expanded. See: [CDK Confirm Permissions Broadening](https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.pipelines/ConfirmPermissionsBroadening.html)| True,False |

## CDK Basics

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region. Note - it doesn't support the sso login yet
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
