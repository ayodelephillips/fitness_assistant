# TF-IDF and Cosine Similarity in the Search Index

This document provides an explanation of how **TF-IDF (Term Frequency-Inverse Document Frequency)** and **cosine similarity** work within the search index implementation.

## 🚀 **Overview**

The search index uses TF-IDF to convert text into numerical vectors and applies cosine similarity to measure the similarity between a query and the documents in the index.

- **TF-IDF** highlights important words in the text by balancing how often words appear in a document vs. across all documents.
- **Cosine Similarity** compares the query vector and document vectors to determine how similar they are.

---

## 🛠 **How TF-IDF Works**

### 1. **Term Frequency (TF)**
Term Frequency measures how often a word appears in a document. The formula is:

\[ \text{TF}(t, d) = \frac{\text{Number of times term } t \text{ appears in document } d}{\text{Total number of terms in document } d} \]

- Common words like **"is"** or **"the"** may have a high TF but aren't always useful.

### 2. **Inverse Document Frequency (IDF)**
Inverse Document Frequency reduces the importance of common words that appear in many documents. The formula is:

\[ \text{IDF}(t, D) = \log \left( \frac{\text{Total number of documents } |D|}{1 + \text{Number of documents containing } t} \right) \]

- Rare words like **"neural network"** will have a higher IDF.

### 3. **TF-IDF Score**
Multiplying the TF and IDF gives the final TF-IDF score for a word in a document:

\[ \text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D) \]

---

## 🧑‍💻 **Using TF-IDF in the Search Index**

In the provided code, TF-IDF is applied using the `TfidfVectorizer` from `sklearn`. Here’s how it works step by step:

1. **Initialize Vectorizers**:
    ```python
    self.vectorizers = {field: TfidfVectorizer(**vectorizer_params) for field in text_fields}
    ```

2. **Fit Documents to Create TF-IDF Matrices**:
    ```python
    texts = [doc.get(field, '') for doc in docs]
    self.text_matrices[field] = self.vectorizers[field].fit_transform(texts)
    ```

- Each matrix contains the TF-IDF scores for all documents, with one matrix per text field.

---

## 📐 **How Cosine Similarity Works**

After converting text into vectors using TF-IDF, cosine similarity is used to measure the similarity between a query and each document.

### **Formula for Cosine Similarity**

\[ \text{cosine similarity} (A, B) = \frac{A \cdot B}{\|A\| \|B\|} \]

Where:
- \( A \cdot B \) is the dot product of the two vectors.
- \( \|A\| \) and \( \|B\| \) are the magnitudes (lengths) of the vectors.

### **Implementation in the Code**

1. **Transform the Query into a Vector**:
    ```python
    query_vecs = {field: self.vectorizers[field].transform([query]) for field in self.text_fields}
    ```

2. **Compute Cosine Similarity**:
    ```python
    sim = cosine_similarity(query_vec, self.text_matrices[field]).flatten()
    ```

- This produces similarity scores for each document based on how closely they match the query.

3. **Boost Results (Optional)**:
    You can assign higher importance to specific fields using the `boost_dict`.
    ```python
    boost = boost_dict.get(field, 1)
    scores += sim * boost
    ```

---

## 🧪 **Example Walkthrough**

Let’s assume you have the following documents:

```python
documents = [
    {"title": "Learn Python", "content": "Python is a great programming language.", "category": "Programming"},
    {"title": "Cooking Pasta", "content": "Learn how to cook delicious pasta recipes.", "category": "Food"},
    {"title": "Data Science with Python", "content": "Explore data science using Python.", "category": "Data Science"}
]
```

### **Performing a Search**
```python
index = Index(text_fields=["title", "content"], keyword_fields=["category"])
index.fit(documents)

# Search query
results = index.search(
    query="Python programming",
    boost_dict={"title": 2, "content": 1},
    num_results=3
)
print(results)
```

### **Explanation**
- The query "Python programming" is vectorized using TF-IDF.
- Cosine similarity is calculated between the query and each document.
- Boosting applies a higher weight to matches in the **title**.
- The top results are returned based on similarity scores.

---

## 📦 **Conclusion**
- TF-IDF captures the relevance of words within documents.
- Cosine similarity measures how well a query matches the documents.
- Boosting and filtering improve the quality of search results.

This combination is efficient for building search engines, chatbots, or recommendation systems.

---

For any further explanations or troubleshooting, feel free to reach out!

