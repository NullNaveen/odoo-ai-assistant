from odoo import api, fields, models

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
    # Newest first: the picker shows its first few rows, and those should be the latest models.
    _order = 'provider, released desc nulls last, name'
    _rec_name = 'name'

    name = fields.Char("Model ID", required=True, index=True)
    provider = fields.Selection(PROVIDERS, required=True, index=True)
    released = fields.Datetime(
        "Released", readonly=True,
        help="When the provider published this model, as its own catalogue reports it.")

    @api.depends('name', 'released')
    def _compute_display_name(self):
        # The month is what tells "gpt-6-sol" from "gpt-5-sol" at a glance.
        for option in self:
            option.display_name = f"{option.name} ({option.released:%b %Y})" if option.released else option.name

    # Odoo 19 dropped list-form _sql_constraints: add_to_registry() only logs
    # "no longer supported" and never builds the index, so the constraint would
    # be silently dead and the warning would fire on every registry build.
    _provider_name_uniq = models.Constraint(
        'UNIQUE(provider, name)',
        'This model is already listed for that provider.',
    )
