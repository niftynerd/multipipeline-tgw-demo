"""Module for setup tools.

Update install_requires list with
additional aws-cdk modules as required.
"""
import setuptools


with open("README.md") as fp:
    long_description = fp.read()

cdk_version = "1.152.0"

setuptools.setup(
    name="cdk_env_pipeline",
    version="0.4.0",

    description="Basic CDK Environment Deployment Pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="niftynerd",
    author_email="niftynerd1337@gmail.com",

    package_dir={"": "cdk_env_pipeline"},
    packages=setuptools.find_packages(where="cdk_env_pipeline"),

    install_requires=[
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
        "cdk-nag",
        "boto3"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: Python :: 3.10.0",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
