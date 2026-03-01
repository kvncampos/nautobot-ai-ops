# Generated manually on 2026-03-01
# Data migration to create all default scheduled jobs:
#   - MCP Server Health Check      (*/5 * * * *)
#   - Hourly Checkpoint Cleanup    (0 * * * *)
#   - Chat Session Cleanup         (*/5 * * * *)
#
# Using migrations instead of nautobot_database_ready signals means each schedule
# is created exactly once on first install.  Users can freely delete or modify the
# scheduled jobs afterwards without them being re-created or reverted on the next
# `nautobot-server migrate`.

from django.db import migrations
from django.utils import timezone

DEFAULT_CELERY_KWARGS = {
    "nautobot_job_ignore_singleton_lock": False,
    "nautobot_job_profile": False,
    "queue": "default",
}


def _get_shared_resources(apps):
    """Return (Job, ScheduledJob, job_user, default_queue) or None if prerequisites missing."""
    JobQueue = apps.get_model("extras", "JobQueue")
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    Job = apps.get_model("extras", "Job")
    User = apps.get_model("users", "User")  # Nautobot swaps auth.User for users.User

    default_queue = JobQueue.objects.filter(name="default", queue_type="celery").first()
    if not default_queue:
        return None

    job_user, _ = User.objects.get_or_create(username="JobRunner")
    return Job, ScheduledJob, job_user, default_queue


def _create_schedule(ScheduledJob, job, job_user, default_queue, name, crontab, description):
    """Create a scheduled job entry only if one with ``name`` does not already exist."""
    if ScheduledJob.objects.filter(name=name).exists():
        return
    ScheduledJob.objects.create(
        name=name,
        task=f"{job.module_name}.{job.job_class_name}",
        job_model=job,
        user=job_user,
        job_queue=default_queue,
        interval="custom",
        crontab=crontab,
        start_time=timezone.now(),
        enabled=True,
        description=description,
        celery_kwargs=DEFAULT_CELERY_KWARGS,
    )


def create_scheduled_jobs(apps, schema_editor):
    """Create all default scheduled jobs if they do not yet exist."""
    result = _get_shared_resources(apps)
    if result is None:
        return
    Job, ScheduledJob, job_user, default_queue = result

    schedule_configs = [
        {
            "module_name": "ai_ops.jobs.mcp_health_check",
            "job_class_name": "MCPServerHealthCheckJob",
            "schedule_name": "MCP Server Health Check",
            "crontab": "*/5 * * * *",
            "description": (
                "Automatically perform health checks on HTTP MCP servers "
                "with retry logic and cache invalidation"
            ),
        },
        {
            "module_name": "ai_ops.jobs.checkpoint_cleanup",
            "job_class_name": "CleanupCheckpointsJob",
            "schedule_name": "Hourly Checkpoint Cleanup",
            "crontab": "0 * * * *",
            "description": "Automatically clean up old LangGraph conversation checkpoints from Redis",
        },
        {
            "module_name": "ai_ops.jobs.chat_session_cleanup",
            "job_class_name": "CleanupExpiredChatsJob",
            "schedule_name": "Chat Session Cleanup",
            "crontab": "*/5 * * * *",
            "description": (
                "Automatically clean up expired chat sessions based on configured TTL "
                "(chat_session_ttl_minutes)"
            ),
        },
    ]

    for config in schedule_configs:
        job = Job.objects.filter(
            module_name=config["module_name"],
            job_class_name=config["job_class_name"],
        ).first()
        if not job:
            continue
        if not job.enabled:
            job.enabled = True
            job.save()
        _create_schedule(
            ScheduledJob,
            job,
            job_user,
            default_queue,
            name=config["schedule_name"],
            crontab=config["crontab"],
            description=config["description"],
        )


def remove_scheduled_jobs(apps, schema_editor):
    """Remove all default scheduled jobs (reverse migration / uninstall)."""
    ScheduledJob = apps.get_model("extras", "ScheduledJob")
    ScheduledJob.objects.filter(
        name__in=[
            "MCP Server Health Check",
            "Hourly Checkpoint Cleanup",
            "Chat Session Cleanup",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai_ops", "0007_remove_llmmodel_documentation_url"),
        ("extras", "0125_jobresult_date_started"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(
            code=create_scheduled_jobs,
            reverse_code=remove_scheduled_jobs,
        ),
    ]
