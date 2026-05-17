"""
Centralized logging configuration for the RAG pipeline.
Provides structured JSON logging, request/response tracking, and error alerting.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "user_query"):
            log_data["user_query"] = record.user_query
        if hasattr(record, "response_time_ms"):
            log_data["response_time_ms"] = record.response_time_ms
        if hasattr(record, "retrieval_count"):
            log_data["retrieval_count"] = record.retrieval_count
        if hasattr(record, "hallucination_score"):
            log_data["hallucination_score"] = record.hallucination_score

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance with both file and console handlers.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # JSON file handler for structured logs
        json_handler = RotatingFileHandler(
            LOGS_DIR / "rag_pipeline.json.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())

        # Console handler for human-readable output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        logger.addHandler(json_handler)
        logger.addHandler(console_handler)

    return logger


class RAGLogger:
    """Helper class for logging RAG-specific events with context."""

    def __init__(self, trace_id: str):
        """
        Initialize RAG logger with trace ID for request tracking.

        Args:
            trace_id: Unique identifier for tracing this request end-to-end
        """
        self.logger = get_logger("fitness_assistant.rag")
        self.trace_id = trace_id

    def _log_with_context(
        self,
        level: int,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Log with trace_id and additional context."""
        extra = {"trace_id": self.trace_id}
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)

    def log_query_received(self, query: str) -> None:
        """Log when a user query is received."""
        self._log_with_context(
            logging.INFO, f"Query received: {query}", user_query=query
        )

    def log_retrieval_start(self) -> None:
        """Log when retrieval from vector DB starts."""
        self._log_with_context(logging.DEBUG, "Starting vector DB retrieval")

    def log_retrieval_complete(
        self,
        num_results: int,
        scores: Optional[list] = None,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """
        Log when retrieval is complete.

        Args:
            num_results: Number of documents retrieved
            scores: Relevance scores of retrieved documents
            response_time_ms: Time taken for retrieval
        """
        self._log_with_context(
            logging.INFO,
            f"Retrieval complete: {num_results} documents retrieved",
            retrieval_count=num_results,
            response_time_ms=response_time_ms,
        )
        if scores:
            self.logger.debug(
                f"Retrieval scores: {scores}", extra={"trace_id": self.trace_id}
            )

    def log_llm_call_start(self) -> None:
        """Log when LLM is being called."""
        self._log_with_context(logging.DEBUG, "Starting LLM inference")

    def log_llm_call_complete(self, response_time_ms: Optional[float] = None) -> None:
        """Log when LLM call is complete."""
        self._log_with_context(
            logging.INFO,
            "LLM inference complete",
            response_time_ms=response_time_ms,
        )

    def log_hallucination_check(self, score: float, is_hallucinating: bool) -> None:
        """
        Log hallucination detection result.

        Args:
            score: Hallucination score (0-1, higher = more hallucination)
            is_hallucinating: Whether hallucination was detected
        """
        self._log_with_context(
            logging.WARNING if is_hallucinating else logging.INFO,
            f"Hallucination check: score={score:.2f}, is_hallucinating={is_hallucinating}",
            hallucination_score=score,
        )

    def log_error(self, error: Exception, context: str = "") -> None:
        """
        Log an error with context.

        Args:
            error: The exception that occurred
            context: Additional context about where/why the error occurred
        """
        self._log_with_context(
            logging.ERROR, f"Error occurred: {context} - {str(error)}", exc_info=True
        )

    def log_response_sent(self, response_length: int) -> None:
        """Log when response is sent to user."""
        self._log_with_context(
            logging.INFO, f"Response sent to user ({response_length} chars)"
        )


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger for the entire application.

    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
    """
    root_logger = logging.getLogger("fitness_assistant")
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # JSON file handler
    json_handler = RotatingFileHandler(
        LOGS_DIR / "fitness_assistant.json.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    json_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(json_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(console_handler)
