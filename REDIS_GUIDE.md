# Redis Session Management Guide

## Overview

Yes, WREN uses Redis Cloud for persistent session storage. All interview state (messages, turn count, analysis) is stored in Redis with 24-hour TTL.

## Your Redis Configuration

From your `.env` file:
```bash
REDIS_HOST=redis-17887.c57.us-east-1-4.ec2.redns.redis-cloud.com
REDIS_PORT=17887
REDIS_PASSWORD=mjZCoOjapBWnTnjBlHDneS6WTVNLF53J
```

## Viewing Sessions in Redis Cloud Dashboard

### 1. Access the Web Interface

1. Go to: https://app.redislabs.com/
2. Log in with your Redis Cloud account
3. Navigate to your database (the one with host `redis-17887.c57.us-east-1-4.ec2.redns.redis-cloud.com`)

### 2. Use the Browser Tool

In the Redis Cloud dashboard:
- Click on your database
- Go to "Browser" tab
- You'll see all keys in your database

### 3. Search for Session Keys

All WREN sessions are prefixed with:
```
langgraph:checkpoint:{session_id}:*
```

Example keys:
```
langgraph:checkpoint:cli_20251108_145739:latest
langgraph:checkpoint:cli_20251108_145739:checkpoint_id_123
```

## Viewing Sessions via redis-cli

### Connect to Redis

```bash
redis-cli -u redis://default:mjZCoOjapBWnTnjBlHDneS6WTVNLF53J@redis-17887.c57.us-east-1-4.ec2.redns.redis-cloud.com:17887
```

### List All Sessions

```bash
# List all checkpoint keys
KEYS langgraph:checkpoint:*

# Count total sessions
KEYS langgraph:checkpoint:* | wc -l

# List just session IDs (unique)
KEYS langgraph:checkpoint:* | cut -d: -f3 | sort -u
```

### View Specific Session

```bash
# Get latest state for a session
GET langgraph:checkpoint:cli_20251108_145739:latest

# Check TTL (time to live)
TTL langgraph:checkpoint:cli_20251108_145739:latest

# See all keys for a session
KEYS langgraph:checkpoint:cli_20251108_145739:*
```

### Inspect Session Data

The data is stored as pickled Python objects, so it won't be human-readable in redis-cli. To inspect it properly:

```python
import redis
import pickle

# Connect
r = redis.Redis(
    host='redis-17887.c57.us-east-1-4.ec2.redns.redis-cloud.com',
    port=17887,
    password='mjZCoOjapBWnTnjBlHDneS6WTVNLF53J',
    decode_responses=False  # Important for pickle
)

# Get session
session_id = "cli_20251108_145739"
key = f"langgraph:checkpoint:{session_id}:latest"
data = r.get(key)

if data:
    state = pickle.loads(data)
    print(f"Turn count: {state['checkpoint']['turn_count']}")
    print(f"Messages: {len(state['checkpoint']['messages'])}")
    print(f"Complete: {state['checkpoint']['is_complete']}")
else:
    print("Session not found or expired")
```

## Python Script to View Sessions

Create `view_redis_sessions.py`:

```python
#!/usr/bin/env python3
"""View all WREN sessions in Redis."""

import redis
import pickle
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to Redis
r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD'),
    decode_responses=False
)

print("=== WREN Sessions in Redis ===\n")

# Get all checkpoint keys
keys = r.keys("langgraph:checkpoint:*:latest")
print(f"Found {len(keys)} sessions:\n")

for key in keys:
    key_str = key.decode('utf-8')
    session_id = key_str.split(':')[2]
    
    # Get TTL
    ttl = r.ttl(key)
    hours_left = ttl / 3600 if ttl > 0 else 0
    
    # Get data
    try:
        data = r.get(key)
        state = pickle.loads(data)
        checkpoint = state.get('checkpoint', {})
        
        print(f"Session: {session_id}")
        print(f"  Turn count: {checkpoint.get('turn_count', 0)}")
        print(f"  Messages: {len(checkpoint.get('messages', []))}")
        print(f"  Complete: {checkpoint.get('is_complete', False)}")
        print(f"  TTL: {hours_left:.1f} hours remaining")
        print()
        
    except Exception as e:
        print(f"Session: {session_id}")
        print(f"  Error reading: {e}")
        print()

print(f"\nTotal active sessions: {len(keys)}")
```

Run it:
```bash
python view_redis_sessions.py
```

## Session Lifecycle

### Creation
- Created when `agent.start_interview(thread_id)` is called
- Initial state: empty messages, turn_count=0

