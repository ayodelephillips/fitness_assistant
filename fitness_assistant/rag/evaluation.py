from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import csv
import time
from datetime import datetime

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
from fitness_assistant.rag.logging_config import RAGLogger
from fitness_assistant.rag.monitoring import HallucinationDetector
from deepeval.models import GeminiModel
import uuid

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
    Creates a comprehensive evaluation set for the fitness assistant.
    Includes diverse queries across different exercise types, equipment, and goals.
    """
    return EvaluationSet(
        name="fitness_comprehensive_evaluation_set",
        cases=[
            # Bicep exercises
            EvaluationCase(
                query="What's a good exercise for biceps?",
                expected_answer="A good exercise for biceps is the Bicep Curl. It involves using dumbbells to curl the weight up towards your shoulders. Other options include barbell curls or resistance band curls.",
            ),
            # Squat variations
            EvaluationCase(
                query="How do I perform a squat?",
                expected_answer="To perform a squat, stand with your feet shoulder-width apart, lower your hips as if sitting in a chair, keep your chest up and weight in your heels, then push through your heels to stand back up.",
            ),
            # Leg exercises
            EvaluationCase(
                query="I want to work my leg muscles, what do you suggest?",
                expected_answer="For leg muscles, you can do exercises like Squats (quadriceps, glutes), Lunges (quads, hamstrings, glutes), Leg Press (quads, hamstrings, glutes), or Calf Raises (calves).",
            ),
            # Chest exercises
            EvaluationCase(
                query="What exercises target the chest without equipment?",
                expected_answer="Bodyweight chest exercises include Push-ups, Pike Push-ups, Diamond Push-ups, and Chest Dips. These effectively work the pectoralis major and minor.",
            ),
            # Upper body
            EvaluationCase(
                query="Show me upper body exercises with resistance bands",
                expected_answer="Resistance band upper body exercises include Chest Press, Shoulder Press, Bicep Curls, Tricep Extensions, Face Pulls, and Rows. These provide variable resistance throughout the range of motion.",
            ),
            # Core exercises
            EvaluationCase(
                query="How can I strengthen my core?",
                expected_answer="Core strengthening exercises include Planks, Dead Bugs, Bird Dogs, Crunches, Russian Twists, and Leg Raises. These target the abdominals, obliques, and lower back.",
            ),
            # Full body
            EvaluationCase(
                query="What's a good full body workout?",
                expected_answer="A full body workout should include exercises for all major muscle groups: chest (push-ups), back (rows), legs (squats), shoulders (overhead press), and core (planks). Aim for 3-4 exercises per session.",
            ),
            # Equipment selection
            EvaluationCase(
                query="I only have dumbbells, what exercises can I do?",
                expected_answer="With dumbbells, you can do a complete workout: Dumbbell Rows, Dumbbell Presses, Dumbbell Curls, Dumbbell Squats, Dumbbell Deadlifts, and Dumbbell Chest Presses. These work all major muscle groups.",
            ),
            # Specific muscle group
            EvaluationCase(
                query="Which exercises work the shoulders?",
                expected_answer="Shoulder exercises include Shoulder Press, Lateral Raises, Front Raises, Rear Delt Flyes, Shrugs, and Upright Rows. These target the deltoids (anterior, medial, and posterior).",
            ),
            # Stretching/Recovery
            EvaluationCase(
                query="What are good stretches for tight hamstrings?",
                expected_answer="Hamstring stretches include Standing Forward Fold, Seated Forward Fold, Lying Hamstring Stretch, and Yoga Poses like Downward Dog. Hold each stretch for 30 seconds.",
            ),
        ],
    )


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""

    query: str
    actual_answer: str
    expected_answer: str
    retrieved_context: str
    answer_relevancy_score: Optional[float] = None
    faithfulness_score: Optional[float] = None
    contextual_recall_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    passed_relevancy: Optional[bool] = None
    passed_faithfulness: Optional[bool] = None
    passed_recall: Optional[bool] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RagEvaluator:
    """
    Runs the RAG pipeline for given queries and evaluates the output
    using DeepEval metrics and additional custom metrics.
    """

    def __init__(self, evaluation_threshold: float = 0.7):
        """
        Initialize evaluator.

        Args:
            evaluation_threshold: Minimum score to pass evaluation (0-1)
        """
        self.vector_db = ManageVectorDb()
        self.llm_flow = LLMFlow()
        self.threshold = evaluation_threshold
        self.hallucination_detector = HallucinationDetector(threshold=0.5)
        self.results: List[EvaluationResult] = []

    def run_pipeline(self, query: str, trace_id: str = "") -> Dict[str, Any]:
        """
        Executes the full RAG pipeline: search, format, and generate.

        Returns a dictionary containing the actual answer, retrieved context,
        and the original query.
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        rag_logger = RAGLogger(trace_id)

        # 1. get context
        search_results = self.vector_db.search(query=query, trace_id=trace_id)
        retrieved_context = format_vector_db_context(search_results.points)
        logging.info(
            f"Retrieved context for query '{query}':\n{retrieved_context[:300]}..."
        )

        # 2.get llm response
        actual_answer = self.llm_flow.run(query=query, context=retrieved_context, trace_id=trace_id)
        logging.info(f"Generated answer for query '{query}':\n{actual_answer}")

        return {
            "actual_answer": actual_answer,
            "retrieved_context": retrieved_context,
            "query": query,
            "trace_id": trace_id,
        }

    def evaluate(self, eval_set: EvaluationSet) -> Dict[str, Any]:
        """
        Evaluates the RAG system against a full evaluation set.
        Uses DeepEval metrics and custom hallucination detection.

        Returns comprehensive evaluation report.
        """
        test_cases = []
        self.results.clear()

        config = LlmConfig()
        eval_model = GeminiModel(
            model_name=GenAIModels.gemini_2_5_flash, api_key=config.google_api_key
        )

        for case in eval_set.cases:
            logging.info(f"Evaluating query: {case.query}")
            pipeline_output = self.run_pipeline(case.query)

            # Detect hallucinations
            hallucination_result = self.hallucination_detector.detect(
                pipeline_output["actual_answer"],
                pipeline_output["retrieved_context"],
            )

            # Create a test case for the deepeval library
            test_case = LLMTestCase(
                input=pipeline_output["query"],
                actual_output=pipeline_output["actual_answer"],
                expected_output=case.expected_answer,
                retrieval_context=[pipeline_output["retrieved_context"]],
            )
            test_cases.append(test_case)

            # Store evaluation result
            result = EvaluationResult(
                query=case.query,
                actual_answer=pipeline_output["actual_answer"],
                expected_answer=case.expected_answer,
                retrieved_context=pipeline_output["retrieved_context"],
                hallucination_score=hallucination_result.score,
            )
            self.results.append(result)

            logging.info("Waiting to avoid hitting API rate limit...")
            time.sleep(35)

        logging.info(f"Prepared {len(test_cases)} test cases for evaluation")

        # Define evaluation metrics
        metrics = [
            AnswerRelevancyMetric(threshold=self.threshold, model=eval_model),
            FaithfulnessMetric(threshold=self.threshold, model=eval_model),
            ContextualRecallMetric(threshold=self.threshold, model=eval_model),
        ]

        print("\n--- Starting RAG Evaluation ---")
        time.sleep(60)

        # Run the evaluation
        evaluate(test_cases=test_cases, metrics=metrics)

        # Process and store results
        for i, test_case in enumerate(test_cases):
            if i < len(self.results):
                # Extract metric scores from test case (DeepEval adds them)
                if hasattr(test_case, "metrics"):
                    for metric in test_case.metrics:
                        if "relevancy" in metric.name.lower():
                            self.results[i].answer_relevancy_score = metric.score
                            self.results[i].passed_relevancy = metric.score >= self.threshold
                        elif "faithfulness" in metric.name.lower():
                            self.results[i].faithfulness_score = metric.score
                            self.results[i].passed_faithfulness = (
                                metric.score >= self.threshold
                            )
                        elif "recall" in metric.name.lower():
                            self.results[i].contextual_recall_score = metric.score
                            self.results[i].passed_recall = metric.score >= self.threshold

        print("--- RAG Evaluation Complete ---\n")
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report with statistics."""
        if not self.results:
            return {"status": "no_results"}

        # Calculate statistics
        relevancy_scores = [
            r.answer_relevancy_score
            for r in self.results
            if r.answer_relevancy_score is not None
        ]
        faithfulness_scores = [
            r.faithfulness_score for r in self.results if r.faithfulness_score is not None
        ]
        recall_scores = [
            r.contextual_recall_score
            for r in self.results
            if r.contextual_recall_score is not None
        ]
        hallucination_scores = [
            r.hallucination_score for r in self.results if r.hallucination_score is not None
        ]

        relevancy_passed = sum(
            1 for r in self.results if r.passed_relevancy is True
        )
        faithfulness_passed = sum(
            1 for r in self.results if r.passed_faithfulness is True
        )
        recall_passed = sum(1 for r in self.results if r.passed_recall is True)

        report = {
            "evaluation_date": datetime.now().isoformat(),
            "total_cases": len(self.results),
            "threshold": self.threshold,
            "metrics": {
                "answer_relevancy": {
                    "average": (
                        sum(relevancy_scores) / len(relevancy_scores)
                        if relevancy_scores
                        else 0
                    ),
                    "min": min(relevancy_scores) if relevancy_scores else 0,
                    "max": max(relevancy_scores) if relevancy_scores else 0,
                    "passed": relevancy_passed,
                    "pass_rate": (
                        relevancy_passed / len(self.results) if self.results else 0
                    ),
                },
                "faithfulness": {
                    "average": (
                        sum(faithfulness_scores) / len(faithfulness_scores)
                        if faithfulness_scores
                        else 0
                    ),
                    "min": min(faithfulness_scores) if faithfulness_scores else 0,
                    "max": max(faithfulness_scores) if faithfulness_scores else 0,
                    "passed": faithfulness_passed,
                    "pass_rate": (
                        faithfulness_passed / len(self.results) if self.results else 0
                    ),
                },
                "contextual_recall": {
                    "average": (
                        sum(recall_scores) / len(recall_scores) if recall_scores else 0
                    ),
                    "min": min(recall_scores) if recall_scores else 0,
                    "max": max(recall_scores) if recall_scores else 0,
                    "passed": recall_passed,
                    "pass_rate": recall_passed / len(self.results) if self.results else 0,
                },
                "hallucination": {
                    "average": (
                        sum(hallucination_scores) / len(hallucination_scores)
                        if hallucination_scores
                        else 0
                    ),
                    "min": min(hallucination_scores) if hallucination_scores else 0,
                    "max": max(hallucination_scores) if hallucination_scores else 0,
                    "flagged": sum(1 for s in hallucination_scores if s > 0.5),
                },
            },
        }

        return report

    def save_results(self, output_path: Optional[str] = None) -> str:
        """
        Save evaluation results to a JSON file.

        Args:
            output_path: Path to save results (default: logs/evaluation_results.json)

        Returns:
            Path where results were saved
        """
        if output_path is None:
            output_dir = Path(__file__).resolve().parent.parent.parent / "logs"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "evaluation_results.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert results to serializable format
        results_data = []
        for result in self.results:
            results_data.append(
                {
                    "query": result.query,
                    "actual_answer": result.actual_answer,
                    "expected_answer": result.expected_answer,
                    "answer_relevancy_score": result.answer_relevancy_score,
                    "faithfulness_score": result.faithfulness_score,
                    "contextual_recall_score": result.contextual_recall_score,
                    "hallucination_score": result.hallucination_score,
                    "passed_relevancy": result.passed_relevancy,
                    "passed_faithfulness": result.passed_faithfulness,
                    "passed_recall": result.passed_recall,
                    "timestamp": result.timestamp,
                }
            )

        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)

        logging.info(f"Evaluation results saved to {output_path}")
        return str(output_path)

    def save_report(self, output_path: Optional[str] = None) -> str:
        """
        Save evaluation report to a JSON file.

        Args:
            output_path: Path to save report (default: logs/evaluation_report.json)

        Returns:
            Path where report was saved
        """
        if output_path is None:
            output_dir = Path(__file__).resolve().parent.parent.parent / "logs"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "evaluation_report.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        report = self.generate_report()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logging.info(f"Evaluation report saved to {output_path}")
        return str(output_path)


if __name__ == "__main__":
    evaluation_set = get_evaluation_set()
    logging.info(f"Evaluation set: {evaluation_set.name} with {len(evaluation_set.cases)} cases")
    
    evaluator = RagEvaluator(evaluation_threshold=0.7)
    report = evaluator.evaluate(evaluation_set)
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(json.dumps(report, indent=2))
    
    # Save results and report
    evaluator.save_results()
    evaluator.save_report()
    
    print("\nResults and report saved to logs/ directory")
