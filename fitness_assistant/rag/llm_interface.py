from qdrant_client import QdrantClient, models
from fitness_assistant.rag.settings import QdrantConfig, LlmConfig
from fitness_assistant.rag.helper import (
    display_rag_response,
    load_data,
    clean_data,
    create_document,
    format_vector_db_context,
)
from fitness_assistant.rag.logging_config import RAGLogger, configure_logging
from fitness_assistant.rag.validators import validate_user_input, validate_llm_response
from fitness_assistant.rag.monitoring import (
    get_metrics_collector,
    HallucinationDetector,
    RetrievalMetrics,
    GenerationMetrics,
)
from fitness_assistant.rag.user_preferences import (
    UserProfile,
    filter_exercises_by_profile,
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client.http.exceptions import ResponseHandlingException

from typing import Optional
import argparse
import time
import uuid
from rich.console import Console
from rich.prompt import Prompt

import logging
from typing import List, Any

# Configure structured logging
configure_logging(level=logging.INFO)


class LLMFlow:
    """
    Define langchain flow for LLM with validation and monitoring
    """

    def __init__(self, config: LlmConfig = LlmConfig()):
        self.llm_config = config
        self.llm = self._connect_to_llm()
        self.chain = self._build_chain()
        self.metrics_collector = get_metrics_collector()
        if not self.llm or not self.chain:
            raise ConnectionError(
                "Failed to initialize LLM or build the processing chain.."
            )

    def get_prompt_from_template(self):
        """
        Build prompt using prompt template
        """
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.llm_config.system_prompt),
                ("human", self.llm_config.human_prompt),
            ]
        )

    def _connect_to_llm(self) -> ChatGoogleGenerativeAI:
        """
        Instantiate llm connection using the chat google generative ai
        """
        return ChatGoogleGenerativeAI(
            api_key=self.llm_config.google_api_key,
            model=self.llm_config.model_name,
            temperature=self.llm_config.temperature,
            top_p=self.llm_config.top_p,
            top_k=self.llm_config.top_k,
            max_output_tokens=self.llm_config.max_output_tokens,
            safety_settings=self.llm_config.safety_settings,
        )

    def _build_chain(self):
        """
        Build llm chain
        """
        try:
            prompt = self.get_prompt_from_template()
            chain = prompt | self.llm
        except ValueError as val_err:
            logging.error(
                f"Could not build chain sucessfully. Ensure prompt follows expected template. error is {val_err}"
            )
        else:
            return chain
        return None

    def run(self, query: str, context: str, trace_id: str = ""):
        """
        Run the rag flow with validation and monitoring
        :params query - Query from the user
        :params  context- context retrived from vector db
        :params trace_id - Trace ID for request tracking
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        rag_logger = RAGLogger(trace_id)

        try:
            start_time = time.time()
            rag_logger.log_llm_call_start()

            response = self.chain.invoke({"question": query, "context": context})
            response_text = response.content

            response_time_ms = (time.time() - start_time) * 1000
            rag_logger.log_llm_call_complete(response_time_ms=response_time_ms)

            # Validate response
            validation_result = validate_llm_response(response_text)
            if validation_result["valid"]:
                rag_logger.log_response_sent(len(response_text))
                self.metrics_collector.record_generation(
                    GenerationMetrics(
                        response_time_ms=response_time_ms,
                        model_name=self.llm_config.model_name,
                    )
                )
            else:
                rag_logger.logger.warning(
                    f"Response validation failed: {validation_result['error']}"
                )

            return response_text

        except Exception as e:
            rag_logger.log_error(e, "LLM generation")
            self.metrics_collector.record_error(str(e))
            raise


class ManageVectorDb:
    """
    Manage qdrant Vector database with monitoring
    """

    def __init__(self, config: QdrantConfig = QdrantConfig()):
        """
        :parmas config - config setting of the vector db
        """
        self.qdrant_config = config
        try:
            self.client = self.create_client(
                url=self.qdrant_config.cluster_url,
                api_key=self.qdrant_config.qdrant_api_key,
            )
        except Exception as e:
            logging.error(f"Failed to create Qdrant client: {e}")
            self.client = None
        self.document = None
        self.query: Optional[str] = None
        self.metrics_collector = get_metrics_collector()

    def load_query(self, query: str):
        """
        Load user's query
        """
        self.query = query

    def create_client(self, url: str, api_key: str):
        """
        Create qdrant client
        """
        return QdrantClient(url=url, api_key=api_key)

    def create_collection(self, collection_name: str, embedding_dimension: int):
        """
        Create a collection that will store all the data points
        """
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_dimension,  # Dimensionality of the vectors
                    distance=models.Distance.COSINE,  # Distance metric for similarity search
                ),
            )
            logging.info(f"Collection '{collection_name}' created successfully.")
        except ResponseHandlingException as e:
            raise ValueError(f"Error with Qdrant API key: {e}")
        except ValueError as e:
            raise ValueError(
                f"Invalid configuration seen for collection '{collection_name}': {e}"
            )
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")

    @staticmethod
    def get_text_embedding_string(record: dict) -> str:
        """
        Get the text embedding string created by concatenating the fields

        :params - record - A dictionary of a single record
        """
        return (
            f"Exercise Name: {record['exercise_name']} — "
            f"Muscle Groups: {record['muscle_groups_activated']} — "
            f"Body Part: {record['body_part']} — "
            f"Instructions: {record['instructions']}"
        )

    @staticmethod
    def get_payload(record: dict, context_mapping: dict) -> dict:
        """
        Get the payload to be used in the Vector Db

        :params - record - A dictionary of a single record
        :params - context_mapping - A dictionary of the mapping

        Returns a dictionary containing the mapped field to its equivalent value from the record
        """
        return {k: record[k] for k, v in context_mapping.items()}

    def convert_documents_to_points(self, document: list[dict], embedding_model: str):
        points = []
        for idx, record in enumerate(document):
            text_to_embed = self.get_text_embedding_string(record=record)

            # Embed with Jina (FastEmbed returns generator, convert to list)
            vector = models.Document(text=text_to_embed, model=embedding_model)
            payload = self.get_payload(
                record=record, context_mapping=self.qdrant_config.context_mapping
            )

            # Create the point
            point = models.PointStruct(id=idx, vector=vector, payload=payload)
            points.append(point)
        return points

    def create_points_and_insert(self, document: list[dict], embedding_model: str):
        """
        Create vector data points from the document
        Insert the points into collection.
        Embed a combination of exercise name and instructions

        :parmas - document - list of documents
        :params - model - embedding model to use
        """
        # embed and upsert-
        points = self.convert_documents_to_points(
            document=document, embedding_model=embedding_model
        )
        self.client.upsert(
            collection_name=self.qdrant_config.collection_name, points=points
        )
        logging.info("Vector Points successfully inserted..")

    def run_vector_embedding(self):
        """
        load and clean document
        Create collection
        insert vectors into collection
        """

        data = load_data(QdrantConfig().document_location)
        data = clean_data(data)
        document = create_document(data)

        # # create collection
        vector_db = ManageVectorDb()

        if not vector_db.collection_exists():
            logging.info("Collection does not exist. Creating it now.")
            vector_db.create_collection(
                collection_name=vector_db.qdrant_config.collection_name,
                embedding_dimension=vector_db.qdrant_config.embedding_dimension,
            )
        else:
            if self.qdrant_config.recreate_collection:
                logging.warning(
                    "Collection already exists. Settings indicate it should be recreated."
                )
                self.client.delete_collection(
                    collection_name=self.qdrant_config.collection_name
                )
                vector_db.create_collection(
                    collection_name=vector_db.qdrant_config.collection_name,
                    embedding_dimension=vector_db.qdrant_config.embedding_dimension,
                )

        # insert points into collection
        vector_db.create_points_and_insert(
            document=document, embedding_model=vector_db.qdrant_config.embedding_model
        )

    def collection_exists(self):
        """
        Check if collection exists
        """
        collections = self.client.get_collections().collections
        return any(c.name == self.qdrant_config.collection_name for c in collections)

    def search(self, query: str, trace_id: str = ""):
        """
        Search for vector in vector db with monitoring
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        rag_logger = RAGLogger(trace_id)
        start_time = time.time()
        rag_logger.log_retrieval_start()

        try:
            results = self.client.query_points(
                collection_name=self.qdrant_config.collection_name,
                query=models.Document(
                    text=query, model=self.qdrant_config.embedding_model
                ),
                limit=self.qdrant_config.response_limit,  # top closest matches
                with_payload=True,  # to get metadata in the results
            )

            response_time_ms = (time.time() - start_time) * 1000
            scores = [p.score for p in results.points] if results.points else []
            top_score = max(scores) if scores else 0.0

            rag_logger.log_retrieval_complete(
                num_results=len(results.points),
                scores=scores,
                response_time_ms=response_time_ms,
            )

            self.metrics_collector.record_retrieval(
                RetrievalMetrics(
                    num_results=len(results.points),
                    scores=scores,
                    response_time_ms=response_time_ms,
                    top_score=top_score,
                )
            )

            return results

        except Exception as e:
            rag_logger.log_error(e, "Vector DB retrieval")
            self.metrics_collector.record_error(str(e))
            raise

    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with synonyms and related terms for better recall
        """
        # Fitness-specific synonyms and related terms
        fitness_synonyms = {
            "push": ["press", "extend", "push away"],
            "pull": ["row", "curl", "draw in"],
            "hold": ["plank", "static", "isometric"],
            "strength": ["resistance", "weight", "muscle building"],
            "stretching": ["flexibility", "mobility", "flex"],
            "cardio": ["aerobic", "endurance", "heart"],
            "upper body": ["chest", "back", "shoulders", "arms"],
            "lower body": ["legs", "quads", "hamstrings", "glutes"],
            "core": ["abs", "abdominals", "midsection"],
        }

        expanded_queries = [query]
        query_lower = query.lower()

        # Add synonym-based expansions
        for key, synonyms in fitness_synonyms.items():
            if key in query_lower:
                for synonym in synonyms:
                    expanded_query = query_lower.replace(key, synonym)
                    if expanded_query != query_lower:
                        expanded_queries.append(expanded_query)

        # Add common exercise variations
        exercise_variations = {
            "squat": ["squats", "bodyweight squat", "air squat"],
            "push-up": ["pushup", "press up", "chest press"],
            "deadlift": ["dead lifts", "dl", "hip hinge"],
            "plank": ["front plank", "abdominal plank", "core hold"],
        }

        for key, variations in exercise_variations.items():
            if key in query_lower:
                expanded_queries.extend([v for v in variations if v not in query_lower])

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in expanded_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries[:5]  # Limit to top 5 expansions

    def hybrid_search(self, query: str, trace_id: str = "", alpha: float = 0.7) -> Any:
        """
        Perform hybrid search combining vector and keyword search
        alpha: weight for vector search (1-alpha for keyword search)
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        rag_logger = RAGLogger(trace_id)
        start_time = time.time()
        rag_logger.log_retrieval_start()

        try:
            # Get expanded queries
            expanded_queries = self.expand_query(query)

            # Vector search with original and expanded queries
            all_vector_results = []
            for exp_query in expanded_queries:
                vector_results = self.client.query_points(
                    collection_name=self.qdrant_config.collection_name,
                    query=models.Document(
                        text=exp_query, model=self.qdrant_config.embedding_model
                    ),
                    limit=self.qdrant_config.response_limit * 2,  # Get more for fusion
                    with_payload=True,
                )
                all_vector_results.extend(vector_results.points)

            # Simple keyword search (text matching in payload)
            keyword_results = []
            query_terms = set(query.lower().split())
            for point in self.client.scroll(
                collection_name=self.qdrant_config.collection_name,
                limit=1000,  # Reasonable limit for keyword search
                with_payload=True,
            )[0]:
                payload_text = " ".join(
                    [
                        str(point.payload.get("exercise_name", "")),
                        str(point.payload.get("type_of_activity", "")),
                        str(point.payload.get("body_part", "")),
                        str(point.payload.get("muscle_groups_activated", "")),
                        str(point.payload.get("instructions", "")),
                    ]
                ).lower()

                # Calculate simple keyword match score
                payload_terms = set(payload_text.split())
                match_score = len(query_terms.intersection(payload_terms)) / max(
                    len(query_terms), 1
                )

                if match_score > 0:
                    # Create a scored point-like object for keyword results
                    keyword_results.append(
                        {"point": point, "score": match_score, "type": "keyword"}
                    )

            # Combine and rerank results
            combined_results = self._combine_and_rerank(
                all_vector_results,
                keyword_results,
                alpha=alpha,
                limit=self.qdrant_config.response_limit,
            )

            response_time_ms = (time.time() - start_time) * 1000
            scores = (
                [p.score for p in combined_results.points]
                if combined_results.points
                else []
            )
            top_score = max(scores) if scores else 0.0

            rag_logger.log_retrieval_complete(
                num_results=len(combined_results.points),
                scores=scores,
                response_time_ms=response_time_ms,
            )

            self.metrics_collector.record_retrieval(
                RetrievalMetrics(
                    num_results=len(combined_results.points),
                    scores=scores,
                    response_time_ms=response_time_ms,
                    top_score=top_score,
                )
            )

            return combined_results

        except Exception as e:
            rag_logger.log_error(e, "Hybrid vector DB retrieval")
            self.metrics_collector.record_error(str(e))
            raise

    def _combine_and_rerank(
        self, vector_results, keyword_results, alpha: float, limit: int
    ):
        """
        Combine vector and keyword search results using reciprocal rank fusion
        """

        # Create dictionaries for scoring
        vector_scores = {}
        keyword_scores: dict[str, float] = {}

        # Score vector results (higher score = better)
        for i, point in enumerate(vector_results):
            vector_scores[point.id] = 1.0 / (i + 1)  # Reciprocal rank

        # Score keyword results
        for i, item in enumerate(keyword_results):
            point_id = item["point"].id
            keyword_scores[point_id] = keyword_scores.get(point_id, 0) + (1.0 / (i + 1))

        # Combine scores
        all_point_ids = set(vector_scores.keys()) | set(keyword_scores.keys())
        combined_scores = {}

        for point_id in all_point_ids:
            vector_score = vector_scores.get(point_id, 0)
            keyword_score = keyword_scores.get(point_id, 0)
            # Normalize and combine
            combined_scores[point_id] = (
                alpha * vector_score + (1 - alpha) * keyword_score
            )

        # Sort by combined score and get top results
        sorted_ids = sorted(
            combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True
        )[:limit]

        # Create a mock results object similar to query_points response
        class MockResults:
            def __init__(self, points=None):
                self.points = points if points is not None else []

        # Retrieve full points for selected IDs
        if sorted_ids:
            # Get points by ID (simplified - in production you'd use retrieve)
            final_points = []
            vector_points_dict = {p.id: p for p in vector_results}

            for point_id in sorted_ids:
                if point_id in vector_points_dict:
                    # Create a copy with updated score for hybrid ranking
                    point = vector_points_dict[point_id]
                    # We'll store the hybrid score separately for logging
                    final_points.append(point)
                else:
                    # Find from keyword results
                    for item in keyword_results:
                        if item["point"].id == point_id:
                            final_points.append(item["point"])
                            break

            return MockResults(final_points)
        else:
            # Return empty results
            return MockResults([])


