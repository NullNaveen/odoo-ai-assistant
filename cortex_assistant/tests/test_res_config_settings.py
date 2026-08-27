from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):
    def test_system_prompt_config_parameter(self):
        field = self.env['res.config.settings']._fields['ai_system_prompt']
        self.assertEqual(field.type, 'char')

        prompt = "First line\nSecond line"
        self.env['ir.config_parameter'].sudo().set_param(
            'cortex_assistant.ai_system_prompt', prompt,
        )
        values = self.env['res.config.settings'].default_get(['ai_system_prompt'])
        self.assertEqual(values['ai_system_prompt'], prompt)
