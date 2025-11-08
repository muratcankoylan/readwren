"""Dedicated agent for generating user literary profiles from interview transcripts."""

import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from src.config.settings import settings
from src.prompts.interview_prompts import InterviewPrompts


class ProfileGeneratorAgent:
    """Dedicated agent that focuses solely on generating literary profiles."""
    
    def __init__(self):
        """Initialize the profile generator with optimized settings for analysis."""
        settings.validate()
        
        # Use Kimi K2 THINKING model for deep profile analysis
        self.llm = ChatOpenAI(
            model="kimi-k2-thinking",  # Thinking model with extended reasoning for profiles
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
            temperature=0.7,
            max_tokens=4000,  # Higher limit for comprehensive profiles + reasoning
        )
        
        print("✓ ProfileGeneratorAgent loaded")
    
    def generate_profile(
        self,
        conversation: List[Dict[str, str]],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive literary profile from conversation transcript.
        
        Args:
            conversation: Full conversation history with role and content
            metadata: Optional metadata about the interview (turns, duration, etc.)
            
        Returns:
            Dict containing structured profile data
        """
        # Build conversation transcript
        transcript = self._format_transcript(conversation)
        
        # Generate profile prompt
        system_prompt = InterviewPrompts.get_summary_prompt(transcript)
        
        # Add metadata context if available
        if metadata:
            system_prompt += f"\n\nINTERVIEW METADATA:\n"
            system_prompt += f"- Total turns: {metadata.get('turn_count', 'unknown')}\n"
            system_prompt += f"- Completion status: {metadata.get('completion_status', 'unknown')}\n"
            if metadata.get('early_termination'):
                system_prompt += "- Note: Interview ended early, extrapolate carefully from available data\n"
        
        # Generate profile
        messages = [SystemMessage(content=system_prompt)]
        response = self.llm.invoke(messages)
        
        # Parse JSON profile
        try:
            profile_data = json.loads(response.content)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from markdown code blocks
            content = response.content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                try:
                    profile_data = json.loads(json_str)
                except json.JSONDecodeError:
                    profile_data = {
                        "error": "Failed to parse profile JSON",
                        "raw_response": response.content
                    }
            else:
                profile_data = {
                    "error": "Failed to parse profile JSON",
                    "raw_response": response.content
                }
        
        # Add metadata to profile
        profile_data["_metadata"] = {
            "interview_turns": metadata.get('turn_count', 0) if metadata else 0,
            "completion_status": metadata.get('completion_status', 'unknown') if metadata else 'unknown',
            "early_termination": metadata.get('early_termination', False) if metadata else False
        }
        
        # Capture reasoning if available
        if hasattr(response, 'additional_kwargs'):
            reasoning = response.additional_kwargs.get('reasoning_content', None)
            if reasoning:
                profile_data["_reasoning"] = reasoning
        
        return profile_data
    
    def _format_transcript(self, conversation: List[Dict[str, str]]) -> str:
        """Format conversation history into a readable transcript.
        
        Args:
            conversation: List of message dicts with role and content
            
        Returns:
            Formatted transcript string
        """
        transcript_lines = []
        
        for msg in conversation:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Skip system messages
            if role == "system":
                continue
            
            # Format based on role
            if role in ["assistant", "ai"]:
                transcript_lines.append(f"INTERVIEWER: {content}")
            elif role in ["user", "human"]:
                transcript_lines.append(f"USER: {content}")
            else:
                transcript_lines.append(f"{role.upper()}: {content}")
        
        return "\n\n".join(transcript_lines)
    
    def validate_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Validate that profile has required fields.
        
        Args:
            profile_data: Generated profile data
            
        Returns:
            True if profile is valid, False otherwise
        """
        if "error" in profile_data:
            return False
        
        required_fields = [
            "taste_anchors",
            "style_signature",
            "narrative_desires"
        ]
        
        for field in required_fields:
            if field not in profile_data:
                return False
        
        return True
    
    def generate_profile_summary(self, profile_data: Dict[str, Any]) -> str:
        """Generate a human-readable summary of the profile.
        
        Args:
            profile_data: Structured profile data
            
        Returns:
            Human-readable summary string
        """
        if not self.validate_profile(profile_data):
            return "Unable to generate profile summary - invalid profile data"
        
        summary_lines = []
        
        # Taste anchors
        if "taste_anchors" in profile_data:
            anchors = profile_data["taste_anchors"]
            if "loves" in anchors and anchors["loves"]:
                summary_lines.append(f"Loves: {', '.join(anchors['loves'][:3])}")
            if "hates" in anchors and anchors["hates"]:
                summary_lines.append(f"Avoids: {', '.join(anchors['hates'][:3])}")
        
        # Reader archetype
        if "reader_archetype" in profile_data:
            summary_lines.append(f"\nReader Type: {profile_data['reader_archetype']}")
        
        # Key themes
        if "narrative_desires" in profile_data:
            desires = profile_data["narrative_desires"]
            if "themes" in desires and desires["themes"]:
                summary_lines.append(f"Key Themes: {', '.join(desires['themes'][:3])}")
        
        return "\n".join(summary_lines)

