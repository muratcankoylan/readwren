# WREN: AI Literary Interview Agent

**An adaptive multi-agent system that extracts your literary DNA through conversation and generates actionable reading profiles.**

WREN solves a critical problem for LLM users: you know what you like, but explaining your literary taste to an AI is hard. WREN's interview agent asks the right questions, listens deeply, and builds a structured profile that any LLM can use to generate precisely targeted content.

Built with **LangGraph**, **LangChain**, and **Kimi K2 Thinking models**.

---

## Why WREN?

**The Problem**: Kimi K2 is a great writer, but users struggle to articulate their literary preferences in a way LLMs can act on. Vague prompts like "write me something good" produce generic results.

**The Solution**: WREN conducts a 12-turn adaptive interview that:
- Extracts taste anchors (what you love/hate and why)
- Maps your style signature (prose density, pacing, tone preferences)
- Identifies narrative desires (story types you wish existed)
- Captures implicit signals (vocabulary richness, engagement patterns)
- Generates a structured, machine-readable profile

**The Result**: A profile you can hand to any LLM to get content that matches your exact taste.

---

## Architecture: Multi-Agent System

WREN uses a **specialized multi-agent architecture** with distinct roles:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
  ┌─────────▼──────────┐    ┌──────────▼──────────┐
  │ InterviewAgent     │    │ ProfileGenerator    │
  │ (kimi-k2-thinking- │    │ (kimi-k2-thinking)  │
  │      turbo)        │    │                     │
  │ - Ask questions    │    │ - Deep analysis     │
  │ - Adapt to style   │    │ - Generate profile  │
  │ - Track coverage   │    │ - Extract reasoning │
  └─────────┬──────────┘    └──────────┬──────────┘
            │                           │
  ┌─────────▼───────────────────────────▼──────────┐
  │          LangGraph StateGraph                   │
  │   ┌─────────────────────────────────────┐      │
  │   │  analyze → generate → save          │      │
  │   └─────────────────────────────────────┘      │
  └─────────┬────────────────────────────────────────┘
            │
  ┌─────────▼──────────┐
  │ RedisCheckpointSaver│
  │  (State Persistence)│
  └─────────────────────┘
```

### Agent 1: InterviewAgent

**Role**: Conversational interviewer that adapts to user responses

**Model**: `kimi-k2-thinking-turbo` (fast, conversational)

**Capabilities**:
- Conducts 12-turn structured interview
- References previous answers (shows it's listening)
- Adjusts question depth based on response style
- Tracks coverage across 5 dimensions
- Uses LangGraph state machine for conversation flow

**Key Innovation**: Uses real-time analysis tools to adapt questioning:
- `ProfileAnalyzerTool`: Measures vocabulary richness, brevity, engagement
- `ConversationAnalyzerTool`: Tracks coverage and determines readiness

### Agent 2: ProfileGeneratorAgent

**Role**: Deep analyst that transforms conversation into structured profile

**Model**: `kimi-k2-thinking` (extended reasoning for analysis)

**Capabilities**:
- Parses full conversation transcript
- Generates JSON profile with 40+ data points
- Scores style preferences on 0-100 scales
- Provides human-readable explanations
- Extracts its own reasoning process

**Key Innovation**: Single-purpose agent runs once, uses expensive model only when needed, includes explanations in second-person for easy sharing.

### Agent 3: ReasoningExtractor

**Role**: Extracts and formats Kimi K2's internal thinking

**Capabilities**:
- Pulls `reasoning_content` from model responses
- Formats for human readability
- Saves separately for transparency
- Enables debugging and insight

---

## LangGraph State Machine

WREN uses **LangGraph** for stateful conversation management:

```python
class InterviewState(TypedDict):
    messages: Annotated[List[BaseMessage], add]  # Conversation history
    turn_count: int                              # Current turn
    profile_data: Dict[str, Any]                 # Generated profile
    is_complete: bool                            # Completion flag
    current_analysis: Dict[str, Any]             # Real-time metrics
```

### Graph Flow

```
User Input
    ↓
[analyze_node]
├─> ProfileAnalyzerTool: Analyze response style
├─> ConversationAnalyzerTool: Check coverage
└─> Update state with analysis
    ↓
[_should_continue]
├─> turn_count >= 12? → generate_profile
└─> turn_count < 12?  → generate_question
    ↓
[generate_question_node]
├─> Build prompt with turn context + analysis
├─> Invoke Kimi K2 Thinking Turbo
├─> Extract reasoning from response
└─> Return AIMessage
    ↓
