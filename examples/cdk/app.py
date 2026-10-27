"""Synthesize a small environment-agnostic CDK app without AWS lookups."""

from aws_cdk import App, RemovalPolicy, Stack
from aws_cdk import aws_s3 as s3


def create_stack(
    app: App,
) -> Stack:
    """
    Describe a private retained bucket without contacting AWS.

    Parameters
    ----------
    app : aws_cdk.App
        Application owning the example stack and its synthesis output.

    Returns
    -------
    aws_cdk.Stack
        Environment-agnostic stack with no assets or context lookups.
    """
    stack = Stack(app, 'GuardrailExample')
    s3.Bucket(
        stack,
        'ExampleBucket',
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        encryption=s3.BucketEncryption.S3_MANAGED,
        enforce_ssl=True,
        removal_policy=RemovalPolicy.RETAIN,
    )
    return stack


def main() -> None:
    """Write a local cloud assembly to cdk.out without deploying resources."""
    app = App(outdir='cdk.out', analytics_reporting=False)
    create_stack(app)
    app.synth()


if __name__ == '__main__':
    main()
