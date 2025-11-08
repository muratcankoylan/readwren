# WREN Literary Interview Agent - Complete Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [Core Components](#core-components)
4. [LangGraph Implementation](#langgraph-implementation)
5. [Redis Integration](#redis-integration)
6. [Data Flow](#data-flow)
7. [Agents](#agents)
8. [Tools](#tools)
9. [Prompts System](#prompts-system)
10. [CLI Interface](#cli-interface)
11. [Configuration](#configuration)
12. [Output Generation](#output-generation)
13. [Profile Rubric](#profile-rubric)
14. [Utilities](#utilities)

---

## Architecture Overview

WREN is a conversational AI system that conducts adaptive literary interviews to extract users' reading preferences and generate structured profiles. The system uses a multi-agent architecture with stateful conversation management.

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                        │
│                   (cli_interview.py)                        │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │ InterviewAgent      │    │ ProfileGenerator    │
         │ (kimi-k2-thinking-  │    │ (kimi-k2-thinking)  │
         │      turbo)         │    │                     │
         └──────────┬──────────┘    └──────────┬──────────┘
                    │                           │
         ┌──────────▼──────────────────────────▼──────────┐
         │            LangGraph StateGraph                 │
         │   ┌─────────────────────────────────────┐      │
         │   │  analyze → generate_question/profile│      │
         │   └─────────────────────────────────────┘      │
         └──────────┬──────────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │ RedisCheckpointSaver │
         │  (State Persistence) │
         └──────────────────────┘
```

### Key Design Decisions

1. **Two-Model**: 
   - Interview model (kimi-k2-thinking-turbo) for interview questions
   - Profile generation model (kimi-k2-thinking) for deep analysis
   - Rationale: Both use thinking models but optimized for different tasks

2. **Stateful Conversations**: 
   - LangGraph manages conversation state
   - Redis provides persistence across sessions
   - State includes messages, turn count, analysis data

3. **Adaptive Interviewing**: 
   - Tools analyze each response
   - System adjusts questioning strategy
   - Coverage tracking ensures comprehensive profiling

---

## Technology Stack

### Core Dependencies

```python
# requirements.txt
langgraph>=1.0.0         # State machine for conversation flow
langchain>=0.3.0          # LLM abstraction layer
langchain-core>=0.3.0     # Core LangChain primitives
openai>=1.0.0             # OpenAI-compatible API client
python-dotenv>=1.0.0      # Environment variable management
redis>=5.0.0              # Session persistence
pydantic>=2.0.0           # Data validation
httpx>=0.27.0             # HTTP client
```

### External Services

- **Moonshot AI API**: LLM provider (Kimi K2 models)
- **Redis Cloud**: Session state storage (optional, falls back to in-memory)

---

## Core Components

### Directory Structure

```
readwren/
├── src/
│   ├── agents/              # AI agents and state management
│   │   ├── interview_agent.py
│   │   ├── profile_generator.py
│   │   ├── redis_checkpointer.py
│   │   └── reasoning_extractor.py
│   ├── tools/               # Analysis and formatting tools
│   │   ├── profile_tools.py
│   │   ├── profile_saver.py
│   │   └── profile_formatter.py
│   ├── prompts/             # System prompts and templates
│   │   └── interview_prompts.py
│   └── config/              # Configuration management
│       └── settings.py
├── cli_interview.py         # Interactive CLI
├── requirements.txt         # Python dependencies
├── env.example              # Environment template
├── user_profiles/           # Output directory
└── profile_rubric.md        # Scoring system
```

---

## LangGraph Implementation

### State Definition

LangGraph manages conversation state through a typed state object:

```python
class InterviewState(TypedDict):
    messages: Annotated[List[BaseMessage], add]  # Conversation history
    turn_count: int                              # Current turn number
    profile_data: Dict[str, Any]                 # Generated profile
    is_complete: bool                            # Interview completion flag
    current_analysis: Dict[str, Any]             # Real-time analysis
```

**Key Feature**: `Annotated[List[BaseMessage], add]` tells LangGraph to *append* new messages rather than replace the list.

### Graph Structure

```python
def _build_graph(self) -> StateGraph:
    workflow = StateGraph(InterviewState)
    
    # Nodes
    workflow.add_node("analyze", self._analyze_node)
    workflow.add_node("generate_question", self._generate_question_node)
    workflow.add_node("generate_profile", self._generate_profile_node)
    
    # Flow
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges(
        "analyze",
        self._should_continue,
        {
            "continue": "generate_question",
            "complete": "generate_profile",
        },
    )
    workflow.add_edge("generate_question", END)
    workflow.add_edge("generate_profile", END)
    
    return workflow
```

### Node Functions

#### 1. Analyze Node
```python
def _analyze_node(self, state: InterviewState) -> InterviewState:
    """
    Analyzes current conversation state before generating response.
    
    - Converts messages to dict format
    - Runs ConversationAnalyzerTool to check coverage
    - Runs ProfileAnalyzerTool on last user response
    - Updates turn_count and current_analysis
    """
    conversation = [
        {"role": msg.type, "content": msg.content} 
        for msg in state["messages"]
    ]
    
    conv_analysis = self.conversation_analyzer._run(conversation)
    
    if user_messages:
        response_analysis = self.profile_analyzer._run(
            last_response, conversation
        )
        conv_analysis["response_analysis"] = response_analysis
    
    return {
        **state,
        "turn_count": conv_analysis["turn_count"],
        "current_analysis": conv_analysis,
    }
```

#### 2. Generate Question Node
```python
def _generate_question_node(self, state: InterviewState) -> InterviewState:
    """
    Generates next interview question using LLM.
    
    - Builds system prompt with turn count
    - Adds analysis context
    - Invokes LLM with conversation history
    - Extracts reasoning content (Kimi K2 Thinking)
    - Returns new AIMessage
    """
    system_prompt = InterviewPrompts.get_system_prompt(state["turn_count"])
    
    if state.get("current_analysis"):
        system_prompt += f"\n\nCURRENT ANALYSIS:\n..."
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = self.llm.invoke(messages)
    
    # Extract reasoning
    reasoning_content = response.additional_kwargs.get('reasoning_content')
    
    ai_message = AIMessage(content=response.content)
    if reasoning_content:
        ai_message.additional_kwargs = {'reasoning_content': reasoning_content}
    
    return {"messages": [ai_message], **state}
```

#### 3. Conditional Routing
```python
def _should_continue(self, state: InterviewState) -> str:
    """
    Determines whether to continue interview or generate profile.
    
    Rules:
    - If turn_count >= 12: complete
    - If ready_for_summary flag set: complete
    - Otherwise: continue
    """
    turn_count = state.get("turn_count", 0)
    analysis = state.get("current_analysis", {})
    
    if turn_count >= 12:
        return "complete"
    if analysis.get("ready_for_summary", False):
        return "complete"
    
    return "continue"
```

### State Compilation

```python
self.checkpointer = self._init_checkpointer(use_redis)
self.app = self.graph.compile(checkpointer=self.checkpointer)
```

The compiled graph becomes a stateful application that:
- Persists state after each invocation
- Supports resuming conversations
- Enables session management via thread_id

---

## Redis Integration

### Custom Checkpointer

We implemented a custom Redis checkpointer `RedisCheckpointSaver`:

```python
class RedisCheckpointSaver(BaseCheckpointSaver):
    def __init__(self, redis_client, namespace="langgraph:checkpoint", ttl=86400):
        super().__init__(serde=JsonPlusSerializer())
        self.redis = redis_client
        self.namespace = namespace
        self.ttl = ttl  # 24 hours default
```

### Key Methods

#### put()
```python
def put(self, config, checkpoint, metadata, new_versions):
    """
    Saves checkpoint to Redis using pickle serialization.
    
    Why pickle?
    - JSON can't serialize Python objects with functions
    - LangGraph state contains complex objects
    - pickle handles everything automatically
    """
    data = {
        "checkpoint": checkpoint,
        "metadata": metadata,
        "config": safe_config
    }
    serialized = pickle.dumps(data)
    
    # Store with TTL for automatic cleanup
    key = self._make_key(thread_id, checkpoint_ns, checkpoint.get("id"))
    self.redis.setex(key, self.ttl, serialized)
```

#### get_tuple()
```python
def get_tuple(self, config):
    """
    Retrieves checkpoint from Redis and reconstructs CheckpointTuple.
    """
    key = self._make_key(thread_id, checkpoint_ns, checkpoint_id)
    serialized = self.redis.get(key)
    
    if serialized is None:
        return None
    
    data = pickle.loads(serialized)
    
    return CheckpointTuple(
        config=data.get("config", config),
        checkpoint=data["checkpoint"],
        metadata=data.get("metadata", {}),
        parent_config=data.get("config", {}).get("configurable")
    )
```

### Fallback Strategy

```python
def _init_checkpointer(self, use_redis: bool):
    if use_redis and settings.redis_host:
        try:
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=False,  # Needs bytes for pickle
                socket_connect_timeout=5
            )
            redis_client.ping()
            return RedisCheckpointSaver(redis_client)
        except redis.exceptions.ConnectionError:
            print("⚠ Falling back to in-memory checkpointing")
            return MemorySaver()
    else:
        return MemorySaver()
```

**MemorySaver**: LangGraph's built-in in-memory checkpointer for development.

---

## Data Flow

### Complete Interview Flow

```
1. USER STARTS INTERVIEW
   ├─> cli_interview.py: agent.start_interview(thread_id)
   ├─> InterviewAgent: Initialize empty state in Redis
   └─> Returns: Initial question (static, no LLM call)

2. USER SENDS RESPONSE
   ├─> cli_interview.py: agent.send_message(user_input, thread_id)
   ├─> InterviewAgent.send_message():
   │   ├─> Get current state from Redis
   │   ├─> Add new HumanMessage to state
   │   └─> Invoke graph with updated state
   │
   ├─> LangGraph StateGraph.invoke():
   │   ├─> [analyze_node]
   │   │   ├─> ConversationAnalyzerTool: Check coverage, turn count
   │   │   ├─> ProfileAnalyzerTool: Analyze response style
   │   │   └─> Update state with analysis
   │   │
   │   ├─> [_should_continue]
   │   │   ├─> Check turn_count >= 12?
   │   │   └─> Route to generate_question or generate_profile
   │   │
   │   └─> [generate_question_node]
   │       ├─> Build system prompt with turn context
   │       ├─> Call LLM with conversation history
   │       ├─> Extract reasoning_content from response
   │       └─> Return AIMessage with question
   │
   └─> State saved to Redis automatically

3. INTERVIEW COMPLETES (turn 12 or early quit)
   ├─> cli_interview.py: profile_generator.generate_profile()
   ├─> ProfileGeneratorAgent:
   │   ├─> Format conversation into transcript
   │   ├─> Build profile generation prompt
   │   ├─> Invoke Kimi K2 Thinking model (4000 tokens)
   │   ├─> Parse JSON response
   │   └─> Extract reasoning_content
   │
   └─> cli_interview.py: profile_saver.save_session_summary()
       ├─> ProfileSaver:
       │   ├─> Create user folder structure
       │   ├─> Save conversation_log.json
       │   ├─> Save profile.json
       │   ├─> Save profile.md
       │   └─> ProfileFormatter: Generate SHAREABLE.txt
       │
       └─> User gets: 4 files in user_profiles/{session_id}/
```

### Message Types

LangChain uses typed messages:

```python
from langchain_core.messages import (
    HumanMessage,    # User input
    AIMessage,       # Agent response
    SystemMessage    # System prompt (not persisted in history)
)

# Example flow:
messages = [
    HumanMessage(content="I love Beloved and The Remains of the Day"),
    AIMessage(content="What draws you to stories with restraint?"),
    HumanMessage(content="I prefer when emotion builds slowly..."),
    AIMessage(content="Do you prefer shorter or longer builds?")
]
```

---

## Agents

### 1. InterviewAgent

**Purpose**: Conducts the 12-question adaptive interview

**Model**: `kimi-k2-thinking-turbo` 
- Temperature: 0.8
- Max tokens: 800
- Fast thinking model optimized for interview questions

**Key Methods**:

```python
def start_interview(self, thread_id: str) -> Dict[str, Any]:
    """
    Initializes session state and returns static initial question.
    No LLM call - just returns INITIAL_QUESTION from prompts.
    """

def send_message(self, user_message: str, thread_id: str) -> Dict[str, Any]:
    """
    Processes user input through LangGraph state machine.
    
    Returns:
        {
            "message": str,          # Agent's response
            "turn_count": int,       # Current turn
            "is_complete": bool,     # Interview done?
            "profile_data": dict     # Final profile (if complete)
        }
    """

def get_profile(self, thread_id: str) -> Dict[str, Any]:
    """Retrieves current profile data from state."""
```

**Tools Used**:
- `ProfileAnalyzerTool`: Analyzes response style
- `ConversationAnalyzerTool`: Tracks coverage and turn count

### 2. ProfileGeneratorAgent

**Purpose**: Generates comprehensive literary profiles from completed interviews

**Model**: `kimi-k2-thinking`
- Temperature: 0.7
- Max tokens: 4000
- Extended reasoning for deep analysis

**Key Methods**:

```python
def generate_profile(
    self, 
    conversation: List[Dict[str, str]], 
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates structured profile from conversation transcript.
    
    Process:
    1. Format conversation into readable transcript
    2. Build profile generation prompt with schema
    3. Invoke Kimi K2 Thinking model
    4. Parse JSON response
    5. Add metadata and reasoning
    
    Returns:
        {
            "taste_anchors": {...},
            "style_signature": {...},
            "narrative_desires": {...},
            "consumption": {...},
            "implicit": {...},
            "explanations": {...},
            "reader_archetype": str,
            "_metadata": {...},
            "_reasoning": str  # Kimi K2's internal thinking
        }
    """

def validate_profile(self, profile_data: Dict[str, Any]) -> bool:
    """Validates presence of required fields."""

def _format_transcript(self, conversation: List[Dict]) -> str:
    """
    Converts conversation to readable format:
    
    INTERVIEWER: What books do you love?
    USER: I love Beloved and The Remains of the Day.
    INTERVIEWER: What draws you to those specifically?
    USER: The emotional restraint...
    """
```

**Why Separate Agent?**

1. **Single Responsibility**: Interview vs Analysis
2. **Model Optimization**: Thinking model only where needed
3. **Reusability**: Can generate profiles from any transcript
4. **Cost Control**: Expensive model used once, not 12 times

### 3. ReasoningExtractor

**Purpose**: Extracts and formats Kimi K2 Thinking model's internal reasoning

**Usage**:

```python
extractor = ReasoningExtractor()

# Extract from single response
reasoning = extractor.extract_reasoning(llm_response)

# Extract from message list
messages_with_reasoning = extractor.extract_from_messages(messages)

# Format for display
formatted = extractor.format_reasoning(reasoning, max_length=300)

# Save to file
extractor.save_reasoning_separately(conversation, "reasoning.json")
```

**Why This Matters**:

Kimi K2 Thinking model includes `reasoning_content` in `additional_kwargs`:

```python
response.additional_kwargs = {
    'reasoning_content': "Let me analyze their preference for restraint. 
                         They mentioned Ishiguro and Morrison, both use 
                         controlled prose. I should probe if they prefer
                         brevity or just emotional control..."
}
```

This reveals the model's thought process - valuable for:
- Transparency
- Debugging
- User insight into how profile was generated

---

## Tools

### 1. ProfileAnalyzerTool

**Purpose**: Analyzes individual user responses for implicit signals

**Extends**: `langchain_core.tools.BaseTool`

**Implementation**:

```python
def _run(self, response_text: str, conversation_history: List) -> Dict:
    """
    Calculates:
    - vocabulary_richness: unique_words / total_words
    - response_brevity: inverse of word count (normalized)
    - engagement_level: heuristic based on examples/emotion words
    
    Returns:
        {
            "vocabulary_richness": 0.0-1.0,
            "response_brevity": 0.0-1.0,
            "engagement_level": 0.0-1.0,
            "word_count": int,
            "analysis": str  # "Response style: detailed. Engagement: high..."
        }
    """
```

**Used By**: InterviewAgent in `_analyze_node` to adapt questioning

### 2. ConversationAnalyzerTool

**Purpose**: Tracks overall conversation progress and coverage

**Implementation**:

```python
def _run(self, conversation_history: List[Dict]) -> Dict:
    """
    Analyzes:
    - Turn count (number of user messages)
    - Coverage of key dimensions (taste, style, narrative, consumption)
    - Readiness for profile generation
    
    Coverage Check:
    - taste_anchors: mentions "book", "author", "story", "novel"
    - style_preference: mentions "prose", "writing", "style", "voice"
    - narrative_desire: mentions "wish", "want", "story", "plot"
    - consumption_habit: mentions "read", "time", "daily", "pages"
    
    Returns:
        {
            "turn_count": int,
            "coverage": {"taste_anchors": bool, ...},
            "coverage_score": 0.0-1.0,
            "ready_for_summary": bool,  # turn >= 8 and coverage >= 0.75
            "recommendation": str
        }
    """
```

**Used By**: InterviewAgent to determine when interview can end early

### 3. ProfileSaver

**Purpose**: Organizes and saves all session outputs

**Folder Structure**:

```
user_profiles/
└── {session_id}/
    ├── logs/
    │   └── conversation_TIMESTAMP.json
    └── profiles/
        ├── profile_TIMESTAMP.json
        ├── profile_TIMESTAMP.md
        └── profile_TIMESTAMP_SHAREABLE.txt
```

**Key Methods**:

```python
def save_session_summary(
    self,
    user_id: str,
    conversation: List[Dict],
    profile_data: Dict,
    metadata: Dict
) -> Dict[str, str]:
    """
    Saves complete session in multiple formats.
    
    Returns paths to:
    - log: Full conversation with reasoning
    - profile_json: Machine-readable profile
    - profile_markdown: Human-readable profile
    - profile_shareable: Formatted for social sharing
    - user_folder: Parent directory
    """

def save_conversation_log(
    self, 
    user_id: str, 
    conversation: List[Dict],
    metadata: Dict,
    include_reasoning: bool = True
) -> str:
    """
    Saves:
    {
        "timestamp": "2025-11-08T15:03:24",
        "user_id": "cli_20251108_145739",
        "metadata": {"turn_count": 8, ...},
        "conversation": [
            {"role": "user", "content": "...", "reasoning_content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """
```

### 4. ProfileFormatter

**Purpose**: Converts structured profiles into human-readable formats

**Key Method**:

```python
def format_for_sharing(self, profile: Dict[str, Any]) -> str:
    """
    Generates formatted text with:
    - Header with reader archetype
    - Reading philosophy section
    - Taste anchors (loves/hates)
    - Style metrics with explanations
    - Ideal story description
    - Anti-patterns
    - Reading habits
    - Implicit signals with explanations
    - Metadata footer
    
    Output is optimized for:
    - Terminal display
    - Social media sharing
    - Documentation
    """
```

**Example Output**:

```
================================================================================
                       LITERARY PROFILE: Fracture Dweller
================================================================================

## WHO YOU ARE AS A READER

You read as an act of emotional archaeology, seeking texts that fracture their
own forms to admit the unsayable...

## WHAT YOU LOVE

**Gravitates toward:** The Remains of the Day, Beloved, The Metamorphosis
**Actively avoids:** Finnegans Wake
...
```

---

## Prompts System

### InterviewPrompts Class

**Location**: `src/prompts/interview_prompts.py`

#### 1. SYSTEM_PROMPT

```python
SYSTEM_PROMPT = """
You are a world-class literary profiler conducting an adaptive interview. 
Your goal is to extract a user's literary DNA—their taste, style preferences, narrative desires, and reading patterns.

CORE PRINCIPLES:
- Ask ONE question at a time
- Always reference their specific previous answers
- Adapt follow-ups based on response depth and style
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
- Match their energy: brief answers get concise follow-ups

STRICT RULES:
- CURRENT TURN: {turn_count} of 12
- If turn < 12: Ask another interview question (do NOT mention completion)
- If turn = 12: Only then offer to generate their profile
- Never say "we've reached" or "final question" before turn 12
"""
```

**Critical Fix**: The "STRICT RULES" section prevents the model from prematurely ending the interview. Originally the prompt said "Never exceed 12 questions", which the model interpreted as permission to end early.

#### 2. INITIAL_QUESTION

```python
INITIAL_QUESTION = """Let's start simple. Name 3 books or stories you've 
loved, and 1 you couldn't finish or actively disliked.

Don't overthink it—first ones that come to mind."""
```

**Static Question**: Returned directly by `start_interview()` without LLM call for speed.

#### 3. PROFILE_SUMMARY_PROMPT

```python
PROFILE_SUMMARY_PROMPT = """Based on this interview conversation, generate a structured JSON profile with the following schema.

CRITICAL: Include an "explanations" section with human-readable interpretations of all metrics. Use a second person tone.

{
  "taste_anchors": {
    "loves": [list of books/authors they loved],
    "hates": [list of books/authors they disliked],
    "inferred_genres": [inferred genre preferences]
  },
  "style_signature": {
    "prose_density": 0-100,
    "pacing": 0-100,
    "tone": 0-100,
    "worldbuilding": 0-100,
    "character_focus": 0-100
  },
  "narrative_desires": {
    "wish": "one sentence capturing their ideal story",
    "preferred_ending": "tragic/bittersweet/hopeful/ambiguous/transcendent",
    "themes": [list of thematic interests]
  },
  "consumption": {
    "daily_time_minutes": estimated minutes (15-180),
    "delivery_frequency": "daily/every_few_days/weekly/binge",
    "pages_per_delivery": estimated pages (5-50)
  },
  "implicit": {
    "vocabulary_richness": 0-1 score,
    "response_brevity_score": 0-1,
    "engagement_index": 0-1 score
  },
  "explanations": {
    "prose_density": "explain their score in plain language",
    "pacing": "explain their pacing preference",
    ...
    "reading_philosophy": "2-3 sentence synthesis",
    "anti_patterns": "what to avoid - specific patterns they reject"
  },
  "reader_archetype": "memorable 2-3 word label"
}

Conversation:
{conversation}

Return ONLY valid JSON, no explanations.
"""
```

**Key Features**:
- Detailed schema with exact format
- 0-100 scales for style metrics (easier to understand than 0-1)
- Explanations section in second person for personal feel
- Reader archetype for memorability

---

## CLI Interface

### cli_interview.py

**Entry Point**: `python cli_interview.py` or `./run_interview.sh`

#### Initialization

```python
def main():
    # 1. Check environment
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ Error: MOONSHOT_API_KEY not set")
        sys.exit(1)
    
    # 2. Initialize agents
    agent = InterviewAgent()              # Interview conductor
    profile_generator = ProfileGeneratorAgent()  # Profile analyst
    profile_saver = ProfileSaver()         # File management
    reasoning_extractor = ReasoningExtractor()   # Reasoning extraction
    
    # 3. Ask user preferences
    show_reasoning = input("Show Kimi K2 reasoning? (y/N): ").lower() == 'y'
    
    # 4. Start interview
    session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    response = agent.start_interview(thread_id=session_id)
```

#### Main Loop

```python
conversation_history = []  # For ProfileGenerator
turn_count = 0             # For display

while True:
    # Get user input
    user_input = input("\nYour response (or 'quit' to exit): ").strip()
    
    # Handle quit
    if user_input.lower() in ["quit", "exit", "q"]:
        # Generate profile early
        profile_data = profile_generator.generate_profile(
            conversation_history,
            metadata={'turn_count': turn_count, 'early_termination': True}
        )
        # Save and exit
        break
    
    # Send to agent
    response = agent.send_message(user_input, thread_id=session_id)
    
    # Extract reasoning
    reasoning = reasoning_extractor.extract_reasoning(response["messages"][-1])
    
    # Track conversation
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({
        "role": "assistant", 
        "content": response["message"],
        "reasoning_content": reasoning  # Optional
    })
    turn_count += 1
    
    # Display
    print(f"Agent: {response['message']}")
    if show_reasoning and reasoning:
        print(f"💭 Reasoning: {reasoning[:300]}...")
    print(f"Progress: {'●' * turn_count}{'○' * (12 - turn_count)} ({turn_count}/12)")
    
    # Check completion
    if response.get("is_complete") or turn_count >= 12:
        # Generate final profile
        profile_data = profile_generator.generate_profile(conversation_history)
        # Save everything
        profile_saver.save_session_summary(
            user_id=session_id,
            conversation=conversation_history,
            profile_data=profile_data
        )
        break
```

#### Features

1. **Input Validation**: Warns on responses > 2000 characters
2. **Graceful Exits**: Generates profile even on Ctrl+C
3. **Progress Display**: Visual progress bar with ●○○○○○○○○○○○
4. **Reasoning Toggle**: Optional display of model's thinking
5. **Character Count**: Shows input length for awareness
6. **Error Handling**: Try/catch with user-friendly messages

---

## Configuration

### Settings Management

**File**: `src/config/settings.py`

```python
class Settings:
    def __init__(self):
        # Moonshot AI (Kimi K2)
        self.moonshot_api_key: str = os.getenv("MOONSHOT_API_KEY", "")
        self.moonshot_base_url: str = os.getenv(
            "MOONSHOT_BASE_URL", 
            "https://api.moonshot.cn/v1"
        )
        
        # Redis (optional)
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
        
        # Application
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self):
        if not self.moonshot_api_key:
            raise ValueError("MOONSHOT_API_KEY is required")

settings = Settings()  # Singleton instance
```

### Environment Variables

**File**: `.env` (copied from `env.example`)

```bash
# Moonshot AI API Configuration
MOONSHOT_API_KEY=sk-your-api-key-here
MOONSHOT_BASE_URL=https://api.moonshot.ai/v1

# Redis Configuration (Optional)
REDIS_HOST=redis-xxxxx.xxx.us-east-1-4.ec2.redns.redis-cloud.com
REDIS_PORT=17887
REDIS_PASSWORD=your-redis-password-here

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG_MODE=false
```

### Running Without Redis

The system automatically falls back to in-memory state if Redis is unavailable:

```python
# This is fine:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Result: In-memory checkpointing, sessions lost on restart
```

---

## Output Generation

### Profile Structure

Generated profiles contain:

```json
{
  "taste_anchors": {
    "loves": ["The Remains of the Day", "Beloved"],
    "hates": ["Finnegans Wake"],
    "inferred_genres": ["modernist fiction", "trauma narratives"]
  },
  "style_signature": {
    "prose_density": 70,
    "pacing": 60,
    "tone": 10,
    "worldbuilding": 20,
    "character_focus": 90
  },
  "narrative_desires": {
    "wish": "A story where language fractures to contain catastrophe",
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
    "pacing": "You read forward with steady momentum...",
    "tone": "You gravitate toward dark and serious works...",
    "worldbuilding": "You prefer interior landscapes over constructed worlds...",
    "character_focus": "You're drawn to psychological depth above all...",
    "vocabulary_richness": "Your language reveals a highly literate mind...",
    "engagement_level": "You engaged deeply and philosophically...",
    "reading_philosophy": "You read as an act of emotional archaeology...",
    "anti_patterns": "Avoid linguistic difficulty as subject rather than method..."
  },
  "reader_archetype": "Fracture Dweller",
  "_metadata": {
    "interview_turns": 8,
    "completion_status": "early_exit",
    "early_termination": true
  },
  "_reasoning": "Let me analyze the full conversation... [Kimi K2 thinking]"
}
```

### Output Formats

1. **JSON** (`profile_TIMESTAMP.json`): Machine-readable, full structure
2. **Markdown** (`profile_TIMESTAMP.md`): Human-readable sections
3. **Shareable** (`profile_TIMESTAMP_SHAREABLE.txt`): Formatted for social sharing
4. **Log** (`conversation_TIMESTAMP.json`): Full transcript with reasoning

### Using Profiles with LLMs

The profile becomes your prompt:

```
Give this to Claude/GPT/Grok/Kimi:

"Write a short story for me using these preferences:
- Prose density: 70/100 (between Morrison and Ishiguro)
- Tone: 10/100 (dark, serious, restrained)
- Character focus: 90/100 (psychological depth over plot)
- Build toward a single devastating moment at 85% through
- Avoid linguistic performance for its own sake
- Theme: Language failing to contain private catastrophe
- Ending: Transcendent (through remaining broken)"

Result: Precisely targeted content matching your taste
```

---

## Performance Considerations

### Model Selection

| Aspect | Interview Agent | Profile Generator |
|--------|----------------|-------------------|
| Model | kimi-k2-thinking-turbo | kimi-k2-thinking |
| Tokens | 800 | 4000 |
| Temperature | 0.8 | 0.7 |
| Speed | ~2-3s | ~10-15s |
| Reasoning | Basic thinking | Extended reasoning |
| Total calls | 12+ | 1 |

**Model Strategy**: Both use thinking capability but turbo version is optimized for faster responses during interview.

### Redis Benefits

1. **Session Persistence**: Resume interviews after disconnect
2. **Multi-device**: Continue on different machine
3. **Debugging**: Inspect state at any point
4. **Analytics**: Track all sessions in one place
5. **TTL Cleanup**: Automatic session expiration (24h default)

### Scalability

Current architecture supports:
- **Concurrent Sessions**: Redis handles multiple users
- **Stateless Deployment**: All state in Redis, any instance can serve
- **Horizontal Scaling**: Add more application instances
- **Rate Limiting**: Per-session in Redis

---

## Profile Rubric

### PROFILE_RUBRIC.md

**Purpose**: Comprehensive scoring system and definitions for all profile metrics

**Location**: `PROFILE_RUBRIC.md` in project root

**Integration**: Dynamically loaded into profile generation prompts

This document provides:
- **Standardized scoring scales** for all metrics
- **Interpretation guidelines** for each score range
- **Example scores with explanations**
- **Consistency guidelines** for profile generation
- **Usage instructions** for both agents and users

### How the Rubric is Used in Code

**Dynamic Loading** (as of latest version):

```python
# src/prompts/interview_prompts.py

@staticmethod
def _load_rubric_section() -> str:
    """Load scoring guidelines from PROFILE_RUBRIC.md."""
    if InterviewPrompts.RUBRIC_PATH.exists():
        rubric_content = InterviewPrompts.RUBRIC_PATH.read_text()
        
        # Extract "Style Signature Metrics" section
        if "## Style Signature Metrics" in rubric_content:
            start_idx = rubric_content.find("## Style Signature Metrics")
            end_idx = rubric_content.find("## Implicit Signals", start_idx)
            scales = rubric_content[start_idx:end_idx].strip()
            return f"\nSCORING GUIDELINES:\n{scales}\n"
    
    # Fallback to inline definitions if file missing
    return "[inline fallback scales]"
```

**Usage in Profile Generation**:

```python
# src/agents/profile_generator.py

def generate_profile(self, conversation, metadata):
    # Rubric is automatically included in the prompt
    system_prompt = InterviewPrompts.get_summary_prompt(transcript)
    
    # The prompt contains:
    # 1. JSON schema
    # 2. SCORING GUIDELINES from PROFILE_RUBRIC.md ← Rubric injected here
    # 3. Conversation transcript
    
    messages = [SystemMessage(content=system_prompt)]
    response = self.llm.invoke(messages)
```

**Benefits**:
- **Single Source of Truth**: Update rubric file → prompts update automatically
- **Consistency**: LLM sees detailed scoring guidance during generation
- **Transparency**: Users can reference the same rubric the LLM uses
- **Maintainability**: No hardcoded scales in multiple files

#### Style Signature Metrics (0-100 scale)

**1. Prose Density**
```
0-20:   Sparse, minimalist (Hemingway, Carver)
21-40:  Clean, direct with occasional flourishes
41-60:  Balanced clarity and complexity
61-80:  Dense, literary prose requiring close reading
81-100: Maximum density (Pynchon, Joyce)
```

**2. Pacing**
```
0-20:   Extremely slow, meditative, philosophical
21-40:  Slow burn, character-focused
41-60:  Moderate mix of action and reflection
61-80:  Brisk, plot-driven with momentum
81-100: Rapid thriller-pace
```

**3. Tone**
```
0-20:   Unrelentingly dark, tragic
21-40:  Serious, melancholic, bittersweet
41-60:  Balanced light and shadow
61-80:  Generally optimistic
81-100: Light, comedic, satirical
```

**4. Worldbuilding**
```
0-20:   Minimal, focuses on character/emotion
21-40:  Light backdrop
41-60:  Moderate worldbuilding serving story
61-80:  Rich, detailed, lived-in worlds
81-100: Intricate systems, encyclopedic (Tolkien)
```

**5. Character Focus**
```
0-20:   Plot/ideas over character
21-40:  Character serves plot
41-60:  Balanced character and plot
61-80:  Character-driven with strong interiority
81-100: Deeply psychological, all about inner life
```

#### Implicit Signals (0.0-1.0 scale)

**Vocabulary Richness**: Calculated from unique words / total words in responses
- 0.0-0.3: Basic vocabulary
- 0.51-0.7: Above-average
- 0.86-1.0: Highly sophisticated, literary

**Response Brevity**: Inverse of response length
- 0.0-0.2: Very long, essay-like
- 0.41-0.6: Balanced
- 0.81-1.0: Extremely brief

**Engagement Index**: Based on examples, emotions, metaphors in responses
- 0.0-0.3: Minimal engagement
- 0.51-0.7: Good engagement
- 0.86-1.0: Maximum engagement, deeply analytical

#### Consumption Habits

**Daily Time**: 15-180 minutes
**Delivery Frequency**: daily | every_few_days | weekly | binge
**Pages Per Delivery**: 5-50 pages

#### Why This Matters

1. **Consistency**: Ensures all profiles use the same scale
2. **Interpretability**: Users understand what their scores mean
3. **Actionability**: LLMs can use precise numeric targets
4. **Comparability**: Profiles can be compared across users

**Usage in Profile Generation**:

The ProfileGeneratorAgent references this rubric to:
- Score metrics consistently
- Generate explanations aligned with scales
- Ensure internal coherence (e.g., high prose_density + high character_focus = literary fiction)

**Example Profile Reference**:

```json
{
  "prose_density": 75,
  "explanations": {
    "prose_density": "You appreciate prose dense enough to require active 
                      reading (61-80 range), not passive consumption. Complexity 
                      serves revelation rather than display."
  }
}
```

The explanation directly references the rubric's 61-80 range definition.

---

## Utilities

### retrieve_profile.py

**Purpose**: Utility script to retrieve interview sessions from Redis and manually generate profiles

**Location**: `retrieve_profile.py` in project root

**Use Case**: When you want to:
- Retrieve a past interview session
- Manually inspect conversation state
- Generate a profile for an incomplete interview
- Test profile generation with custom data

**Usage**:

```python
#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

from src.agents import InterviewAgent

# Your session ID from interview
session_id = "cli_20251108_145739"

# Retrieve from Redis
agent = InterviewAgent(use_redis=True)
profile = agent.get_profile(thread_id=session_id)

print(f"Turns: {profile.get('turn_count')}")
print(f"Complete: {profile.get('is_complete')}")
```

**Manual Profile Creation**:

The script also demonstrates how to manually create a profile structure:

```python
your_profile = {
    "taste_anchors": {
        "loves": ["Book 1", "Book 2"],
        "hates": ["Book 3"],
        "inferred_genres": ["literary_fiction"]
    },
    "style_signature": {
        "prose_density": 75,
        "pacing": 35,
        "tone": 20,
        "worldbuilding": 30,
        "character_focus": 85
    },
    "narrative_desires": {
        "wish": "Your ideal story in one sentence",
        "preferred_ending": "bittersweet",
        "themes": ["theme1", "theme2"]
    },
    "consumption": {
        "daily_time_minutes": 60,
        "delivery_frequency": "daily",
        "pages_per_delivery": 20
    },
    "implicit": {
        "vocabulary_richness": 0.85,
        "response_brevity_score": 0.3,
        "engagement_index": 0.9
    },
    "reader_archetype": "Your Archetype",
    "reading_philosophy": "Your philosophy",
    "anti_patterns": ["pattern1", "pattern2"]
}

# Save to file
with open(f"profile_{session_id}.json", 'w') as f:
    json.dump(your_profile, indent=2, fp=f)
```

**When to Use**:

1. **Session Recovery**: Redis session expired but you have the conversation log
2. **Profile Refinement**: Generate profile, then manually adjust scores
3. **Testing**: Create test profiles with known metrics
4. **Analysis**: Inspect how profiles are structured

### user_profiles/ Directory

**Structure**:

```
user_profiles/
└── {session_id}/
    ├── logs/
    │   └── conversation_TIMESTAMP.json      # Full transcript with reasoning
    └── profiles/
        ├── profile_TIMESTAMP.json           # Machine-readable profile
        ├── profile_TIMESTAMP.md             # Human-readable markdown
        └── profile_TIMESTAMP_SHAREABLE.txt  # Formatted for sharing
```

**Example Session**: `cli_20251108_145739/`

**Conversation Log** (`logs/conversation_20251108_150303.json`):
```json
{
  "timestamp": "2025-11-08T15:03:24",
  "user_id": "cli_20251108_145739",
  "metadata": {
    "turn_count": 8,
    "completion_status": "early_exit",
    "early_termination": true
  },
  "conversation": [
    {
      "role": "user",
      "content": "Three books I've loved: The Remains of the Day..."
    },
    {
      "role": "assistant",
      "content": "Your taste gravitates toward emotional precision...",
      "reasoning_content": "Let me analyze their preference for restraint..."
    }
  ],
  "note": "reasoning_content field contains Kimi K2 internal thinking process"
}
```

**Profile JSON** (`profiles/profile_20251108_150303.json`):
```json
{
  "taste_anchors": {...},
  "style_signature": {...},
  "narrative_desires": {...},
  "consumption": {...},
  "implicit": {...},
  "explanations": {...},
  "reader_archetype": "Fracture Dweller",
  "_metadata": {
    "interview_turns": 8,
    "completion_status": "early_exit",
    "early_termination": true
  },
  "_reasoning": "Kimi K2 thinking process..."
}
```

**Profile Markdown** (`profiles/profile_20251108_150303.md`):
AI-readable format with sections and formatting.

**Accessing Profiles**:

```python
import json
from pathlib import Path

# List all sessions
sessions = list(Path("user_profiles").iterdir())

# Load specific profile
session_id = "cli_20251108_145739"
profile_path = Path("user_profiles") / session_id / "profiles"
latest_profile = sorted(profile_path.glob("profile_*.json"))[-1]

with open(latest_profile) as f:
    profile = json.load(f)
```

**Backup and Portability**:

The `user_profiles/` directory is:
- **Self-contained**: All session data in one place
- **Portable**: Can be copied/archived
- **Timestamped**: Multiple profiles per session
- **Traceable**: Links back to conversation that generated it

**Privacy Note**:

- `.gitignore` excludes `user_profiles/` by default
- Contains user responses and personal preferences
- Should be treated as private data
- For demo purposes, add specific sessions manually

---

## Debugging

### Enable Debug Mode

```bash
export DEBUG_MODE=true
python cli_interview.py
```

Shows:
```
DEBUG: Generating question with 8 messages in history
DEBUG: Last message type: human, content preview: I read forward through fissures...
```

### Inspect Redis State

```python
import redis
import pickle

r = redis.Redis(host='...', port=..., password='...')

# List all sessions
keys = r.keys("langgraph:checkpoint:*")

# Get specific session
data = r.get("langgraph:checkpoint:cli_20251108_145739:latest")
state = pickle.loads(data)

print(state["checkpoint"]["messages"])
print(state["checkpoint"]["turn_count"])
```

### Check Profile Generation

```python
from src.agents import ProfileGeneratorAgent

generator = ProfileGeneratorAgent()

# Test with sample conversation
conversation = [
    {"role": "user", "content": "I love Beloved..."},
    {"role": "assistant", "content": "What draws you..."}
]

profile = generator.generate_profile(conversation)
print(json.dumps(profile, indent=2))
```

---

## Conclusion

WREN demonstrates practical application of:
- **LangGraph**: Stateful conversation management
- **LangChain**: LLM abstraction and message handling
- **Redis**: Persistent state storage
- **Adaptive AI**: Dynamic questioning based on response analysis
- **Multi-agent Systems**: Specialized agents for different tasks
- **Prompt Engineering**: Precise control over LLM behavior

The system successfully bridges the gap between human intuition about literary taste and machine-actionable instructions for content generation.

---

## Quick Reference

### Start Interview
```bash
./run_interview.sh
```

### Environment Setup
```bash
cp env.example .env
# Edit .env with your API keys
source .env
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### File Locations
- **Agents**: `src/agents/`
- **Tools**: `src/tools/`
- **Prompts**: `src/prompts/`
- **Config**: `src/config/`
- **CLI**: `cli_interview.py`
- **Outputs**: `user_profiles/{session_id}/`
- **Rubric**: `PROFILE_RUBRIC.md`
- **Utilities**: `retrieve_profile.py`

### Key Classes
- `InterviewAgent`: Main interview conductor
- `ProfileGeneratorAgent`: Profile analysis
- `RedisCheckpointSaver`: State persistence
- `ProfileSaver`: File management
- `ProfileFormatter`: Human-readable output

### Key Methods
- `agent.start_interview(thread_id)`
- `agent.send_message(text, thread_id)`
- `generator.generate_profile(conversation)`
- `saver.save_session_summary(user_id, conversation, profile)`

---

**Built by**: Muratcan Koylan  
**Repository**: https://github.com/muratcankoylan/readwren  
**Twitter**: @koylanai  
**License**: Open Source

