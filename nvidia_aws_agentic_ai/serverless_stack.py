from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_sqs as sqs,
    # SQS is no longer needed for this model
    # aws_sqs as sqs,
    aws_s3_notifications as s3n,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct
import os


class ServerlessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========================================
        # S3 BUCKETS
        # ========================================

        raw_bucket = s3.Bucket(
            self,
            "RawDocumentsBucket",
            bucket_name=f"raw-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        verified_bucket = s3.Bucket(
            self,
            "VerifiedDocumentsBucket",
            bucket_name=f"verified-documents-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        kg_bucket = s3.Bucket(
            self,
            "KnowledgeGraphBucket",
            bucket_name=f"knowledge-graph-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ========================================
        # DYNAMODB TABLES
        # ========================================

        jobs_table = dynamodb.Table(
            self,
            "DocumentJobsTable",
            table_name="DocumentJobs",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        sentences_table = dynamodb.Table(
            self,
            "SentencesTable",
            table_name="Sentences",
            partition_key=dynamodb.Attribute(
                name="sentence_hash", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        sentences_table.add_global_secondary_index(
            index_name="ByJobId",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sentence_hash", type=dynamodb.AttributeType.STRING
            ),
        )

        llm_log_table = dynamodb.Table(
            self,
            "LLMCallLogTable",
            table_name="LLMCallLog",
            partition_key=dynamodb.Attribute(
                name="call_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        llm_log_table.add_global_secondary_index(
            index_name="ByJobId",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
        )
        llm_log_table.add_global_secondary_index(
            index_name="BySentenceHash",
            partition_key=dynamodb.Attribute(
                name="sentence_hash", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
        )

        llm_extracts_table = dynamodb.Table(
            self,
            "LLMCallExtractsTable",
            table_name="LLMCallExtracts",
            partition_key=dynamodb.Attribute(
                name="call_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        llm_extracts_table.add_global_secondary_index(
            index_name="BySentenceHash",
            partition_key=dynamodb.Attribute(
                name="sentence_hash", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
        )

        llm_extracts_table.add_global_secondary_index(
            index_name="ByJobId",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
        )

        # ========================================
        # LAMBDA LAYERS
        # ========================================
        
        # Requests library layer for LLM/Embedding calls
        requests_layer = _lambda.LayerVersion(
            self,
            "RequestsLayer",
            code=_lambda.Code.from_asset("lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Requests library for HTTP calls to NVIDIA NIM"
        )

        # ========================================
        # LAMBDA FUNCTIONS
        # ========================================

        # L1: Upload Handler (API -> S3 Pre-signed URL)
        upload_handler = _lambda.Function(
            self,
            "UploadHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l1_upload_handler")
            ),
            timeout=Duration.minutes(1),  # Should be fast
            memory_size=512,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
        )

        # L2: Validate Document (S3 Trigger -> L3)
        validate_doc = _lambda.Function(
            self,
            "ValidateDoc",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l2_validate_doc")
            ),
            timeout=Duration.minutes(15),  # For iterative verification
            memory_size=1024,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
        )

        # L3: Sanitize Document (L2 -> SFN) <<< NEW LAMBDA
        sanitize_doc = _lambda.Function(
            self,
            "SanitizeDoc",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            # <<< YOU MUST CREATE THIS FOLDER AND FILE
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l3_sanitize_doc")
            ),
            timeout=Duration.minutes(15),  # For iterative sanitization
            memory_size=1024,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
                "VERIFIED_BUCKET": verified_bucket.bucket_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                # STATE_MACHINE_ARN and LLM_CALL_LAMBDA_NAME added later
            },
        )

        # Grant L2 permission to invoke L3
        validate_doc.add_environment("SANITIZE_LAMBDA_NAME", sanitize_doc.function_name)
        sanitize_doc.grant_invoke(validate_doc)

        # L4: List All Docs (API)
        list_all_docs = _lambda.Function(
            self,
            "ListAllDocs",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l4_list_all_docs")
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={"JOBS_TABLE": jobs_table.table_name},
        )

        # Manual Trigger (Bypass S3 trigger issues)
        manual_trigger = _lambda.Function(
            self,
            "ManualTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l1_manual_trigger")
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
        )

        # NOTE: L3_UpdateDocStatus is now renamed L_UpdateDocStatus
        # This function is used by the API to GET status, not part of the main flow
        update_doc_status_api = _lambda.Function(
            self,
            "UpdateDocStatusApi",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l3_update_doc_status")
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "LLM_LOG_TABLE": llm_log_table.table_name,
            },
        )

        # L5/L6 are no longer needed, SFN handles sentence status
        # update_sentence_status = ...
        # dedup_sentence = ...

        # L7: LLM Call (Used by SFN)
        llm_call = _lambda.Function(
            self,
            "LLMCall",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "llm_gateway", "l7_llm_call")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            reserved_concurrent_executions=3,  # Reserve 3 for LLM calls
            layers=[requests_layer],
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "LLM_CALL_PARSED_TABLE": llm_extracts_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "GENERATE_ENDPOINT": os.environ.get("APP_GENERATE_ENDPOINT_URL", ""),
            },
        )

        # L8: Embedding Call (Used by SFN)
        embedding_call = _lambda.Function(
            self,
            "EmbeddingCall",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "llm_gateway", "l8_embedding_call")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            layers=[requests_layer],
            environment={
                "KG_BUCKET": kg_bucket.bucket_name,
                "EMBED_ENDPOINT": os.environ.get("APP_EMBED_ENDPOINT_URL", ""),
            },
        )

        # L8 (SFN Helper): Get Sentences <<< NEW LAMBDA
        get_sentences_from_s3 = _lambda.Function(
            self,
            "GetSentencesFromS3",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            # <<< YOU MUST CREATE THIS FOLDER AND FILE
            code=_lambda.Code.from_asset(
                os.path.join(
                    "src", "lambda_src", "job_mgmt", "l8_get_sentences_from_s3"
                )
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "VERIFIED_BUCKET": verified_bucket.bucket_name,
                "SENTENCES_TABLE": sentences_table.table_name,
            },
        )

        # L5: Check Dedup (The Fix Logic)
        l5_check_dedup = _lambda.Function(
            self,
            "CheckDedupTask",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l5_check_dedup")
            ),
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "SENTENCES_TABLE": sentences_table.table_name
            },
        )

        # L24: Score Extractions (GSSR Scorer) - Must be defined before L9-L11
        score_extractions = _lambda.Function(
            self,
            "ScoreExtractions",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l24_score_extractions")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "KG_BUCKET": kg_bucket.bucket_name,
                "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
            },
        )

        # L9-L16: KG Agent & Graph Ops Functions (All used by SFN)
        extract_entities = _lambda.Function(
            self,
            "ExtractEntities",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l9_extract_entities")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
                "SCORER_LAMBDA_NAME": score_extractions.function_name,
            },
        )
        extract_kriya = _lambda.Function(
            self,
            "ExtractKriya",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l10_extract_kriya")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
                "SCORER_LAMBDA_NAME": score_extractions.function_name,
            },
        )
        build_events = _lambda.Function(
            self,
            "BuildEvents",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l11_build_events")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
                "SCORER_LAMBDA_NAME": score_extractions.function_name,
            },
        )
        audit_events = _lambda.Function(
            self,
            "AuditEvents",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l12_audit_events")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
            },
        )
        extract_relations = _lambda.Function(
            self,
            "ExtractRelations",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l13_extract_relations")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
            },
        )
        extract_attributes = _lambda.Function(
            self,
            "ExtractAttributes",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "kg_agents", "l14_extract_attributes")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
            },
        )
        graph_node_ops = _lambda.Function(
            self,
            "GraphNodeOps",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "graph_ops", "l15_graph_node_ops")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            layers=[requests_layer],
            environment={"KG_BUCKET": kg_bucket.bucket_name},
        )
        graph_edge_ops = _lambda.Function(
            self,
            "GraphEdgeOps",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "graph_ops", "l16_graph_edge_ops")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            layers=[requests_layer],
            environment={
                "KG_BUCKET": kg_bucket.bucket_name,
                "SENTENCES_TABLE": sentences_table.table_name
            },
        )

        # L17-L18: RAG Functions (API)
        retrieve_from_embedding = _lambda.Function(
            self,
            "RetrieveFromEmbedding",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "rag", "l17_retrieve_from_embedding")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            reserved_concurrent_executions=2,  # As per your budget
            environment={"KG_BUCKET": kg_bucket.bucket_name},
        )
        synthesize_answer = _lambda.Function(
            self,
            "SynthesizeAnswer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "rag", "l18_synthesize_answer")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            reserved_concurrent_executions=2,  # As per your budget
            environment={
                "RETRIEVE_LAMBDA": retrieve_from_embedding.function_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "LLM_LOG_TABLE": llm_log_table.table_name,
                "SENTENCES_TABLE": sentences_table.table_name,
            },
        )

        # Query API - Submit and Status
        query_processor = _lambda.Function(
            self,
            "QueryProcessor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "rag", "l23_query_processor")
            ),
            timeout=Duration.minutes(5),
            memory_size=1024,
            layers=[requests_layer],
            environment={
                "KG_BUCKET": kg_bucket.bucket_name,
                "QUERIES_TABLE": "Queries",
                "SENTENCES_TABLE": sentences_table.table_name,
                "LLM_CALL_LAMBDA_NAME": llm_call.function_name,
                "RETRIEVE_LAMBDA": retrieve_from_embedding.function_name,
                "EMBED_ENDPOINT": os.environ.get("APP_EMBED_ENDPOINT_URL", ""),
            },
        )

        query_submit = _lambda.Function(
            self,
            "QuerySubmit",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "api_tools", "l21_query_submit")
            ),
            timeout=Duration.seconds(30),
            environment={
                "QUERIES_TABLE": "Queries",
                "QUERY_PROCESSOR_LAMBDA": query_processor.function_name,
            },
        )

        query_status = _lambda.Function(
            self,
            "QueryStatus",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "api_tools", "l22_query_status")
            ),
            timeout=Duration.seconds(30),
            environment={
                "QUERIES_TABLE": "Queries",
            },
        )

        # L19-L20: API Observability Tools
        get_processing_chain = _lambda.Function(
            self,
            "GetProcessingChain",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join(
                    "src", "lambda_src", "api_tools", "l19_get_processing_chain"
                )
            ),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={"LLM_LOG_TABLE": llm_log_table.table_name},
        )
        get_sentence_chain = _lambda.Function(
            self,
            "GetSentenceChain",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "api_tools", "l20_get_sentence_chain")
            ),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={"LLM_LOG_TABLE": llm_log_table.table_name},
        )

        # ========================================
        # IAM PERMISSIONS
        # ========================================

        s3_permissions = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
            ],
            resources=[
                raw_bucket.bucket_arn,
                raw_bucket.bucket_arn + "/*",
                verified_bucket.bucket_arn,
                verified_bucket.bucket_arn + "/*",
                kg_bucket.bucket_arn,
                kg_bucket.bucket_arn + "/*",
            ],
        )
        dynamodb_permissions = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:DeleteItem",
            ],
            resources=[
                jobs_table.table_arn,
                jobs_table.table_arn + "/index/*",
                sentences_table.table_arn,
                sentences_table.table_arn + "/index/*",
                llm_log_table.table_arn,
                llm_log_table.table_arn + "/index/*",
                llm_extracts_table.table_arn,
                llm_extracts_table.table_arn + "/index/*",
            ],
        )
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0",
            ],
        )

        # Collect ALL Lambdas
        all_functions = [
            upload_handler,
            validate_doc,
            sanitize_doc,
            list_all_docs,
            manual_trigger,
            update_doc_status_api,
            llm_call,
            embedding_call,
            get_sentences_from_s3,
            l5_check_dedup,
            extract_entities,
            extract_kriya,
            build_events,
            audit_events,
            extract_relations,
            extract_attributes,
            graph_node_ops,
            graph_edge_ops,
            score_extractions,
            retrieve_from_embedding,
            synthesize_answer,
            get_processing_chain,
            get_sentence_chain,
        ]

        # Apply common permissions
        for func in all_functions:
            func.add_to_role_policy(s3_permissions)
            func.add_to_role_policy(dynamodb_permissions)

        # Add Bedrock permissions only to LLM and embedding functions
        llm_call.add_to_role_policy(bedrock_policy)
        embedding_call.add_to_role_policy(bedrock_policy)

        # Grant L18 permission to invoke L17
        retrieve_from_embedding.grant_invoke(synthesize_answer)
        
        # Grant agent Lambdas permission to invoke L7 (LLM Call)
        llm_call.grant_invoke(extract_entities)
        llm_call.grant_invoke(extract_kriya)
        llm_call.grant_invoke(build_events)
        llm_call.grant_invoke(audit_events)
        llm_call.grant_invoke(extract_relations)
        llm_call.grant_invoke(extract_attributes)
        llm_call.grant_invoke(validate_doc)
        llm_call.grant_invoke(sanitize_doc)
        llm_call.grant_invoke(synthesize_answer)
        llm_call.grant_invoke(query_processor)
        llm_call.grant_invoke(score_extractions)
        
        # Grant extraction Lambdas permission to invoke L24 (Scorer)
        score_extractions.grant_invoke(extract_entities)
        score_extractions.grant_invoke(extract_kriya)
        score_extractions.grant_invoke(build_events)

        # Query API permissions
        query_processor.grant_invoke(query_submit)
        retrieve_from_embedding.grant_invoke(query_processor)
        kg_bucket.grant_read(query_processor)
        sentences_table.grant_read_data(query_processor)
        
        # Grant DynamoDB permissions for Queries table
        query_submit.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"],
            resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/Queries"]
        ))
        query_status.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem"],
            resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/Queries"]
        ))
        query_processor.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Scan"],
            resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/Queries"]
        ))
        
        # Add LLM function name to agent environments
        for agent_func in [extract_entities, extract_kriya, build_events, audit_events, 
                          extract_relations, extract_attributes, validate_doc, 
                          sanitize_doc, synthesize_answer, score_extractions]:
            agent_func.add_environment("LLM_CALL_LAMBDA_NAME", llm_call.function_name)
        
        # Add scorer function name to extraction agent environments
        for agent_func in [extract_entities, extract_kriya, build_events]:
            agent_func.add_environment("SCORER_LAMBDA_NAME", score_extractions.function_name)
        
        # Grant manual trigger permission to invoke L3
        manual_trigger.add_environment("SANITIZE_LAMBDA_NAME", sanitize_doc.function_name)
        sanitize_doc.grant_invoke(manual_trigger)

        # ========================================
        # S3 TRIGGERS
        # ========================================

        # S3 PUT to raw_bucket triggers L2_ValidateDoc
        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(validate_doc),
            s3.NotificationKeyFilter(suffix=".txt"),
        )

        # ========================================
        # SQS TRIGGERS (None)
        # ========================================

        # ========================================
        # STEP FUNCTIONS STATE MACHINE
        # ========================================

        # <<< NEW SFN DEFINITION: "PER-DOCUMENT" WORKFLOW <<<

        # SFN Step 1: Get array of sentences from S3
        get_sentences_task = tasks.LambdaInvoke(
            self,
            "GetSentencesTask",
            lambda_function=get_sentences_from_s3,
            payload_response_only=True,
            result_path="$.sentence_data",  # Puts output at {"sentence_data": {"sentences": [...]}}
        )

        # SFN Step 2: KG extraction - Sequential with GSSR retry
        # Entities first
        entities_task = tasks.LambdaInvoke(
            self,
            "EntitiesTask",
            lambda_function=extract_entities,
            payload_response_only=True,
        )
        
        # Check if D1 needs retry
        check_d1_retry = sfn.Choice(self, "CheckD1Retry")
        check_d1_retry.when(
            sfn.Condition.and_(
                sfn.Condition.is_present("$.status"),
                sfn.Condition.string_equals("$.status", "retry")
            ),
            entities_task  # Loop back to entities
        )

        # Kriya second
        kriya_task = tasks.LambdaInvoke(
            self, "KriyaTask", 
            lambda_function=extract_kriya, 
            payload_response_only=True,
        )
        
        # Check if D2a needs retry
        check_d2a_retry = sfn.Choice(self, "CheckD2aRetry")
        check_d2a_retry.when(
            sfn.Condition.and_(
                sfn.Condition.is_present("$.status"),
                sfn.Condition.string_equals("$.status", "retry")
            ),
            kriya_task  # Loop back to kriya
        )
        
        # Embedding third
        embedding_task = tasks.LambdaInvoke(
            self, "EmbeddingTask",
            lambda_function=embedding_call,
            payload_response_only=True,
            result_path=sfn.JsonPath.DISCARD,
        )

        # Build events fourth
        build_events_task = tasks.LambdaInvoke(
            self,
            "BuildEventsTask",
            lambda_function=build_events,
            payload_response_only=True,
        )
        
        # Check if D2b needs retry
        check_d2b_retry = sfn.Choice(self, "CheckD2bRetry")
        check_d2b_retry.when(
            sfn.Condition.and_(
                sfn.Condition.is_present("$.status"),
                sfn.Condition.string_equals("$.status", "retry")
            ),
            build_events_task  # Loop back to build events
        )

        # Extract relations from events
        relations_task = tasks.LambdaInvoke(
            self,
            "RelationsTask",
            lambda_function=extract_relations,
            payload_response_only=True,
            result_path=sfn.JsonPath.DISCARD,
        )

        # Store nodes and edges in NetworkX
        graph_node_task = tasks.LambdaInvoke(
            self,
            "GraphNodeTask",
            lambda_function=graph_node_ops,
            payload_response_only=True,
            result_path=sfn.JsonPath.DISCARD,
        )
        graph_edge_task = tasks.LambdaInvoke(
            self,
            "GraphEdgeTask",
            lambda_function=graph_edge_ops,
            payload_response_only=True,
            result_path=sfn.JsonPath.DISCARD,
        )

        # Chain: Sequential processing with retry logic
        # D1 -> Check retry -> D2a -> Check retry -> Embedding -> D2b -> Check retry -> Relations -> Graph
        entities_task.next(check_d1_retry)
        check_d1_retry.otherwise(kriya_task)

        kriya_task.next(check_d2a_retry)
        check_d2a_retry.otherwise(embedding_task)

        embedding_task.next(build_events_task)
        build_events_task.next(check_d2b_retry)
        check_d2b_retry.otherwise(relations_task)

        relations_task.next(graph_node_task)
        graph_node_task.next(graph_edge_task)

        sentence_processing_flow = entities_task

        # SFN Step 3: Create the Map state to run the sub-workflow
        process_all_sentences_map = sfn.Map(
            self,
            "ProcessAllSentencesMap",
            items_path=sfn.JsonPath.string_at("$.sentence_data.sentences"),
            max_concurrency=1,  # MUST BE 1. This map processes 1 sentence, which spawns ~6 parallel agents. max_concurrency > 1 will overload l7_llm_call (limit 3).
            result_path="$.map_results",
        ).iterator(sentence_processing_flow)

        # Add final task to mark job as completed
        mark_complete_task = tasks.LambdaInvoke(
            self,
            "MarkJobCompleteTask",
            lambda_function=update_doc_status_api,
            payload=sfn.TaskInput.from_object({
                "job_id": sfn.JsonPath.string_at("$.job_id"),
                "action": "mark_complete"
            }),
            result_path=sfn.JsonPath.DISCARD,
        )

        # Final SFN Definition: Chain Step 1 -> Step 3 -> Mark Complete
        definition = get_sentences_task.next(process_all_sentences_map).next(mark_complete_task)

        state_machine = sfn.StateMachine(
            self,
            "KarakaKGProcessing",
            # <<< FIX 2: 'definition' is deprecated, use 'definition_body'
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            state_machine_name="KarakaKGProcessing",
        )

        # === Grant L3 (SanitizeDoc) permission to start the SFN ===
        state_machine.grant_start_execution(sanitize_doc)
        sanitize_doc.add_environment(
            "STATE_MACHINE_ARN", state_machine.state_machine_arn
        )

        # ========================================
        # API GATEWAY
        # ========================================

        api = apigw.RestApi(
            self,
            "KarakaKGApi",
            rest_api_name="KarakaKG Service",
            description="API for knowledge graph processing and observability",
        )

        # POST /upload
        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST", apigw.LambdaIntegration(upload_handler))

        # GET /status/{job_id}
        status_resource = api.root.add_resource("status")
        job_id_resource = status_resource.add_resource("{job_id}")
        job_id_resource.add_method(
            "GET", apigw.LambdaIntegration(update_doc_status_api)
        )  # Use the renamed L_UpdateDocStatus

        # POST /query
        query_resource = api.root.add_resource("query")
        query_resource.add_method("POST", apigw.LambdaIntegration(synthesize_answer))

        # POST /query/submit
        query_submit_resource = query_resource.add_resource("submit")
        query_submit_resource.add_method("POST", apigw.LambdaIntegration(query_submit))

        # GET /query/status/{query_id}
        query_status_resource = query_resource.add_resource("status")
        query_id_resource = query_status_resource.add_resource("{query_id}")
        query_id_resource.add_method("GET", apigw.LambdaIntegration(query_status))

        # GET /processing-chain/{doc_id}
        chain_resource = api.root.add_resource("processing-chain")
        doc_chain_resource = chain_resource.add_resource("{doc_id}")
        doc_chain_resource.add_method(
            "GET", apigw.LambdaIntegration(get_processing_chain)
        )

        # GET /sentence-chain/{sentence_hash}
        sentence_chain_resource = api.root.add_resource("sentence-chain")
        sentence_hash_resource = sentence_chain_resource.add_resource("{sentence_hash}")
        sentence_hash_resource.add_method(
            "GET", apigw.LambdaIntegration(get_sentence_chain)
        )

        # GET /docs
        api.root.add_resource("docs").add_method(
            "GET", apigw.LambdaIntegration(list_all_docs)
        )

        # POST /trigger/{job_id} - Manual trigger for processing
        trigger_resource = api.root.add_resource("trigger")
        trigger_job_resource = trigger_resource.add_resource("{job_id}")
        trigger_job_resource.add_method(
            "POST", apigw.LambdaIntegration(manual_trigger)
        )

        # ========================================
        # OUTPUTS
        # ========================================

        # 'self.add_outputs' is removed in CDK v2. Use CfnOutput instead.
        CfnOutput(self, "RawBucket", value=raw_bucket.bucket_name)
        CfnOutput(self, "VerifiedBucket", value=verified_bucket.bucket_name)
        CfnOutput(self, "KGBucket", value=kg_bucket.bucket_name)
        CfnOutput(self, "JobsTable", value=jobs_table.table_name)
        CfnOutput(self, "SentencesTableNameOutput", value=sentences_table.table_name)
        CfnOutput(self, "LLMCallLogTableOutput", value=llm_log_table.table_name)
        CfnOutput(self, "LLMCallExtractsTableOutput", value=llm_extracts_table.table_name)
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