State persisted to Redis → Ready for next turn
```

**Why LangGraph?**
- Built-in state persistence (Redis or in-memory)
- Clean separation of analysis → decision → generation
- Resumable sessions (pick up where you left off)
- Type-safe state transitions

---

## Redis Integration

WREN implements a **custom Redis checkpointer** for LangGraph:

```python
class RedisCheckpointSaver(BaseCheckpointSaver):
    def put(self, config, checkpoint, metadata, new_versions):
        # Serializes full state with pickle (handles Python objects)
        serialized = pickle.dumps({
            "checkpoint": checkpoint,
            "metadata": metadata,
            "config": config
        })
        self.redis.setex(key, self.ttl, serialized)  # 24h TTL
```

**Why Custom?**
- LangGraph doesn't include Redis checkpointer out of the box
- Standard JSON serialization fails on Python objects
- Pickle handles complex state including functions/lambdas

**Benefits**:
- Sessions persist across restarts
- Resume interrupted interviews
- Inspect state at any point
- Auto-expiration after 24 hours

---

## Prompt Engineering

### Adaptive System Prompt

```python
SYSTEM_PROMPT = """You are a world-class literary profiler conducting 
an adaptive interview.

CORE PRINCIPLES:
- Ask ONE question at a time
- Always reference their specific previous answers
- Adapt follow-ups based on response depth and style
- Continue asking questions until turn 12

STRICT RULES:
- CURRENT TURN: {turn_count} of 12
- If turn < 12: Ask another question (do NOT mention completion)
- If turn = 12: Only then offer to generate their profile
"""
```

**Key Features**:
- Dynamic turn injection prevents premature completion
- Explicit rules override model's tendency to end early
- References previous answers (shows listening)
- Adapts energy level to user responses

### Profile Generation Prompt

The system dynamically loads scoring guidelines from `PROFILE_RUBRIC.md`:

```python
@staticmethod
def get_summary_prompt(conversation: str, include_rubric: bool = True):
    # Load rubric scales from file
    rubric_section = _load_rubric_section()
    
    return f"""Generate JSON profile with:
    
    JSON SCHEMA: [detailed structure]
    
    SCORING GUIDELINES:
    {rubric_section}  ← Dynamically loaded from PROFILE_RUBRIC.md
    
    Conversation:
    {conversation}
    """
```

**Why Dynamic Loading?**
- Single source of truth (update rubric → prompts update automatically)
- LLM sees detailed scoring guidance
- Consistent scoring across all profiles

---

## Tools & Analysis

### ProfileAnalyzerTool

```python
def _run(self, response_text: str, conversation_history: List) -> Dict:
    """Analyzes individual responses for implicit signals."""
    
    # Calculate metrics
    vocabulary_richness = unique_words / total_words
    response_brevity = 1 / (word_count / 100)  # Normalized
    engagement_level = heuristic(examples, emotion_words, depth)
    
    return {
        "vocabulary_richness": 0.0-1.0,
        "response_brevity": 0.0-1.0,
        "engagement_level": 0.0-1.0
    }
```

### ConversationAnalyzerTool

```python
def _run(self, conversation_history: List[Dict]) -> Dict:
    """Tracks coverage across 5 dimensions."""
    
    coverage = {
        "taste_anchors": check_keywords(["book", "author", "story"]),
        "style_preference": check_keywords(["prose", "writing", "style"]),
        "narrative_desire": check_keywords(["wish", "want", "story"]),
        "consumption_habit": check_keywords(["read", "time", "daily"])
    }
    
    return {
        "turn_count": len(user_messages),
        "coverage": coverage,
        "coverage_score": sum(coverage.values()) / len(coverage),
        "ready_for_summary": turn >= 8 and coverage_score >= 0.75
    }
