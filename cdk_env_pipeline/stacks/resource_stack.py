"""Module to create a Resource Stack.

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

EG: raw_bucket = self.stage.storage.resources["rawBucket"]
    where stage.storage = ResourceStack(
            stage=self,
            id=f"{self._prefix()}-storage",
            cdk_def=target.resources.storage.s3,
            resource_names=target.resources.storage.bucket_names
        )
EG: crawler_role = self.stage.iam.resources["crawlerRole"]

"""
from typing import List
from lib.cdk_classes import (
    CDKStack,
    CDKStage,
)
from lib.cdk_resource import CDKResourceDef


class ResourceStack(CDKStack):
    def __init__(
            self,
            stage: CDKStage,
            id: str,
            cdk_def: CDKResourceDef,
            resource_names: List[str],
            **kwargs,
    ) -> None:
        self.cdk_def = cdk_def
        self.resource_names = resource_names
        super().__init__(stage, id, **kwargs)
