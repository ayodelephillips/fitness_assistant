from dataclasses import dataclass, field
from typing import List, Dict, Any

from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRecallMetric,
)
from deepeval.test_case import LLMTestCase

from fitness_assistant.rag.llm_interface import ManageVectorDb, LLMFlow
from fitness_assistant.rag.helper import format_vector_db_context
from fitness_assistant.rag.settings import LlmConfig, GenAIModels
from deepeval.models import GeminiModel
import time

import logging

logging.basicConfig(level=logging.INFO)


@dataclass
class EvaluationCase:
    """Represents a single question-answer pair for evaluation."""

    query: str
    expected_answer: str  # A ground-truth or ideal answer


@dataclass
class EvaluationSet:
    """A collection of evaluation cases."""

    name: str
    cases: List[EvaluationCase] = field(default_factory=list)


def get_evaluation_set() -> EvaluationSet:
    """
    Creates a sample evaluation set for the fitness assistant.
    # TODO- load from file
    """
    return EvaluationSet(
        name="fitness_bicep_and_leg_workout_eval",
        cases=[
            EvaluationCase(
                query="What's a good exercise for biceps?",
                expected_answer="A good exercise for biceps is the Bicep Curl. It involves using dumbbells to curl the weight up towards your shoulders.",
            ),
            EvaluationCase(
                query="How do I perform a squat?",
                expected_answer="To perform a squat, you should stand with your feet shoulder-width apart, lower your hips as if sitting in a chair, and keep your chest up.",
            ),
            EvaluationCase(
                query="I want to work my leg muscles, what do you suggest?",
                expected_answer="For leg muscles, you can do exercises like Squats, which work the quadriceps and glutes, or Lunges.",
            ),
        ],
    )


class RagEvaluator:
    """
    Runs the RAG pipeline for a given query and evaluates the output.
    """

    def __init__(self):
        self.vector_db = ManageVectorDb()
        self.llm_flow = LLMFlow()

    def run_pipeline(self, query: str) -> Dict[str, Any]:
        """
        Executes the full RAG pipeline: search, format, and generate.

        Returns a dictionary containing the actual answer, retrieved context,
        and the original query.
        """
        # 1. get context
        search_results = self.vector_db.search(query=query)
        retrieved_context = format_vector_db_context(search_results.points)
        logging.info(
            f"Retrieved context for query '{query}':\n{retrieved_context[:300]}..."
        )

        # 2.get llm response
        actual_answer = self.llm_flow.run(query=query, context=retrieved_context)
        logging.info(f"Generated answer for query '{query}':\n{actual_answer}")

        return {
            "actual_answer": actual_answer,
            "retrieved_context": retrieved_context,
            "query": query,
        }

    def evaluate(self, eval_set: EvaluationSet) -> None:
        """
        Evaluates the RAG system against a full evaluation set.

        params: eval_set - An EvaluationSet containing multiple EvaluationCase instances.
        """
        test_cases = []
        for case in eval_set.cases:
            logging.info(f"Evaluating query: {case.query}")
            pipeline_output = self.run_pipeline(case.query)

            # Create a test case for the deepeval library
            test_case = LLMTestCase(
                input=pipeline_output["query"],
                actual_output=pipeline_output["actual_answer"],
                expected_output=case.expected_answer,
                retrieval_context=[pipeline_output["retrieved_context"]],
            )
            test_cases.append(test_case)

            logging.info("Waiting to avoid hitting API rate limit...")
            time.sleep(35)

        logging.info(f"Test cases:{test_cases}")

        config = LlmConfig()
        eval_model = GeminiModel(
            model_name=GenAIModels.gemini_2_5_flash, api_key=config.google_api_key
        )
        metrics = [
            AnswerRelevancyMetric(
                threshold=0.7, model=eval_model
            ),  # Is the answer relevant to the query?
            FaithfulnessMetric(
                threshold=0.7, model=eval_model
            ),  # Does the answer stick to the facts in the context? (Anti-hallucination)
            ContextualRecallMetric(
                threshold=0.7, model=eval_model
            ),  # Does the context contain all the info needed to answer? (Retrieval quality)
        ]

        print("\n--- Starting RAG Evaluation ---")

        time.sleep(60)
        # Run the evaluation
        evaluate(test_cases=test_cases, metrics=metrics)
        print("--- RAG Evaluation Complete ---")


# if __name__ == "__main__":
#     evaluation_set = get_evaluation_set()
#     logging.info(f"Evaluation set: {evaluation_set}")
#     evaluator = RagEvaluator()
#     evaluator.evaluate(evaluation_set)

if __name__ == "__main__":
    config = LlmConfig()
    eval_model = GeminiModel(
        model_name=GenAIModels.gemini_2_5_flash, api_key=config.google_api_key
    )
