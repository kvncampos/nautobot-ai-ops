# Middleware Configuration Guide

This guide provides comprehensive examples for configuring middleware with LLM models in the AI Ops App. Middleware allows you to enhance, modify, or monitor interactions with LLM models through a flexible priority-based execution system.

## Overview

Middleware executes in a chain pattern with configurable priority:

```
Request → [Priority 10: Logging] → [Priority 20: Cache] → [Priority 30: Retry] → LLM → Response
```

Each middleware can process requests before they reach the LLM and/or process responses before they're returned to the user.

## Middleware Execution Order

Middleware priority determines execution order:

- **Lower numbers execute first** (1-100)
- **Ties broken alphabetically** by middleware name
- **Pre-processing**: Priority 1 → 100 → LLM
- **Post-processing**: LLM → Priority 100 → 1

### Recommended Priority Ranges

| Priority Range | Purpose | Examples |
|----------------|---------|----------|
| 1-20 | Request validation, logging | ValidationMiddleware, LoggingMiddleware |
| 21-40 | Caching, PII redaction | CacheMiddleware, PIIMiddleware |
| 41-60 | Rate limiting, circuit breakers | RateLimitMiddleware |
| 61-80 | Retry logic, fallbacks | RetryMiddleware |
| 81-100 | Response processing, metrics | MetricsMiddleware |

## Middleware Types

### Built-in Middleware

Available through LangChain:

- **CacheMiddleware** - Response caching to reduce API calls
- **RetryMiddleware** - Automatic retry with exponential backoff
- **RateLimitMiddleware** - Request rate limiting
- **LoggingMiddleware** - Request/response logging
- **ValidationMiddleware** - Input/output validation

### Custom Middleware

Implement custom middleware for:

- PII detection and redaction
- Custom authentication/authorization
- Domain-specific transformations
- Security scanning
- Cost tracking
- Custom metrics

## Configuration Steps

### Step 1: Create Middleware Type

Navigate to **AI Platform > Configuration > Middleware Types**

Click **+ Add** to create a new middleware type.

**Screenshot Placeholder:**
> _[Screenshot: Middleware Types List View]_

### Step 2: Configure Middleware Instance

Navigate to **AI Platform > Configuration > LLM Middleware**

Click **+ Add** to apply middleware to a model.

**Screenshot Placeholder:**
> _[Screenshot: LLM Middleware Configuration Form]_

### Step 3: Test Configuration

Use the AI Chat Assistant to verify middleware is functioning.

## Common Middleware Configurations

### Cache Middleware

Reduces API costs by caching responses for identical requests.

#### Configuration

```json
{
  "cache_backend": "redis",
  "max_entries": 10000,
  "ttl_seconds": 3600,
  "key_prefix": "llm_cache:",
  "cache_responses_only": true,
  "exclude_patterns": ["random", "uuid", "current_time"]
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: CacheMiddleware
Is Custom: ☐ (Built-in LangChain)
Description: Caches LLM responses to reduce API calls and costs
Default Config:
{
  "cache_backend": "redis",
  "max_entries": 10000,
  "ttl_seconds": 3600
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: CacheMiddleware
Config:
{
  "cache_backend": "redis",
  "max_entries": 10000,
  "ttl_seconds": 3600,
  "key_prefix": "prod_gpt4o_cache:"
}
Config Version: 1.1.0
Is Active: ✓
Is Critical: ☐
Priority: 20
```

**Screenshot Placeholder:**
> _[Screenshot: Cache Middleware Configuration]_

#### Benefits

- ✓ Reduces API costs for repeated queries
- ✓ Improves response time for cached requests
- ✓ Decreases load on LLM provider
- ✓ Configurable TTL per use case

#### Best Practices

- Set TTL based on data freshness requirements
- Use cache for deterministic queries (temperature = 0)
- Higher cache TTL for stable content
- Lower cache TTL for dynamic content
- Monitor cache hit rate
- Clear cache when models are updated

---

### Retry Middleware

Handles transient failures with exponential backoff.

#### Configuration

```json
{
  "max_retries": 3,
  "initial_delay": 1.0,
  "max_delay": 60.0,
  "exponential_base": 2,
  "retry_on": [
    "rate_limit_error",
    "timeout_error",
    "connection_error",
    "server_error"
  ],
  "do_not_retry_on": [
    "authentication_error",
    "invalid_request_error"
  ]
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: RetryMiddleware
Is Custom: ☐ (Built-in LangChain)
Description: Automatic retry with exponential backoff for transient failures
Default Config:
{
  "max_retries": 3,
  "initial_delay": 1.0,
  "max_delay": 60.0,
  "exponential_base": 2
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: RetryMiddleware
Config:
{
  "max_retries": 3,
  "initial_delay": 1.0,
  "max_delay": 60.0,
  "exponential_base": 2,
  "retry_on": ["rate_limit_error", "timeout_error", "connection_error"]
}
Config Version: 1.1.0
Is Active: ✓
Is Critical: ✓ (Production environments)
Priority: 30
```

**Screenshot Placeholder:**
> _[Screenshot: Retry Middleware Configuration]_

#### Retry Logic

```
Attempt 1: Wait 0s → Fail
Attempt 2: Wait 1s (1.0 * 2^0) → Fail
Attempt 3: Wait 2s (1.0 * 2^1) → Fail
Attempt 4: Wait 4s (1.0 * 2^2) → Success
```

#### Benefits

- ✓ Handles rate limiting automatically
- ✓ Recovers from transient network issues
- ✓ Prevents cascading failures
- ✓ Configurable retry strategy

#### Best Practices

- Mark as critical for production models
- Configure max_retries based on SLA requirements
- Set appropriate max_delay to avoid long waits
- Don't retry on authentication errors
- Monitor retry rates to identify issues

---

### Logging Middleware

Logs requests and responses for debugging and monitoring.

#### Configuration

```json
{
  "log_level": "INFO",
  "log_requests": true,
  "log_responses": true,
  "include_tokens": true,
  "include_latency": true,
  "include_model_info": true,
  "log_to_file": true,
  "file_path": "/var/log/ai_ops/llm_requests.log",
  "max_log_length": 1000,
  "mask_sensitive_data": true
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: LoggingMiddleware
Is Custom: ☐ (Built-in LangChain)
Description: Logs LLM requests and responses for debugging and monitoring
Default Config:
{
  "log_level": "INFO",
  "log_requests": true,
  "log_responses": true,
  "include_tokens": true
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: LoggingMiddleware
Config:
{
  "log_level": "INFO",
  "log_requests": true,
  "log_responses": true,
  "include_tokens": true,
  "include_latency": true,
  "include_model_info": true,
  "log_to_file": true,
  "file_path": "/var/log/ai_ops/prod_llm.log",
  "max_log_length": 1000
}
Config Version: 1.1.0
Is Active: ✓
Is Critical: ☐
Priority: 10
```

**Screenshot Placeholder:**
> _[Screenshot: Logging Middleware Configuration]_

#### Log Format

```
[2024-01-09 12:34:56] INFO - Model: gpt-4o
Request: "What is the status of device SW-CORE-01?"
Response: "Device SW-CORE-01 is online and operational..."
Tokens: 125 (prompt) + 87 (completion) = 212 total
Latency: 1.23s
```

#### Benefits

- ✓ Debugging failed requests
- ✓ Performance monitoring
- ✓ Usage analytics
- ✓ Compliance and auditing
- ✓ Cost tracking

#### Best Practices

- Always enable for production environments
- Use INFO level for normal operations
- Use DEBUG level for troubleshooting
- Mask sensitive data in logs
- Rotate log files regularly
- Monitor log file sizes

---

### Rate Limit Middleware

Controls request rate to prevent quota exhaustion.

#### Configuration

```json
{
  "requests_per_minute": 60,
  "requests_per_hour": 1000,
  "requests_per_day": 10000,
  "burst_size": 10,
  "strategy": "sliding_window",
  "queue_requests": true,
  "max_queue_size": 100
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: RateLimitMiddleware
Is Custom: ☐ (Built-in LangChain)
Description: Controls request rate to prevent quota exhaustion
Default Config:
{
  "requests_per_minute": 60,
  "burst_size": 10
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: RateLimitMiddleware
Config:
{
  "requests_per_minute": 60,
  "requests_per_hour": 1000,
  "burst_size": 10,
  "strategy": "sliding_window",
  "queue_requests": true,
  "max_queue_size": 100
}
Config Version: 1.1.0
Is Active: ✓
Is Critical: ☐
Priority: 50
```

**Screenshot Placeholder:**
> _[Screenshot: Rate Limit Middleware Configuration]_

#### Benefits

- ✓ Prevents quota exhaustion
- ✓ Controls costs
- ✓ Ensures fair resource allocation
- ✓ Prevents API provider throttling

#### Best Practices

- Set limits based on API tier/quota
- Leave headroom for bursts
- Monitor queue sizes
- Adjust limits based on usage patterns

---

### Validation Middleware

Validates inputs and outputs for security and correctness.

#### Configuration

```json
{
  "validate_input": true,
  "validate_output": true,
  "max_input_length": 10000,
  "max_output_length": 20000,
  "allowed_input_patterns": ["^[a-zA-Z0-9\\s\\.,!?-]+$"],
  "blocked_output_patterns": ["<script>", "DROP TABLE", "rm -rf"],
  "sanitize_html": true,
  "reject_on_validation_failure": true
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: ValidationMiddleware
Is Custom: ☐ (Built-in LangChain)
Description: Validates input and output for security and correctness
Default Config:
{
  "validate_input": true,
  "validate_output": true,
  "max_input_length": 10000
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: ValidationMiddleware
Config:
{
  "validate_input": true,
  "validate_output": true,
  "max_input_length": 10000,
  "max_output_length": 20000,
  "sanitize_html": true,
  "reject_on_validation_failure": true
}
Config Version: 1.1.0
Is Active: ✓
Is Critical: ✓ (Security critical)
Priority: 15
```

**Screenshot Placeholder:**
> _[Screenshot: Validation Middleware Configuration]_

#### Benefits

- ✓ Prevents injection attacks
- ✓ Ensures data quality
- ✓ Protects against malicious inputs
- ✓ Validates response format

#### Best Practices

- Enable for all production models
- Mark as critical for security
- Customize patterns for your domain
- Log validation failures
- Review blocked patterns regularly

---

## Custom Middleware Examples

### PII Redaction Middleware

Detects and redacts personally identifiable information.

#### Configuration

```json
{
  "pii_entities": [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "SSN",
    "CREDIT_CARD",
    "IP_ADDRESS"
  ],
  "redaction_strategy": "replace",
  "replacement_text": "[REDACTED]",
  "log_detections": true,
  "confidence_threshold": 0.85
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: PIIRedactionMiddleware
Is Custom: ✓
Description: Detects and redacts PII from requests and responses
Default Config:
{
  "pii_entities": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
  "redaction_strategy": "replace",
  "replacement_text": "[REDACTED]"
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: PIIRedactionMiddleware
Config:
{
  "pii_entities": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "SSN"],
  "redaction_strategy": "replace",
  "replacement_text": "[REDACTED]",
  "log_detections": true,
  "confidence_threshold": 0.85
}
Config Version: 1.0.0
Is Active: ✓
Is Critical: ✓
Priority: 25
```

**Screenshot Placeholder:**
> _[Screenshot: PII Redaction Middleware Configuration]_

#### Implementation

```python
# ai_ops/middleware/pii_redaction.py
from ai_ops.middleware.base import BaseMiddleware

class PIIRedactionMiddleware(BaseMiddleware):
    """Redacts PII from requests and responses."""
    
    def process_request(self, request):
        # Detect and redact PII from request
        pass
    
    def process_response(self, response):
        # Detect and redact PII from response
        pass
```

---

### Cost Tracking Middleware

Tracks token usage and estimated costs.

#### Configuration

```json
{
  "track_tokens": true,
  "track_costs": true,
  "cost_per_1k_input_tokens": 0.03,
  "cost_per_1k_output_tokens": 0.06,
  "log_to_database": true,
  "alert_threshold": 100.0,
  "alert_email": "admin@example.com"
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: CostTrackingMiddleware
Is Custom: ✓
Description: Tracks token usage and estimated costs per request
Default Config:
{
  "track_tokens": true,
  "track_costs": true
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: CostTrackingMiddleware
Config:
{
  "track_tokens": true,
  "track_costs": true,
  "cost_per_1k_input_tokens": 0.03,
  "cost_per_1k_output_tokens": 0.06,
  "log_to_database": true,
  "alert_threshold": 100.0,
  "alert_email": "ops@example.com"
}
Config Version: 1.0.0
Is Active: ✓
Is Critical: ☐
Priority: 85
```

**Screenshot Placeholder:**
> _[Screenshot: Cost Tracking Middleware Configuration]_

---

### Circuit Breaker Middleware

Prevents cascading failures by stopping requests when error rate is high.

#### Configuration

```json
{
  "failure_threshold": 5,
  "success_threshold": 2,
  "timeout": 60,
  "half_open_max_requests": 3,
  "failure_rate_threshold": 0.5,
  "window_size": 10
}
```

#### Setup in Nautobot

**Create Middleware Type:**
```
Name: CircuitBreakerMiddleware
Is Custom: ✓
Description: Circuit breaker pattern to prevent cascading failures
Default Config:
{
  "failure_threshold": 5,
  "timeout": 60
}
```

**Apply to Model:**
```
LLM Model: gpt-4o
Middleware: CircuitBreakerMiddleware
Config:
{
  "failure_threshold": 5,
  "success_threshold": 2,
  "timeout": 60,
  "half_open_max_requests": 3
}
Config Version: 1.0.0
Is Active: ✓
Is Critical: ☐
Priority: 55
```

**Screenshot Placeholder:**
> _[Screenshot: Circuit Breaker Middleware Configuration]_

---

## Complete Middleware Stack Examples

### Production Model (gpt-4o)

Comprehensive middleware stack for production workloads:

```
Priority 10: LoggingMiddleware - Request/response logging
Priority 15: ValidationMiddleware - Security validation
Priority 20: CacheMiddleware - Response caching (1 hour TTL)
Priority 25: PIIRedactionMiddleware - PII detection and redaction
Priority 30: RetryMiddleware - Exponential backoff retry
Priority 50: RateLimitMiddleware - Rate limiting
Priority 85: CostTrackingMiddleware - Cost monitoring
```

**Screenshot Placeholder:**
> _[Screenshot: Production Middleware Stack]_

### Development Model (ollama:llama2)

Minimal middleware for local development:

```
Priority 10: LoggingMiddleware - Verbose debugging
Priority 15: ValidationMiddleware - Input validation only
```

**Screenshot Placeholder:**
> _[Screenshot: Development Middleware Stack]_

### Non-Production Model (gpt-3.5-turbo)

Balanced middleware for testing:

```
Priority 10: LoggingMiddleware - Standard logging
Priority 20: CacheMiddleware - Extended caching (4 hour TTL)
Priority 30: RetryMiddleware - Basic retry logic
Priority 50: RateLimitMiddleware - Relaxed limits
```

**Screenshot Placeholder:**
> _[Screenshot: Non-Production Middleware Stack]_