```

**These tools feed into the agent's decision-making**, enabling adaptive questioning based on what's been covered.

---

## Output: Structured Profiles

WREN generates **4 output formats**:

### 1. JSON Profile (`profile_TIMESTAMP.json`)

```json
{
  "taste_anchors": {
    "loves": ["The Remains of the Day", "Beloved"],
    "hates": ["Finnegans Wake"],
    "inferred_genres": ["modernist fiction", "trauma narratives"]
  },
  "style_signature": {
    "prose_density": 70,    // 0-100 scale
    "pacing": 60,
    "tone": 10,
    "worldbuilding": 20,
    "character_focus": 90
  },
  "narrative_desires": {
    "wish": "Language fracturing to contain catastrophe",
    "preferred_ending": "transcendent",
    "themes": ["language limits", "trauma", "alienation"]
  },
  "consumption": {
    "daily_time_minutes": 75,
    "delivery_frequency": "every_few_days",
    "pages_per_delivery": 30
  },
  "implicit": {
    "vocabulary_richness": 0.95,
    "response_brevity_score": 0.2,
    "engagement_index": 0.95
  },
  "explanations": {
    "prose_density": "You appreciate complex prose when it reveals emotion...",
    "reading_philosophy": "You read as an act of emotional archaeology..."
  },
  "reader_archetype": "Fracture Dweller"
}
```

### 2. Markdown Profile (`profile_TIMESTAMP.md`)

Human-readable with sections and formatting.

### 3. Shareable Profile (`profile_TIMESTAMP_SHAREABLE.txt`)

Optimized for social media / documentation sharing.

### 4. Conversation Log (`conversation_TIMESTAMP.json`)

Full transcript with reasoning content from Kimi K2.

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/muratcankoylan/readwren.git
cd readwren

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env.example .env
# Edit .env with your Moonshot API key
```

### Configuration

```bash
# .env file
MOONSHOT_API_KEY=sk-your-api-key-here
MOONSHOT_BASE_URL=https://api.moonshot.ai/v1

# Optional: Redis for persistent sessions
REDIS_HOST=your-redis-host.com
REDIS_PORT=17887
REDIS_PASSWORD=your-password
```

Get your Moonshot API key: https://platform.moonshot.ai/

### Run Interview

```bash
./run_interview.sh
```

Or directly:

```bash
python cli_interview.py
```

### Example Session

```
Let's start simple. Name 3 books you've loved, and 1 you couldn't finish.

Your response: I love The Remains of the Day for its devastating restraint, 
Beloved for how it makes the unspeakable tangible, and The Metamorphosis 
for crystallizing alienation. I couldn't finish Finnegans Wake.

Agent: Your taste gravitates toward emotional precision over linguistic 
spectacle. When you say "devastating restraint," what specific moment 
in Ishiguro's novel best exemplifies this for you?

Progress: ●○○○○○○○○○○○ (1/12)
```

After 12 turns:

```
✓ Profile saved to: user_profiles/cli_20251108_145739/
  - conversation_20251108_150303.json (full transcript)
  - profile_20251108_150303.json (structured data)
  - profile_20251108_150303.md (human-readable)
  - profile_20251108_150303_SHAREABLE.txt (social sharing)
```

---

## Using Your Profile

Once generated, give your profile to any LLM:

```
Claude/GPT/Grok/Kimi, write a short story for me using these preferences:

- Prose density: 70/100 (between Morrison and Ishiguro)
- Tone: 10/100 (dark, serious, restrained)
- Character focus: 90/100 (psychological depth over plot)
- Theme: Language failing to contain private catastrophe
- Ending: Transcendent (through remaining broken)
- Avoid: Linguistic performance for its own sake
```

**Result**: Precisely targeted content matching your exact taste.

---

## Project Structure

```
readwren/
├── src/
│   ├── agents/              # AI agents
│   │   ├── interview_agent.py       # Main interviewer (LangGraph)
│   │   ├── profile_generator.py     # Profile analyst
│   │   ├── redis_checkpointer.py    # Custom Redis persistence
│   │   └── reasoning_extractor.py   # Kimi K2 reasoning handler
│   ├── tools/               # Analysis tools
│   │   ├── profile_tools.py         # Response analyzers
│   │   ├── profile_saver.py         # File management
│   │   └── profile_formatter.py     # Output formatting
│   ├── prompts/             # Prompt engineering
│   │   └── interview_prompts.py     # System prompts + rubric loader
│   └── config/              # Configuration
│       └── settings.py
├── cli_interview.py         # Interactive CLI
├── requirements.txt         # Python dependencies
├── env.example              # Environment template
├── run_interview.sh         # Startup script
├── PROFILE_RUBRIC.md        # Scoring system (loaded dynamically)
├── TECHNICAL_DOCUMENTATION.md  # Complete technical docs
├── RUBRIC_INTEGRATION.md    # Rubric usage guide
├── REDIS_GUIDE.md           # Redis setup and usage
└── user_profiles/           # Generated outputs (gitignored)
```

---

## Technical Details

