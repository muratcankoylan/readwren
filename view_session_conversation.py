#!/usr/bin/env python3
"""View full conversation from a Redis session in readable format."""

import redis
import pickle
import os
import sys
from dotenv import load_dotenv
import json

load_dotenv()

def view_session(session_id):
    """Display full conversation for a session."""
    
    # Connect to Redis
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT')),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=False
        )
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"✗ Redis connection failed: {e}")
        return

    # Get session data
    key = f"langgraph:checkpoint:{session_id}:latest"
    data = r.get(key)
    
    if not data:
        print(f"Session '{session_id}' not found in Redis")
        print(f"\nTried key: {key}")
        print("\nAvailable sessions:")
        keys = r.keys("langgraph:checkpoint:*:latest")
        for k in keys[:10]:
            sid = k.decode('utf-8').split(':')[2]
            print(f"  - {sid}")
        return

    # Unpickle and display
    try:
        state = pickle.loads(data)
        checkpoint = state.get('checkpoint', {})
        
        print("=" * 80)
        print(f"SESSION: {session_id}".center(80))
        print("=" * 80)
        print()
        
        # Session info
        turn_count = checkpoint.get('turn_count', 0)
        is_complete = checkpoint.get('is_complete', False)
        messages = checkpoint.get('messages', [])
        
        print(f"Turn Count: {turn_count}/12")
        print(f"Status: {'Complete' if is_complete else 'In Progress'}")
        print(f"Total Messages: {len(messages)}")
        print()
        
        if not messages:
            print("No messages in this session yet.")
            return
        
        # Display conversation
        print("=" * 80)
        print("CONVERSATION".center(80))
        print("=" * 80)
        print()
        
        for i, msg in enumerate(messages, 1):
            # Get message details
            role = msg.type if hasattr(msg, 'type') else 'unknown'
            content = msg.content if hasattr(msg, 'content') else str(msg)
            
            # Format role
            if role in ['human', 'user']:
                print(f"\n{'─' * 80}")
                print(f"👤 USER (Message {i})")
                print(f"{'─' * 80}")
            elif role in ['ai', 'assistant']:
                print(f"\n{'─' * 80}")
                print(f"🎭 AGENT (Message {i})")
                print(f"{'─' * 80}")
            else:
                print(f"\n{'─' * 80}")
                print(f"📝 {role.upper()} (Message {i})")
                print(f"{'─' * 80}")
            
            print(content)
            
            # Show reasoning if available
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                reasoning = msg.additional_kwargs.get('reasoning_content')
                if reasoning:
                    print(f"\n💭 REASONING:")
                    print(f"{'─' * 80}")
                    # Show first 500 chars of reasoning
                    preview = reasoning[:500] + "..." if len(reasoning) > 500 else reasoning
                    print(preview)
        
        print()
        print("=" * 80)
        
        # Show analysis data if available
        current_analysis = checkpoint.get('current_analysis', {})
        if current_analysis:
            print("\nANALYSIS DATA")
            print("─" * 80)
            print(json.dumps(current_analysis, indent=2))
        
        # Show profile if generated
        profile_data = checkpoint.get('profile_data', {})
        if profile_data:
            print("\nPROFILE GENERATED")
            print("─" * 80)
            archetype = profile_data.get('reader_archetype', 'N/A')
            print(f"Reader Archetype: {archetype}")
            
            if 'style_signature' in profile_data:
                print("\nStyle Signature:")
                for key, value in profile_data['style_signature'].items():
                    print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Error decoding session: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print("Usage: python view_session_conversation.py <session_id>")
        print()
        print("Example:")
        print("  python view_session_conversation.py cli_20251108_145739")
        print()
        print("To list all sessions:")
        print("  python view_redis_sessions.py")
        return
    
    session_id = sys.argv[1]
    view_session(session_id)


if __name__ == "__main__":
    main()