## Middleware Management

### Enable/Disable Middleware

Navigate to **AI Platform > Configuration > LLM Middleware**

- Toggle **Is Active** to enable/disable without deletion
- Disabled middleware remains configured for future use

**Screenshot Placeholder:**
> _[Screenshot: Middleware Enable/Disable Toggle]_

### Update Middleware Priority

1. Click middleware instance to edit
2. Update **Priority** field (1-100)
3. Save changes
4. Restart affected services

**Screenshot Placeholder:**
> _[Screenshot: Priority Update Form]_

### Critical vs Non-Critical

- **Critical Middleware**: Agent fails to start if middleware cannot load
- **Non-Critical Middleware**: Errors logged, agent continues

Use critical flag for security-related middleware (validation, PII redaction).

## Monitoring Middleware

### Performance Impact

Monitor middleware overhead:

```python
# Check middleware execution time
from ai_ops.helpers.middleware import get_middleware_metrics

metrics = get_middleware_metrics(model_name="gpt-4o")
# {
#   "LoggingMiddleware": {"avg_time": 0.002, "calls": 1234},
#   "CacheMiddleware": {"avg_time": 0.015, "calls": 1234, "hit_rate": 0.45},
#   "RetryMiddleware": {"avg_time": 0.001, "calls": 1234, "retry_rate": 0.03}
# }
```

### Cache Hit Rates

Track cache effectiveness:

```bash
# Redis CLI
redis-cli
> INFO stats
> KEYS llm_cache:*
> TTL llm_cache:some_key
```

### Error Rates

Monitor middleware errors:

```bash
# Check logs
tail -f /var/log/ai_ops/llm_requests.log | grep ERROR
```

## Best Practices Summary

### Priority Assignment

1. **10-20**: Logging, validation (foundation)
2. **21-40**: Caching, PII redaction (enhancement)
3. **41-60**: Rate limiting, circuit breaker (protection)
4. **61-80**: Retry logic (reliability)
5. **81-100**: Metrics, cost tracking (monitoring)

### Configuration Management

- ✓ Version control middleware configurations
- ✓ Test middleware in non-production first
- ✓ Document custom middleware thoroughly
- ✓ Monitor middleware performance impact
- ✓ Review and update configurations quarterly

### Security Considerations

- ✓ Always enable validation middleware
- ✓ Mark security middleware as critical
- ✓ Enable PII redaction for sensitive data
- ✓ Mask sensitive data in logs
- ✓ Audit middleware access regularly

### Performance Optimization

- ✓ Minimize middleware count per model
- ✓ Use caching to reduce API calls
- ✓ Monitor middleware execution time
- ✓ Disable unused middleware
- ✓ Profile middleware chains regularly

## Troubleshooting

### Middleware Not Executing

**Check:**
- Is middleware marked as Active?
- Is the model using the correct middleware?
- Are there any configuration errors in logs?
- Is the middleware type properly registered?

### High Latency

**Check:**
- Number of active middleware
- Middleware priority order
- Cache hit rates
- Retry rates
- Network latency

### Configuration Errors

**Common Issues:**
- Invalid JSON in config field
- Missing required parameters
- Incompatible config_version
- Middleware dependencies not met

## Next Steps

After configuring middleware:

1. [Set up MCP Servers](mcp_server_configuration.md) - Extend capabilities
2. [Monitor Performance](../admin/health_checks.md) - Track middleware metrics
3. [Review Logs](../dev/architecture.md) - Analyze middleware execution
4. [Optimize Configuration](app_use_cases.md) - Fine-tune settings

## Related Documentation

- [Models Reference](../dev/code_reference/models.md) - Middleware model details
- [Provider Configuration](provider_configuration.md) - LLM provider setup
- [Architecture Overview](../dev/architecture.md) - Middleware architecture
- [API Documentation](../dev/code_reference/api.md) - Middleware API endpoints
