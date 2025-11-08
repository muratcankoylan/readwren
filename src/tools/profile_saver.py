"""Tool for saving interview logs and profiles to user folders."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Import ProfileFormatter but handle circular import
try:
    from .profile_formatter import ProfileFormatter
except ImportError:
    ProfileFormatter = None


class ProfileSaver:
    """Saves interview logs and profiles to organized user folders."""
    
    def __init__(self, base_dir: str = "user_profiles"):
        """Initialize profile saver.
        
        Args:
            base_dir: Base directory for storing user profiles
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def create_user_folder(self, user_id: str) -> Path:
        """Create folder structure for a user.
        
        Args:
            user_id: User/session identifier
            
        Returns:
            Path to user folder
        """
        user_folder = self.base_dir / user_id
        user_folder.mkdir(exist_ok=True)
        
        # Create subfolders
        (user_folder / "logs").mkdir(exist_ok=True)
        (user_folder / "profiles").mkdir(exist_ok=True)
        
        return user_folder
    
    def save_conversation_log(
        self, 
        user_id: str, 
        conversation: List[Dict[str, str]], 
        metadata: Dict[str, Any] = None,
        include_reasoning: bool = True
    ) -> str:
        """Save conversation log to user folder.
        
        Args:
            user_id: User/session identifier
            conversation: List of message dicts with role and content
            metadata: Optional metadata about the conversation
            include_reasoning: Whether to include Kimi K2 reasoning content
            
        Returns:
            Path to saved log file
        """
        user_folder = self.create_user_folder(user_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = user_folder / "logs" / f"conversation_{timestamp}.json"
        
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "metadata": metadata or {},
            "conversation": conversation,
            "note": "reasoning_content field contains Kimi K2 internal thinking process" if include_reasoning else None
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return str(log_file)
    
    def save_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any],
        format: str = "json"
    ) -> str:
        """Save user profile to user folder.
        
        Args:
            user_id: User/session identifier
            profile_data: Profile data dictionary
            format: Output format ('json' or 'markdown')
            
        Returns:
            Path to saved profile file
        """
        user_folder = self.create_user_folder(user_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            profile_file = user_folder / "profiles" / f"profile_{timestamp}.json"
            
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
        
        elif format == "markdown":
            profile_file = user_folder / "profiles" / f"profile_{timestamp}.md"
            
            markdown = self._profile_to_markdown(profile_data)
            with open(profile_file, 'w') as f:
                f.write(markdown)
        
        return str(profile_file)
    
    def save_session_summary(
        self,
        user_id: str,
        conversation: List[Dict[str, str]],
        profile_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Save complete session (log + profile).
        
        Args:
            user_id: User/session identifier
            conversation: Full conversation history
            profile_data: Generated profile
            metadata: Optional session metadata
            
        Returns:
            Dict with paths to saved files
        """
        log_path = self.save_conversation_log(user_id, conversation, metadata)
        json_path = self.save_profile(user_id, profile_data, format="json")
        md_path = self.save_profile(user_id, profile_data, format="markdown")
        
        # Also save human-readable shareable version if formatter available
        shareable_path = None
        if ProfileFormatter is not None:
            try:
                formatter = ProfileFormatter()
                shareable = formatter.format_for_sharing(profile_data)
                shareable_path = self._save_shareable(user_id, shareable)
            except Exception as e:
                print(f"Warning: Could not generate shareable format: {e}")
        
        return {
            "log": log_path,
            "profile_json": json_path,
            "profile_markdown": md_path,
            "profile_shareable": shareable_path,
            "user_folder": str(self.base_dir / user_id)
        }
    
    def _save_shareable(self, user_id: str, content: str) -> str:
        """Save shareable profile format.
        
        Args:
            user_id: User/session identifier
            content: Formatted shareable content
            
        Returns:
            Path to saved file
        """
        user_folder = self.create_user_folder(user_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shareable_file = user_folder / "profiles" / f"profile_{timestamp}_SHAREABLE.txt"
        
        with open(shareable_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(shareable_file)
    
    def _profile_to_markdown(self, profile: Dict[str, Any]) -> str:
        """Convert profile to markdown format.
        
        Args:
            profile: Profile data dictionary
            
        Returns:
            Formatted markdown string
        """
        md = "# Literary DNA Profile\n\n"
        
        # Reader archetype if available
        if "reader_archetype" in profile:
            md += f"**Archetype:** {profile['reader_archetype']}\n\n"
        
        if "reading_philosophy" in profile:
            md += f"*{profile['reading_philosophy']}*\n\n"
        
        md += "---\n\n"
        
        # Taste anchors
        if "taste_anchors" in profile:
            md += "## Taste Anchors\n\n"
            ta = profile["taste_anchors"]
            if "loves" in ta:
                md += f"**Loves:** {', '.join(ta['loves'])}\n\n"
            if "hates" in ta:
                md += f"**Hates:** {', '.join(ta['hates'])}\n\n"
            if "inferred_genres" in ta:
                md += f"**Genres:** {', '.join(ta['inferred_genres'])}\n\n"
        
        # Style signature
        if "style_signature" in profile:
            md += "## Style Signature\n\n"
            for key, value in profile["style_signature"].items():
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            md += "\n"
        
        # Narrative desires
        if "narrative_desires" in profile:
            md += "## Narrative Desires\n\n"
            nd = profile["narrative_desires"]
            if "wish" in nd:
                md += f"**Story Wish:** {nd['wish']}\n\n"
            if "preferred_ending" in nd:
                md += f"**Preferred Ending:** {nd['preferred_ending']}\n\n"
            if "themes" in nd:
                md += f"**Themes:** {', '.join(nd['themes'])}\n\n"
        
        # Consumption
        if "consumption" in profile:
            md += "## Reading Habits\n\n"
            cons = profile["consumption"]
            for key, value in cons.items():
                if isinstance(value, list):
                    md += f"- **{key.replace('_', ' ').title()}:** {', '.join(value)}\n"
                else:
                    md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            md += "\n"
        
        # Implicit metrics
        if "implicit" in profile:
            md += "## Reading Metrics\n\n"
            for key, value in profile["implicit"].items():
                if isinstance(value, float):
                    md += f"- **{key.replace('_', ' ').title()}:** {value:.0%}\n"
                else:
                    md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        
        return md

