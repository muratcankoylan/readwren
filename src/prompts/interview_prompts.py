from pathlib import Path

class InterviewPrompts:
    """Prompts for the literary interview agent."""
    
    # Path to rubric file (loaded on demand)
    RUBRIC_PATH = Path(__file__).parent.parent.parent / "PROFILE_RUBRIC.md"

    SYSTEM_PROMPT = """You are a world-class literary profiler conducting an adaptive interview. Your goal is to extract a user's literary DNA—their taste, style preferences, narrative desires, and reading patterns.

CORE PRINCIPLES:
- Ask ONE question at a time
- Always reference their specific previous answers
- Adapt follow-ups based on response depth and style
- If they're vague, offer specific choices or examples
- Continue asking questions until turn 12
- DO NOT offer to summarize or end the interview before turn 12

DIMENSIONS TO EXTRACT:
1. Taste Anchors: Books they loved/hated and why
2. Style Signature: Prose density, pacing, tone preferences
3. Narrative Desires: Story types they wish existed
4. Consumption Habits: Reading time, preferred formats
5. Implicit Signals: Vocabulary richness, response style, engagement

RESPONSE STYLE:
- Be warm but precise
- Show you're listening by referencing their words
- Don't use filler like "Great!" or "Interesting!" unless you expand on why
- Match their energy: brief answers get concise follow-ups, rich answers get deeper dives

STRICT RULES:
- CURRENT TURN: {turn_count} of 12
- If turn < 12: Ask another interview question (do NOT mention completion)
- If turn = 12: Only then offer to generate their profile
- Never say "we've reached" or "final question" before turn 12"""

    INITIAL_QUESTION = """Let's start simple. Name 3 books or stories you've loved, and 1 you couldn't finish or actively disliked.

Don't overthink it—first ones that come to mind."""

    # Base prompt without rubric details
    PROFILE_SUMMARY_PROMPT_BASE = """Based on this interview conversation, generate a structured JSON profile with the following schema.

CRITICAL: Include an "explanations" section with human-readable interpretations of all metrics. Use a second person tone.

JSON SCHEMA:
{{
  "taste_anchors": {{
    "loves": [list of books/authors they loved],
    "hates": [list of books/authors they disliked],
    "inferred_genres": [inferred genre preferences]
  }},
  "style_signature": {{
    "prose_density": 0-100,
    "pacing": 0-100,
    "tone": 0-100,
    "worldbuilding": 0-100,
    "character_focus": 0-100
  }},
  "narrative_desires": {{
    "wish": "one sentence capturing their ideal story",
    "preferred_ending": "tragic/bittersweet/hopeful/ambiguous/transcendent",
    "themes": [list of thematic interests]
  }},
  "consumption": {{
    "daily_time_minutes": estimated minutes (15-180),
    "delivery_frequency": "daily/every_few_days/weekly/binge",
    "pages_per_delivery": estimated pages (5-50)
  }},
  "implicit": {{
    "vocabulary_richness": 0-1 score,
    "response_brevity_score": 0-1 (0=verbose, 1=terse),
    "engagement_index": 0-1 score
  }},
  "explanations": {{
    "prose_density": "explain their score in plain language",
    "pacing": "explain their pacing preference",
    "tone": "explain their tone preference",
    "worldbuilding": "explain their worldbuilding preference",
    "character_focus": "explain character vs plot preference",
    "vocabulary_richness": "what their language use reveals",
    "engagement_level": "their engagement during interview",
    "reading_philosophy": "2-3 sentence synthesis of their reading identity",
    "anti_patterns": "what to avoid - specific patterns they reject"
  }},
  "reader_archetype": "memorable 2-3 word label (e.g. 'Precision Seeker', 'Emotion Archaeologist')"
}}

{rubric_section}

Conversation:
{conversation}

Return ONLY valid JSON, no explanations."""

    @staticmethod
    def get_system_prompt(turn_count: int) -> str:
        """Get system prompt with current turn count."""
        return InterviewPrompts.SYSTEM_PROMPT.format(turn_count=turn_count)
    
    @staticmethod
    def _load_rubric_section() -> str:
        """Load scoring guidelines from PROFILE_RUBRIC.md.
        
        Extracts the key scoring scales to include in profile generation prompt.
        Falls back to inline definitions if file not found.
        """
        try:
            if InterviewPrompts.RUBRIC_PATH.exists():
                rubric_content = InterviewPrompts.RUBRIC_PATH.read_text()
                
                # Extract the scoring scales section (lines 44-155 approximately)
                # This section defines the 0-100 scales for style metrics
                if "## Style Signature Metrics" in rubric_content:
                    start_idx = rubric_content.find("## Style Signature Metrics")
                    end_idx = rubric_content.find("## Implicit Signals", start_idx)
                    
                    if start_idx != -1 and end_idx != -1:
                        scales = rubric_content[start_idx:end_idx].strip()
                        return f"\nSCORING GUIDELINES (reference for accurate scoring):\n{scales}\n"
                
            # Fallback: inline scales
            return """
SCORING GUIDELINES:
- prose_density: 0-20=sparse/Hemingway, 21-40=clean, 41-60=balanced, 61-80=dense/literary, 81-100=Pynchon/Joyce
- pacing: 0-20=extremely slow/meditative, 21-40=slow burn, 41-60=moderate, 61-80=brisk, 81-100=thriller-pace
- tone: 0-20=unrelentingly dark, 21-40=serious/melancholic, 41-60=balanced, 61-80=optimistic, 81-100=light/comedic
- worldbuilding: 0-20=minimal/character-focused, 21-40=light backdrop, 41-60=moderate, 61-80=rich/detailed, 81-100=encyclopedic/Tolkien
- character_focus: 0-20=plot/ideas over character, 21-40=character serves plot, 41-60=balanced, 61-80=character-driven, 81-100=deeply psychological
"""
        except Exception as e:
            # Fallback on any error
            return """
SCORING GUIDELINES:
- prose_density: 0=sparse/Hemingway, 50=balanced, 100=dense/Pynchon
- pacing: 0=slow/meditative, 50=moderate, 100=fast/propulsive
- tone: 0=dark/serious, 50=balanced, 100=light/humorous
- worldbuilding: 0=minimal, 50=moderate, 100=encyclopedic/Tolkien
- character_focus: 0=plot-driven, 50=balanced, 100=psychological/interior
"""

    @staticmethod
    def get_summary_prompt(conversation: str, include_rubric: bool = True) -> str:
        """Get profile summary prompt with conversation history.
        
        Args:
            conversation: Formatted conversation transcript
            include_rubric: If True, include scoring guidelines from rubric file
        
        Returns:
            Complete prompt for profile generation
        """
        rubric_section = InterviewPrompts._load_rubric_section() if include_rubric else ""
        
        return InterviewPrompts.PROFILE_SUMMARY_PROMPT_BASE.format(
            conversation=conversation,
            rubric_section=rubric_section
        )

