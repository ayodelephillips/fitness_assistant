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

A. Pipenv is used to manage packages and dependencies using a pipfile.

Make sure you have pipenv installed.

```bash
pip install pipenv
```

B. Installing the dependencies:

```bash
pipenv install
```

```bash
pipenv install  --dev
```


C. Running gemma3 locally
```bash
ollama run gemma3:2b  
```



D. Pull  qdrant container  in docker
```bash
docker pull qdrant/qdrant
```


E. Running qdrant  in docker
6333 is for the REST API
6334 is for the gRPC API
quadranst_storage  mounts local storage to keep data persistent even if the container is deleted/restarted
```bash
docker run -p 6333:6333 -p 6334:6334 -v"$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant
```

F. Install qdrant client and fastembed which does the data vectorization

```bash
pipenv install -q "qdrant-client[fastembed]>=1.14.2"
```

G. Access the vector db in quandrant by going to http://localhost:6333/dashboard

Running Jupyter Notebook for experiments
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





## Evaluation


## Retrieval

## RAg Flow


## Monitoring


deploying model on docker container - https://chatgpt.com/share/67fc3eff-21e0-8007-9f03-a7575d0fb78a
