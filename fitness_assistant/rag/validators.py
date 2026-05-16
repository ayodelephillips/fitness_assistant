"""
Pydantic validators for RAG output and input validation.
Prevents prompt injection and ensures output schema compliance.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class ExerciseRecommendation(BaseModel):
    """Validated exercise recommendation from LLM."""

    exercise_name: str = Field(..., description="Name of the exercise")
    type_of_activity: str = Field(..., description="Type of activity (e.g., Strength)")
    equipment: str = Field(..., description="Equipment needed")
    body_part: str = Field(..., description="Primary body part targeted")
    muscle_groups: List[str] = Field(
        ..., description="Muscle groups activated"
    )
    instructions: str = Field(..., description="Step-by-step instructions")
    video_link: Optional[str] = Field(None, description="URL to demo video")

    @validator("exercise_name", "type_of_activity", "equipment", "body_part")
    def sanitize_string_fields(cls, v):
        """Remove potential injection patterns from string fields."""
        if not isinstance(v, str):
            raise ValueError("Field must be a string")
        # Remove common injection patterns
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)  # Remove control characters
        if len(v) > 500:
            raise ValueError("Field value too long")
        return v.strip()

    @validator("instructions")
    def validate_instructions(cls, v):
        """Validate instructions field."""
        if not isinstance(v, str):
            raise ValueError("Instructions must be a string")
        if len(v) < 10:
            raise ValueError("Instructions too short")
        if len(v) > 2000:
            raise ValueError("Instructions too long")
        return v.strip()

    @validator("video_link")
    def validate_video_link(cls, v):
        """Validate video link is a proper URL."""
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Video link must be a string")
        # Basic URL validation
        if not v.startswith(("http://", "https://", "www.")):
            raise ValueError("Invalid video link format")
        if len(v) > 500:
            raise ValueError("Video link too long")
        return v


class RAGResponse(BaseModel):
    """Validated RAG response from LLM."""

    answer: str = Field(..., description="The main answer to the user query")
    recommendations: List[ExerciseRecommendation] = Field(
        default_factory=list, description="List of exercise recommendations"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score of the answer"
    )
    sources: List[str] = Field(
        default_factory=list, description="Sources used for the answer"
    )

    @validator("answer")
    def validate_answer(cls, v):
        """Validate the main answer."""
        if not isinstance(v, str):
            raise ValueError("Answer must be a string")
        if len(v) < 10:
            raise ValueError("Answer too short")
        if len(v) > 5000:
            raise ValueError("Answer too long")
        # Remove control characters
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        return v.strip()

    @validator("confidence")
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")
        return v


class UserQuery(BaseModel):
    """Validated user query for the RAG system."""

    query: str = Field(..., min_length=1, max_length=500)
    user_id: Optional[str] = Field(None, max_length=50)
    session_id: Optional[str] = Field(None, max_length=50)

    @validator("query")
    def sanitize_query(cls, v):
        """Remove potential injection patterns from user query."""
        if not isinstance(v, str):
            raise ValueError("Query must be a string")

        # Remove null bytes and other control characters
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)

        # Remove common prompt injection patterns
        injection_patterns = [
            r"(?i)(ignore|forget|disregard)\s+(all\s+)?previous",
            r"(?i)(you\s+are|you\'re)\s+now",
            r"(?i)(do\s+not|don\'t)\s+follow",
            r"(?i)system\s+prompt",
            r"(?i)reset\s+(your\s+)?instructions",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, v):
                logger.warning(f"Potential injection pattern detected in query: {v}")
                raise ValueError("Query contains suspicious patterns")

        return v.strip()

    @validator("user_id", "session_id")
    def validate_ids(cls, v):
        """Validate user and session IDs."""
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", v):
            raise ValueError("Invalid ID format")
        return v


class QueryRateLimitConfig(BaseModel):
    """Configuration for query rate limiting."""

    max_queries_per_minute: int = Field(default=60, ge=1)
    max_queries_per_hour: int = Field(default=1000, ge=1)
    max_daily_queries: int = Field(default=10000, ge=1)
    max_concurrent_requests: int = Field(default=10, ge=1)

    @validator("max_queries_per_minute")
    def validate_minute_limit(cls, v):
        """Ensure per-minute limit is reasonable."""
        if v > 1000:
            raise ValueError("Per-minute limit too high")
        return v


def validate_llm_response(response_text: str) -> dict:
    """
    Try to parse and validate LLM response as structured output.
    Falls back to treating it as plain text if parsing fails.

    Args:
        response_text: Raw text response from LLM

    Returns:
        Validated response dictionary or error dict

    """
    import json

    try:
        # Try parsing as JSON
        response_data = json.loads(response_text)

        # Try to validate as RAGResponse
        validated = RAGResponse(**response_data)
        return {"valid": True, "data": validated.model_dump()}

    except json.JSONDecodeError:
        # Not JSON, treat as plain text answer
        try:
            validated = RAGResponse(
                answer=response_text,
                recommendations=[],
                confidence=0.7,  # Default confidence for unstructured responses
            )
            return {"valid": True, "data": validated.model_dump()}

        except Exception as e:
            logger.error(f"Failed to validate response: {e}")
            return {
                "valid": False,
                "error": str(e),
                "raw_response": response_text[:500],
            }


def validate_user_input(query: str, user_id: Optional[str] = None) -> dict:
    """
    Validate and sanitize user input.

    Args:
        query: User's query string
        user_id: Optional user identifier

    Returns:
        Dictionary with validation result and sanitized data or error

    """
    try:
        user_query = UserQuery(query=query, user_id=user_id)
        return {"valid": True, "data": user_query.model_dump()}
    except Exception as e:
        logger.warning(f"User input validation failed: {e}")
        return {"valid": False, "error": str(e)}
