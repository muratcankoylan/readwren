# How the Rubric is Used in WREN

## Overview

The `PROFILE_RUBRIC.md` file defines scoring scales for all profile metrics. This document explains how the rubric is integrated into the code and used during profile generation.

## Integration Points

### 1. Profile Generation Prompt

**Location**: `src/prompts/interview_prompts.py`

The rubric is **dynamically loaded** and injected into the profile generation prompt:

```python
# When ProfileGeneratorAgent generates a profile:
prompt = InterviewPrompts.get_summary_prompt(conversation, include_rubric=True)
```

**What happens**:
1. `_load_rubric_section()` reads `PROFILE_RUBRIC.md`
2. Extracts the "Style Signature Metrics" section (scoring scales)
3. Injects it into the prompt as `SCORING GUIDELINES`
4. The LLM sees these scales when generating scores

### 2. Rubric Loading Process

```python
@staticmethod
def _load_rubric_section() -> str:
    """Load scoring guidelines from PROFILE_RUBRIC.md."""
    if InterviewPrompts.RUBRIC_PATH.exists():
        rubric_content = InterviewPrompts.RUBRIC_PATH.read_text()
        
        # Extract scoring scales section
        if "## Style Signature Metrics" in rubric_content:
            start_idx = rubric_content.find("## Style Signature Metrics")
            end_idx = rubric_content.find("## Implicit Signals", start_idx)
            scales = rubric_content[start_idx:end_idx].strip()
            return f"\nSCORING GUIDELINES:\n{scales}\n"
    
    # Fallback if file missing
    return "SCORING GUIDELINES: [inline definitions]"
```

