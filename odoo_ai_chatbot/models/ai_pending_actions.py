from odoo import models, fields, api

PENDING_ACTION_TTL_MINUTES = 10


class AIPendingAction(models.Model):
    _name = 'ai.pending.action'
    _description = 'AI Agent action awaiting explicit user confirmation'
    _order = 'create_date desc'

    session_id = fields.Many2one('ai.chat.session', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, index=True)

    action_type = fields.Selection([
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('translate', 'Update Translations'),
        ('method', 'Run Action / Button'),
    ], required=True)

    model_name = fields.Char(required=True)
    domain = fields.Char(required=True, help="JSON-encoded search domain")
    record_ids = fields.Char(help="JSON list of record ids snapshotted at proposal time")
    method_name = fields.Char(help="Record method / button to invoke (method action only)")
    values = fields.Char(help="JSON-encoded write values (update only)")
    field_name = fields.Char(help="Translated field name (translate only)")
    translations = fields.Char(help="JSON-encoded lang->value map (translate only)")

    record_count = fields.Integer(help="Number of matching records at proposal time")

    # Hardening:  id of the newest USER message at proposal time. A confirmation is only
    # honoured when it arrives on a LATER user message (i.e. the user really did reply "yes"
    # in their own turn). Without this the gate is prompt-only, and a model will happily call
    # delete_odoo_records -> confirm_pending_action inside a SINGLE turn, destroying records the
    # user never approved. Verified: qwen3.6:35b-mlx does exactly that. See _confirm guard.
    proposed_msg_id = fields.Integer(
        string="Proposed after message",
        help="ai.chat.message id of the latest user message when this action was proposed. "
             "Confirmation must come from a strictly newer user message.",
    )

    state = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], default='pending', required=True, index=True)

    @api.model
    def _expire_stale(self):
        """Mark pending actions older than the TTL as expired. Call this
        before creating/confirming actions, or via a cron."""
        cutoff = fields.Datetime.now() - fields.Datetime.to_timedelta(f"{PENDING_ACTION_TTL_MINUTES} minutes") \
            if hasattr(fields.Datetime, 'to_timedelta') else None
        # Simpler, dependency-free cutoff calculation:
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(minutes=PENDING_ACTION_TTL_MINUTES)
        stale = self.search([('state', '=', 'pending'), ('create_date', '<', cutoff)])
        stale.write({'state': 'expired'})
        return stale

    def is_expired(self):
        self.ensure_one()
        from datetime import timedelta
        return fields.Datetime.now() - self.create_date > timedelta(minutes=PENDING_ACTION_TTL_MINUTES)