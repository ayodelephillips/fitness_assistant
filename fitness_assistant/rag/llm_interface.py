from qdrant_client import QdrantClient, models
from fitness_assistant.rag.settings import QdrantConfig, LlmConfig
from fitness_assistant.rag.helper import (
    display_rag_response,
    load_data,
    clean_data,
    create_document,
    format_vector_db_context,
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client.http.exceptions import ResponseHandlingException

from typing import Optional
import argparse
from rich.console import Console
from rich.prompt import Prompt
from rich.logging import RichHandler
from langsmith import traceable
import logging

# logging.basicConfig(level=logging.INFO)
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(markup=True, rich_tracebacks=True)
    ],  # Use RichHandler for logging
)


class LLMFlow:
    """
    Define langchain flow for LLM
    """

    def __init__(self, config: LlmConfig = LlmConfig()):
        self.llm_config = config
        self.llm = self._connect_to_llm()
        self.chain = self._build_chain()
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
            chain = (prompt | self.llm).with_config(
                {"run_name": "fitness_assistant_rag_chain"}
            )
        except ValueError as val_err:
            logging.error(
                f"Could not build chain sucessfully. Ensure prompt follows expected template. error is {val_err}"
            )
        else:
            return chain
        return None

    @traceable(name="rag_flow_run", run_type="llm")
    def run(self, query: str, context: str):
        """
        Run the rag flow
        :params query - Query from the user
        :params  context- context retrived from vector db
        """
        response = self.chain.invoke({"question": query, "context": context})
        return response.content


class ManageVectorDb:
    """
    Manage qdrant Vector database
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

    @traceable(name="create_collection", run_type="tool")
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
        Build the text used for embedding from the most retrieval-relevant fields.

        Chunks on: name, category/activity, equipment, muscles, description, instructions.
        These columns are produced by the V2 JSON normalizer (and match cleaned V1 CSV).

        :params - record - A dictionary of a single record
        """
        parts = [
            f"Exercise Name: {record.get('exercise_name', '')}",
            f"Type of Activity: {record.get('type_of_activity', '')}",
            f"Equipment: {record.get('type_of_equipment', '')}",
            f"Muscle Groups: {record.get('muscle_groups_activated', '')}",
            f"Body Part: {record.get('body_part', '')}",
        ]
        description = record.get("description") or ""
        if description:
            parts.append(f"Description: {description}")
        parts.append(f"Instructions: {record.get('instructions', '')}")
        return " — ".join(parts)

    @staticmethod
    def get_payload(record: dict, context_mapping: dict) -> dict:
        """
        Get the payload to be used in the Vector Db

        :params - record - A dictionary of a single record
        :params - context_mapping - A dictionary of the mapping

        Returns a dictionary containing the mapped field to its equivalent value from the record
        """
        return {k: record.get(k, "") for k in context_mapping}

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

    @traceable(name="create_points_and_insert", run_type="tool")
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

    @traceable(name="run_vector_embedding", run_type="chain")
    def run_vector_embedding(self):
        """
        load and clean document
        Create collection
        insert vectors into collection
        """

        data = load_data(self.qdrant_config.document_location)
        data = clean_data(data)
        document = create_document(data)
        logging.info(
            f"Loaded {len(document)} exercises from {self.qdrant_config.document_location}"
        )

        # reuse this instance for collection ops / inserts
        vector_db = self

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

    @traceable(name="search_vector_db", run_type="retriever")
    def search(self, query: str):
        """
        Search for vector in vector db
        """
        results = self.client.query_points(
            collection_name=self.qdrant_config.collection_name,
            query=models.Document(text=query, model=self.qdrant_config.embedding_model),
            limit=self.qdrant_config.response_limit,  # top closest matches
            with_payload=True,  # to get metadata in the results
        )
        return results


@traceable(name="rag-pipeline", run_type="chain")
def rag(user_query: str, config: QdrantConfig | None = None):
    """
    Entrypoint for the RAG pipeline.
    Recieves user's query, get vectors from Vector db, and return LLM response

    :params - user_query - Query from the user
    :params - config -optional configuration for qdrant
    """

    if config:
        vector_db = ManageVectorDb(config=config)
    else:
        vector_db = ManageVectorDb()

    if vector_db.qdrant_config.create_vectors:
        vector_db.run_vector_embedding()

    # # search with vector
    results = vector_db.search(query=user_query)
    context = format_vector_db_context(results.points)

    display_rag_response(console_instance=Console(), answer=context, is_context=True)

    rag_instance = LLMFlow()
    return rag_instance.run(query=user_query, context=context)


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
