import json
from typing import Dict, Any, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class AnalyzeResponseInput(BaseModel):
    """Input for response analysis."""

    response_text: str = Field(description="The user's response to analyze")
    conversation_history: List[Dict[str, str]] = Field(
        description="Previous conversation turns"
    )


class ProfileAnalyzerTool(BaseTool):
    """Tool to analyze user responses and extract implicit signals."""

    name: str = "profile_analyzer"
    description: str = """Analyzes a user's response to extract implicit signals like vocabulary richness, 
    response brevity, and engagement level. Use this to adapt your questioning strategy."""

    def _run(
        self, response_text: str, conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Analyze a user response for implicit signals."""
        words = response_text.split()
        unique_words = set(word.lower() for word in words)

        # Calculate vocabulary richness (unique words / total words)
        vocab_richness = len(unique_words) / len(words) if words else 0

        # Response brevity (inverse of word count, normalized)
        brevity = max(0, 1 - (len(words) / 100))

        # Simple engagement heuristic
        has_examples = any(
            indicator in response_text.lower()
            for indicator in ["like", "such as", "for example", "because"]
        )
        has_emotion = any(
            word in response_text.lower()
            for word in ["love", "hate", "amazing", "terrible", "boring"]
        )
        engagement = 0.5 + (0.25 if has_examples else 0) + (0.25 if has_emotion else 0)

        return {
            "vocabulary_richness": round(vocab_richness, 2),
            "response_brevity": round(brevity, 2),
            "engagement_level": round(engagement, 2),
            "word_count": len(words),
            "analysis": self._generate_analysis(
                vocab_richness, brevity, engagement, len(words)
            ),
        }

    def _generate_analysis(
        self, vocab: float, brevity: float, engagement: float, word_count: int
    ) -> str:
        """Generate human-readable analysis."""
        style = "terse" if word_count < 20 else "detailed" if word_count > 60 else "moderate"
        engagement_level = "high" if engagement > 0.7 else "moderate" if engagement > 0.4 else "low"

        return f"Response style: {style}. Engagement: {engagement_level}. Suggest {'binary choices' if brevity > 0.7 else 'open-ended follow-ups'}."


class ConversationAnalyzerTool(BaseTool):
    """Tool to analyze overall conversation patterns."""

    name: str = "conversation_analyzer"
    description: str = """Analyzes the full conversation to identify patterns, extract preferences, 
    and determine if enough information has been gathered."""

    def _run(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation history for patterns."""
        if not conversation_history:
            return {
                "turn_count": 0,
                "coverage": {},
                "ready_for_summary": False,
            }

        turn_count = len([msg for msg in conversation_history if msg.get("role") == "user"])

        # Check coverage of key dimensions
        coverage = {
            "taste_anchors": self._check_mentions(
                conversation_history, ["book", "author", "story", "novel"]
            ),
            "style_preference": self._check_mentions(
                conversation_history, ["prose", "writing", "style", "voice"]
            ),
            "narrative_desire": self._check_mentions(
                conversation_history, ["wish", "want", "story", "plot"]
            ),
            "consumption_habit": self._check_mentions(
                conversation_history, ["read", "time", "daily", "pages"]
            ),
        }

        coverage_score = sum(1 for v in coverage.values() if v) / len(coverage)
        ready_for_summary = turn_count >= 8 and coverage_score >= 0.75

        return {
            "turn_count": turn_count,
            "coverage": coverage,
            "coverage_score": round(coverage_score, 2),
            "ready_for_summary": ready_for_summary,
            "recommendation": "Consider wrapping up and summarizing profile" if ready_for_summary else "Continue probing for missing dimensions",
        }

    def _check_mentions(
        self, conversation: List[Dict[str, str]], keywords: List[str]
    ) -> bool:
        """Check if any keywords were mentioned in user responses."""
        user_messages = [
            msg.get("content", "").lower()
            for msg in conversation
            if msg.get("role") == "user"
        ]
        full_text = " ".join(user_messages)
        return any(keyword in full_text for keyword in keywords)

