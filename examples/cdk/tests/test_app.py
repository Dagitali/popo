"""Inspect the synthesized CDK template without credentials or deployment."""

from tempfile import TemporaryDirectory
from unittest import TestCase

from aws_cdk import App
from aws_cdk.assertions import Template

from app import create_stack


class TestExampleStack(TestCase):
    """Keep the optional application test independent of Popo's checks."""

    def test_private_bucket(self) -> None:
        """
        Synthesize a retained bucket with explicit public-access blocking.
        """
        with TemporaryDirectory(prefix='cdk-example-') as output:
            app = App(outdir=output, analytics_reporting=False)
            template = Template.from_stack(create_stack(app))
            template.resource_count_is('AWS::S3::Bucket', 1)
            template.has_resource_properties(
                'AWS::S3::Bucket',
                {
                    'PublicAccessBlockConfiguration': {
                        'BlockPublicAcls': True,
                        'BlockPublicPolicy': True,
                        'IgnorePublicAcls': True,
                        'RestrictPublicBuckets': True,
                    },
                    'BucketEncryption': {
                        'ServerSideEncryptionConfiguration': [
                            {
                                'ServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': 'AES256',
                                },
                            },
                        ],
                    },
                },
            )
            template.has_resource(
                'AWS::S3::Bucket',
                {'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain'},
            )
