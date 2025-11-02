import json
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer


class EksStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Get NVIDIA vars from context
        nvidia_key = self.node.try_get_context("nvidia_api_key")
        nvidia_email = self.node.try_get_context("nvidia_email")
        if not nvidia_key or not nvidia_email:
            raise Exception("Provide --context nvidia_api_key=... and nvidia_email=...")

        aws_account_id = self.account

        # 2. Create the EKS Cluster
        cluster = eks.Cluster(
            self,
            "HackathonCluster",
            version=eks.KubernetesVersion.V1_28,
            default_capacity=0,
            kubectl_layer=KubectlV28Layer(self, "KubectlLayer"),
        )

        # 3. Add Voclabs Role to Cluster Auth
        voclabs_role_arn = f"arn:aws:iam::{aws_account_id}:role/voclabs"
        voclabs_role = iam.Role.from_role_arn(self, "VoclabsRole", voclabs_role_arn)
        cluster.aws_auth.add_role_mapping(
            voclabs_role, groups=["system:masters"], username="voclabs-user"
        )

        # 4. Create ONE Node Group with GPU instance
        nodegroup = cluster.add_nodegroup_capacity(
            "main-gpu-nodegroup",
            instance_types=[ec2.InstanceType("g6e.xlarge")],
            min_size=1,
            max_size=1,
            desired_size=1,
        )

        # 5. Add NVIDIA Device Plugin (version verified for K8s 1.28)
        nvidia_plugin = cluster.add_helm_chart(
            "NvidiaDevicePlugin",
            chart="nvidia-device-plugin",
            repository="https://nvidia.github.io/k8s-device-plugin",
            namespace="kube-system",
            version="0.15.0",  # ✅ Officially supported version
        )
        nvidia_plugin.node.add_dependency(nodegroup)

        # 6. Create the 'nim' namespace
        nim_namespace = cluster.add_manifest(
            "NimNamespace",
            {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "nim"}},
        )

        # 7. Create NGC API Secret (for env injection)
        api_secret = cluster.add_manifest(
            "NgcApiSecret",
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "ngc-api", "namespace": "nim"},
                "type": "Opaque",
                "stringData": {"NGC_API_KEY": nvidia_key},
            },
        )
        api_secret.node.add_dependency(nim_namespace)

        # 8. Create Docker Registry Secret (using stringData - no double base64!)
        registry_secret = cluster.add_manifest(
            "RegistrySecret",
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "registry-secret", "namespace": "nim"},
                "type": "kubernetes.io/dockerconfigjson",
                "stringData": {
                    ".dockerconfigjson": json.dumps(
                        {
                            "auths": {
                                "nvcr.io": {
                                    "username": "$oauthtoken",
                                    "password": nvidia_key,
                                    "email": nvidia_email,
                                }
                            }
                        }
                    )
                },
            },
        )
        registry_secret.node.add_dependency(nim_namespace)

        # 9. Generator (8B) Deployment
        app_label_gen = {"app": "nim-generator"}
        gen_deployment = cluster.add_manifest(
            "GeneratorDeployment",
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "nim-generator",  # ✅ Valid name (no colon or special chars)
                    "namespace": "nim",
                },
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
                                    "image": "nvcr.io/nvidia/nim/llama-3.1-nemotron-nano-8b-v1:latest",
                                    "ports": [{"containerPort": 8000}],
                                    "resources": {"limits": {"nvidia.com/gpu": "1"}},
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
                                    "readinessProbe": {
                                        "httpGet": {"path": "/health", "port": 8000},
                                        "initialDelaySeconds": 30,
                                        "periodSeconds": 10,
                                    },
                                }
                            ],
                        },
                    },
                },
            },
        )
        gen_deployment.node.add_dependency(
            nodegroup, registry_secret, api_secret, nvidia_plugin
        )

        # 10. Embedder (E5) Deployment
        app_label_embed = {"app": "nim-embedder"}
        embed_deployment = cluster.add_manifest(
            "EmbedderDeployment",
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "nim-embedder",  # ✅ Valid name
                    "namespace": "nim",
                },
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": app_label_embed},
                    "template": {
                        "metadata": {"labels": app_label_embed},
                        "spec": {
                            "imagePullSecrets": [{"name": "registry-secret"}],
                            "containers": [
                                {
                                    "name": "nim-embedder",
                                    "image": "nvcr.io/nvidia/nim/llama-3.2-nv-embedqa-1b-v2:latest",  # ✅ Correct path
                                    "ports": [{"containerPort": 8000}],
                                    "resources": {"limits": {"nvidia.com/gpu": "1"}},
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
                                    "readinessProbe": {
                                        "httpGet": {"path": "/health", "port": 8000},
                                        "initialDelaySeconds": 30,
                                        "periodSeconds": 10,
                                    },
                                }
                            ],
                        },
                    },
                },
            },
        )
        embed_deployment.node.add_dependency(
            nodegroup, registry_secret, api_secret, nvidia_plugin
        )

        # 11. LoadBalancer Services
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

        # 12. Outputs
        gen_lb_url = cluster.get_service_load_balancer_address(
            "nim-generator-lb", namespace="nim"
        )
        embed_lb_url = cluster.get_service_load_balancer_address(
            "nim-embedder-lb", namespace="nim"
        )
        CfnOutput(self, "GenerateEndpoint", value=f"http://{gen_lb_url}")
        CfnOutput(self, "EmbedEndpoint", value=f"http://{embed_lb_url}")
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)
