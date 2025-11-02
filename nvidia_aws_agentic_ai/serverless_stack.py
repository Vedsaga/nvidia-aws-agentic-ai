from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigw,
    # SQS is no longer needed for this model
    # aws_sqs as sqs,
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
                # STATE_MACHINE_ARN added later
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
            environment={
                "LLM_CALL_LOG_TABLE": llm_log_table.table_name,
                "JOBS_TABLE": jobs_table.table_name,
                "SENTENCES_TABLE": sentences_table.table_name,
                "KG_BUCKET": kg_bucket.bucket_name,
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
            environment={"KG_BUCKET": kg_bucket.bucket_name},
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
            update_doc_status_api,
            llm_call,
            embedding_call,
            get_sentences_from_s3,
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
            get_sentence_chain,
        ]

        # Apply common permissions
        for func in all_functions:
            func.add_to_role_policy(s3_permissions)
            func.add_to_role_policy(dynamodb_permissions)

        # Add Bedrock permissions to functions that need it
        llm_call.add_to_role_policy(bedrock_policy)
        embedding_call.add_to_role_policy(bedrock_policy)
        # Add Bedrock for L2 (Validate) and L3 (Sanitize)
        validate_doc.add_to_role_policy(bedrock_policy)
        sanitize_doc.add_to_role_policy(bedrock_policy)
        # Add Bedrock for KG agent functions
        extract_entities.add_to_role_policy(bedrock_policy)
        extract_kriya.add_to_role_policy(bedrock_policy)
        build_events.add_to_role_policy(bedrock_policy)
        audit_events.add_to_role_policy(bedrock_policy)
        extract_relations.add_to_role_policy(bedrock_policy)
        extract_attributes.add_to_role_policy(bedrock_policy)
        # Add Bedrock for RAG
        synthesize_answer.add_to_role_policy(bedrock_policy)

        # Grant L18 permission to invoke L17
        retrieve_from_embedding.grant_invoke(synthesize_answer)

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

        # SFN Step 2: Define the sub-workflow for ONE sentence
        # This is your original SFN definition, now inside a Map state
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
        parallel_entities_kriya.branch(entities_task).branch(kriya_task)

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
        parallel_relations_attributes.branch(relations_task).branch(attributes_task)

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

        # Chain the sub-workflow together
        sentence_processing_flow = (
            parallel_entities_kriya.next(build_events_task)
            .next(audit_events_task)
            .next(parallel_relations_attributes)
            .next(
                sfn.Parallel(self, "GraphOps")
                .branch(graph_node_task)
                .branch(graph_edge_task)
            )
        )

        # SFN Step 3: Create the Map state to run the sub-workflow
        process_all_sentences_map = sfn.Map(
            self,
            "ProcessAllSentencesMap",
            items_path=sfn.JsonPath.string_at("$.sentence_data.sentences"),
            # <<< THIS SOLVES YOUR THROTTLING PROBLEM
            max_concurrency=2,
            result_path="$.map_results",  # Discard results
        )
        process_all_sentences_map.iterator(sentence_processing_flow)

        # Final SFN Definition: Chain Step 1 and Step 3
        definition = get_sentences_task.next(process_all_sentences_map)

        state_machine = sfn.StateMachine(
            self,
            "KarakaKGProcessing",
            definition=definition,
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
            "GET", apagw.LambdaIntegration(list_all_docs)
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
                "ApiUrl": api.url,
                "StateMachineArn": state_machine.state_machine_arn,
            }
        )
