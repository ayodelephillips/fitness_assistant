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

### CLI Mode
There are 2 modes for executing the llm_interface.py script.

i. To create a collection of vector embeddings, and also ask the user for his/her question
```bash
cd fitness_assistant/rag
python llm_interface.py --create-vectors
```

ii. To run the RAG pipeline on an existing collection of vector embeddings
```bash
cd fitness_assistant/rag
python llm_interface.py
```

### Streamlit Web UI (Recommended)
A chat-based web interface built with Streamlit.

```bash
# From the project root
poetry run streamlit run fitness_assistant/streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`.

**Features:**
- Chat-style conversation with the fitness assistant
- Expandable retrieved context for transparency
- Sidebar with RAG explanation

### Docker (Containerised Deployment)
Build and run the Streamlit app in a container:

```bash
# Build the image
docker build -t fitness-assistant .

# Run the container (pass API keys as env vars)
docker run -p 8501:8501 \
  -e QDRANT_API_KEY="your-key" \
  -e GOOGLE_API_KEY="your-key" \
  fitness-assistant
```

## Deployment

### Option 1: Streamlit Community Cloud (Free, Fastest)
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click "New app" → select this repo → branch `main` → file `fitness_assistant/streamlit_app.py`
4. Add secrets: `QDRANT_API_KEY` and `GOOGLE_API_KEY` in the Streamlit Cloud dashboard
5. Deploy — your app will be live at `https://<your-app>.streamlit.app`

### Option 2: Container Registry + Cloud Run
1. Build and tag the image:
   ```bash
   docker build -t fitness-assistant .
   docker tag fitness-assistant ghcr.io/ayodelephillips/fitness-assistant:latest
   ```
2. Push to GitHub Container Registry:
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u ayodelephillips --password-stdin
   docker push ghcr.io/ayodelephillips/fitness-assistant:latest
   ```
3. Deploy to Google Cloud Run:
   ```bash
   gcloud run deploy fitness-assistant \
     --image ghcr.io/ayodelephillips/fitness-assistant:latest \
     --set-env-vars "QDRANT_API_KEY=...,GOOGLE_API_KEY=..." \
     --allow-unauthenticated
   ```

## Next steps
1. ~~Deployment~~ ✅ Done — Streamlit Community Cloud or Cloud Run
![What is this](fitness_assistant/rag/data/Next_steps_Fitness_Assistant.jpg)


## Evaluation(Incomplete) - using DeepEval
There is an evaluation script created in rag/evaluation.py
it.
i. Define test data(a set of questions, and expected  ideal answer).
 This is  the evaluation set.

ii. For each query, get the context from the vector db, pass to the LLM for a full response(As observed in LLM_interface.py).

iii. LLMTestCases are created. Each test case contains:-
a. The original query
b. The actual ouput generated by RAG
c. Expected output: which is the ground truth
d. retrival context: documents gatherd from vector db

iv. Define evaluation metrics, such as
AnswerRelevancyMetric(how relevant is the answer to the question?), FaithfulnessMetric(Does the answer stick to the facts in the context?), ContextualRecallMetric(Did vector db retrieve all the info needed to answer?).

v. Deepeval goes through each test case, uses Gemini to score actual output against each metric



## Monitoring

## 📊 Visual Flowchart
For a complete visual walkthrough of the entire RAG pipeline (including Mermaid diagrams with detailed node explanations, data transformation flows, and system architecture), see the dedicated flowchart document:

➡️ **[flowchart_readme.md](./flowchart_readme.md)**

It covers:
1. High-level overview (ASCII diagram)
2. Detailed Mermaid flowchart with all code paths
3. Step-by-step walkthrough table for every node
4. Data transformation flow (JSON → vectors → answers)
5. Key design decisions visualised
6. System architecture diagram
7. Query resolution timeline with estimated latency

## 🔍 Payload Indexes For Filtered Queries
Payload indexes allow you to efficiently **filter** vector search results by payload fields (e.g. "only stretching exercises", "only exercises using dumbbells"). Without indexes, Qdrant must scan every point's payload — which breaks graph visualization in the Qdrant UI and slows down filtered queries.

The system now **automatically creates keyword payload indexes** on these fields when a collection is created:

| Indexed Field | Why | Example Filter Query |
|---------------|-----|---------------------|
| `type_of_activity` | Filter by exercise category | `"stretching"`, `"strength"` |
| `type_of_equipment` | Filter by equipment needed | `"dumbbell"`, `"none"` |
| `body_part` | Filter by target body part | `"core"`, `"arms"` |
| `muscle_groups_activated` | Filter by specific muscles | `"calves"`, `"biceps"` |
| `exercise_name` | Look up specific exercises | `"squat"`, `"bench press"` |

Each index is **independent** — you can filter on any one field or combine multiple in a single query. To add or modify indexed fields, update `payload_index_fields` in `settings.py`.

> **Pro tip**: Use the Qdrant UI dashboard with filter queries like `{"key": "type_of_activity", "match": {"value": "stretching"}}` to visualize only specific subsets of your vector graph.

## Improvements
1. Use pydantic output parser to prevent prompt Injection.
2. Langsmith for tracing, prompt /versioning
3. Monitoring pipeline to catch hallucinations.
4. Improve data quality(Instructions column)
5. Retrieval quality [using HSNW](https://qdrant.tech/documentation/beginner-tutorials/retrieval-quality/)
6. Increase data used for building vector db
7. improve data quality
8. ~~add streamlit frontend~~ ✅ Done
9. llm-as-a-judge
10. MCP in projects
11. reranking(fetch about 500 from rag, then rerank to get absolute best option)
12. hybrid search - sparse vectors, etc

---

# 🧠 How The RAG System Works (Beginner-Friendly Guide)

This section explains everything you need to know about how Fitness Assistant answers your questions — from what RAG is, right down to how text gets converted into numbers. Written for a non-technical audience (LinkedIn posts, stakeholders, curious devs).

---

## 1. What Is RAG? (The 30-Second Analogy)

**RAG** = **R**etrieval-**A**ugmented **G**eneration

Imagine you're a personal trainer (the AI) who has a filing cabinet of 500 exercise cards (the database). When a client asks *"give me exercises for my calf"*, instead of guessing from memory, you:

1. **Retrieve** → Go to the filing cabinet and pull out the 3 most relevant exercise cards
2. **Augment** → Place those cards on your desk as reference material you must stick to
3. **Generate** → Read the cards and give the client a well-structured answer using **only** what's on the cards

**Why this matters**:
- Without RAG, the AI would just guess based on its training data. It might make up exercises, get muscle groups wrong, or recommend equipment you don't have.
- With RAG, every answer is **grounded in actual data**. The AI cannot deviate from the facts in the retrieved documents.

---

## 2. The Big Picture — Two Phases

The system works in two distinct phases:

### Phase 1: Building The Filing Cabinet (Indexing / Ingestion)
This is the setup step. It happens once (or whenever new exercises are added).

```
[JSON file with 500 exercises]
           ↓
