"""Utility for extracting and processing Kimi K2 reasoning content."""

from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage


class ReasoningExtractor:
    """Extracts and processes reasoning content from Kimi K2 Thinking model responses."""
    
    @staticmethod
    def extract_reasoning(response: Any) -> Optional[str]:
        """Extract reasoning content from a model response.
        
        Args:
            response: Response object from LLM
            
        Returns:
            Reasoning content string if available, None otherwise
        """
        # Check for reasoning in additional_kwargs
        if hasattr(response, 'additional_kwargs'):
            reasoning = response.additional_kwargs.get('reasoning_content')
            if reasoning:
                return reasoning
        
        # Check for reasoning in response_metadata
        if hasattr(response, 'response_metadata'):
            reasoning = response.response_metadata.get('reasoning_content')
            if reasoning:
                return reasoning
        
        return None
    
    @staticmethod
    def extract_from_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Extract reasoning from a list of messages.
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            List of dicts with message content and reasoning (if available)
        """
        results = []
        
        for msg in messages:
            result = {
                "role": msg.type,
                "content": msg.content
            }
            
            # Check for reasoning in additional_kwargs
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                reasoning = msg.additional_kwargs.get('reasoning_content')
                if reasoning:
                    result["reasoning_content"] = reasoning
            
            results.append(result)
        
        return results
    
    @staticmethod
    def format_reasoning(reasoning: str, max_length: int = None) -> str:
        """Format reasoning content for display.
        
        Args:
            reasoning: Raw reasoning content
            max_length: Optional max length to truncate to
            
        Returns:
            Formatted reasoning string
        """
        if not reasoning:
            return ""
        
        formatted = reasoning.strip()
        
        if max_length and len(formatted) > max_length:
            formatted = formatted[:max_length] + "..."
        
        return formatted
    
    @staticmethod
    def save_reasoning_separately(
        conversation: List[Dict[str, Any]], 
        output_path: str
    ) -> None:
        """Save reasoning content to a separate file.
        
        Args:
            conversation: Conversation with reasoning content
            output_path: Path to save reasoning file
        """
        import json
        from pathlib import Path
        
        reasoning_data = []
        
        for i, msg in enumerate(conversation):
            if "reasoning_content" in msg:
                reasoning_data.append({
                    "turn": i,
                    "role": msg.get("role"),
                    "content_preview": msg.get("content", "")[:100] + "...",
                    "reasoning": msg["reasoning_content"]
                })
        
        if reasoning_data:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(reasoning_data, f, indent=2)

