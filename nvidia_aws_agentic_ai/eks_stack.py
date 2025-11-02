import base64
import json
from aws_cdk import Stack, CfnOutput, aws_eks as eks, aws_ec2 as ec2
from constructs import Construct
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer


class EksStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Get the NVIDIA API key from the context
        nvidia_key = self.node.try_get_context("nvidia_api_key")
        if not nvidia_key:
            raise Exception("Provide --context nvidia_api_key=...")

        # 2. Create the EKS Cluster
        cluster = eks.Cluster(
            self,
            "HackathonCluster",
            version=eks.KubernetesVersion.V1_28,
            default_capacity=0,  # We will add one custom node group
            kubectl_layer=KubectlV28Layer(self, "KubectlLayer"),  # <--- ADD THIS LINE
        )

        # 3. Create ONE Node Group (for BOTH models)
        nodegroup = cluster.add_nodegroup_capacity(
            "main-gpu-nodegroup",
            instance_types=[ec2.InstanceType("g5.xlarge")],
            min_size=1,  # <--- 1 Node
            max_size=1,  # <--- 1 Node
            desired_size=1,
        )

        # 4. Create the 'nim' namespace
        nim_namespace = cluster.add_manifest(
            "NimNamespace",
            {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "nim"}},
        )

        # 5. Create the NVIDIA API secrets (same as before)
        api_secret = cluster.add_manifest(
            "NgcApiSecret",
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "ngc-api", "namespace": "nim"},
                "stringData": {"NGC_API_KEY": nvidia_key},
            },
        )
        api_secret.node.add_dependency(nim_namespace)

        docker_auth_str = f"$oauthtoken:{nvidia_key}"
        docker_auth_b64 = base64.b64encode(docker_auth_str.encode()).decode("utf-8")
        docker_config_json = json.dumps(
            {"auths": {"nvcr.io": {"auth": docker_auth_b64}}}
        )
        docker_config_b64 = base64.b64encode(docker_config_json.encode()).decode(
            "utf-8"
        )

        reg_secret = cluster.add_manifest(
            "RegistrySecret",
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "registry-secret", "namespace": "nim"},
                "type": "kubernetes.io/dockerconfigjson",
                "data": {".dockerconfigjson": docker_config_b64},
            },
        )
        reg_secret.node.add_dependency(nim_namespace)

        # 6. We are NOT using Helm. We define the deployments directly
        #    so we can control the 'resources' key.

        # --- Generator (8B) Deployment ---
        app_label_gen = {"app": "nim-generator"}
        gen_deployment = cluster.add_manifest(
            "GeneratorDeployment",
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "nim-generator-deployment", "namespace": "nim"},
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": app_label_gen},
                    "template": {
                        "metadata": {"labels": app_label_gen},
                        "spec": {
                            "imagePullSecrets": [{"name": "registry-secret"}],
                            "containers": [
                                {
                                    "name": "nim-llm",
                                    "image": "nvcr.io/nim/meta/Llama-3.1-Nemotron-Nano-8B-v1:1.0.0",
                                    "ports": [{"containerPort": 8000}],
                                    "env": [
                                        {
                                            "name": "NGC_API_KEY",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "ngc-api",
                                                    "key": "NGC_API_KEY",
                                                }
                                            },
                                        }
                                    ],
                                    # CRITICAL: We DO NOT specify a 'resources'
                                    # block for 'nvidia.com/gpu'. This makes it
                                    # "best-effort" and allows sharing.
                                }
                            ],
                        },
                    },
                },
            },
        )
        gen_deployment.node.add_dependency(nodegroup, reg_secret, api_secret)

        # --- Embedder (1B) Deployment ---
        app_label_embed = {"app": "nim-embedder"}
        embed_deployment = cluster.add_manifest(
            "EmbedderDeployment",
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "nim-embedder-deployment", "namespace": "nim"},
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": app_label_embed},
                    "template": {
                        "metadata": {"labels": app_label_embed},
                        "spec": {
                            "imagePullSecrets": [{"name": "registry-secret"}],
                            "containers": [
                                {
                                    "name": "nim-llm",
                                    "image": "nvcr.io/nim/nvidia/llama-3.2-nv-embedqa-1b-v2:1.0.0",
                                    "ports": [{"containerPort": 8000}],
                                    "env": [
                                        {
                                            "name": "NGC_API_KEY",
                                            "valueFrom": {
                                                "secretKeyRef": {
                                                    "name": "ngc-api",
                                                    "key": "NGC_API_KEY",
                                                }
                                            },
                                        }
                                    ],
                                    # CRITICAL: Also no 'resources' block.
                                }
                            ],
                        },
                    },
                },
            },
        )
        embed_deployment.node.add_dependency(nodegroup, reg_secret, api_secret)

        # 7. Create LoadBalancers (same as before)
        gen_lb = cluster.add_manifest(
            "GeneratorLB",
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "nim-generator-lb", "namespace": "nim"},
                "spec": {
                    "type": "LoadBalancer",
                    "ports": [{"port": 80, "targetPort": 8000}],
                    "selector": app_label_gen,
                },
            },
        )
        gen_lb.node.add_dependency(gen_deployment)

        embed_lb = cluster.add_manifest(
            "EmbedderLB",
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "nim-embedder-lb", "namespace": "nim"},
                "spec": {
                    "type": "LoadBalancer",
                    "ports": [{"port": 80, "targetPort": 8000}],
                    "selector": app_label_embed,
                },
            },
        )
        embed_lb.node.add_dependency(embed_deployment)

        # 8. Output the Load Balancer URLs
        gen_lb_url = cluster.get_service_load_balancer_address(
            "nim-generator-lb", namespace="nim"
        )
        embed_lb_url = cluster.get_service_load_balancer_address(
            "nim-embedder-lb", namespace="nim"
        )

        CfnOutput(self, "GenerateEndpoint", value=f"http://{gen_lb_url}")
        CfnOutput(self, "EmbedEndpoint", value=f"http://{embed_lb_url}")