[Load & clean the data]
           ↓
[For each exercise, create a "summary card"]
           ↓
[Convert each summary card into a vector fingerprint]
           ↓
[Store all 500 fingerprints in Qdrant (vector database)]
```

### Phase 2: Answering Questions (Query & Generation)
This happens every time a user asks a question.

```
User: "give me exercises that build my calf"
                  ↓
[Convert the question into the same kind of fingerprint]
                  ↓
[Compare question's fingerprint against all 500 exercise fingerprints]
                  ↓
[Grab the 3 most similar exercises]
                  ↓
[Feed those 3 exercises + the question to Gemini (Google AI)]
                  ↓
[Gemini writes a friendly answer using only those 3 exercises as source]
```

---

## 3. What Are Vectors And Embeddings?

### The Core Concept

- **Vector**: A list of numbers, like `[0.23, -0.45, 0.12, ..., 0.89]` — 512 numbers long in our case.
- **Embedding**: The process of converting text (words, sentences, paragraphs) into a vector.

### The Barcode Analogy

Every product in a supermarket has a unique barcode. When scanned, the barcode tells the computer exactly what that product is. Similarly:

- Every piece of text has a unique **vector fingerprint**
- **Similar texts** have **similar vectors** (they point in the same direction in 512-dimensional space)
- **Different texts** have **different vectors** (they point in different directions)

```
Text A: "Standing Calf Raise — targets the calves"
Vector A: [0.92, -0.34, 0.15, ..., 0.78]  ← points toward "lower leg exercises"

Text B: "Seated Calf Raise — targets the calves"
Vector B: [0.90, -0.30, 0.12, ..., 0.76]  ← very close to Vector A (similar meaning)

Text C: "Bench Press — targets the chest"
Vector C: [-0.45, 0.67, -0.23, ..., 0.11]  ← far from Vector A (different meaning)
```

### How The Jina Embedding Model Converts Text Into 512 Numbers

This is a 4-step process:

#### Step 1: Tokenization (Breaking Text Into Pieces)

The sentence `"Standing Calf Raise — Strength — Dumbbell — Calves"` gets split into smaller pieces called **tokens** using a WordPiece tokenizer:

```
["Stand", "##ing", "Calf", "Raise", "—", "Strength", "—", "Dumb", "##bell", "—", "Calves"]
```

- Common words stay whole: `"Calf"`, `"Strength"`
- Rare words break into subwords: `"Dumbbell"` → `"Dumb"` + `"##bell"` (the `##` means "continuation of the previous word")
- Each token becomes a **token ID** from a fixed vocabulary of ~30,000 pieces

> **Analogy**: Like how words are made of letters, sentences are made of tokens. The model has a dictionary of 30,000 word-pieces it understands.

#### Step 2: Token Embedding (Each Token Gets A Starting Vector)

Each token ID is looked up in an **embedding table** — a giant matrix where every token maps to a 512-number vector. These vectors were randomly initialized and then gradually adjusted during training.

```
"Stand"  → [0.12, -0.34, 0.56, ..., 0.78]  (512 numbers)
"##ing"  → [-0.23, 0.45, -0.12, ..., 0.34]  (512 numbers)
"Calf"   → [0.67, -0.89, 0.01, ..., -0.45]  (512 numbers)
...
```

At this stage, each token's vector knows nothing about its context — "Calf" (the body part) and "Calf" (the baby cow) have the same vector.

#### Step 3: Transformer Layers With Self-Attention (The Magic)

This is the core algorithm. Jina uses a **Transformer** architecture — specifically based on BERT/AlBERT with **12 transformer layers stacked on top of each other**.

**What happens in each layer:**

Every token looks at every other token and asks: *"How relevant are you to me?"*

For the sentence `"Standing Calf Raise targets the Calves"`:

When processing the token `"Calves"`, the model computes **attention scores**:

| Token | Attention Score | Meaning |
|-------|----------------|---------|
| "Calf" | 0.85 | Very relevant — same concept |
| "Raise" | 0.60 | Relevant — it's a calf raise |
| "Standing" | 0.40 | Somewhat relevant — describes the stance |
| "targets" | 0.20 | Weakly relevant |
| "the" | 0.05 | Not relevant — filler word |

Each token's vector gets **updated** by blending in information from tokens it found relevant:

```
New_Vector("Calves") =
    0.30 × Original("Calves")    (keep most of its own meaning)
  + 0.25 × Vector("Calf")        (pull in "Calf" information)
  + 0.15 × Vector("Raise")       (pull in "Raise" information)
  + 0.10 × Vector("Standing")    (pull in "Standing" information)
  + 0.10 × Vector("targets")
  + 0.05 × Vector("the")
  + 0.05 × (other tokens...)
```

This happens in **all 12 layers sequentially**. Each layer captures more abstract relationships:

- **Early layers (1-3)**: Syntax — "Calf" modifies "Raise", "Standing" modifies "Calf Raise"
- **Middle layers (4-8)**: Semantics — "Calf" and "Calves" are related, this is about lower body
- **Late layers (9-12)**: Context — This is a strength exercise targeting the lower legs using dumbbells

> **The Attention Algorithm (simplified):**
>
> For every pair of tokens (i, j), compute:
> ```
> score(i, j) = softmax(Query(i) · Key(j) / √d)
> ```
> Where:
> - `Query(i)` = a transformation of token i's vector — "what am I looking for?"
> - `Key(j)` = a transformation of token j's vector — "what information do you have?"
> - The **dot product** (`·`) measures alignment between them (bigger = more aligned)
> - Dividing by `√d` (square root of 512) keeps values from getting too large
> - **Softmax** converts all scores into probabilities that sum to 1
>
> Then the output for token i is:
> ```
> Output(i) = sum of [score(i,j) × Value(j)] for all positions j
> ```
> Where `Value(j)` = yet another transformation — "what information are you passing along?"

**What each of the 512 dimensions might represent:**

Think of each dimension as a "micro-question" the model learned during training:

| Dimension | What It Might Detect |
|-----------|---------------------|
| #1 | "Is this about body parts?" |
| #42 | "Is this about lower body specifically?" |
| #87 | "Does this involve equipment?" |
| #156 | "Is this a pushing or pulling motion?" |
| #203 | "Is this strength or cardio?" |
| #311 | "Is this exercise done standing?" |
| #489 | "Does this target calves specifically?" |

These are **learned features** — no human assigned these meanings. The model discovered them organically through training on millions of text examples.

#### Step 4: Pooling (One Vector For The Whole Text)

After 12 transformer layers, we have 11 token vectors (one per token in our example), each 512 numbers long. We need **one vector** for the entire exercise text.

**Mean pooling**: Average all token vectors together (element-wise):

```
Final_Vector[0] = average of all 11 tokens' 1st number
Final_Vector[1] = average of all 11 tokens' 2nd number
...
Final_Vector[511] = average of all 11 tokens' 512th number
```

This produces a single 512-number vector where:
- If most tokens are about "calves" and "lower leg", the calves-related dimensions will have high values
- If most tokens are about "strength", strength-related dimensions will be high
- The vector as a whole represents the **semantic gist** of the entire text

### How The Model Learned To Do This

Jina was trained on **hundreds of millions of text pairs** using **contrastive learning**:

```
(Positive pair)   "Standing Calf Raise — Calves"  ↔  "Seated Calf Raise — Calves"
(Negative pair)   "Standing Calf Raise — Calves"  ↔  "Bench Press — Chest"
```

The training algorithm:
1. Take two related texts (positive pair) → embed both → compute their vectors
2. Take two unrelated texts (negative pair) → embed both → compute their vectors
3. **Loss function**: Pull positive vectors closer together (increase similarity), push negative vectors apart (decrease similarity)
4. After millions of examples, the model learns to place semantically similar texts near each other in the 512-dimensional space

The result:
- **"Calf" and "Calves"** end up in almost the same location in vector space because the training data showed they appear in similar contexts
- **"Calf" and "Shoulder"** end up far apart because they rarely appear together in fitness contexts

### Visual Summary of Embedding

```
Text: "Standing Calf Raise — Strength — Calves"
                    ↓
           [WordPiece Tokenizer]
                    ↓
    ["Stand", "##ing", "Calf", "Raise", "—", "Strength", "—", "Calves"]
                    ↓
           [Token Embedding Lookup]
                    ↓
  Each token → 512-number vector (starting values from training)
                    ↓
      [12× Transformer Layers with Self-Attention]
                    ↓
  Each token now has a 512-number vector that understands context
  ("Calf" now knows it's near "Raise" and "Calves" — not a baby cow)
                    ↓
           [Mean Pooling]
                    ↓
  Single 512-number vector representing the entire exercise
                    ↓
           [Stored in Qdrant vector database]
```

---

## 4. What Does "Dimension = 512" Mean?

### The Map Coordinates Analogy

Think of dimensions as **coordinates on a map**:

- A 2D map uses 2 coordinates (x, y) to locate a point — e.g., a restaurant at (51.5, -0.12) = London
- A 3D map uses 3 coordinates (x, y, z) to locate a point in space — e.g., a drone at (10, 20, 5) = 10m east, 20m north, 5m up
- A **512-dimensional map** uses 512 coordinates to locate a **concept** in "meaning space"

### Why 512 Dimensions Specifically?

The choice of 512 is a **trade-off**:

| Dimensions | Pros | Cons |
|-----------|------|------|
| **Low (128)** | Cheap storage, fast search | Can't capture enough nuance — "squat" and "deadlift" might look too similar |
| **Medium (512)** ← **OUR CHOICE** | Good balance: captures enough nuance for exercise descriptions while fitting in free-tier infrastructure | — |
| **High (1024-3072)** | Captures very fine semantic detail | Expensive storage, slower search, "curse of dimensionality" (distances become less meaningful) |

**Real-world comparisons**:
- OpenAI `text-embedding-3-small`: **1536 dimensions**
- OpenAI `text-embedding-3-large`: **3072 dimensions**
- Our Jina `jina-embeddings-v2-small-en`: **512 dimensions**
- Google's `text-embedding-004`: **768 dimensions**

Jina's 512 is sufficient for our use case because exercise descriptions are relatively short structured text — we don't need thousands of dimensions to distinguish calf raises from bicep curls.

### The Curse Of Dimensionality (Why Not 10,000?)

In high-dimensional spaces, all vectors tend to become **equally distant** from each other — a counterintuitive mathematical phenomenon. This makes similarity search less meaningful. 512 stays well below the threshold where this becomes a problem for our dataset size.

---

## 5. What Columns Are Used For Embedding And Why

The critical method is `get_text_embedding_string()` in `llm_interface.py` (line 158). It builds a single text string from these fields:

```
Exercise Name: Standing Calf Raise —
Type of Activity: Strength —
Equipment: Dumbbell —
Muscle Groups: Calves —
Body Part: Calves —
Description: A strength exercise targeting the calves... —
Instructions: Stand with feet shoulder-width apart, raise your heels...
```

### Why Each Column Is Included

| Column | Why It's Included | Example Query Match |
|--------|------------------|---------------------|
| **Exercise Name** | Direct name matching | "calf raise" → "Calf Raise" |
| **Type of Activity** | Matches goal/type queries | "stretching exercises" → "Stretching" |
| **Equipment** | Matches equipment filters | "with dumbbells" → "Dumbbell" |
| **Muscle Groups** | **Primary semantic signal** — the most important field for matching queries about body parts | "calf" → "Calves" |
| **Body Part** | Alternative body part signal, catches cases where user refers to "lower leg" instead of "calves" | "lower leg" → "Calves" |
| **Description** | Adds semantic richness about what the exercise does | "targets the gastrocnemius and soleus" |
| **Instructions** | The longest text field — provides the most semantic signal for the embedding model to work with | "raise your heels", "lower your heels" |

### What's NOT Embedded And Why

| Field | Reason Excluded |
|-------|----------------|
| **video_link** | `https://youtube.com/watch?v=...` has no semantic meaning for search — a URL tells you nothing about what the exercise is |
| **variations_on** | Secondary/optional metadata field. Excluded to keep the embedding text focused on the exercise's own identity |

### The Data Processing Pipeline

```
JSON file (500 exercises)
        ↓
helper.py: load_json_data()
  - Reads the V2 JSON structure
  - Normalises: flattens primary_muscles + secondary_muscles into muscle_groups_activated
  - Derives body_part from primary muscles
  - Joins list fields into comma-separated strings
        ↓
helper.py: clean_data()
  - Drops duplicates on exercise name
  - Lowercases column names, replaces spaces with underscores
        ↓
helper.py: create_document()
  - Converts DataFrame to list of dicts
        ↓
llm_interface.py: get_text_embedding_string()
  - Builds the embedding text from selected columns
  - Used for the **vector** (what gets searched)
        ↓
llm_interface.py: get_payload()
  - Stores ALL fields (including video_link, variations_on) as metadata
  - Used for the **payload** (what gets returned with search results)
```

**Key insight**: The vector (what's searched) and the payload (what's returned) can contain different fields. We embed only search-relevant fields, but return complete exercise information.

---

## 6. How Does The Vector DB Know "calf" Means Calf Exercises?

### Step-by-Step Walkthrough

When a user types **"give me exercises that build my calf"**, here's exactly what happens:

### Step 1: The Query Gets Embedded

The user query `"give me exercises that build my calf"` passes through the **same Jina embedding model** used during indexing. It becomes a 512-number vector.

### Step 2: Cosine Similarity Comparison

Qdrant compares the query vector against all 500 exercise vectors using **cosine similarity** — a mathematical measure of how "pointed in the same direction" two vectors are:

```
similarity = cos(θ) = (A · B) / (||A|| × ||B||)
```

**What this means in practice:**

| Scenario | Cosine Similarity | Interpretation |
|----------|------------------|----------------|
| Query vs "Standing Calf Raise" | **~0.85** | Very similar — excellent match |
| Query vs "Seated Calf Raise" | **~0.82** | Very similar — excellent match |
| Query vs "Squat" | **~0.45** | Somewhat similar — both are leg exercises |
| Query vs "Bench Press" | **~0.20** | Not similar — different body part |

### Step 3: Why Calf Exercises Win

The exercise "Standing Calf Raise" has this embedding text:
```
Exercise Name: Standing Calf Raise — Type of Activity: Strength —
Equipment: Dumbbell — Muscle Groups: Calves — Body Part: Calves —
Description: Targets the gastrocnemius... —
Instructions: Stand with feet shoulder-width apart, raise your heels...
```

Meanwhile, the user query is:
```
give me exercises that build my calf
```

The Jina model learned during training that:
- "calf" and "Calves" share subword token patterns (C-a-l-f / C-a-l-v-e-s)
- "calf" in fitness contexts appears near words like "raise", "heel", "leg"
- "calves" is the plural of "calf" — same semantic meaning
- The overall fitness-related language ("exercises", "build") aligns with strength exercise descriptions

So the vectors end up close together in the 512-dimensional space.

### Step 4: Top-3 Results Retrieved

Qdrant returns the 3 most similar exercises (our `response_limit = 3`). These always include calf-targeting exercises when the query mentions "calf".

### Step 5: Gemini Generates The Answer

The retrieved exercises (their full payloads including video links) are formatted into a context text and passed to Gemini along with the system prompt:

```
System: You're a fitness instructor. Answer the QUESTION based on the CONTEXT from our
exercises database. Use only the facts from the CONTEXT when answering.

Human:
QUESTION: give me exercises that build my calf

CONTEXT:
Exercise: Standing Calf Raise
Type of activity: Strength
Equipment: Dumbbell
Body part: Calves
Muscle groups: Calves
Instructions: Stand with feet shoulder-width apart...
Video link: https://www.youtube.com/watch?v=...

---

Exercise: Seated Calf Raise
Type of activity: Strength
Equipment: Dumbbell
Body part: Calves
Muscle groups: Calves
Instructions: Sit on a bench...
Video link: https://www.youtube.com/watch?v=...
```

Gemini then writes a human-friendly answer using **only** these exercises, with proper formatting, instructions, and video links.

---

## 7. Why Jina Embeddings V2 Small EN?

Four reasons for this specific model choice:

| Reason | Explanation |
|--------|-------------|
| **1. Model Size** | The "small" variant has ~35M parameters (vs ~110M for base). Runs efficiently on CPU — no GPU needed for inference. |
| **2. 512 Dimensions** | Balanced for free-tier Qdrant Cloud. Storage costs scale with dimensions (512 = ~4× cheaper than 2048). |
| **3. 8192 Token Limit** | Can handle the full concatenated text string for each exercise (name + type + equipment + muscles + description + instructions). Some models only support 512 tokens. |
| **4. English-Optimised** | "small-en" = optimised for English text. Our entire dataset is in English. |

**Potential alternatives** (from the [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)):
- `BAAI/bge-small-en-v1.5` — similar size, slightly better benchmark scores
- `sentence-transformers/all-MiniLM-L6-v2` — another popular lightweight option
- `intfloat/multilingual-e5-small` — if multilingual support is needed later

---

## 8. Why Gemini As The LLM?

Three reasons:

| Reason | Detail |
|--------|--------|
| **GCP Integration** | Future deployment on Google Cloud Run aligns with Gemini being a Google product. |
| **Multimodal** | Current dataset has video links. Gemini can process video natively, opening future possibilities like "show me the form check from this video." |
| **Generous Free Tier** | Gemini 2.5 Flash is free within rate limits — ideal for prototyping and small-scale use. |

---

## 9. What Is The Usefulness Of This RAG System?

Five key benefits:

### 1. No Hallucination
Without RAG, an AI might make up exercises like "Calf Stretch Machine" that don't exist in your database. With RAG, the LLM is **forced** to answer only from retrieved context. If it can't find calf exercises in the context, it must say so rather than inventing them.

### 2. Always Up-To-Date
To add a new exercise (e.g., "Nordic Curl"), you simply:
1. Add it to the JSON file
2. Re-run `--create-vectors` to embed and upsert it
3. Done — no retraining, no fine-tuning, no model updates

### 3. Traceability
Every answer can be traced back to the specific exercise records that informed it. This is critical for:
- Auditing (why did the AI recommend this exercise?)
- Debugging (is a wrong answer caused by bad retrieval or bad generation?)
- Quality improvement (which exercises are most commonly retrieved?)

### 4. Semantic Understanding
Unlike keyword search (which requires exact text matching), semantic search understands:
| Query | What It Matches |
|-------|----------------|
| "calf" | "Calves", "gastrocnemius", "heel raise", "lower leg" |
| "upper body push" | "Bench Press", "Push-Up", "Shoulder Press", "Overhead Press" |
| "no equipment" | exercises with `equipment: none` |
| "core work" | "Plank", "Crunches", "Russian Twist", "Dead Bug" |

### 5. Scalable
Vector search in Qdrant uses **HNSW (Hierarchical Navigable Small World)** graphs — a data structure that can search millions of vectors in milliseconds. Growing from 500 to 500,000 exercises would add only milliseconds to search time.

---

## 10. Ways To Improve — Reranking

### What Is Reranking?

Currently, the system uses **one-stage retrieval**:
1. Embed the query
2. Compare against all 500 exercise vectors
3. Take the top 3

With **reranking**, we use two stages:

```
Stage 1 (Cheap & Fast)            Stage 2 (Accurate)
     ↓                                  ↓
Query → Vector Search → Top 20 → Cross-Encoder → Top 3
                                  Reranker
```

### Why Two Stages?

- The first-stage vector search is **fast** but **approximate** — it's like looking at summaries of 500 books to find the most relevant 20
- The second-stage reranker is **slower** but **more accurate** — it reads each of the 20 shortlisted documents in full, paired with the query, and scores them more precisely

### How A Cross-Encoder Reranker Works

Unlike the embedding model (which encodes query and document separately), a cross-encoder takes **both query and document together** in one pass:

```
Input: "[CLS] give me exercises that build my calf [SEP] Standing Calf Raise:
        Stand with feet shoulder-width apart, raise your heels... [SEP]"

Output: relevance_score = 0.92  (highly relevant)
```

It uses **full cross-attention** between query tokens and document tokens — meaning every query word can attend to every document word. This is more computationally expensive (can't pre-compute for all 500 exercises) but much more accurate.

### Implementation Approach

```
from sentence_transformers import CrossEncoder

# Load a reranker model
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# After getting top 20 from Qdrant:
pairs = [(query, doc_text) for doc_text in top_20_docs]
scores = reranker.predict(pairs)  # Returns relevance scores

# Re-sort by score, take top 3
reranked_results = sorted(zip(top_20_docs, scores),
                          key=lambda x: x[1], reverse=True)[:3]
```

### Expected Improvement

| Metric | Without Reranker | With Reranker |
|--------|-----------------|---------------|
| Recall@3 | ~85% | ~95% |
| Precision@3 | ~80% | ~92% |

The reranker catches cases where:
- The query uses uncommon synonyms the embedding model didn't fully capture
- The most relevant document was ranked 4th or 5th by vector similarity but is actually the best match
- Multiple very similar exercises exist (reranker can better distinguish between them)

---

## 11. Generation Parameters

| Parameter | Value | What It Controls | Justification |
|-----------|-------|-----------------|---------------|
| temperature | 0.4 | Governs model randomness — how "creative" the output is | Reliability — model sticks closely to context from DB, less likely to make things up |
| top_k | 1 | Restricts model to choose only from the k most likely next tokens | Restrictive — ensures model selects the single most likely next token at each step |
| top_p | 1 | An alternative to top_k — cumulative probability threshold | A p-value of 1 tells Gemini to use temperature/top_k as primary output controller |
| max_output_tokens | 4000 | Maximum length of the LLM's response | Cost — restricts response length to what's needed for a few exercises |

---

## 12. Full End-to-End Code Flow

### Ingestion Phase (`--create-vectors` flag):

```
main() (llm_interface.py:318)
  │
  ├── argparser detects --create-vectors
  │
  ├── Prompt user: "Do you want to recreate the collection?"
  │     └── If yes → QdrantConfig(create_vectors=True, recreate_collection=True)
  │     └── If no  → QdrantConfig(create_vectors=True, recreate_collection=False)
  │
  └── rag(query, config)  (llm_interface.py:291)
        │
        └── ManageVectorDb(config)  (llm_interface.py:106)
              │
              ├── QdrantClient(url, api_key) — connects to Qdrant Cloud
              │
              ├── run_vector_embedding()  (llm_interface.py:228)
              │     │
              │     ├── load_data(file_path)  → helper.py:21
              │     │     └── Reads JSON, normalises to DataFrame
              │     │
              │     ├── clean_data(df)  → helper.py:110
              │     │     └── Deduplicates, lowercases columns
              │     │
              │     ├── create_document(df)  → helper.py:131
              │     │     └── DataFrame → list of dicts
              │     │
              │     ├── collection_exists()  → (checks if "exercise_collection" exists)
              │     │
              │     ├── create_collection(name, dimension=512)  → (creates Qdrant collection)
              │     │
              │     ├── create_points_and_insert(docs, model)  → llm_interface.py:209
              │     │     │
              │     │     ├── For each record:
              │     │     │   ├── get_text_embedding_string(record)
              │     │     │   │     → "Exercise Name: ... — Type of Activity: ... — ..."
              │     │     │   ├── models.Document(text=string, model="jinaai/jina-embeddings-v2-small-en")
              │     │     │   │     → Jina embeds text into 512-dim vector (via FastEmbed)
              │     │     │   └── get_payload(record, context_mapping)
              │     │     │         → All fields stored as metadata
              │     │     │
              │     │     └── client.upsert(collection, points) — sends to Qdrant
              │     │
              │     └── ✅ Collection ready — 500 vectors stored
```

### Query & Generation Phase:

```
main() (llm_interface.py:318)
  │
  ├── Prompt user: "Enter your Fitness question:"
  │     └── "give me exercises that build my calf"
  │
  └── rag(query, config)  (llm_interface.py:291)
        │
        ├── ManageVectorDb() — connects to Qdrant
        │     └── search(query)  (llm_interface.py:277)
        │           │
        │           ├── models.Document(text=query, model=embedding_model)
        │           │     → Jina embeds the query into a 512-dim vector
        │           │
        │           ├── client.query_points(
        │           │     collection_name="exercise_collection",
        │           │     query=embedded_query_vector,
        │           │     limit=3,          # Top 3 closest matches
        │           │     with_payload=True  # Return full exercise data
        │           │   )
        │           │     → Qdrant finds 3 nearest vectors by cosine similarity
        │           │
        │           └── Returns ScoredPoint array (3 closest exercises)
        │
        ├── format_vector_db_context(results)  → helper.py:138
        │     └── Converts each ScoredPoint's payload into readable text
        │         using context_mapping field labels
        │
        ├── LLMFlow()  (llm_interface.py:34)
        │     ├── ChatGoogleGenerativeAI(model="gemini-2.5-flash", ...)
        │     └── chain = prompt_template | llm
        │
        └── LLMFlow.run(query, context)  (llm_interface.py:91)
              │
              ├── chain.invoke({
              │     "question": "give me exercises that build my calf",
              │     "context": "Exercise: Standing Calf Raise\nType: Strength\n..."
              │   })
              │     → Gemini receives system prompt + context + question
              │     → Generates answer based ONLY on context
              │
              └── Returns final answer text
                    → Displayed to user via rich console panel
```

---

## Decision logic
1. elected jina-embeddings-v2-small-en because of the following:

 - modest model size and vector dimension, making it efficient to index and query in free-tier infrastructure

 - good semantic embedding capability for English, especially for relatively short structured text (exercise descriptions, instructions)

- compatibility with long input lengths (it supports up to 8192 tokens in its embedding family)

- balanced cost, performance, and resource usage

However, there are some potential models in the [mteb leaderboard](https://huggingface.co/spaces/mteb/leaderboard)  that may offer better performance.

2. Using Gemini
- A big part for this decision is because of easy integration to GCP
- while current RAG is text-based, dataset contains video links which is great as Gemini is multimodal
- Generous Free Tier

3. Generation Parameters
temperature(0.4), top_p(1), top_k(1), max_output_tokens(4000)

Attempt | temperature(0.4) |top_k(1) | top_p(1) | max_output_tokens(4000)
--- | --- | --- | --- |---
what it contols? | Governs model randomness | restrict model choice to the k most likely next tokens | An alternative to top_k. | LLM Output  |
Justification | Reliability. model sticks closely to context from db, and is less likely to make stuff up | restrictive. ensures model select only the single most likely next token at each point | a p-value of 1 tells Gemini to assign temperature/top_k as primary output controller | Cost  |


## E2E flowchart
 ```mermaid
flowchart TD
    %% Creation and Ingestion Flow
    Start[User Query] --> Script[Script Invocation<br>--create-vectors]
    Script --> Main[main Function<br>Parse Args]
    Main --> Check{Check --create-vectors}

    Check -- Yes --> InitLC[Initialize LangChainClient]
    InitLC --> InitDB[Create ManageVectorDb instance]
    InitDB --> RunEmbed[run_vector_embedding]
    RunEmbed --> LoadDocs[load_documents]
    LoadDocs --> CreatePts[create_points_and_insert]
    CreatePts --> GetStr[get_text_embedding_string]
    GetStr --> GetPay[get_payload]
    GetPay --> Upsert[upsert into Qdrant]

    %% Query and Retrieval Flow
    Upsert --> Query[User Query]
    Query --> Handle[Handle User Query]
    Handle --> GenEmbed[Generate Query Embedding]
    GenEmbed --> Search[Search in Qdrant]
    Search --> Retrieve[Retrieve Results]
    Retrieve --> GetResp[Get Response from Documents]
    GetResp --> LLM[LLM Response]

    %% Color Styling
    classDef ingestion fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef retrieval fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;

    class Script,Main,Check,InitLC,InitDB,RunEmbed,LoadDocs,CreatePts,GetStr,GetPay,Upsert ingestion;
    class Query,Handle,GenEmbed,Search,Retrieve,GetResp,LLM retrieval;
```

## Algorithm Reference: Cosine Similarity

The core mathematical operation that makes semantic search work:

```
cos(θ) = (A · B) / (||A|| × ||B||)

Where:
  A · B   = sum of (a₁×b₁ + a₂×b₂ + ... + a₅₁₂×b₅₁₂)  [dot product]
  ||A||   = sqrt(a₁² + a₂² + ... + a₅₁₂²)            [magnitude of A]
  ||B||   = sqrt(b₁² + b₂² + ... + b₅₁₂²)            [magnitude of B]
```

In simpler terms: it measures the **angle** between two vectors in 512-dimensional space. The smaller the angle, the more semantically similar the texts.

- **cos(θ) = 1**: Vectors point in exactly the same direction (identical meaning)
- **cos(θ) = 0**: Vectors are perpendicular (no relationship)
- **cos(θ) = -1**: Vectors point in opposite directions (opposite meaning)

## Algorithm Reference: Self-Attention (Transformer Core)

This is what powers the Jina embedding model. For each token in a sequence, self-attention computes:

```
For each token i:
  1. Compute Query(i) = W_q × token_vector(i)
  2. Compute Key(j)   = W_k × token_vector(j)  for all j
  3. Compute Value(j) = W_v × token_vector(j)  for all j

  4. attention_score(i, j) = softmax(Query(i) · Key(j) / √d)

  5. New_vector(i) = sum over j of [attention_score(i, j) × Value(j)]
```

Where W_q, W_k, W_v are learned weight matrices (different in each of the 12 layers). This runs in parallel across all tokens, then repeats 12 times (once per layer).

## Algorithm Reference: HNSW (Hierarchical Navigable Small World)

Qdrant uses this data structure internally for fast vector search. Think of it like a **multi-level map**:

- **Top level**: Only a few "landmark" vectors — coarse navigation
- **Middle levels**: More vectors — finer navigation
- **Bottom level**: All vectors — exact search

Search starts at the top (coarse) and drills down:
1. Find the nearest landmark vector at the top level
2. Follow connections to nearby vectors at the next level
3. Repeat until reaching the bottom level with the true nearest neighbours

This gives **O(log n)** search time — even with 500,000 vectors, search takes only a few milliseconds.
