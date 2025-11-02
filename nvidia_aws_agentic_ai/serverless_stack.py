from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_sqs as sqs,
    aws_s3_notifications as s3n,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Duration,
    RemovalPolicy,
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

        # GSI: ByJobId (For getting all sentences in a document)
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

        # GSI 1: ByJobId (For chronological document flow/count)
        llm_log_table.add_global_secondary_index(
            index_name="ByJobId",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
        )

        # CRITICAL FIX/FEATURE: GSI 2: BySentenceHash (For sentence-level observability/RAG counts)
        llm_log_table.add_global_secondary_index(
            index_name="BySentenceHash",
            partition_key=dynamodb.Attribute(
                name="sentence_hash", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
        )

        # ========================================
        # SQS QUEUES (Standard SQS for maximum parallelism)
        # ========================================

        kg_tasks_dlq = sqs.Queue(
            self,
            "KGTasksDLQ",
            queue_name="kg-tasks-dlq",
            visibility_timeout=Duration.minutes(15),
        )

        kg_tasks_queue = sqs.Queue(
            self,
            "KGTasksQueue",
            queue_name="kg-tasks-queue",
            visibility_timeout=Duration.minutes(15),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3, queue=kg_tasks_dlq
            ),
        )

        # ========================================
        # LAMBDA FUNCTIONS (L1 - L18)
        # ========================================

        # Job Management Functions (l1-l4)
        upload_handler = _lambda.Function(
            self,
            "UploadHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l1_upload_handler")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
        )

        # NOTE: This Lambda must now populate 'preview_text' and 'processed_s3_path' in DocumentJobs
        validate_doc = _lambda.Function(
            self,
            "ValidateDoc",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l2_validate_doc")
            ),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name,
            },
        )

        # NOTE: This Lambda must query LLMCallLog for aggregated status data
        update_doc_status = _lambda.Function(
            self,
            "UpdateDocStatus",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l3_update_doc_status")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "JOBS_TABLE": jobs_table.table_name,
                "LLM_LOG_TABLE": llm_log_table.table_name,
            },
        )

        # NOTE: This Lambda must implement cursor-based pagination
        list_all_docs = _lambda.Function(
            self,
            "ListAllDocs",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "job_mgmt", "l4_list_all_docs")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={"JOBS_TABLE": jobs_table.table_name},
        )

        # Sentence Management Functions (l5-l6)
        update_sentence_status = _lambda.Function(
            self,
            "UpdateSentenceStatus",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join(
                    "src", "lambda_src", "sentence_mgmt", "l5_update_sentence_status"
                )
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={"SENTENCES_TABLE": sentences_table.table_name},
        )

        dedup_sentence = _lambda.Function(
            self,
            "DedupSentence",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset(
                os.path.join("src", "lambda_src", "sentence_mgmt", "l6_dedup_sentence")
            ),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "SENTENCES_TABLE": sentences_table.table_name,
                "KG_QUEUE_URL": kg_tasks_queue.queue_url,
            },
        )

        # LLM Gateway Functions (l7-l8)
        # NOTE: This Lambda must log start_time, end_time (or latency_ms), model, and prompt_template
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
            reserved_concurrent_executions=3,
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
            },
        )

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
            environment={"KG_BUCKET": kg_bucket.bucket_name},
        )

        # KG Agent Functions (l9-l14)
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

        # Graph Operations Functions (l15-l16)
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
            environment={"KG_BUCKET": kg_bucket.bucket_name},
        )

        # RAG Functions (l17-l18)
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
            reserved_concurrent_executions=2,
            environment={"KG_BUCKET": kg_bucket.bucket_name},
        )

        # NOTE: This Lambda must enrich the response with structured references (requires LLMCallLog GSI)
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
            environment={
                "RETRIEVE_LAMBDA": retrieve_from_embedding.function_name,
                "KG_BUCKET": kg_bucket.bucket_name,
                "LLM_LOG_TABLE": llm_log_table.table_name,  # Required for number_llm_calls
                "SENTENCES_TABLE": sentences_table.table_name,  # Required for sentence text/metadata
            },
        )

        # New API Tools for Observability (l19 - l20)

        # NEW: Document Processing Chain (L19)
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

        # NEW: Sentence Processing Chain (L20)
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
        # IAM PERMISSIONS (HACKATHON CONCESSION: Broad IAM for speed)
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

        # NOTE: Permissions updated to cover GSI access for new Lambdas
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
            ],
        )

        sqs_permissions = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "sqs:SendMessage",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl",
            ],
            resources=[kg_tasks_queue.queue_arn, kg_tasks_dlq.queue_arn],
        )

        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0",
            ],
        )

        # COLLECT ALL 20 FUNCTIONS
        all_functions = [
            upload_handler,
            validate_doc,
            update_doc_status,
            list_all_docs,
            update_sentence_status,
            dedup_sentence,
            llm_call,
            embedding_call,
            extract_entities,
            extract_kriya,
            build_events,
            audit_events,
            extract_relations,
            extract_attributes,
            graph_node_ops,
            graph_edge_ops,
            retrieve_from_embedding,
            synthesize_answer,
            get_processing_chain,
            get_sentence_chain,  # NEW API TOOLS
        ]

        for func in all_functions:
            func.add_to_role_policy(s3_permissions)
            func.add_to_role_policy(dynamodb_permissions)

        dedup_sentence.add_to_role_policy(sqs_permissions)
        llm_call.add_to_role_policy(sqs_permissions)

        llm_call.add_to_role_policy(bedrock_policy)
        embedding_call.add_to_role_policy(bedrock_policy)

        retrieve_from_embedding.grant_invoke(synthesize_answer)

        # ========================================
        # S3 TRIGGERS
        # ========================================

        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(validate_doc),
            s3.NotificationKeyFilter(suffix=".txt"),
        )

        # ========================================
        # SQS TRIGGERS
        # ========================================

        llm_call.add_event_source(_lambda.SqsEventSource(kg_tasks_queue, batch_size=1))

        # ========================================
        # STEP FUNCTIONS STATE MACHINE
        # ========================================

        parallel_entities_kriya = sfn.Parallel(self, "ParallelEntitiesKriya")

        entities_task = tasks.LambdaInvoke(
            self,
            "EntitiesTask",
            lambda_function=extract_entities,
            payload_response_only=True,
        )
        kriya_task = tasks.LambdaInvoke(
            self, "KriyaTask", lambda_function=extract_kriya, payload_response_only=True
        )

        parallel_entities_kriya.branch(entities_task)
        parallel_entities_kriya.branch(kriya_task)

        build_events_task = tasks.LambdaInvoke(
            self,
            "BuildEventsTask",
            lambda_function=build_events,
            payload_response_only=True,
        )
        audit_events_task = tasks.LambdaInvoke(
            self,
            "AuditEventsTask",
            lambda_function=audit_events,
            payload_response_only=True,
        )

        parallel_relations_attributes = sfn.Parallel(
            self, "ParallelRelationsAttributes"
        )

        relations_task = tasks.LambdaInvoke(
            self,
            "RelationsTask",
            lambda_function=extract_relations,
            payload_response_only=True,
        )
        attributes_task = tasks.LambdaInvoke(
            self,
            "AttributesTask",
            lambda_function=extract_attributes,
            payload_response_only=True,
        )

        parallel_relations_attributes.branch(relations_task)
        parallel_relations_attributes.branch(attributes_task)

        graph_node_task = tasks.LambdaInvoke(
            self,
            "GraphNodeTask",
            lambda_function=graph_node_ops,
            payload_response_only=True,
        )
        graph_edge_task = tasks.LambdaInvoke(
            self,
            "GraphEdgeTask",
            lambda_function=graph_edge_ops,
            payload_response_only=True,
        )

        definition = (
            parallel_entities_kriya.next(build_events_task)
            .next(audit_events_task)
            .next(parallel_relations_attributes)
            .next(
                sfn.Parallel(self, "GraphOps")
                .branch(graph_node_task)
                .branch(graph_edge_task)
            )
        )

        state_machine = sfn.StateMachine(
            self,
            "KarakaKGProcessing",
            definition=definition,
            state_machine_name="KarakaKGProcessing",
        )

        # ========================================
        # API GATEWAY (NEW OBSERVABILITY ENDPOINTS)
        # ========================================

        api = apigw.RestApi(
            self,
            "KarakaKGApi",
            rest_api_name="KarakaKG Service",
            description="API for knowledge graph processing and observability",
        )

        # Doc Upload
        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST", apigw.LambdaIntegration(upload_handler))

        # Doc Status Read (Aggregated Status)
        status_resource = api.root.add_resource("status")
        job_id_resource = status_resource.add_resource("{job_id}")
        job_id_resource.add_method("GET", apigw.LambdaIntegration(update_doc_status))

        # Query Endpoint (RAG)
        query_resource = api.root.add_resource("query")
        query_resource.add_method("POST", apigw.LambdaIntegration(synthesize_answer))

        # NEW: Document Processing Chain (L19)
        chain_resource = api.root.add_resource("processing-chain")
        doc_chain_resource = chain_resource.add_resource("{doc_id}")
        doc_chain_resource.add_method(
            "GET", apigw.LambdaIntegration(get_processing_chain)
        )

        # NEW: Sentence Processing Chain (L20)
        sentence_chain_resource = api.root.add_resource("sentence-chain")
        sentence_hash_resource = sentence_chain_resource.add_resource("{sentence_hash}")
        sentence_hash_resource.add_method(
            "GET", apigw.LambdaIntegration(get_sentence_chain)
        )

        # Doc Listing (L4)
        api.root.add_resource("docs").add_method(
            "GET", apigw.LambdaIntegration(list_all_docs)
        )

        # ========================================
        # OUTPUTS
        # ========================================

        self.add_outputs(
            {
                "RawBucket": raw_bucket.bucket_name,
                "VerifiedBucket": verified_bucket.bucket_name,
                "KGBucket": kg_bucket.bucket_name,
                "JobsTable": jobs_table.table_name,
                "SentencesTable": sentences_table.table_name,
                "LLMCallLogTable": llm_log_table.table_name,
                "KGQueueUrl": kg_tasks_queue.queue_url,
                "ApiUrl": api.url,
                "StateMachineArn": state_machine.state_machine_arn,
            }
        )
