import aws_cdk as core
import aws_cdk.assertions as assertions

from nvidia_aws_agentic_ai.nvidia_aws_agentic_ai_stack import NvidiaAwsAgenticAiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in nvidia_aws_agentic_ai/nvidia_aws_agentic_ai_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = NvidiaAwsAgenticAiStack(app, "nvidia-aws-agentic-ai")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
