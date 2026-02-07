# Langfuse & Semantic Cache Setup Instructions

## Issues Fixed

### 1. **Langfuse Authentication Errors** ✅
**Problem**: Invalid credentials errors in Langfuse logs
```
langfuse-web-1 | Error: Invalid credentials
langfuse-web-1 | No key found for public key
langfuse-web-1 | storing api-key-non-existent in redis
```

**Root Cause**: Placeholder API keys in `development.env` were not actual Langfuse keys.

**Solution**: Updated configuration to support proper API key generation workflow.

### 2. **Semantic Cache Ollama Connection** ✅
**Problem**: Semantic cache failing to connect to Ollama
```
[SEMANTIC_CACHE] ⚠ Initialization failed: Failed to connect to Ollama
```

**Root Cause**: No Ollama service defined in docker-compose setup.

**Solution**: Added Ollama service to `docker-compose.langfuse.yml`.

### 3. **Missing S3 Bucket Configurations** ✅
**Problem**: Langfuse v3 requires multiple S3 buckets but only events bucket was configured.

**Root Cause**: Incomplete S3/MinIO configuration per [Langfuse documentation](https://langfuse.com/self-hosting/configuration).

**Solution**: Added configurations for:
- `LANGFUSE_S3_MEDIA_UPLOAD_*` (required)
- `LANGFUSE_S3_BATCH_EXPORT_*` (optional)
- Updated MinIO to create all buckets on startup

---

## Changes Made

### 1. `development/development.env`
- ✅ Updated Langfuse API key configuration with instructions
- ✅ Added missing S3 access key credentials
- ✅ Added all required S3 bucket configurations
- ✅ Updated Ollama endpoint configuration

### 2. `development/docker-compose.langfuse.yml`
- ✅ Added **Ollama service** for embeddings and semantic cache
- ✅ Updated MinIO to create 3 buckets: `langfuse-events`, `langfuse-media`, `langfuse-batch`
- ✅ Added `ollama_data` volume

### 3. `development/creds.example.env`
- ✅ Added detailed Langfuse API key setup instructions
- ✅ Added support for headless initialization (optional)

### 4. `network-agent/docker-compose.yml` (bonus fix)
- ✅ Added missing media and batch export S3 configurations
- ✅ Updated MinIO bucket creation

---

## Next Steps

### Option A: Manual Setup (Recommended for Development)

1. **Copy the example creds file** (if you haven't already):
   ```bash
   cd /Users/kvncampos/CodeProjects/AI_PROJECTS/nautobot-ai-ops/development
   cp creds.example.env creds.env
   ```

2. **Leave Langfuse keys empty initially** in `creds.env`:
   ```env
   LANGFUSE_PUBLIC_KEY=""
   LANGFUSE_SECRET_KEY=""
   ```

3. **Start the services**:
   ```bash
   cd /Users/kvncampos/CodeProjects/AI_PROJECTS/nautobot-ai-ops
   invoke debug
   ```

4. **Pull Ollama embedding model** (after services are up):
   ```bash
   docker exec -it <ollama-container-name> ollama pull mxbai-embed-large
   ```
   
   To find the Ollama container name:
   ```bash
   docker ps | grep ollama
   ```

5. **Generate Langfuse API Keys**:
   - Access Langfuse UI: http://localhost:8000
   - Create an account or login
   - Go to: **Settings → API Keys**
   - Click **"Create new key"**
   - Copy the keys

6. **Update `creds.env`** with the generated keys:
   ```env
   LANGFUSE_PUBLIC_KEY="pk-lf-xxxxxxxxxxxxxxxx"
   LANGFUSE_SECRET_KEY="sk-lf-xxxxxxxxxxxxxxxx"
   ```

7. **Restart Nautobot** to apply the keys:
   ```bash
   docker-compose restart nautobot worker beat
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
Look for this log in Nautobot:
```
[deep_agent] ✓ Langfuse observability enabled
```

Instead of:
```
[deep_agent] ⚠ Failed to initialize Langfuse: <error>
```

### 2. Check Semantic Cache
Look for this log:
```
[deep_agent] Semantic caching enabled (ttl=3600s, threshold=0.05)
```

Instead of:
```
[SEMANTIC_CACHE] ⚠ Initialization failed: Failed to connect to Ollama
```

### 3. Check MinIO Buckets
Access MinIO console: http://localhost:9003
- Username: `minio`
- Password: `miniosecret`

Verify 3 buckets exist:
- `langfuse-events`
- `langfuse-media`
- `langfuse-batch`

---

## Troubleshooting

### Issue: Langfuse still shows "Invalid credentials"
**Solution**: 
1. Make sure you've generated keys from the UI (Step 5 above)
2. Verify keys are set in `creds.env`
3. Restart the services that use Langfuse

### Issue: Semantic cache still failing
**Solutions**:
1. Check Ollama is running:
   ```bash
   docker ps | grep ollama
   curl http://localhost:11434/api/tags
   ```

2. Pull the embedding model:
   ```bash
   docker exec -it <ollama-container> ollama pull mxbai-embed-large
   ```

3. Check Redis is accessible:
   ```bash
   docker exec -it redis redis-cli ping
   # Should return: PONG
   ```

### Issue: MinIO buckets not created
**Solution**:
```bash
# Recreate MinIO service
docker-compose down minio
docker volume rm <project>_minio_data
docker-compose up -d minio

# Verify buckets
docker exec -it minio-<container> ls -la /data/
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
│  │ - Semantic   │     └──────────┬───────────────┘     │
│  │   Cache      │                │                      │
│  └───────┬──────┘                │                      │
│          │                       │                      │
│          ▼                       ▼                      │
│  ┌──────────────┐     ┌────────────────────┐           │
│  │   Ollama     │     │    MinIO (S3)      │           │
│  │ Port: 11434  │     │    Port: 9002/9003 │           │
│  │              │     │                    │           │
│  │ - Embeddings │     │ - langfuse-events  │           │
│  │ - mxbai-     │     │ - langfuse-media   │           │
│  │   embed-     │     │ - langfuse-batch   │           │
│  │   large      │     └────────────────────┘           │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐     ┌────────────────────┐           │
│  │   Redis      │────▶│   PostgreSQL       │           │
│  │ Port: 6379   │     │   Port: 5432       │           │
│  │              │     │                    │           │
│  │ - Cache      │     │ - Nautobot DB      │           │
│  │ - Semantic   │     │ - Langfuse DB      │           │
│  │   Cache      │     └────────────────────┘           │
│  └──────────────┘                                       │
│                       ┌────────────────────┐           │
│                       │   ClickHouse       │           │
│                       │   Port: 8123/9000  │           │
│                       │                    │           │
│                       │ - Analytics DB     │           │
│                       │ - Traces storage   │           │
│                       └────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## References

- [Langfuse Self-Hosting Configuration](https://langfuse.com/self-hosting/configuration)
- [Langfuse ClickHouse Setup](https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse)
- [Langfuse Headless Initialization](https://langfuse.com/self-hosting/administration/headless-initialization)
- [Ollama Documentation](https://ollama.com/library/mxbai-embed-large)

---

## Summary

All configuration issues have been resolved:
- ✅ Langfuse authentication properly configured
- ✅ Ollama service added for semantic cache
- ✅ All required S3/MinIO buckets configured
- ✅ Missing access keys added
- ✅ Documentation updated

**Next**: Follow Option A or B above to complete the setup!
