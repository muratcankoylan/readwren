"""Formats literary profiles for human readability and sharing."""

from typing import Dict, Any


class ProfileFormatter:
    """Formats profiles with explanations for user understanding."""
    
    @staticmethod
    def format_for_sharing(profile: Dict[str, Any]) -> str:
        """Generate a shareable, human-readable profile document.
        
        Args:
            profile: Structured profile data with metrics and explanations
            
        Returns:
            Formatted string suitable for sharing
        """
        lines = []
        
        # Header
        archetype = profile.get("reader_archetype", "Literary Profile")
        lines.append("=" * 80)
        lines.append(f"LITERARY PROFILE: {archetype}".center(80))
        lines.append("=" * 80)
        lines.append("")
        
        # Reading Philosophy
        if "explanations" in profile and "reading_philosophy" in profile["explanations"]:
            lines.append("## WHO YOU ARE AS A READER")
            lines.append("")
            lines.append(profile["explanations"]["reading_philosophy"])
            lines.append("")
            lines.append("-" * 80)
            lines.append("")
        
        # Taste Anchors
        if "taste_anchors" in profile:
            lines.append("## WHAT YOU LOVE")
            lines.append("")
            ta = profile["taste_anchors"]
            if "loves" in ta and ta["loves"]:
                loves_text = ", ".join(ta["loves"][:5])
                lines.append(f"**Gravitates toward:** {loves_text}")
                lines.append("")
            if "hates" in ta and ta["hates"]:
                hates_text = ", ".join(ta["hates"][:3])
                lines.append(f"**Actively avoids:** {hates_text}")
                lines.append("")
            if "inferred_genres" in ta and ta["inferred_genres"]:
                genres_text = ", ".join(ta["inferred_genres"][:5])
                lines.append(f"**Preferred genres:** {genres_text}")
                lines.append("")
            lines.append("-" * 80)
            lines.append("")
        
        # Style Signature with Explanations
        if "style_signature" in profile:
            lines.append("## HOW YOU LIKE YOUR STORIES")
            lines.append("")
            
            style = profile["style_signature"]
            explanations = profile.get("explanations", {})
            
            metrics = [
                ("prose_density", "Prose Density", style.get("prose_density")),
                ("pacing", "Pacing Preference", style.get("pacing")),
                ("tone", "Tone Preference", style.get("tone")),
                ("worldbuilding", "Worldbuilding Detail", style.get("worldbuilding")),
                ("character_focus", "Character vs Plot", style.get("character_focus"))
            ]
            
            for key, label, value in metrics:
                if value is not None:
                    lines.append(f"**{label}:** {value}/100")
                    if key in explanations:
                        lines.append(f"  {explanations[key]}")
                    lines.append("")
            
            lines.append("-" * 80)
            lines.append("")
        
        # Narrative Desires
        if "narrative_desires" in profile:
            lines.append("## THE STORY YOU'RE LOOKING FOR")
            lines.append("")
            nd = profile["narrative_desires"]
            
            if "wish" in nd:
                lines.append(f"**Your ideal story:**")
                lines.append(f"{nd['wish']}")
                lines.append("")
            
            if "preferred_ending" in nd:
                lines.append(f"**Preferred ending:** {nd['preferred_ending']}")
                lines.append("")
            
            if "themes" in nd and nd["themes"]:
                themes_text = ", ".join(nd["themes"][:6])
                lines.append(f"**Core themes:** {themes_text}")
                lines.append("")
            
            lines.append("-" * 80)
            lines.append("")
        
        # Anti-Patterns
        if "explanations" in profile and "anti_patterns" in profile["explanations"]:
            lines.append("## WHAT DOESN'T WORK FOR YOU")
            lines.append("")
            lines.append(profile["explanations"]["anti_patterns"])
            lines.append("")
            lines.append("-" * 80)
            lines.append("")
        
        # Reading Habits
        if "consumption" in profile:
            lines.append("## YOUR READING HABITS")
            lines.append("")
            cons = profile["consumption"]
            
            if "daily_time_minutes" in cons:
                lines.append(f"**Typical reading time:** ~{cons['daily_time_minutes']} minutes/day")
            if "delivery_frequency" in cons:
                lines.append(f"**Reading frequency:** {cons['delivery_frequency']}")
            if "pages_per_delivery" in cons:
                lines.append(f"**Session length:** ~{cons['pages_per_delivery']} pages")
            lines.append("")
            lines.append("-" * 80)
            lines.append("")
        
        # Implicit Signals
        if "implicit" in profile and "explanations" in profile:
            lines.append("## WHAT YOUR LANGUAGE REVEALS")
            lines.append("")
            impl = profile["implicit"]
            exp = profile["explanations"]
            
            if "vocabulary_richness" in impl:
                score = impl["vocabulary_richness"]
                lines.append(f"**Vocabulary richness:** {score:.2f}/1.0")
                if "vocabulary_richness" in exp:
                    lines.append(f"  {exp['vocabulary_richness']}")
                lines.append("")
            
            if "engagement_index" in impl:
                score = impl["engagement_index"]
                lines.append(f"**Engagement level:** {score:.2f}/1.0")
                if "engagement_level" in exp:
                    lines.append(f"  {exp['engagement_level']}")
                lines.append("")
            
            lines.append("-" * 80)
            lines.append("")
        
        # Metadata
        if "_metadata" in profile:
            lines.append("## ABOUT THIS PROFILE")
            lines.append("")
            meta = profile["_metadata"]
            
            turns = meta.get("interview_turns", 0)
            status = meta.get("completion_status", "unknown")
            early = meta.get("early_termination", False)
            
            lines.append(f"Based on {turns} interview responses.")
            if early:
                lines.append("Note: Interview ended early - some preferences are extrapolated.")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("Generated by Muratcan's Literary Interview Agent".center(80))
        lines.append("https://https://x.com/koylanai".center(80))
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_metrics_table(profile: Dict[str, Any]) -> str:
        """Generate a concise metrics table.
        
        Args:
            profile: Structured profile data
            
        Returns:
            Formatted metrics table
        """
        if "style_signature" not in profile:
            return "No style metrics available"
        
        style = profile["style_signature"]
        
        lines = []
        lines.append("STYLE METRICS")
        lines.append("-" * 40)
        lines.append(f"Prose Density:      {style.get('prose_density', 'N/A'):>3}/100")
        lines.append(f"Pacing:             {style.get('pacing', 'N/A'):>3}/100")
        lines.append(f"Tone:               {style.get('tone', 'N/A'):>3}/100")
        lines.append(f"Worldbuilding:      {style.get('worldbuilding', 'N/A'):>3}/100")
        lines.append(f"Character Focus:    {style.get('character_focus', 'N/A'):>3}/100")
        lines.append("-" * 40)
        
        return "\n".join(lines)
    
    @staticmethod
    def add_rubric_reference(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Add rubric reference URLs to profile.
        
        Args:
            profile: Profile data
            
        Returns:
            Profile with added references
        """
        profile["_rubric"] = {
            "url": "https://github.com/muratcankoylan/literaryinterview/blob/main/PROFILE_RUBRIC.md",
            "description": "See PROFILE_RUBRIC.md for detailed explanation of all metrics"
        }
        return profile

