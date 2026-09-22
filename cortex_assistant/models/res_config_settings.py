import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

from .ai_model_option import PROVIDERS

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PARAM = 'cortex_assistant.ai_system_prompt'

# Offered before "Refresh models" has ever run, so the picker is never empty.
FALLBACK_MODELS = {
    'openai': ['gpt-5.6-terra', 'gpt-5.6-luna', 'gpt-5.6-sol', 'gpt-6-astra'],
    'anthropic': ['claude-sonnet-5', 'claude-opus-5'],
    'ollama': ['qwen3:latest'],
    'openai_compatible': [],
    'bedrock': [],
}

# Substrings marking a model that cannot do tool calling. This assistant is an
# agent — without function calling it can only hallucinate, so hide them.
_NON_CHAT_HINTS = (
    'embed', 'whisper', 'tts', 'audio', 'transcribe', 'realtime', 'moderation',
    'image', 'dall-e', 'rerank', 'guard', 'similarity',
)

DEFAULT_OPENAI_BASE = 'https://api.openai.com/v1'
DEFAULT_ANTHROPIC_BASE = 'https://api.anthropic.com/v1'
DEFAULT_OLLAMA_BASE = 'http://localhost:11434'
FETCH_TIMEOUT = 20


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection(
        PROVIDERS, string="AI Provider", default='ollama',
        config_parameter='cortex_assistant.ai_provider')

    # Unified settings — one API key, one model, one optional base URL, used by every provider.
    ai_api_key = fields.Char(
        "API Key", password=True, config_parameter='cortex_assistant.ai_api_key',
        help="Your provider API key. Optional for a local Ollama server; not used by Bedrock.")
    # Deliberately a Char, not a Selection: an id the provider does not list (a
    # fine-tune, a brand-new release) must still be typeable, and a Selection
    # blanks — then silently wipes on Save — any value missing from its options.
    ai_model = fields.Char(
        "Model", config_parameter='cortex_assistant.ai_model',
        help="The model id sent to the provider. Pick one from the list, or type any id. "
             "A tool-calling capable model is required.")
    # The picker. A Many2one domain is evaluated client-side against the field
    # values currently on screen, so switching the Provider radio re-filters this
    # list immediately — which a Selection cannot do (its options are computed
    # server-side from the *saved* provider).
    ai_model_id = fields.Many2one(
        'ai.model.option', string="Model",
        domain="[('provider', '=', ai_provider)]",
        help="Choose one of your provider's models, or type any id and pick "
             "Create to use it. 'Refresh models' pulls the current list.")
    ai_base_url = fields.Char(
        "Base URL", config_parameter='cortex_assistant.ai_base_url',
        help="Ollama server URL (e.g. http://localhost:11434), or the endpoint for an "
             "OpenAI-compatible provider (Groq, OpenRouter, Together, vLLM, LM Studio, …). "
             "Leave blank to use OpenAI/Anthropic defaults.")

    # Amazon Bedrock uses AWS credentials instead of an API key.
    bedrock_aws_access_key = fields.Char("AWS Access Key", password=True, config_parameter='cortex_assistant.bedrock_aws_access_key')
    bedrock_aws_secret_key = fields.Char("AWS Secret Key", password=True, config_parameter='cortex_assistant.bedrock_aws_secret_key')
    bedrock_region = fields.Char("AWS Region", default="us-east-1", config_parameter='cortex_assistant.bedrock_region')

    ai_system_prompt = fields.Text(
        "System Prompt (optional)",
        help="Advanced: override the assistant's built-in instructions. Leave blank to use the default.")

    # ------------------------------------------------------------------
    # Values
    # ------------------------------------------------------------------
    def get_values(self):
        """Read the two settings Odoo cannot store through `config_parameter`.

        ai_system_prompt: res.config.settings only accepts boolean/integer/float/
        char/selection/many2one/datetime there, so this multi-line Text is read
        and written by hand — otherwise Odoo 19 raises "Field
        res.config.settings.ai_system_prompt must have type ..." and the whole
        Settings page fails to open.

        ai_model_id: the picker mirrors ai_model (the Char that ai_agent.py
        actually reads), so a value typed by hand — or one the provider has
        since delisted — still appears selected instead of an empty box.
        """
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res['ai_system_prompt'] = icp.get_param(SYSTEM_PROMPT_PARAM, '')
        name = (icp.get_param('cortex_assistant.ai_model') or '').strip()
        provider = icp.get_param('cortex_assistant.ai_provider') or 'ollama'
        option = False
        if name:
            Option = self.env['ai.model.option'].sudo()
            option = Option.search([('provider', '=', provider), ('name', '=', name)], limit=1)
            if not option:
                # Configured by hand or delisted upstream — list it so the
                # picker reflects what is actually in use.
                option = Option.create({'name': name, 'provider': provider})
        res['ai_model_id'] = option.id if option else False
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            SYSTEM_PROMPT_PARAM, self.ai_system_prompt or '')

    # ------------------------------------------------------------------
    # Model picker
    # ------------------------------------------------------------------
    @api.onchange('ai_model_id')
    def _onchange_ai_model_id(self):
        """Picking from the list fills the Model field that actually gets saved."""
        for rec in self:
            if rec.ai_model_id:
                rec.ai_model = rec.ai_model_id.name

    @api.onchange('ai_provider')
    def _onchange_ai_provider(self):
        """Clear a picker entry belonging to the previous provider."""
        for rec in self:
            if rec.ai_model_id and rec.ai_model_id.provider != rec.ai_provider:
                rec.ai_model_id = False

    def _fetch_provider_models(self, provider, api_key, base_url):
        """Return the model ids the provider currently offers.

        Each provider publishes its own catalogue, so a newly released model
        shows up here with no code change.
        """
        if provider == 'ollama':
            root = (base_url or DEFAULT_OLLAMA_BASE).rstrip('/')
            resp = requests.get(f'{root}/api/tags', timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            return [m['name'] for m in resp.json().get('models', []) if m.get('name')]

        if provider == 'anthropic':
            root = (base_url or DEFAULT_ANTHROPIC_BASE).rstrip('/')
            resp = requests.get(
                f'{root}/models',
                headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
                timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            return [m['id'] for m in resp.json().get('data', []) if m.get('id')]

        if provider in ('openai', 'openai_compatible'):
            root = (base_url or DEFAULT_OPENAI_BASE).rstrip('/')
            # An OpenAI-compatible base URL may or may not already carry /v1.
            if provider == 'openai_compatible' and not root.endswith('/v1'):
                root = f'{root}/v1'
            resp = requests.get(
                f'{root}/models',
                headers={'Authorization': f'Bearer {api_key or "not-needed"}'},
                timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            return [m['id'] for m in resp.json().get('data', []) if m.get('id')]

        raise UserError(
            "Amazon Bedrock does not publish a model list over this API. "
            "Type the model id from the AWS console into the Model field instead.")

    def action_refresh_ai_models(self):
        """Pull the live model list from the selected provider into ai.model.option."""
        self.ensure_one()
        # Persist first: the fetch needs the provider/key/base URL just typed.
        self.execute()

        icp = self.env['ir.config_parameter'].sudo()
        provider = icp.get_param('cortex_assistant.ai_provider') or 'ollama'
        api_key = icp.get_param('cortex_assistant.ai_api_key') or ''
        base_url = icp.get_param('cortex_assistant.ai_base_url') or ''

        try:
            ids = self._fetch_provider_models(provider, api_key, base_url)
        except UserError:
            raise
        except Exception as exc:
            _logger.exception("Could not fetch models for provider %s", provider)
            # Surface the real cause: a rejected key and an unreachable endpoint
            # need different fixes, and "try again" tells the user neither.
            raise UserError(
                f"Could not fetch the model list from '{provider}'.\n\n"
                f"{type(exc).__name__}: {exc}"
            ) from exc

        chat_ids = sorted({
            m for m in ids
            if not any(hint in m.lower() for hint in _NON_CHAT_HINTS)
        })
        if not chat_ids:
            raise UserError(
                f"'{provider}' returned {len(ids)} models, but none look like chat models.")

        added = self._sync_model_options(provider, chat_ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Model list updated",
                'message': f"{len(chat_ids)} models available from '{provider}' ({added} new).",
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    @api.model
    def _sync_model_options(self, provider, model_ids):
        """Make ai.model.option match model_ids for this provider. Returns new count."""
        Option = self.env['ai.model.option'].sudo()
        existing = Option.search([('provider', '=', provider)])
        by_name = {o.name: o for o in existing}

        wanted = set(model_ids)
        to_create = [{'name': m, 'provider': provider} for m in model_ids if m not in by_name]
        if to_create:
            Option.create(to_create)

        # Drop ids the provider no longer offers, so the list cannot go stale.
        # Keep whatever is currently configured, even if delisted, so the saved
        # setting stays visible in the picker.
        current = self.env['ir.config_parameter'].sudo().get_param('cortex_assistant.ai_model')
        stale = existing.filtered(lambda o: o.name not in wanted and o.name != current)
        if stale:
            stale.unlink()
        return len(to_create)

    @api.model
    def _seed_fallback_options(self):
        """Give every provider a starting list so the picker is never empty.

        Called from the post-init hook; safe to re-run (create is skipped for
        ids that already exist).
        """
        for provider, models_ in FALLBACK_MODELS.items():
            if not models_:
                continue
            Option = self.env['ai.model.option'].sudo()
            have = set(Option.search([('provider', '=', provider)]).mapped('name'))
            missing = [{'name': m, 'provider': provider} for m in models_ if m not in have]
            if missing:
                Option.create(missing)
