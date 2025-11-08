#!/usr/bin/env python3
"""View all WREN sessions stored in Redis."""

import redis
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    # Connect to Redis
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=False  # Need bytes for pickle
        )
        r.ping()
        print("✓ Connected to Redis\n")
    except redis.exceptions.ConnectionError as e:
        print(f"✗ Redis connection failed: {e}")
        print("\nCheck your .env file has:")
        print("  REDIS_HOST=...")
        print("  REDIS_PORT=...")
        print("  REDIS_PASSWORD=...")
        return

    print("=" * 80)
    print("WREN SESSIONS IN REDIS".center(80))
    print("=" * 80 + "\n")

    # Get all checkpoint keys
    keys = r.keys("langgraph:checkpoint:*:latest")
    
    if not keys:
        print("No active sessions found.")
        print("\nSessions expire after 24 hours.")
        print("To see archived sessions, check: user_profiles/")
        return

    print(f"Found {len(keys)} active session(s):\n")

    for key in keys:
        key_str = key.decode('utf-8')
        session_id = key_str.split(':')[2]
        
        # Get TTL
        ttl = r.ttl(key)
        hours_left = ttl / 3600 if ttl > 0 else 0
        
        print(f"Session ID: {session_id}")
        print("-" * 80)
        
        try:
            # Get and unpickle data
            data = r.get(key)
            if not data:
                print("  [Empty or expired]\n")
                continue
                
            state = pickle.loads(data)
            checkpoint = state.get('checkpoint', {})
            
            # Display session info
            turn_count = checkpoint.get('turn_count', 0)
            messages = checkpoint.get('messages', [])
            is_complete = checkpoint.get('is_complete', False)
            
            print(f"  Turn count: {turn_count}/12")
            print(f"  Messages: {len(messages)}")
            print(f"  Status: {'Complete' if is_complete else 'In progress'}")
            print(f"  TTL: {hours_left:.1f} hours remaining")
            
            # Show last message preview if available
            if messages:
                last_msg = messages[-1]
                content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
                preview = content[:80] + "..." if len(content) > 80 else content
                print(f"  Last message: {preview}")
            
            # Show profile status
            profile_data = checkpoint.get('profile_data', {})
            if profile_data:
                archetype = profile_data.get('reader_archetype', 'N/A')
                print(f"  Profile generated: {archetype}")
            
            print()
            
        except Exception as e:
            print(f"  Error reading session: {e}\n")

    print("=" * 80)
    print(f"Total active sessions: {len(keys)}")
    print("=" * 80)
    
    # Show Redis info
    info = r.info('memory')
    memory_mb = info['used_memory'] / (1024 * 1024)
    print(f"\nRedis memory usage: {memory_mb:.2f} MB")


if __name__ == "__main__":
    main()