### Technology Stack

- **LangGraph**: State machine for conversation flow
- **LangChain**: LLM abstraction layer
- **Moonshot AI**: Kimi K2 models (turbo + thinking)
- **Redis**: Session persistence (optional)
- **Python 3.11+**

### Model Strategy

| Aspect | InterviewAgent | ProfileGenerator |
|--------|----------------|------------------|
| Model | kimi-k2-thinking-turbo | kimi-k2-thinking |
| Tokens | 800 | 4000 |
| Temperature | 0.8 | 0.7 |
| Speed | ~2-3s | ~10-15s |
| Reasoning | Basic thinking | Extended reasoning |
| Total calls | 12+ | 1 |

**Strategy**: Use thinking-turbo for fast conversational turns, reserve full thinking model for deep analysis at the end.

### State Management

```python
# LangGraph state with Redis persistence
state = {
    "messages": [HumanMessage, AIMessage, ...],
    "turn_count": 8,
    "current_analysis": {
        "coverage_score": 0.85,
        "vocabulary_richness": 0.92
    },
    "is_complete": False
}

# Automatically saved to Redis after each turn
# TTL: 24 hours (configurable)
```

---

## Advanced Features

### Session Management

```bash
# View all active Redis sessions
python view_redis_sessions.py

# View specific conversation
python view_conversation_log.py user_profiles/cli_20251108_145739/logs/conversation.json

# Retrieve session from Redis
python retrieve_profile.py
```

### Kimi K2 Reasoning

WREN extracts and displays Kimi K2's internal thinking:

```
💭 REASONING:
Let me analyze their preference for restraint. They mentioned Ishiguro 
and Morrison, both use controlled prose. I should probe if they prefer 
brevity or just emotional control. The Finnegans Wake rejection suggests 
they dislike when complexity becomes performative...
```

Enable in CLI:

```bash
Show Kimi K2 reasoning? (y/N): y
```

### Custom Rubric

Edit `PROFILE_RUBRIC.md` to adjust scoring scales. Changes automatically propagate to profile generation prompts.

---

## Documentation

- **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)**: Complete architecture, agents, tools, prompts, data flow
- **[PROFILE_RUBRIC.md](PROFILE_RUBRIC.md)**: Scoring system and metric definitions
- **[RUBRIC_INTEGRATION.md](RUBRIC_INTEGRATION.md)**: How rubric is used in code
- **[REDIS_GUIDE.md](REDIS_GUIDE.md)**: Redis setup and session management

---

## Utilities

- `view_redis_sessions.py`: List all active sessions with metadata
- `view_session_conversation.py`: Decode Redis checkpoint for a session
- `view_conversation_log.py`: Display saved conversation logs
- `retrieve_profile.py`: Retrieve and manually edit profiles

---

## Use Cases

1. **Content Creators**: Generate stories/essays matching your style
2. **Readers**: Get precise book recommendations
3. **Writers**: Articulate your voice for AI writing assistants
4. **Product Teams**: Build user profiles for personalization
5. **Researchers**: Study literary preferences and taste formation

---

## Why Multi-Agent?

**Single-agent approach** (naive):
- One LLM does everything: interview + analyze + generate profile
- Expensive model runs 12+ times
- Can't optimize for different tasks
- Mixed concerns (conversation vs analysis)

**Multi-agent approach** (WREN):
- **InterviewAgent**: Fast, conversational model (turbo)
- **ProfileGenerator**: Deep analysis model (thinking)
- **Each agent optimized for its role**
- Thinking model runs once (cost-efficient)
- Clean separation of concerns
- Tools feed into agent decision-making

This architecture is **reusable**: same pattern works for medical history, design preferences, dietary taste, etc.

---

## Contributing

WREN is open source. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Areas for contribution:
- Additional analysis tools
- New output formats
- Web UI
- Multi-language support
- Alternative LLM support

---

## License

Open Source - MIT License

---

## Credits

**Built by**: Muratcan Koylan ([@koylanai](https://twitter.com/koylanai))

**Powered by**:
- [Moonshot AI](https://platform.moonshot.ai/) (Kimi K2 models)
- [LangChain](https://www.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)

---

## Questions?

- **Twitter**: [@koylanai](https://twitter.com/koylanai)
- **GitHub Issues**: [readwren/issues](https://github.com/muratcankoylan/readwren/issues)
- **Documentation**: See [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

---

**WREN**: Because explaining your taste shouldn't be harder than having it.

