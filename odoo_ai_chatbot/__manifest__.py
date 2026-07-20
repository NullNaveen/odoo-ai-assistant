{
    'name': 'AI Assistant',
    'version': '2.6.0',
    'category': 'Productivity',
    'summary': 'In-app AI assistant that reads, totals and edits your Odoo data on your own LLM.',
    'description': """
AI Assistant for Odoo
=====================

An agentic assistant docked in the Odoo backend. It answers questions from your live
database and can act on it through a set of guarded tools — read, count, aggregate
(SUM/AVG/…), create, update, translate and delete — always as the logged-in user and
always within Odoo's access rights. Destructive changes are proposed first and only run
after the user confirms.

Runs on your own models via Ollama (local, private) or Amazon Bedrock.

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
            'odoo_ai_chatbot/static/src/components/chatbot/*.js',
            'odoo_ai_chatbot/static/src/components/chatbot/*.xml',
            'odoo_ai_chatbot/static/src/components/chatbot/*.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
