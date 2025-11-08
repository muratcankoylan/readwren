import json
import os
import redis
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.prompts import InterviewPrompts
from src.tools import ProfileAnalyzerTool, ConversationAnalyzerTool
from src.agents.redis_checkpointer import RedisCheckpointSaver


class InterviewState(TypedDict):
    """State for the interview graph."""

    messages: Annotated[List[BaseMessage], add]
    turn_count: int
    profile_data: Dict[str, Any]
    is_complete: bool
    current_analysis: Dict[str, Any]


class InterviewAgent:
    """Literary interview agent using LangGraph and Kimi K2 Thinking model."""

    def __init__(self, use_redis: bool = True):
        """Initialize the interview agent with Kimi K2 model.
        
        Args:
            use_redis: If True, use Redis for persistent checkpointing. 
                      If False, use in-memory checkpointing (development only).
        """
        settings.validate()

        # Initialize regular Kimi K2 model for interviewing (faster, no thinking overhead)
        self.llm = ChatOpenAI(
            model="𝚔𝚒𝚖𝚒-𝚔𝟸-𝚝𝚑𝚒𝚗𝚔𝚒𝚗𝚐-𝚝𝚞𝚛𝚋𝚘",  # Regular Kimi model for conversational questions
            api_key=settings.moonshot_api_key,
            base_url=settings.moonshot_base_url,
            temperature=0.8,
            max_tokens=800,  # Standard tokens for interview questions
        )

        # Initialize tools
        self.profile_analyzer = ProfileAnalyzerTool()
        self.conversation_analyzer = ConversationAnalyzerTool()

        # Build the graph
        self.graph = self._build_graph()
        
        # Initialize checkpointer (Redis or in-memory)
        self.checkpointer = self._init_checkpointer(use_redis)
        self.app = self.graph.compile(checkpointer=self.checkpointer)

    def _init_checkpointer(self, use_redis: bool):
        """Initialize the appropriate checkpointer based on configuration.
        
        Args:
            use_redis: Whether to use Redis or in-memory checkpointing
            
        Returns:
            Checkpointer instance (RedisSaver or MemorySaver)
        """
        if use_redis and settings.redis_host:
            try:
                # Create Redis client
                redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password if settings.redis_password else None,
                    decode_responses=False,  # LangGraph needs bytes mode
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test connection
                redis_client.ping()
                
                print("✓ Connected to Redis")
                return RedisCheckpointSaver(redis_client)
                
            except redis.exceptions.ConnectionError as e:
                print(f"⚠ Redis connection failed: {e}")
                print("⚠ Falling back to in-memory checkpointing")
                return MemorySaver()
            except Exception as e:
                print(f"⚠ Redis initialization failed: {e}")
                print("⚠ Falling back to in-memory checkpointing")
                return MemorySaver()
        else:
            if not use_redis:
                print("ℹ Using in-memory checkpointing (development mode)")
            else:
                print("⚠ Redis not configured, using in-memory checkpointing")
            return MemorySaver()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the interview."""
        workflow = StateGraph(InterviewState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("generate_question", self._generate_question_node)
        workflow.add_node("generate_profile", self._generate_profile_node)

        # Define edges
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

    def _analyze_node(self, state: InterviewState) -> InterviewState:
        """Analyze current conversation state."""
        conversation = [
            {"role": msg.type, "content": msg.content} for msg in state["messages"]
        ]

        # Analyze conversation progress
        conv_analysis = self.conversation_analyzer._run(conversation)

        # Analyze last user response if exists
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if user_messages:
            last_response = user_messages[-1].content
            response_analysis = self.profile_analyzer._run(last_response, conversation)
            conv_analysis["response_analysis"] = response_analysis

        return {
            **state,
            "turn_count": conv_analysis["turn_count"],
            "current_analysis": conv_analysis,
        }

    def _generate_question_node(self, state: InterviewState) -> InterviewState:
        """Generate next interview question."""
        # Build system prompt with context
        system_prompt = InterviewPrompts.get_system_prompt(state["turn_count"])

        # Add analysis context if available
        if state.get("current_analysis"):
            analysis = state["current_analysis"]
            system_prompt += f"\n\nCURRENT ANALYSIS:\n"
            system_prompt += f"- Turn count: {analysis.get('turn_count', 0)}\n"
            system_prompt += f"- Coverage: {analysis.get('coverage_score', 0)}\n"
            if "response_analysis" in analysis:
                system_prompt += f"- Response style: {analysis['response_analysis'].get('analysis', '')}\n"

        # Filter out empty messages and prepare for LLM
        valid_messages = [msg for msg in state["messages"] if msg.content.strip()]
        
        # DEBUG: Log conversation length and last user message (can be disabled in production)
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            print(f"DEBUG: Generating question with {len(valid_messages)} messages in history")
            if len(valid_messages) > 0:
                last_msg = valid_messages[-1]
                print(f"DEBUG: Last message type: {last_msg.type}, content preview: {last_msg.content[:80]}...")
        
        messages = [SystemMessage(content=system_prompt)] + valid_messages

        # Generate next question with reasoning capture
        response = self.llm.invoke(messages)
        
        # Extract reasoning content if available (Kimi K2 Thinking model)
        reasoning_content = None
        if hasattr(response, 'additional_kwargs'):
            # Kimi K2 may include reasoning in additional_kwargs
            reasoning_content = response.additional_kwargs.get('reasoning_content', None)
        
        # Store reasoning in metadata if available
        ai_message = AIMessage(content=response.content)
        if reasoning_content:
            ai_message.additional_kwargs = {'reasoning_content': reasoning_content}

        return {
            **state,
            "messages": [ai_message],
        }

    def _generate_profile_node(self, state: InterviewState) -> InterviewState:
        """Generate final profile from conversation."""
        # Build conversation transcript
        conversation = "\n".join(
            [
                f"{msg.type}: {msg.content}"
                for msg in state["messages"]
                if not isinstance(msg, SystemMessage)
            ]
        )

        # Generate profile with higher token limit for JSON output
        summary_prompt = InterviewPrompts.get_summary_prompt(conversation)
        
        # Use a fresh LLM instance with higher token limit for profile generation
        profile_llm = ChatOpenAI(
            model="kimi-k2-thinking",
            api_key=self.llm.api_key,
            base_url=self.llm.base_url,
            temperature=0.7,
            max_tokens=3000,  # More tokens for complete JSON profile
        )
        
        messages = [SystemMessage(content=summary_prompt)]
        response = profile_llm.invoke(messages)

        # Parse JSON profile
        try:
            profile_data = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            profile_data = {"error": "Failed to parse profile", "raw": response.content}
        
        # Capture reasoning content for profile generation
        if hasattr(response, 'additional_kwargs'):
            reasoning = response.additional_kwargs.get('reasoning_content', None)
            if reasoning:
                profile_data["_reasoning"] = reasoning

        return {
            **state,
            "profile_data": profile_data,
            "is_complete": True,
            "messages": [AIMessage(content=f"Profile generated: {json.dumps(profile_data, indent=2)}")],
        }

    def _should_continue(self, state: InterviewState) -> str:
        """Determine if interview should continue or complete."""
        analysis = state.get("current_analysis", {})
        turn_count = state.get("turn_count", 0)

        # Check if ready to complete
        if turn_count >= 12:
            return "complete"

        if analysis.get("ready_for_summary", False):
            return "complete"

        return "continue"

    def start_interview(self, thread_id: str = "default") -> Dict[str, Any]:
        """Start a new interview session."""
        # Return initial question directly without processing through graph
        # The graph will start processing when user sends first response
        config = {"configurable": {"thread_id": thread_id}}
        
        # Initialize empty state in checkpointer for this thread
        initial_state: InterviewState = {
            "messages": [],
            "turn_count": 0,
            "profile_data": {},
            "is_complete": False,
            "current_analysis": {},
        }
        
        # Store initial state
        self.app.update_state(config, initial_state)

        return {
            "message": InterviewPrompts.INITIAL_QUESTION,
            "turn_count": 0,
            "is_complete": False,
        }

    def send_message(
        self, user_message: str, thread_id: str = "default"
    ) -> Dict[str, Any]:
        """Send a user message and get agent response."""
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state
        current_state = self.app.get_state(config)

        # Get existing messages and add new user message
        existing_messages = current_state.values.get("messages", []) if current_state.values else []
        
        # Add user message to state (append to existing messages)
        new_state: InterviewState = {
            "messages": [HumanMessage(content=user_message)],  # LangGraph will append with Annotated[List, add]
            "turn_count": current_state.values.get("turn_count", 0) if current_state.values else 0,
            "profile_data": current_state.values.get("profile_data", {}) if current_state.values else {},
            "is_complete": current_state.values.get("is_complete", False) if current_state.values else False,
            "current_analysis": current_state.values.get("current_analysis", {}) if current_state.values else {},
        }

        # Run graph
        result = self.app.invoke(new_state, config)

        return {
            "message": result["messages"][-1].content if result.get("messages") else "",
            "turn_count": result.get("turn_count", 0),
            "is_complete": result.get("is_complete", False),
            "profile_data": result.get("profile_data", {}),
        }

    def get_profile(self, thread_id: str = "default") -> Dict[str, Any]:
        """Get current profile data for a session."""
        config = {"configurable": {"thread_id": thread_id}}
        current_state = self.app.get_state(config)

        return {
            "profile_data": current_state.values.get("profile_data", {}),
            "turn_count": current_state.values.get("turn_count", 0),
            "is_complete": current_state.values.get("is_complete", False),
        }

