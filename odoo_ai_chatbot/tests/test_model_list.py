from datetime import datetime

from odoo.tests import TransactionCase

# A slice of OpenAI's real catalogue (October 2026).
CATALOGUE = [
    ('babbage-002', datetime(2023, 8, 21)),
    ('gpt-3.5-turbo', datetime(2023, 2, 28)),
    ('gpt-3.5-turbo-0125', datetime(2024, 1, 23)),
    ('gpt-5.5', datetime(2026, 4, 22)),
    ('gpt-5.5-2026-04-23', datetime(2026, 4, 22)),
    ('gpt-5.5-pro', datetime(2026, 4, 22)),
    ('gpt-6-luna', datetime(2026, 9, 14)),
    ('gpt-6.1-sol', datetime(2026, 9, 27)),
    ('gpt-image-2.5-flare', datetime(2026, 9, 4)),
    ('gpt-live-1', datetime(2026, 9, 8)),
    ('chat-latest', datetime(2026, 5, 2)),
    ('text-embedding-3-large', datetime(2024, 1, 25)),
    ('my-finetune', None),
]


class TestModelList(TransactionCase):

    def test_newest_usable_models_come_first(self):
        ranked = self.env['res.config.settings']._rank_models('openai', CATALOGUE)
        self.assertEqual([name for name, _released in ranked],
                         ['gpt-6.1-sol', 'gpt-6-luna', 'gpt-5.5', 'gpt-3.5-turbo', 'my-finetune'])

    def test_picker_lists_newest_first_with_month(self):
        Settings = self.env['res.config.settings']
        Settings._sync_model_options('openai', Settings._rank_models('openai', CATALOGUE))
        options = self.env['ai.model.option'].search([('provider', '=', 'openai')])
        self.assertEqual(options[:2].mapped('name'), ['gpt-6.1-sol', 'gpt-6-luna'])
        self.assertEqual(options[0].display_name, 'gpt-6.1-sol (Sep 2026)')
