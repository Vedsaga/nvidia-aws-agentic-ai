import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    Duration,
)
from constructs import Construct


class EventDrivenStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Event-driven architecture components will be defined here
        
        # Example: Event bus for custom events
        self.event_bus = events.EventBus(
            self, "CustomEventBus",
            event_bus_name="karaka-events"
        )
        
        # Example: DLQ for failed events
        self.dlq = sqs.Queue(
            self, "EventDLQ",
            queue_name="karaka-event-dlq",
            retention_period=Duration.days(14)
        )
        
        # Storage for event processing
        self.events_table = dynamodb.Table(
            self, "EventsTable",
            table_name="Events",
            partition_key=dynamodb.Attribute(
                name="event_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        
        # S3 bucket for event artifacts
        self.artifacts_bucket = s3.Bucket(
            self, "EventArtifacts",
            bucket_name=f"event-artifacts-{self.account}-{self.region}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )