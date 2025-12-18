# Background Jobs

This page documents the background jobs provided by the AI Ops App.

## Overview

The AI Ops App includes Nautobot Jobs for automated maintenance tasks. Jobs can be run manually or scheduled for automatic execution.

## Cleanup Checkpoints Job

::: ai_ops.jobs.checkpoint_cleanup.CleanupCheckpointsJob
    options:
        show_root_heading: true
        show_source: false

The Cleanup Checkpoints Job removes old conversation history from Redis to prevent unbounded growth.

### Purpose

Conversation checkpoints are stored in Redis for maintaining chat history. Over time, these checkpoints accumulate and consume Redis memory. This job periodically cleans up old checkpoints based on a retention policy.

### Job Details

- **Name**: Cleanup Old Checkpoints
- **Group**: AI Agents
- **Description**: Clean up old LangGraph conversation checkpoints from Redis based on retention policy
- **Scheduling**: Can be scheduled for automatic execution
- **Sensitive Variables**: None

### How It Works

```python
class CleanupCheckpointsJob(Job):
    """Job to clean up old conversation checkpoints from Redis."""
    
    def run(self):
        """Entry point for the job."""
        # Execute cleanup task
        result = cleanup_old_checkpoints()
        
        if result.get("success"):
            self.logger.info(
                f"✅ Checkpoint cleanup completed: "
                f"processed {result['processed_count']} keys "
                f"(retention: {result['retention_days']} days)"
            )
        else:
            self.logger.error(f"❌ Checkpoint cleanup failed: {result.get('error')}")
            raise Exception(f"Cleanup failed: {result.get('error')}")
        
        return result
```

### Cleanup Task

The underlying cleanup task is defined in `ai_ops/celery_tasks.py`:

```python
def cleanup_old_checkpoints(retention_days: int = 30) -> dict:
    """Clean up old LangGraph checkpoints from Redis.
    
    Args:
        retention_days: Number of days to retain checkpoints
        
    Returns:
        Dictionary with cleanup results:
        {
            "success": bool,
            "processed_count": int,
            "deleted_count": int,
            "retention_days": int,
            "error": str (if failed)
        }
    """
```

### Retention Policy

**Default Retention**: 30 days

Checkpoints older than the retention period are removed. The retention period is calculated from the checkpoint's timestamp.

**Configurable**: The retention period can be adjusted by modifying the `cleanup_old_checkpoints()` function call.

### Running the Job

#### Manual Execution

1. Navigate to **Jobs > Jobs** in Nautobot
2. Find **AI Agents > Cleanup Old Checkpoints**
3. Click **Run Job Now**
4. Review the job log for results

#### Scheduled Execution

1. Navigate to **Jobs > Jobs**
2. Find **AI Agents > Cleanup Old Checkpoints**
3. Click **Schedule Job**
4. Configure schedule:
   - **Name**: Descriptive name for the schedule
   - **Interval**: How often to run (e.g., daily, weekly)
   - **Start Time**: When to start running
   - **Enabled**: Check to activate the schedule

**Recommended Schedule**: Daily or weekly, depending on usage volume.

### Job Output

The job returns a dictionary with cleanup statistics:

```python
{
    "success": True,
    "processed_count": 150,  # Total keys scanned
    "deleted_count": 45,     # Keys deleted
    "retention_days": 30,    # Retention period used
    "error": None            # Error message if failed
}
```

### Example Job Log

```
2024-12-05 10:30:00 INFO Starting checkpoint cleanup task...
2024-12-05 10:30:05 INFO ✅ Checkpoint cleanup completed: processed 150 keys (retention: 30 days)
2024-12-05 10:30:05 INFO Deleted 45 old checkpoint keys
2024-12-05 10:30:05 SUCCESS Job completed successfully
```

## Checkpoint Storage

### Redis Key Structure

Checkpoints are stored in Redis with a specific key pattern:

```
checkpoint:{thread_id}:{checkpoint_id}
```

Example keys:
```
checkpoint:user-session-abc123:2024-12-05T10:30:00
checkpoint:user-session-def456:2024-12-05T11:45:00
```

### Checkpoint Content

Each checkpoint stores:
- **Messages**: Conversation history
- **Metadata**: Timestamp, user info, etc.
- **Agent State**: Current state of the agent

### Redis Database

Checkpoints use a separate Redis database:
- **Default Database**: DB 2
- **Configurable via**: `LANGGRAPH_REDIS_DB` environment variable
- **Isolation**: Separate from cache (DB 0) and Celery (DB 1)

## Cleanup Process

### Step-by-Step Process

1. **Connect to Redis**
   ```python
   redis_client = get_redis_connection()
   ```

2. **Scan for Checkpoint Keys**
   ```python
   for key in redis_client.scan_iter(match="checkpoint:*"):
       process_key(key)
   ```

3. **Check Timestamp**
   ```python
   checkpoint_data = redis_client.get(key)
   timestamp = extract_timestamp(checkpoint_data)
   age = now - timestamp
   ```

4. **Delete Old Checkpoints**
   ```python
   if age > retention_period:
       redis_client.delete(key)
       deleted_count += 1
   ```

5. **Return Results**
   ```python
   return {
       "success": True,
       "processed_count": total_keys,
       "deleted_count": deleted_keys,
       "retention_days": retention_days
   }
   ```

