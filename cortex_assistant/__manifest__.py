{
    'name': 'AI Assistant',
    'version': '19.0.2.6.0',
    'category': 'Productivity',
    'summary': 'In-app AI assistant that reads, totals and edits your Odoo data — on your own LLM, with a confirmation gate.',
    'description': """
AI Assistant for Odoo
=====================

An agentic assistant docked in the Odoo backend. It answers questions from your live
database in plain language and can act on it through a set of guarded tools — read, count,
aggregate (SUM/AVG/…), look up records, read chatter, check stock, render PDFs, export CSV,
schedule activities, create, update, translate, delete and run workflow buttons (confirm /
post / validate / cancel).

Safe by design
--------------
Every create, update, delete and workflow action is PROPOSED first and only runs after the
user explicitly confirms — the gate is enforced in code, not just the prompt. The assistant
always acts as the logged-in user, so Odoo's own access rights and record rules apply on top:
it can never do anything the user could not do by hand.

Your choice of AI, including fully local
----------------------------------------
Works with OpenAI, Anthropic (Claude), Google Gemini, any OpenAI-compatible endpoint,
Amazon Bedrock, or a fully local / self-hosted server (Ollama, LM Studio, MLX) — so your
data can stay on your own infrastructure.

Runs on Odoo 17, 18 and 19 — Community or Enterprise.

Based on the original "AI Chatbot" by Tarang Kushwaha (LGPL-3).
    """,
    'author': 'NullNaveen',
    'website': 'https://github.com/NullNaveen/odoo-ai-assistant',
    'external_dependencies': {
        'python': ['langchain', 'langchain-community', 'langchain-ollama', 'langgraph', 'bleach', 'markdown'],
    },
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/res_config_settings_views.xml',
        'views/ai_chat_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cortex_assistant/static/src/components/chatbot/*.js',
            'cortex_assistant/static/src/components/chatbot/*.xml',
            'cortex_assistant/static/src/components/chatbot/*.scss',
        ],
    },
    'images': [
        'static/description/hero_screenshot.png',
        'static/description/totals.png',
        'static/description/settings.png',
        'static/description/dark.png',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
