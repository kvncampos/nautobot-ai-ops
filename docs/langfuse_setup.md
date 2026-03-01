# Langfuse Observability Setup

## Overview

Langfuse provides full LLM observability for the Deep Agent: every LLM call, tool invocation, and subagent delegation is captured as a trace. This guide covers the complete setup for local development using the included Docker Compose stack.

## Issues Addressed in This Release

### 1. **Langfuse Authentication Errors** ✅
**Problem**: Invalid credentials errors in Langfuse logs
```
langfuse-web-1 | Error: Invalid credentials
langfuse-web-1 | No key found for public key
langfuse-web-1 | storing api-key-non-existent in redis
```

**Root Cause**: Placeholder API keys in `development.env` were not actual Langfuse keys.

**Solution**: Updated configuration to support proper API key generation workflow.

### 2. **Missing S3 Bucket Configurations** ✅
**Problem**: Langfuse v3 requires multiple S3 buckets but only the events bucket was configured.

**Root Cause**: Incomplete S3/MinIO configuration per [Langfuse documentation](https://langfuse.com/self-hosting/configuration).

**Solution**: Added configurations for all three required buckets:
- `LANGFUSE_S3_EVENT_UPLOAD_*` (required)
- `LANGFUSE_S3_MEDIA_UPLOAD_*` (required)
- `LANGFUSE_S3_BATCH_EXPORT_*` (optional)
- MinIO pre-creates all buckets on startup

---

## Changes Made

### 1. `development/development.env`
- ✅ Updated Langfuse API key configuration with setup instructions
- ✅ Added missing S3 access key credentials
- ✅ Added all required S3 bucket configurations

### 2. `development/docker-compose.langfuse.yml`
- ✅ Updated MinIO to pre-create all 3 buckets: `langfuse-events`, `langfuse-media`, `langfuse-batch`

### 3. `development/creds.example.env`
- ✅ Added detailed Langfuse API key setup instructions
- ✅ Added support for headless initialization (optional)

---

## Next Steps

### Option A: Manual Setup (Recommended for Development)

1. **Copy the example creds file** (if you haven't already):
   ```bash
   cd development
   cp creds.example.env creds.env
   ```

2. **Leave Langfuse keys empty initially** in `creds.env`:
   ```env
   LANGFUSE_PUBLIC_KEY=""
   LANGFUSE_SECRET_KEY=""
   ```

3. **Start the services**:
   ```bash
   invoke debug
   ```

4. **Generate Langfuse API Keys**:
   - Access Langfuse UI: http://localhost:8000
   - Create an account or login
   - Go to: **Settings → API Keys**
   - Click **"Create new key"**
   - Copy the keys

5. **Update `creds.env`** with the generated keys:
   ```env
   LANGFUSE_PUBLIC_KEY="pk-lf-xxxxxxxxxxxxxxxx"
   LANGFUSE_SECRET_KEY="sk-lf-xxxxxxxxxxxxxxxx"
   ```

6. **Restart Nautobot** to apply the keys:
   ```bash
   docker compose restart nautobot worker beat
   ```

### Option B: Headless Initialization (For Automation/CI)

Uncomment and configure these variables in `creds.env`:

```env
# Langfuse Headless Initialization
LANGFUSE_INIT_ORG_NAME="Nautobot AI Ops"
LANGFUSE_INIT_ORG_ID="nautobot-ai-ops"
LANGFUSE_INIT_PROJECT_NAME="Development"
LANGFUSE_INIT_PROJECT_ID="dev"
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=""  # Auto-generated
LANGFUSE_INIT_PROJECT_SECRET_KEY=""  # Auto-generated
LANGFUSE_INIT_USER_EMAIL="admin@example.com"
LANGFUSE_INIT_USER_NAME="Admin"
LANGFUSE_INIT_USER_PASSWORD="changeme123!"
```

Then copy the auto-generated keys from logs to `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.

---

## Verification

### 1. Check Langfuse Connection
Look for this log line in Nautobot after sending a message:
```
[deep_agent] Langfuse callback attached to graph
```

If Langfuse initialization fails you will see:
```
[deep_agent] Failed to initialize Langfuse: <error>
```

### 2. Check MinIO Buckets
Access MinIO console: http://localhost:9003

- Username: `minio`
- Password: `miniosecret`

Verify 3 buckets exist:
- `langfuse-events`
- `langfuse-media`
- `langfuse-batch`

### 3. View Traces in Langfuse UI
Open http://localhost:8000, go to your project, and click **Traces**. Each conversation turn appears as a top-level trace with child spans for each LLM call and tool invocation.

---

## Troubleshooting

### Issue: Langfuse still shows "Invalid credentials"
**Solution**:
1. Make sure you've generated keys from the UI (Step 4 in Option A above)
2. Verify keys are set in `creds.env`
3. Restart the services that use Langfuse:
   ```bash
   docker compose restart nautobot worker beat
   ```

### Issue: No traces appearing in Langfuse UI
**Solutions**:
1. Verify `ENABLE_LANGFUSE=true` is set in `development.env`
2. Check that `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are non-empty in `creds.env`
3. Confirm Langfuse services are healthy:
   ```bash
   docker compose ps langfuse-web langfuse-worker
   ```

### Issue: MinIO buckets not created
**Solution**:
```bash
# Recreate MinIO service to re-run bucket creation
docker compose down minio
docker volume rm <project>_minio_data
docker compose up -d minio

# Verify buckets
docker compose exec minio ls -la /data/
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Nautobot AI Ops                      │
│  ┌──────────────┐     ┌──────────────────────────┐     │
│  │ Deep Agent   │────▶│  Langfuse (Port 8000)    │     │
│  │              │     │  - Web UI & API          │     │
│  │ - LLM calls  │     │  - Trace collection      │     │
│  │ - Tool calls │     └──────────┬───────────────┘     │
│  │ - Subagents  │                │                      │
│  └───────┬──────┘                │                      │
│          │                       │                      │
│          ▼                       ▼                      │
│  ┌──────────────┐     ┌────────────────────┐           │
│  │   Redis      │     │    MinIO (S3)      │           │
│  │ Port: 6379   │     │    Port: 9002/9003 │           │
│  │              │     │                    │           │
│  │ - Checkpoint │     │ - langfuse-events  │           │
│  │ - Store      │     │ - langfuse-media   │           │
│  │ - Tool cache │     │ - langfuse-batch   │           │
│  └──────────────┘     └────────────────────┘           │
│                                                          │
│  ┌──────────────────┐  ┌────────────────────┐           │
│  │   PostgreSQL     │  │   ClickHouse       │           │
│  │   Port: 5432     │  │   Port: 8123/9000  │           │
│  │                  │  │                    │           │
│  │ - Nautobot DB    │  │ - Analytics DB     │           │
│  │ - Langfuse DB    │  │ - Traces storage   │           │
│  │ - LangGraph      │  └────────────────────┘           │
│  │   checkpoint DB  │                                    │
│  └──────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
```

---

## References

- [Langfuse Self-Hosting Configuration](https://langfuse.com/self-hosting/configuration)
- [Langfuse ClickHouse Setup](https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse)
- [Langfuse Headless Initialization](https://langfuse.com/self-hosting/administration/headless-initialization)
- [Deep Agent Architecture](DEEP_AGENT_ARCHITECTURE.md)

---

## Summary

All configuration issues have been resolved:
- ✅ Langfuse authentication properly configured
- ✅ All required S3/MinIO buckets configured
- ✅ Missing access keys added
- ✅ Documentation updated

**Next**: Follow Option A or B above to complete the setup!