def rag(
    user_query: str,
    config: QdrantConfig | None = None,
    user_profile: UserProfile | None = None,
):
    """
    Entrypoint for the RAG pipeline.
    Recieves user's query, get vectors from Vector db, and return LLM response
    Includes input validation and monitoring

    :params - user_query - Query from the user
    :params - config - optional configuration for qdrant
    :params - user_profile - optional user profile for personalized filtering
    """
    trace_id = str(uuid.uuid4())
    rag_logger = RAGLogger(trace_id)
    metrics_collector = get_metrics_collector()

    try:
        # Validate user input
        validation_result = validate_user_input(user_query)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid input: {validation_result['error']}")

        rag_logger.log_query_received(user_query)
        metrics_collector.record_query()

        if config:
            vector_db = ManageVectorDb(config=config)
        else:
            vector_db = ManageVectorDb()

        if vector_db.qdrant_config.create_vectors:
            vector_db.run_vector_embedding()

        # search with vector - use hybrid search for better results
        # Toggle between vector and hybrid search via config or parameter
        use_hybrid_search = getattr(vector_db.qdrant_config, "use_hybrid_search", False)
        if use_hybrid_search:
            results = vector_db.hybrid_search(query=user_query, trace_id=trace_id)
        else:
            results = vector_db.search(query=user_query, trace_id=trace_id)

        # Apply user profile filtering if provided
        if user_profile and results.points:
            exercises = [point.payload for point in results.points]
            filtered_exercises = filter_exercises_by_profile(exercises, user_profile)

            if filtered_exercises:
                # Update results with filtered exercises

                filtered_points = []
                for idx, exercise in enumerate(filtered_exercises):
                    for point in results.points:
                        if point.payload == exercise:
                            filtered_points.append(point)
                            break
                results.points = filtered_points

        context = format_vector_db_context(results.points)

        display_rag_response(
            console_instance=Console(), answer=context, is_context=True
        )

        rag_instance = LLMFlow()
        response = rag_instance.run(
            query=user_query, context=context, trace_id=trace_id
        )

        # Check for hallucinations
        detector = HallucinationDetector(threshold=0.5)
        hallucination_result = detector.detect(response, context)
        rag_logger.log_hallucination_check(
            hallucination_result.score, hallucination_result.is_hallucinating
        )
        metrics_collector.record_hallucination(hallucination_result.score)

        return response

    except Exception as e:
        rag_logger.log_error(e, "RAG pipeline")
        metrics_collector.record_error(str(e))
        raise


