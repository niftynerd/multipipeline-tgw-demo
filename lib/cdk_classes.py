"""Module to define some CDK Helper Classes."""

from aws_cdk import (
    Stage,
    Stack
)

import importlib

from lib.cdk_resource import CDKResourceDef


from lib.cdk_project_classes import (
    CDKTargetAWSEnv
)

from deploy_config import (
    project
)


class CDKStage(Stage):
    """Custom Stage Class with predined helpers."""

    def __init__(
            self,
            scope: Stack,
            id: str,
            target: CDKTargetAWSEnv,
            **kwargs
    ) -> None:
        """Create an instance of the class."""
        super().__init__(scope, id, **kwargs)
        self.target = target

    def _prefix(self) -> str:
        return f"{project.name}-{self.target.name}"


class CDKStack(Stack):
    """Custom Stack Class with predined helpers."""
    def __init__(
        self,
        stage: CDKStage,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(stage, id, **kwargs)
        self.stage = stage
        self._provision_resources()

    def _provision_resources(self) -> None:
        """Create CDK Resource objects."""
        self.resources = {}
        for resource_name in self.resource_names:
            self._provision_resource(
                resource_name,
                self.cdk_def
            )

    def _provision_resource(
        self,
        resource_name: str,
        cdk_def: CDKResourceDef
    ) -> None:
        resource = CDKResource(
            scope=self,
            cdk_def=cdk_def,
            name=resource_name
        )
        self.resources[f"{resource_name}{cdk_def.type}"] = resource

    def _prefix(self) -> str:
        return f"{project.name}-{self.stage.target.name}"

    def _get_cdk_def(self, type, module, name_ref, kargs):
        return CDKResourceDef(
            type=type,
            module=module,
            name_ref=name_ref,
            kargs=kargs,
            permissions=[]
        )


class CDKResource():
    """Class to create AWS CDK resources."""

    def __init__(
        self,
        scope: CDKStack,
        cdk_def: CDKResourceDef,
        name: str
    ) -> None:
        self.stack = scope
        self.cdk_def = cdk_def
        self.id = self._get_resource_id(name)
        self._create_resource()

    def _create_resource(self) -> None:
        """Create the AWS CDK resource.

        Uses the dynamic nature of Python to import the necessry module and
        provision a CDK Resource.

        self.resource = getattr(
            globals()[CDKResourceDef.module],
            CDKResourceDef.type
        ) equates to:
        self.resource = getattr(globals()["aws_s3"], "Bucket") equates to:
        self.resource = aws_s3.Bucket(**kargs) where:
        **kargs = (scope=self.stack, id=self.id, ...) etc.

        """
        self._import_cdk_module()

        kargs = self._get_kargs()
        self.resource = getattr(
            globals()[self.cdk_def.module],
            self.cdk_def.type
        )(**kargs)

        self.resource.apply_removal_policy(
            self.stack.stage.target.removal_policy
        )

        self.name = getattr(self.resource, self.cdk_def.name_ref)

    def _get_resource_id(self, name: str) -> str:
        """Create a unique resource id based on object context.

        Will create {project.name}-{stage.name}-{name}{Resource.type}.
        EG: dlh-dev-rawBucket
        """
        return f"{self.stack._prefix()}-{name}{self.cdk_def.type}"

    def _import_cdk_module(self) -> None:
        """Import the aws_cdk module we need to create this resource."""
        globals()[self.cdk_def.module] = importlib.import_module(
            f"aws_cdk.{self.cdk_def.module}"
        )

    def _get_kargs(self) -> dict:
        """Construct kargs for CDK resource.

        All CDK objects need a scope and an identifier.
        We then add the resource specific kargs from our CDKResourseDef.
        EG: aws_s3.Bucket takes "enforce_ssl" and "encryption" as arguments.
        """
        kargs = {
            "scope": self.stack,
            "id": self.id
        }
        if self.cdk_def.karg_name:
            kargs[self.cdk_def.name_ref] = self.id.lower()
        kargs.update(self.cdk_def.kargs)

        return kargs
