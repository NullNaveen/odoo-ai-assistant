from odoo import fields, models

PROVIDERS = [
    ('ollama', 'Ollama (local)'),
    ('openai', 'OpenAI'),
    ('anthropic', 'Anthropic (Claude)'),
    ('bedrock', 'Amazon Bedrock'),
    ('openai_compatible', 'OpenAI-compatible endpoint'),
]


class AiModelOption(models.Model):
    """One model id offered by one provider.

    Populated by "Refresh models" in Settings, which reads each provider's own
    catalogue — so a newly released model appears without a code change. A real
    model (rather than a Selection) is what lets the Settings dropdown filter on
    the provider the user has *currently* clicked, before saving: a domain is
    evaluated client-side against unsaved values, a Selection is not.
    """
    _name = 'ai.model.option'
    _description = 'AI Model Option'
    _order = 'provider, name'
    _rec_name = 'name'

    name = fields.Char("Model ID", required=True, index=True)
    provider = fields.Selection(PROVIDERS, required=True, index=True)

    # Odoo 19 dropped list-form _sql_constraints: add_to_registry() only logs
    # "no longer supported" and never builds the index, so the constraint would
    # be silently dead and the warning would fire on every registry build.
    _provider_name_uniq = models.Constraint(
        'UNIQUE(provider, name)',
        'This model is already listed for that provider.',
    )