### Updates
- Updated after each `agent.send_message()`
- Stores full conversation history
- Includes analysis data

### Expiration
- TTL: 24 hours (86400 seconds)
- Automatically deleted after expiration
- Can be manually deleted

### Manual Deletion

```bash
# Delete specific session
redis-cli -u redis://default:PASSWORD@HOST:PORT DEL langgraph:checkpoint:SESSION_ID:latest

# Delete all WREN sessions (be careful!)
redis-cli -u redis://default:PASSWORD@HOST:PORT --scan --pattern "langgraph:checkpoint:*" | xargs redis-cli -u redis://default:PASSWORD@HOST:PORT DEL
```

## Debugging Session Issues

### Session Not Found

```python
from src.agents import InterviewAgent

agent = InterviewAgent(use_redis=True)
session_id = "cli_20251108_145739"

# Try to get profile
result = agent.get_profile(thread_id=session_id)

if not result.get('profile_data'):
    print("Session expired or not found")
    print("Check if key exists in Redis:")
    # Use redis-cli or Python script above
```

### Session Won't Save

Check connection:
```python
import redis
import os
from dotenv import load_dotenv

load_dotenv()

try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        password=os.getenv('REDIS_PASSWORD')
    )
    r.ping()
    print("✓ Redis connected")
except redis.exceptions.ConnectionError as e:
    print(f"✗ Redis connection failed: {e}")
```

### View Raw Session Data

```bash
# In redis-cli
redis-cli -u redis://default:PASSWORD@HOST:PORT

# Get key info
TYPE langgraph:checkpoint:cli_20251108_145739:latest
OBJECT ENCODING langgraph:checkpoint:cli_20251108_145739:latest
MEMORY USAGE langgraph:checkpoint:cli_20251108_145739:latest
```

## Best Practices

### Session Management

1. **Use meaningful session IDs**: `cli_YYYYMMDD_HHMMSS` format
2. **Monitor TTL**: Sessions expire after 24h
3. **Backup important sessions**: Save to `user_profiles/` before expiration
4. **Clean up**: Old sessions auto-delete

### Security

1. **Never commit `.env`**: Redis credentials in `.env` (gitignored)
2. **Rotate passwords**: Change Redis password periodically
3. **Use read-only for debugging**: Create read-only Redis user for inspection

### Performance

1. **Key naming**: Consistent prefix (`langgraph:checkpoint:`)
2. **TTL management**: 24h default, adjust if needed
3. **Connection pooling**: Redis client handles this automatically

## Monitoring

### Check Redis Health

```bash
# Connection test
redis-cli -u redis://default:PASSWORD@HOST:PORT PING

# Memory usage
redis-cli -u redis://default:PASSWORD@HOST:PORT INFO memory

# Number of keys
redis-cli -u redis://default:PASSWORD@HOST:PORT DBSIZE

# Key distribution
redis-cli -u redis://default:PASSWORD@HOST:PORT --scan --pattern "langgraph:*" | wc -l
```

### Session Statistics

```python
import redis
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    password=os.getenv('REDIS_PASSWORD')
)

keys = r.keys("langgraph:checkpoint:*:latest")
print(f"Active sessions: {len(keys)}")

# Average TTL
ttls = [r.ttl(key) for key in keys]
avg_ttl = sum(ttls) / len(ttls) if ttls else 0
print(f"Average TTL: {avg_ttl/3600:.1f} hours")
```

## Troubleshooting

### "Redis connection failed"
- Check `.env` file has correct credentials
- Verify Redis Cloud database is active
- Test connection with redis-cli

### "Session expired"
- Sessions expire after 24 hours
- Use `user_profiles/` logs to recover conversation
- Re-run profile generation with logs

### "Can't pickle object"
- This is handled by our custom `RedisCheckpointSaver`
- Uses `pickle.dumps()` instead of JSON
- If you see this error, check if custom types are in state

## Redis Cloud Dashboard Features

In the Redis Cloud web interface you can:
- **View keys**: Browse all session keys
- **Monitor metrics**: Memory usage, operations/sec
- **Set alerts**: Get notified of issues
- **Backup**: Create backups of your data
- **Scale**: Increase memory/connections if needed

## Alternative: View Without Redis Dashboard

If you don't have web access, use the Python script or redis-cli exclusively. All session inspection can be done programmatically.

---

**Summary**: Yes, we use Redis Cloud for session persistence. View sessions via web dashboard, redis-cli, or Python scripts. Sessions expire after 24h. All conversation state is backed up to `user_profiles/` directory.

