from qdrant_client import QdrantClient, models
from fitness_assistant.rag.settings import QdrantConfig, LlmConfig, VectorDataContext
from fitness_assistant.rag.helper import load_data, clean_data, create_document, format_vector_db_context
import pandas as pd

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import logging

logging.basicConfig(level=logging.INFO)



class RagFlow:
    def __init__(self, 
                 config:LlmConfig=LlmConfig()):
        self.llm_config = config



    def get_prompt_from_template(self):
        """
        Build prompt using prompt template
        """
        return ChatPromptTemplate.from_messages([
            ("system", self.llm_config.system_prompt),
            ("human", self.llm_config.human_prompt),
        ])



    def connect_to_llm(self) -> None:
        """
        Instantiate llm connection
        """
        self.llm =  ChatGoogleGenerativeAI(
            api_key=self.llm_config.google_api_key,
            model=self.llm_config.model_name,
            temperature=self.llm_config.temperature,
            top_p=self.llm_config.top_p,
            top_k=self.llm_config.top_k,
            max_output_tokens=self.llm_config.max_output_tokens,
            safety_settings=self.llm_config.safety_settings,
        )

    def generate_response(self, 
                          query:str,
                          context:str):
        """
        Generate single response from llm
        """
        response =self.chain.invoke({"question": query, "context": context})
        print("\n\n\n anoda responase")
        print(response)
        return response.content
    

    def build_chain(self):
        """
        Build llm chain
        """
        prompt = self.get_prompt_from_template()
        self.chain = prompt | self.llm


    def run(self, query:str, context:str):
        """
        Run the rag flow
        :params query - Query from the user
        :params  context- context retrived from vector db
        """
        self.connect_to_llm()
        self.build_chain()
        response = self.generate_response(query=query, context=context)
        print("responseeeeee!!!!!")
        print(response)

    # load data
    # clean data
    # create document
    # build prompt

    # a class to create/manage vectors
   
    # a class to manage the RAG.


class ManageVectorDb:
    """
    Manage qdrant Vector database
    """
    def __init__(self,
                 data:str|list[dict],
                 data_context: VectorDataContext,
                 config: QdrantConfig = QdrantConfig()
                 ):
        """
        :parmas data - can be either a user query(when searching) or a document for embedding
        :parmas data_context - gives context to the type of data passed
        :parmas config - config setting of the vector db
        """
        self.qdrant_config = config
        self.data = data
        self.data_context = data_context
        self.client = self.create_client(
            url = self.qdrant_config.cluster_url,
            api_key = self.qdrant_config.qdrant_api_key

        )
        

    def load_query(self, query:str):
        """
        Load user's query
        """
        self.query = query


    def create_client(self, url: str, api_key: str):
        """
        Create qdrant client
        """
        qdrant_client = QdrantClient(
            url=url, 
            api_key=api_key,
        )
        return qdrant_client


    def create_collection(self, 
                          collection_name: str,
                          embedding_dimension: int):
        """
        Create a collection that will store all the data points
        """
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_dimension,  # Dimensionality of the vectors
                distance=models.Distance.COSINE  # Distance metric for similarity search
            )
        )


    def convert_documents_to_points(self,document: list[dict], embedding_model:str):
        """
        Insert the points into collection.
        Embed a combination of exercise name and instructions

        Use payload as type of activity, type of equipment and the body part
        """
        # embed and upsert-
        points = []
        for idx, record in enumerate(document):
            # Combine relevant fields for embedding
            text_to_embed = f"{record['exercise_name']} — {record['instructions']}"
        
            # Embed with Jina (FastEmbed returns generator, convert to list)
            vector=models.Document(text=text_to_embed, model=embedding_model)
        
            payload={
                        "type_of_activity": record['type_of_activity'],
                        "type_of_equipment": record['type_of_equipment'],
                        "body_part": record['body_part']
                    }
            # Create the point
            point = models.PointStruct(
                id=idx,
                vector=vector,
                payload=record
            )
            points.append(point)

        self.client.upsert(
        collection_name=self.qdrant_config.collection_name,
        points=points
        )
        logging.info(f"Points successfully inserted..")

    def run_vector_embedding(self):
        """
        load and clean document
        Create collection
        insert vectors into collection
        """
       
        if not self.collection_exists():
            logging.info(f"Collection {self.qdrant_config.collection_name} does not exist. Creating it now.")
            self.create_collection(
                collection_name=self.qdrant_config.collection_name,
                embedding_dimension=self.qdrant_config.embedding_dimension
            )
        else:
            logging.info(f"Collection {self.qdrant_config.collection_name} already exists.")
            
    def collection_exists(self):
        """
        Check if collection exists
        """
        collections = self.client.get_collections().collections
        return any(c.name == self.qdrant_config.collection_name for c in collections)


    def search(self, query:str):
        """
        Search for vector in vector db
        """
        results = self.client.query_points(
            collection_name=self.qdrant_config.collection_name,
            query=models.Document( 
                text=query,
                model=self.qdrant_config.embedding_model 
            ),
            limit=self.qdrant_config.response_limit, # top closest matches
            with_payload=True #to get metadata in the results
        )
        logging.info(f"Vector search completed with results.{len(results.points)}")

        return results

    

if __name__ == '__main__':
        
        # load data
        # data = load_data(QdrantConfig().document_location)

        # data = clean_data(data)
        # document = create_document(data)
   

        # # create collection
        # vector_db = ManageVectorDb(
        #     data=document,
        #     data_context=VectorDataContext.document
        # )

        # if not vector_db.collection_exists():
        #     logging.info(f"Collection does not exist. Creating it now.")
        #     vector_db.create_collection(collection_name=vector_db.qdrant_config.collection_name,
        #                             embedding_dimension=vector_db.qdrant_config.embedding_dimension)

        # else:
        #     logging.info(f"Collection already exists.")

               
        # # insert points into collection
        # vector_db.convert_documents_to_points(document=document, 
        #                                         embedding_model=vector_db.qdrant_config.embedding_model)

        
        # vector_db.run_vector_embedding()
        vector_db = ManageVectorDb(
            data=None,
            data_context=VectorDataContext.document
        )
        query = 'what exercise helps me grow my biceps'
        # # search with vector
        results = vector_db.search(
            query=query
        )
        
        context = format_vector_db_context(results.points)
        print(context)
        
        # # call llm
        rag_instance = RagFlow()
        rag_instance.run(query=query, context=context)
        # pass