**Key Features**:
- Automatically extracts relevant section
- Fallback to inline definitions if file missing
- Error-tolerant (won't break if rubric format changes)

### 3. Agent Usage

**ProfileGeneratorAgent** (`src/agents/profile_generator.py`):

```python
def generate_profile(self, conversation, metadata):
    # Build prompt with rubric included
    system_prompt = InterviewPrompts.get_summary_prompt(transcript)
    
    # The prompt now contains:
    # 1. JSON schema
    # 2. Scoring guidelines from PROFILE_RUBRIC.md ← HERE
    # 3. Conversation transcript
    
    messages = [SystemMessage(content=system_prompt)]
    response = self.llm.invoke(messages)
```

### 4. What the LLM Sees

When generating a profile, Kimi K2 receives:

```
Based on this interview conversation, generate a structured JSON profile...

JSON SCHEMA:
{
  "style_signature": {
    "prose_density": 0-100,
    "pacing": 0-100,
    ...
  },
  ...
}

SCORING GUIDELINES (reference for accurate scoring):
## Style Signature Metrics

### 1. Prose Density (0-100)
0-20: Sparse, minimalist (Hemingway, Carver)
21-40: Clean, direct with occasional flourishes
41-60: Balanced clarity and complexity
61-80: Dense, literary prose requiring close reading
81-100: Maximum density (Pynchon, Joyce)

### 2. Pacing (0-100)
0-20: Extremely slow, meditative, philosophical
21-40: Slow burn, character-focused
...

Conversation:
USER: I love Beloved...
INTERVIEWER: What draws you...

Return ONLY valid JSON, no explanations.
```

## Benefits of This Approach

### 1. Single Source of Truth
- Update `PROFILE_RUBRIC.md` → automatically updates prompts
- No need to maintain scores in multiple places

### 2. Consistency
- All profiles scored against same scales
- LLM has detailed guidance for edge cases

### 3. Transparency
- Users can read the same rubric the LLM uses
- Explanations reference rubric ranges (e.g., "61-80 range")

### 4. Flexibility
- Can disable rubric injection: `get_summary_prompt(convo, include_rubric=False)`
- Can test different rubric versions
- Easy to A/B test prompt variations

## Rubric Structure in PROFILE_RUBRIC.md

The file must contain these sections (extracted automatically):

```markdown
## Style Signature Metrics

### 1. Prose Density (0-100)
[scale definitions]

### 2. Pacing (0-100)
[scale definitions]

### 3. Tone (0-100)
[scale definitions]

### 4. Worldbuilding (0-100)
[scale definitions]

### 5. Character Focus (0-100)
[scale definitions]

## Implicit Signals
[next section - marks end of extraction]
```

**Extraction Logic**: Everything between `## Style Signature Metrics` and `## Implicit Signals` is included in the prompt.

## Testing Rubric Integration

### Verify Rubric is Loaded

```python
from src.prompts.interview_prompts import InterviewPrompts

# Get prompt with rubric
prompt = InterviewPrompts.get_summary_prompt("test", include_rubric=True)

# Check if rubric is present
if "SCORING GUIDELINES" in prompt:
    print("✓ Rubric loaded successfully")
    print(f"Prompt length: {len(prompt)} characters")
else:
    print("✗ Rubric not loaded (falling back to inline)")
```

### View Extracted Rubric Section

```python
rubric_section = InterviewPrompts._load_rubric_section()
print(rubric_section)
```

### Test Profile Generation with Rubric

```python
from src.agents.profile_generator import ProfileGeneratorAgent

generator = ProfileGeneratorAgent()

conversation = [
    {"role": "user", "content": "I love dense, literary prose like Morrison"},
    {"role": "assistant", "content": "What specifically about the density appeals to you?"}
]

profile = generator.generate_profile(conversation)

# Check if scores align with rubric
print(f"Prose density: {profile['style_signature']['prose_density']}/100")
print(f"Explanation: {profile['explanations']['prose_density']}")

# Expected: score around 70-80 (dense/literary range)
# Explanation should reference the rubric's 61-80 definition
```

## Updating the Rubric

When you update `PROFILE_RUBRIC.md`:

1. **No code changes needed** - it's loaded dynamically
2. **Restart any running agents** - they cache the prompt
3. **Test with a sample interview** - verify scores make sense
4. **Check explanations** - should reference new scale definitions

## Fallback Behavior

If `PROFILE_RUBRIC.md` is missing or malformed:

- System falls back to simplified inline scales
- Profile generation continues (won't crash)
- Warning in console: "Using fallback scoring guidelines"

## Future Enhancements

### 1. Rubric Versioning
```python
RUBRIC_VERSION = "2.1"  # Track rubric changes
profile["_rubric_version"] = RUBRIC_VERSION
```

### 2. Multiple Rubrics
```python
# Load different rubrics for different genres
rubric = load_rubric("fiction")  # vs load_rubric("poetry")
```

### 3. Rubric Validation
```python
def validate_rubric(rubric_path):
    """Ensure rubric has required sections and valid scale definitions."""
    content = rubric_path.read_text()
    assert "## Style Signature Metrics" in content
    assert all(metric in content for metric in REQUIRED_METRICS)
```

### 4. Prompt Caching
```python
# Cache the loaded rubric to avoid re-reading file
_rubric_cache = None
_rubric_mtime = None

def _load_rubric_section():
    global _rubric_cache, _rubric_mtime
    current_mtime = RUBRIC_PATH.stat().st_mtime
    
    if _rubric_cache is None or current_mtime > _rubric_mtime:
        # Reload if file changed
        _rubric_cache = _read_rubric()
        _rubric_mtime = current_mtime
    
    return _rubric_cache
```

## Summary

**Question**: "Where is the rubric used in the code?"

**Answer**:
1. **Loaded**: `src/prompts/interview_prompts.py` → `_load_rubric_section()`
2. **Injected**: Into `PROFILE_SUMMARY_PROMPT_BASE` via `{rubric_section}` placeholder
3. **Used**: By `ProfileGeneratorAgent` when calling `InterviewPrompts.get_summary_prompt()`
4. **Seen**: By Kimi K2 LLM as part of the profile generation system prompt

The rubric is now **dynamic** - editing `PROFILE_RUBRIC.md` automatically updates the profile generation prompt without touching any code.

