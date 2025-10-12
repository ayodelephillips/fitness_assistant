# Fitness Assistant by Phillips

## 🏋️ Problem Description

Many people struggle to find clear, personalized workout guidance.
Online resources are scattered, and beginners often feel overwhelmed by equipment choices, form instructions, and exercise variety.

**Fitness Assistant by Phillips** solves this by offering an AI-powered chat assistant that helps users discover and understand exercises quickly and interactively.

## 📂 Dataset

The project uses a synthetic dataset of **500 exercises**, generated with ChatGPT and stored in the `data` folder. Each entry includes:

- **Exercise Name**
- **Type of Activity** (e.g., Strength, Stretching)
- **Equipment Used**
- **Target Body Part**
- **Movement Type** (Push, Pull, Hold)
- **Muscle Groups Activated**
- **Instructions**
- **Video Link**

Example:

```
Yoga Flow | Stretching | Foam Roller | Core | Hold | Quadriceps, Glutes, Hamstrings | Step forward... | [Video](https://www.youtube.com/watch?v=op9kVnSso6Q)
```

## 🤖 What It Does

Users can chat with the assistant to:

1. Discover exercises based on body part, equipment, or goal
2. Get step-by-step instructions
3. Watch demo videos
4. Build a workout routine with natural language prompts
5. Get replacement for exercise in their routine. The assistant can suggest suitable alternatives that target the same muscle groups or require similar equipment.



Example queries:

> "Show me upper body push exercises with a kettlebell."
> "How do I do a cable row?"

This tool makes fitness guidance fast, accessible, and user-friendly.

---

Built to make staying fit easier and smarter.

---


## Running It

1. Prerequisites:

    A.  Poetry is used to manage packages and dependencies using a pyproject.toml file


    ```bash
    pip install poetry
    ```

    B. Installing the dependencies:

    ```bash
    poetry install
    ```




    C. Install qdrant for managing the Vector DB.
    There are 2 methods for using qdrant.

     i. Using docker locally

        a. Pull  qdrant container  in docker
        ```bash
        docker pull qdrant/qdrant
        ```


        b. Running qdrant  in docker
        6333 is for the REST API
        6334 is for the gRPC API
        quadranst_storage  mounts local storage to keep data persistent even if the container is deleted/restarted
        ```bash
        docker run -p 6333:6333 -p 6334:6334 -v"$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant
        ```

        C. Install qdrant client and fastembed which does the data vectorization. This is already stated in pyproject.toml
        ```bash
        pipenv install -q "qdrant-client[fastembed]>=1.14.2"
        ```

         Access the vector db in quandrant by going to http://localhost:6333/dashboard

     ii. Using the Qdrant cloud free tier cluster as shown [here](https://qdrant.tech/documentation/cloud/create-cluster/)
     It provides you a UI(which allows you see the data points of each vectors), and an API key to connect


    D. Create API key from google ai studio [here](https://aistudio.google.com/)

    E. Environment Variables
    Ensure to create a .env file to store your environment variables

    QDRANT_API_KEY=<QDRANT_API_KEY>
    GOOGLE_API_KEY=<GOOGLE_API_KEY
Note, you would need to update the <cluster_url> in fitness_assistant/rag/settings.py

2. Running Jupyter Notebook for experiments
Disregard the notebooks, as it's largely for experiments
```bash
cd notebooks
pipenv run jupyter notebook
```

Running pre-commit on files before pushing to git branch
```bash
pipenv run pre-commit run --all-files
```


Running the elastic search server
 in docker
```bash
docker run -it --name elasticsearch -p9200:9200 -p9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" docker.elastic.co/elasticsearch/elasticsearch:8.4.3
```


install pre-commit as part of workflows
```bash
pre-commit install
```

3. Running the app

i. cd into fitness_assistant/rag directory.
There are 2 modes for executing the llm_interface.py script.

ii. To create a collection of vector embeddings, and also ask the user for his/her question
```bash
python llm_interface.py --create-vectors
```

iii. To run the RAG pipeline on an existing collection of vector embeddings
```bash
python llm_interface.py

```

## Next steps
1. Deployment
A cloud run deployment
![What is this](fitness_assistant/rag/data/Next_steps_Fitness_Assistant.jpg)
## Evaluation


## Retrieval


## Monitoring

## Improvements
