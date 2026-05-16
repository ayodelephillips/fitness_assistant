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
    QueryRateLimiter,
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
from rich.logging import RichHandler

import logging

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


def rag(user_query: str, config: QdrantConfig | None = None, user_profile: UserProfile | None = None):
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

        # search with vector
        results = vector_db.search(query=user_query, trace_id=trace_id)
        
        # Apply user profile filtering if provided
        if user_profile and results.points:
            exercises = [point.payload for point in results.points]
            filtered_exercises = filter_exercises_by_profile(exercises, user_profile)
            
            if filtered_exercises:
                # Update results with filtered exercises
                from qdrant_client.http import models as qdrant_models
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
        response = rag_instance.run(query=user_query, context=context, trace_id=trace_id)

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
