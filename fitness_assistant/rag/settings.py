from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_google_genai import (HarmBlockThreshold, HarmCategory)
from enum import Enum
from dotenv import load_dotenv
from pathlib import Path

 
class VectorDataContext(str, Enum):
    """
    Context for data received
    """
    user_query = 'user_query'
    document='document'


class GenAIModels(str, Enum):
    gemini_2_5_flash = 'gemini-2.5-flash'
    gemini_2_5_pro='gemini-2.5-pro'


class QdrantConfig(BaseSettings):
    """
    Config settings used by Qdrant Vector Db
    """
    collection_name: str = 'exercise_collection'
    cluster_url: str = "https://51ddb13e-4d76-493c-98f3-8cd6c1319268.europe-west3-0.gcp.cloud.qdrant.io:6333"
    qdrant_api_key: str
    model_config = SettingsConfigDict(case_sensitive=False,
                                      env_file=".env", 
                                      env_file_encoding="utf-8", 
                                      extra="ignore")
    embedding_model: str = "jinaai/jina-embeddings-v2-small-en"
    embedding_dimension: int = 512
    response_limit:int = 3
    document_location: Path = Path(__file__).resolve().parent.joinpath(*['data', 'detailed_exercise_dataset.csv'])




class LlmConfig(BaseSettings):
    """
    Config settings used by the LLM
    """
    model_name: str = GenAIModels.gemini_2_5_pro
    system_prompt:str = """
        You're a fitness instructor. Answer the QUESTION based on the CONTEXT from our exercises database.
        Use only the facts from the CONTEXT when answering the QUESTION.
        Ensure to include multiple exercises, alongside the type of activity, equipment, body part, muscle group activated and instructions
        

        Make sure to include the full  video link in the context in your response. You will be penalized if you don't do that.
        Ensure your response is human friendly!!. That is very critical
    """.strip()

    human_prompt : str = """
        
        QUESTION: {question}

        CONTEXT: 
        {context}
    """.strip()

    temperature: float = 0.4
    top_p: int = 1
    top_k: int = 1
    max_output_tokens: int = 4000

    safety_settings: dict = Field(
        description="safety settings used by the llm",
        default_factory=lambda: {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
         HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
         HarmCategory.HARM_CATEGORY_VIOLENCE: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
         HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
         HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
         HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    )

    google_api_key: str # llm api
    model_config = SettingsConfigDict(case_sensitive=False,
                                      env_file=".env", 
                                      env_file_encoding="utf-8", 
                                      extra="ignore")
    context_mapping :dict = Field(
        description="Map vector db context result to llm friendly fields",
        default_factory=lambda: {
        "exercise_name": "🏋️ Exercise",
        "type_of_activity": "• Type of activity",
        "type_of_equipment": "• Equipment",
        "body_part": "• Body part",
        "instructions": "📋 Instructions",
        "video_link": "🎥 Video link"
    }
    )
    
    def __init__(self, **kwargs):
        load_dotenv()
        super().__init__(**kwargs)


# if __name__ == "__main__":
#     # This block now uses the LlmConfig class to get all settings,
#     # including the model name and API key (which is loaded automatically).
#     # This is a better test as it validates your configuration classes.
#     llm_config = LlmConfig()
#     print(f"Loaded key: {llm_config.google_api_key[:8]}...")

#     import os
#     print("GOOGLE_API_KEY loaded:", os.getenv("GOOGLE_API_KEY")[:10], "...")
#     from langchain_google_genai import ChatGoogleGenerativeAI
    
#     y = {
#         HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
#          HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
#          HarmCategory.HARM_CATEGORY_VIOLENCE: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
#          HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
#          HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
#          HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
#     }

#     llm = ChatGoogleGenerativeAI(
        
#         model=llm_config.model_name,
#         temperature=llm_config.temperature,
#         safety_settings=y,
#         convert_system_message_to_human=True,  # ensures system prompts are handled gracefully
#     )

#     # Example: a simple chat prompt
#     prompt = "what is the best sexual position. ensure to use the safety settings in place"

#     # Option 1: Simple one-shot call
#     response = llm.invoke(prompt)
#     print("LLM Response:\n", response.content)

if __name__ == "__main__":
    conf = LlmConfig()
    print(conf.context_mapping)
    #  y = Path(__file__).resolve().parent
    #  print(type(y))
    #  print(y)