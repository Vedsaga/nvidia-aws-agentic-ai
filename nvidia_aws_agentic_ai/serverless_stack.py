from aws_cdk import Stack
from constructs import Construct


class ServerlessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # We will add S3, DynamoDB, and Lambdas here later.
        # For now, it's just a placeholder.
        pass
