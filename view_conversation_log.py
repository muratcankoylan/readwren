#!/usr/bin/env python3
"""View conversation from saved log files in readable format."""

import json
import sys
from pathlib import Path

def view_conversation(log_file):
    """Display conversation in readable format."""
    
    try:
        with open(log_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {log_file}")
        return
    except json.JSONDecodeError:
        print(f"Invalid JSON in file: {log_file}")
        return

    print("=" * 80)
    print(f"CONVERSATION LOG".center(80))
    print("=" * 80)
    print()
    
    # Show metadata
    print(f"Session ID: {data.get('user_id', 'N/A')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    
    metadata = data.get('metadata', {})
    print(f"Turn Count: {metadata.get('turn_count', 'N/A')}")
    print(f"Status: {metadata.get('completion_status', 'N/A')}")
    print()
    
    # Show conversation
    conversation = data.get('conversation', [])
    
    if not conversation:
        print("No conversation messages found.")
        return
    
    print("=" * 80)
    print("MESSAGES".center(80))
    print("=" * 80)
    
    for i, msg in enumerate(conversation, 1):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        
        print()
        if role in ['user', 'human']:
            print(f"{'─' * 80}")
            print(f"👤 USER (Turn {(i+1)//2})")
            print(f"{'─' * 80}")
        elif role in ['assistant', 'ai']:
            print(f"{'─' * 80}")
            print(f"🎭 AGENT (Turn {i//2})")
            print(f"{'─' * 80}")
        else:
            print(f"{'─' * 80}")
            print(f"📝 {role.upper()}")
            print(f"{'─' * 80}")
        
        print(content)
        
        # Show reasoning if available
        reasoning = msg.get('reasoning_content')
        if reasoning:
            print(f"\n💭 KIMI K2 REASONING:")
            print(f"{'·' * 80}")
            # Show first 300 chars
            preview = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            print(preview)
    
    print()
    print("=" * 80)
    print(f"Total messages: {len(conversation)}")
    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python view_conversation_log.py <log_file_path>")
        print()
        print("Example:")
        print("  python view_conversation_log.py user_profiles/cli_20251108_145739/logs/conversation_20251108_150303.json")
        print()
        print("Or find your logs:")
        print("  ls -lt user_profiles/*/logs/*.json")
        return
    
    log_file = sys.argv[1]
    view_conversation(log_file)


if __name__ == "__main__":
    main()

