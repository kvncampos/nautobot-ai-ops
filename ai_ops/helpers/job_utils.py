"""Utility functions for Nautobot job scheduling and management."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from nautobot.extras.models import Job, ScheduledJob

from ai_ops.helpers.get_info import get_default_job_queue

User = get_user_model()

logger = logging.getLogger(__name__)

# Constants for Nautobot job scheduling and management
DEFAULT_JOB_RUNNER_USER = "JobRunner"


def enable_job_and_get_details(module_name, job_class_name):
    """Enable a Nautobot job if disabled and return job details.

    Args:
        module_name: The module name of the job (e.g., "ai_ops.jobs.checkpoint_cleanup")
        job_class_name: The job class name (e.g., "CleanupCheckpointsJob")

    Returns:
        tuple: (job, job_user, default_queue, task_class_path) or (None, None, None, None) if prerequisites fail
    """
    # Get the job
    job = Job.objects.filter(module_name=module_name, job_class_name=job_class_name).first()

    if not job:
        logger.warning(f"{job_class_name} not found. Job may not be registered yet.")
        return None, None, None, None

    # Enable the job if not already enabled
    if not job.enabled:
        job.enabled = True
        job.save()
        logger.info(f"Enabled {job_class_name}")

    # Get the existing JobRunner user
    try:
        job_user, created = User.objects.get_or_create(username=DEFAULT_JOB_RUNNER_USER)
        if created:
            logger.info(f"Created user '{DEFAULT_JOB_RUNNER_USER}' for job scheduling")
    except User.DoesNotExist:
        logger.error(f"User '{DEFAULT_JOB_RUNNER_USER}' does not exist. Cannot schedule job.")
        return None, None, None, None

    # Get the default job queue
    logger.debug(f"Getting default job queue for {job_class_name}...")
    default_queue = get_default_job_queue()
    logger.info(f"Using job queue: {default_queue.name} (pk={default_queue.pk}, type={default_queue.queue_type})")

    # Build the task class path for the job
    task_class_path = f"{job.module_name}.{job.job_class_name}"

    return job, job_user, default_queue, task_class_path


def create_or_update_scheduled_job(
    schedule_name,
    job,
    job_user,
    default_queue,
    task_class_path,
    crontab,
    description,
    celery_kwargs=None,
):
    """Create or update a scheduled job with the given parameters.

    Args:
        schedule_name: Name of the scheduled job
        job: Job model instance
        job_user: User instance who owns the scheduled job
        default_queue: JobQueue instance
        task_class_path: Full path to the task class (e.g., "ai_ops.jobs.checkpoint_cleanup.CleanupCheckpointsJob")
        crontab: Crontab schedule string (e.g., "0 * * * *")
        description: Description of what the scheduled job does
        celery_kwargs: Optional dict of Celery kwargs. Defaults to standard kwargs if not provided.

    Returns:
        ScheduledJob: The created or updated scheduled job instance
    """
    if celery_kwargs is None:
        celery_kwargs = {
            "nautobot_job_ignore_singleton_lock": False,
            "nautobot_job_profile": False,
            "queue": "default",
        }

    # Check if schedule already exists
    existing_schedule = ScheduledJob.objects.filter(name=schedule_name).first()

    if existing_schedule:
        logger.info(f"Scheduled job '{schedule_name}' already exists")
        # Update if needed - ensure user is set and schedule is correct
        needs_update = False
        if not existing_schedule.user:
            existing_schedule.user = job_user
            needs_update = True
        if not existing_schedule.task or existing_schedule.task != task_class_path:
            existing_schedule.task = task_class_path
            needs_update = True
        if existing_schedule.crontab != crontab:
            existing_schedule.crontab = crontab
            needs_update = True
        if not existing_schedule.enabled:
            existing_schedule.enabled = True
            needs_update = True
        if existing_schedule.job_queue != default_queue:
            existing_schedule.job_queue = default_queue
            needs_update = True
        if existing_schedule.celery_kwargs != celery_kwargs:
            existing_schedule.celery_kwargs = celery_kwargs
            needs_update = True

        if needs_update:
            existing_schedule.save()
            logger.info(f"Updated scheduled job: {schedule_name}")

        return existing_schedule
    else:
        # Create new scheduled job
        with transaction.atomic():
            scheduled_job = ScheduledJob.objects.create(
                name=schedule_name,
                task=task_class_path,
                job_model=job,
                user=job_user,
                job_queue=default_queue,
                interval="custom",
                crontab=crontab,
                start_time=timezone.now(),
                enabled=True,
                description=description,
                celery_kwargs=celery_kwargs,
            )
        logger.info(f"Created scheduled job: {scheduled_job.name} (ID: {scheduled_job.pk})")
        return scheduled_job
