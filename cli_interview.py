#!/usr/bin/env python3
"""
Interactive CLI for the Wren Interview Agent.

Usage:
    python cli_interview.py
"""

import os
import sys
import json
from datetime import datetime
from src.agents import InterviewAgent, ReasoningExtractor, ProfileGeneratorAgent
from src.tools import ProfileSaver


def print_separator(char="─", length=80):
    """Print a visual separator."""
    print(char * length)


def print_agent_message(message: str):
    """Print agent message with formatting."""
    print(f"\n🎭 Agent: {message}\n")


def print_user_message(message: str):
    """Print user message with formatting."""
    print(f"You: {message}")


def print_status(turn_count: int, max_turns: int = 12):
    """Print current progress."""
    progress = "●" * turn_count + "○" * (max_turns - turn_count)
    print(f"\nProgress: {progress} ({turn_count}/{max_turns})")


def save_profile(profile_data: dict, session_id: str):
    """Save profile to JSON file."""
    filename = f"profile_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(profile_data, f, indent=2)
    print(f"\n✓ Profile saved to: {filename}")


def main():
    """Run interactive interview session."""
    print("\n" + "=" * 80)
    print("WREN INTERVIEW AGENT".center(80))
    print("Literary Profiling via Kimi K2 Thinking Model".center(80))
    print("=" * 80 + "\n")

    # Check API key
    if not os.getenv("MOONSHOT_API_KEY"):
        print("❌ Error: MOONSHOT_API_KEY not set in environment")
        print("\nPlease:")
        print("1. Copy env.example to .env")
        print("2. Add your API key from https://platform.moonshot.ai/")
        print("3. Run: export $(cat .env | xargs)")
        sys.exit(1)

    # Initialize agents and tools
    try:
        print("Initializing agents...")
        agent = InterviewAgent()
        profile_generator = ProfileGeneratorAgent()
        profile_saver = ProfileSaver()
        reasoning_extractor = ReasoningExtractor()
        print("✓ Agents initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Ask if user wants to see reasoning
    show_reasoning_input = input("\nShow Kimi K2 reasoning process? (y/N): ").strip().lower()
    show_reasoning = show_reasoning_input == 'y'
    print()

    # Generate session ID
    session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Session ID: {session_id}\n")
    print_separator("=")

    # Start interview
    try:
        response = agent.start_interview(thread_id=session_id)
        print_agent_message(response["message"])
        print_status(response["turn_count"])
    except Exception as e:
        print(f"❌ Error starting interview: {e}")
        sys.exit(1)

    # Track conversation for logging
    conversation_history = []
    turn_count = 0
    
    # Main conversation loop
    while True:
        print_separator()

        # Get user input
        try:
            user_input = input("\nYour response (or 'quit' to exit): ").strip()
            
            # Validate input length (warn if very long)
            if len(user_input) > 2000:
                print(f"⚠ Long response detected ({len(user_input)} characters)")
                confirm = input("Continue anyway? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Response truncated to 2000 characters")
                    user_input = user_input[:2000]
                    
        except (KeyboardInterrupt, EOFError):
            print("\n\nInterview interrupted.")
            # Generate profile before exiting
            print("\nGenerating profile from interview so far...")
            profile_data = profile_generator.generate_profile(
                conversation_history,
                metadata={
                    'turn_count': turn_count,
                    'completion_status': 'interrupted',
                    'early_termination': True
                }
            )
            # Save profile
            try:
                profile_paths = profile_saver.save_session_summary(
                    user_id=session_id,
                    conversation=conversation_history,
                    profile_data=profile_data,
                    metadata={'completion_status': 'interrupted'}
                )
                print(f"\n✓ Profile saved to: {profile_paths['user_folder']}")
            except Exception as e:
                print(f"⚠ Failed to save profile: {e}")
            sys.exit(0)

        if not user_input:
            print("Please provide a response.")
            continue

        # Check for quit command
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nEnding interview early...")
            print("Generating your literary profile...\n")
            
            # Generate profile using dedicated agent
            profile_data = profile_generator.generate_profile(
                conversation_history,
                metadata={
                    'turn_count': turn_count,
                    'completion_status': 'early_exit',
                    'early_termination': True
                }
            )
            
            # Display and save profile
            print_separator("=")
            print("\n🎉 Your Literary Profile\n")
            print_separator("=")
            
            if profile_data and not profile_data.get("error"):
                print(json.dumps(profile_data, indent=2))
                
                # Save everything
                try:
                    profile_paths = profile_saver.save_session_summary(
                        user_id=session_id,
                        conversation=conversation_history,
                        profile_data=profile_data,
                        metadata={
                            'turn_count': turn_count,
                            'completion_status': 'early_exit'
                        }
                    )
                    print(f"\n✓ Profile saved to:")
                    print(f"  - User folder: {profile_paths['user_folder']}")
                    print(f"  - Conversation: {profile_paths['log']}")
                    print(f"  - Profile JSON: {profile_paths['profile_json']}")
                    print(f"  - Profile Markdown: {profile_paths['profile_markdown']}")
                except Exception as e:
                    print(f"\n⚠ Failed to save profile: {e}")
            else:
                print(f"❌ Profile generation failed: {profile_data.get('error', 'Unknown error')}")
            
            break

        # Send message to agent
        try:
            print(f"[Sending {len(user_input)} chars...]")
            response = agent.send_message(user_input, thread_id=session_id)
            
            # Extract reasoning if available
            reasoning = None
            if response.get("messages"):
                latest_msg = response["messages"][-1]
                reasoning = reasoning_extractor.extract_reasoning(latest_msg)
            
            # Track conversation
            conversation_history.append({"role": "user", "content": user_input})
            assistant_entry = {"role": "assistant", "content": response["message"]}
            if reasoning:
                assistant_entry["reasoning_content"] = reasoning
            conversation_history.append(assistant_entry)
            turn_count += 1

            print_user_message(user_input)
            print_agent_message(response["message"])
            
            # Show reasoning if enabled
            if show_reasoning and reasoning:
                print(f"\n💭 [Reasoning]: {reasoning[:300]}..." if len(reasoning) > 300 else f"\n💭 [Reasoning]: {reasoning}")
            
            print_status(turn_count)  # Use local turn count for display

            # Check if complete
            if response.get("is_complete") or turn_count >= 12:
                print_separator("=")
                print("\n🎉 Interview Complete!\n")
                print_separator("=")

                # Generate profile using dedicated profile generator agent
                print("Generating your comprehensive literary profile...\n")
                profile_data = profile_generator.generate_profile(
                    conversation_history,
                    metadata={
                        'turn_count': turn_count,
                        'completion_status': 'complete',
                        'early_termination': False
                    }
                )
                
                # Show profile generation reasoning if available
                if show_reasoning and isinstance(profile_data, dict) and "_reasoning" in profile_data:
                    print(f"\n💭 [Profile Generation Reasoning]:\n{profile_data['_reasoning'][:500]}...")

                # Display profile
                if profile_data and not profile_data.get("error"):
                    print("\nYour Literary Profile:")
                    print_separator()
                    print(json.dumps(profile_data, indent=2))

                    # Save using ProfileSaver
                    try:
                        paths = profile_saver.save_session_summary(
                            user_id=session_id,
                            conversation=conversation_history,
                            profile_data=profile_data,
                            metadata={
                                "turns": turn_count,
                                "completion_status": "complete",
                                "completed_at": datetime.now().isoformat()
                            }
                        )
                        
                        print(f"\n✓ Session saved to: {paths['user_folder']}")
                        print(f"  - Conversation log: {os.path.basename(paths['log'])}")
                        print(f"  - Profile (JSON): {os.path.basename(paths['profile_json'])}")
                        print(f"  - Profile (Markdown): {os.path.basename(paths['profile_markdown'])}")
                        
                    except Exception as e:
                        print(f"\n⚠ Could not save session: {e}")
                        # Fallback to old save method
                        save_profile(profile_data, session_id)
                else:
                    print(f"❌ Profile generation failed: {profile_data.get('error', 'Unknown error')}")

                break

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")
            continue

    print("\n" + "=" * 80)
    print("Thank you for using Wren Interview Agent".center(80))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

