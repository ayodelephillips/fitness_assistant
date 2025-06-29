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

Pipenv is used to manage packages and dependencies using a pipfile.

Make sure you have pipenv installed.

```bash
pip install pipenv
```

Installing the dependencies:

```bash
pipenv install
```


Running Jupyter Notebook for experiments
```bash
cd notebooks
pipenv run jupyter notebook
```




## Evaluation


## Retrieval

## RAg Flow


## Monitoring


deploying model on docker container - https://chatgpt.com/share/67fc3eff-21e0-8007-9f03-a7575d0fb78a
