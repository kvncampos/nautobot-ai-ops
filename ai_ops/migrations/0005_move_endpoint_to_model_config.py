# Generated manually on 2026-02-08
# Migration to move endpoint and api_version fields to model_config JSONField

from django.db import migrations, models


def migrate_endpoint_to_model_config(apps, schema_editor):
    """Migrate existing endpoint and api_version values to model_config."""
    LLMModel = apps.get_model('ai_ops', 'LLMModel')

    for model in LLMModel.objects.all():
        config_updates = {}

        # Migrate endpoint to model_config
        if model.endpoint:
            # Use 'azure_endpoint' for Azure, 'base_url' for others
            # Note: We can't easily determine provider here, so we'll use both keys
            config_updates['endpoint'] = model.endpoint
            config_updates['azure_endpoint'] = model.endpoint  # Azure uses azure_endpoint
            config_updates['base_url'] = model.endpoint  # OpenAI/Ollama use base_url

        # Migrate api_version to model_config (Azure-specific)
        if model.api_version:
            config_updates['api_version'] = model.api_version

        # Only update if there are changes
        if config_updates:
            # Merge with existing model_config
            current_config = model.model_config or {}
            # Only add if not already set (don't override existing values)
            for key, value in config_updates.items():
                if key not in current_config:
                    current_config[key] = value

            model.model_config = current_config
            model.save(update_fields=['model_config'])


def reverse_migrate(apps, schema_editor):
    """Reverse migration - copy model_config values back to endpoint/api_version."""
    LLMModel = apps.get_model('ai_ops', 'LLMModel')

    for model in LLMModel.objects.all():
        if model.model_config:
            # Try to restore endpoint from various keys
            endpoint = (
                model.model_config.get('endpoint')
                or model.model_config.get('azure_endpoint')
                or model.model_config.get('base_url')
            )
            if endpoint:
                model.endpoint = endpoint

            # Restore api_version
            api_version = model.model_config.get('api_version')
            if api_version:
                model.api_version = api_version

            model.save(update_fields=['endpoint', 'api_version'])


class Migration(migrations.Migration):

    dependencies = [
        ('ai_ops', '0004_llmmodel_model_config'),
    ]

    operations = [
        # Step 1: Add documentation_url field
        migrations.AddField(
            model_name='llmmodel',
            name='documentation_url',
            field=models.URLField(
                blank=True,
                help_text=(
                    "Link to LangChain documentation for this model's provider "
                    "(e.g., https://python.langchain.com/docs/integrations/chat/openai). "
                    "Helps users understand available model_config parameters."
                ),
                max_length=500,
            ),
        ),

        # Step 2: Migrate data from endpoint/api_version to model_config
        migrations.RunPython(migrate_endpoint_to_model_config, reverse_migrate),

        # Step 3: Remove old fields
        migrations.RemoveField(
            model_name='llmmodel',
            name='endpoint',
        ),
        migrations.RemoveField(
            model_name='llmmodel',
            name='api_version',
        ),
    ]
