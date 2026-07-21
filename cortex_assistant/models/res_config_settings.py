from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('ollama', 'Ollama (local)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic (Claude)'),
        ('bedrock', 'Amazon Bedrock'),
        ('openai_compatible', 'OpenAI-compatible endpoint'),
    ], string="AI Provider", default='ollama', config_parameter='cortex_assistant.ai_provider')

    # Unified settings — one API key, one model, one optional base URL, used by every provider.
    ai_api_key = fields.Char(
        "API Key", password=True, config_parameter='cortex_assistant.ai_api_key',
        help="Your provider API key. Optional for a local Ollama server; not used by Bedrock.")
    ai_model = fields.Char(
        "Model", config_parameter='cortex_assistant.ai_model',
        help="e.g. gpt-4o-mini (OpenAI), claude-3-5-sonnet-latest (Anthropic), "
             "or an Ollama model such as qwen3:latest. A tool-calling capable model is required.")
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
        "System Prompt (optional)", config_parameter='cortex_assistant.ai_system_prompt',
        help="Advanced: override the assistant's built-in instructions. Leave blank to use the default.")