def main():
    """
    Using Argparser, guide the user through the RAG pipeline
    """
    parser = argparse.ArgumentParser(
        description="Run the Fitness assistant pipeline interactively."
    )
    parser.add_argument(
        "--create-vectors",
        action="store_true",
        help="An optional flag to create vector embedding. "
        "If provided, you will be asked whether you want to recreate the collection."
        "A collection is a 'bank' of the exercise vectors",
    )
    args = parser.parse_args()
    qdrant_config = None

    query = Prompt.ask("[bold cyan]Enter your Fitness question:[/bold cyan]")

    if not query:
        logging.warning("[bold red]No questions entered. Exiting[/bold red]")
        return

    if args.create_vectors:
        logging.info("[yellow] You chose to run vector embedding.[/yellow]")

        while True:
            recreate_choice = Prompt.ask(
                "[bold cyan]Do you want to recreate the collection?[/bold cyan]",
                choices=["yes", "no", "y", "n"],
                default="no",
            )

            if recreate_choice in ("yes", "y"):
                logging.info(
                    "[blue]Configured to recreate collection and vector embeddings...[/blue]"
                )
                qdrant_config = QdrantConfig(
                    create_vectors=True, recreate_collection=True
                )
                break

            elif recreate_choice in ("no", "n"):
                logging.info(
                    " Configured to upsert new vectors without recreating collection..."
                )
                qdrant_config = QdrantConfig(
                    create_vectors=True, recreate_collection=False
                )
                break

            else:
                logging.warning(
                    "[red]⚠️ Invalid choice. Please enter 'yes' or 'no'.[/red]"
                )

    response = rag(user_query=query, config=qdrant_config)
    display_rag_response(console_instance=Console(), answer=response)


if __name__ == "__main__":
    main()