### Performance Considerations

- **Scan vs Keys**: Uses `SCAN` to avoid blocking Redis
- **Batch Processing**: Processes keys in batches
- **Memory Efficient**: Doesn't load all keys into memory
- **Non-Blocking**: Allows Redis to serve other requests

## Monitoring

### Job Execution Status

Monitor job execution through Nautobot:

1. Navigate to **Jobs > Job Results**
2. Filter by job name: "Cleanup Old Checkpoints"
3. Review execution history:
   - Success/failure status
   - Execution duration
   - Number of keys processed
   - Error messages if any

### Redis Monitoring

Monitor Redis usage:

```bash
# Connect to Redis
redis-cli -h localhost -p 6379 -n 2

# Count checkpoint keys
SCAN 0 MATCH checkpoint:* COUNT 1000

# Check memory usage
INFO memory

# Get database statistics
INFO keyspace
```

### Metrics to Track

- **Checkpoint Count**: Total number of checkpoints
- **Redis Memory**: Memory used by checkpoint database
- **Cleanup Frequency**: How often cleanup runs
- **Deletion Rate**: Number of checkpoints deleted per run

## Troubleshooting

### Job Fails to Execute

**Check Redis Connectivity**:
```python
from ai_ops.checkpointer import get_redis_connection

try:
    redis_client = get_redis_connection()
    redis_client.ping()
    print("Redis connection OK")
except Exception as e:
    print(f"Redis connection failed: {e}")
```

**Verify Environment Variables**:
```bash
echo $NAUTOBOT_REDIS_HOST
echo $NAUTOBOT_REDIS_PORT
echo $LANGGRAPH_REDIS_DB
```

**Check Redis Permissions**:
- Ensure Redis password is correct
- Verify network connectivity
- Check firewall rules

### No Checkpoints Deleted

**Possible Causes**:
- All checkpoints are within retention period
- Checkpoint keys have different pattern
- Wrong Redis database selected

**Verify Checkpoint Keys**:
```bash
redis-cli -h localhost -p 6379 -n 2 KEYS "checkpoint:*"
```

### Job Takes Too Long

**For Large Datasets**:
- Increase job timeout
- Run during off-peak hours
- Consider reducing retention period
- Optimize Redis performance

### Memory Not Freed

After cleanup, Redis memory may not immediately decrease:

1. **Check Deleted Keys**:
   ```bash
   INFO stats
   ```
   Look for `evicted_keys` or deleted count

2. **Redis Memory Reclaim**:
   Redis may not immediately release memory to OS
   - Memory reused for new keys
   - Run `MEMORY PURGE` (Redis 4.0+)

3. **Verify Cleanup Results**:
   Check job log for deleted count

## Best Practices

### Scheduling

1. **Regular Execution**: Schedule to run at least weekly
2. **Off-Peak Hours**: Run during low-traffic periods
3. **Monitor First Runs**: Check initial executions carefully
4. **Adjust Frequency**: Based on checkpoint creation rate

### Retention Policy

1. **Balance History vs Space**: Longer retention = more history, more space
2. **Consider Use Patterns**: How long do users need history?
3. **Compliance Requirements**: Legal/regulatory retention needs
4. **Storage Capacity**: Redis memory limitations

### Monitoring

1. **Set Up Alerts**: Alert on job failures
2. **Track Metrics**: Monitor key count and memory
3. **Regular Reviews**: Periodically review cleanup effectiveness
4. **Log Analysis**: Review logs for patterns

### Disaster Recovery

1. **Redis Backup**: Regular Redis backups include checkpoints
2. **Retention Coordination**: Align with backup schedule
3. **Test Restoration**: Verify checkpoint data in backups
4. **Document Procedure**: Clear recovery process

## Advanced Configuration

### Custom Retention Period

Modify the retention period by editing the job:

```python
# ai_ops/jobs/checkpoint_cleanup.py

def run(self):
    # Custom retention: 60 days instead of 30
    result = cleanup_old_checkpoints(retention_days=60)
    # ... rest of the code
```

### Conditional Cleanup

Implement conditional cleanup based on memory usage:

```python
def run(self):
    redis_client = get_redis_connection()
    memory_info = redis_client.info('memory')
    used_memory_mb = memory_info['used_memory'] / (1024 * 1024)
    
    if used_memory_mb > 1000:  # Over 1GB
        # Aggressive cleanup
        result = cleanup_old_checkpoints(retention_days=7)
    else:
        # Normal cleanup
        result = cleanup_old_checkpoints(retention_days=30)
    
    return result
```

### Selective Cleanup

Clean up specific thread patterns:

```python
def cleanup_user_checkpoints(user_id: str):
    """Clean up checkpoints for a specific user."""
    redis_client = get_redis_connection()
    pattern = f"checkpoint:user-{user_id}-*"
    
    deleted = 0
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
        deleted += 1
    
    return deleted
```

## Related Documentation

- Checkpointer Configuration - Redis checkpoint setup (see `ai_ops/checkpointer.py`)
- Celery Tasks - Background task definitions (see `ai_ops/celery_tasks.py`)
- [Agents](agents.md) - How agents use checkpoints
- [External Interactions](../../user/external_interactions.md) - Redis configuration
