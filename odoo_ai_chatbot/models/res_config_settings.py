from odoo import models, fields

SYSTEM_PROMPT_PARAM = 'odoo_ai_chatbot.ai_system_prompt'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('ollama', 'Ollama (local)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic (Claude)'),
        ('bedrock', 'Amazon Bedrock'),
        ('openai_compatible', 'OpenAI-compatible endpoint'),
    ], string="AI Provider", default='ollama', config_parameter='odoo_ai_chatbot.ai_provider')

    # Unified settings — one API key, one model, one optional base URL, used by every provider.
    ai_api_key = fields.Char(
        "API Key", password=True, config_parameter='odoo_ai_chatbot.ai_api_key',
        help="Your provider API key. Optional for a local Ollama server; not used by Bedrock.")
    ai_model = fields.Char(
        "Model", config_parameter='odoo_ai_chatbot.ai_model',
        help="e.g. gpt-4o-mini (OpenAI), claude-3-5-sonnet-latest (Anthropic), "
             "or an Ollama model such as qwen3:latest. A tool-calling capable model is required.")
    ai_base_url = fields.Char(
        "Base URL", config_parameter='odoo_ai_chatbot.ai_base_url',
        help="Ollama server URL (e.g. http://localhost:11434), or the endpoint for an "
             "OpenAI-compatible provider (Groq, OpenRouter, Together, vLLM, LM Studio, …). "
             "Leave blank to use OpenAI/Anthropic defaults.")

    # Amazon Bedrock uses AWS credentials instead of an API key.
    bedrock_aws_access_key = fields.Char("AWS Access Key", password=True, config_parameter='odoo_ai_chatbot.bedrock_aws_access_key')
    bedrock_aws_secret_key = fields.Char("AWS Secret Key", password=True, config_parameter='odoo_ai_chatbot.bedrock_aws_secret_key')
    bedrock_region = fields.Char("AWS Region", default="us-east-1", config_parameter='odoo_ai_chatbot.bedrock_region')

    ai_system_prompt = fields.Text(
        "System Prompt (optional)",
        help="Advanced: override the assistant's built-in instructions. Leave blank to use the default.")

    # res.config.settings only accepts boolean/integer/float/char/selection/many2one/datetime for
    # `config_parameter`, so this multi-line Text is read and written by hand. With config_parameter
    # Odoo 19 raises "Field res.config.settings.ai_system_prompt must have type ..." in
    # _get_classified_fields and the whole Settings page fails to open (seen on 19.0+e, 2026-09-22).
    def get_values(self):
        res = super().get_values()
        res['ai_system_prompt'] = self.env['ir.config_parameter'].sudo().get_param(SYSTEM_PROMPT_PARAM, '')
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(SYSTEM_PROMPT_PARAM, self.ai_system_prompt or '')
