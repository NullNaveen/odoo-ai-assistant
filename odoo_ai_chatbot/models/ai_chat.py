import re

from odoo import models, fields, api

TITLE_MAX = 48
LEGACY_NAME_RE = re.compile(r"^Chat Session - ")


class AIChatSession(models.Model):
    _name = 'ai.chat.session'
    _description = 'AI Chat Session'
    _order = 'create_date desc'

    name = fields.Char(string="Session Name")
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.uid)
    message_ids = fields.One2many('ai.chat.message', 'session_id', string="Messages")
    summary = fields.Text(string="Conversation Summary", default="")

    # ------------------------------------------------------------------
    # Titles
    # ------------------------------------------------------------------
    @api.model
    def _title_from_text(self, text):
        """First user message -> list title: tags stripped, whitespace collapsed, truncated."""
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return False
        return text[:TITLE_MAX] + ("…" if len(text) > TITLE_MAX else "")

    def _display_title(self):
        """Stored name unless it's empty or a legacy auto-name; then derive from the first
        user message so pre-existing sessions get readable titles without a migration."""
        self.ensure_one()
        if self.name and not LEGACY_NAME_RE.match(self.name):
            return self.name
        first = self.message_ids.filtered(lambda m: m.role == 'user')[:1]
        return self._title_from_text(first.content) or "New conversation"

    def _maybe_autotitle(self, user_text):
        """Set the title from the first user message. Called by the agent on each turn;
        only fills in when no real title exists yet, so a manual rename always sticks."""
        for session in self:
            if not session.name or LEGACY_NAME_RE.match(session.name):
                title = self._title_from_text(user_text)
                if title:
                    session.name = title

    # ------------------------------------------------------------------
    # Frontend API (record rules scope everything to the calling user)
    # ------------------------------------------------------------------
    @api.model
    def get_current_session(self):
        session = self.search([('user_id', '=', self.env.uid)], limit=1, order='create_date desc')
        if session:
            return {'session_id': session.id, 'messages': session._message_payload()}
        return {'session_id': False, 'messages': []}

    def _message_payload(self):
        self.ensure_one()
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in self.message_ids.sorted('create_date')
        ]

    @api.model
    def get_sessions(self, limit=100):
        """The user's conversations, newest activity first, for the history panel."""
        sessions = self.search([('user_id', '=', self.env.uid)], limit=limit)
        # last activity = newest message per session, fetched in one grouped query
        last_by_session = {
            s.id: agg
            for s, agg in self.env['ai.chat.message']._read_group(
                [('session_id', 'in', sessions.ids)],
                groupby=['session_id'], aggregates=['create_date:max'],
            )
        }
        counts = {
            s.id: n
            for s, n in self.env['ai.chat.message']._read_group(
                [('session_id', 'in', sessions.ids)],
                groupby=['session_id'], aggregates=['__count'],
            )
        }
        rows = []
        for s in sessions:
            last = last_by_session.get(s.id) or s.create_date
            rows.append({
                'id': s.id,
                'title': s._display_title(),
                'last_activity': fields.Datetime.to_string(last),
                'message_count': counts.get(s.id, 0),
            })
        rows.sort(key=lambda r: r['last_activity'], reverse=True)
        return rows

    @api.model
    def get_session_messages(self, session_id):
        session = self.browse(session_id).exists()
        if not session or session.user_id.id != self.env.uid:
            return {'session_id': False, 'messages': []}
        return {'session_id': session.id, 'messages': session._message_payload()}

    @api.model
    def rename_session(self, session_id, name):
        session = self.browse(session_id).exists()
        if not session or session.user_id.id != self.env.uid:
            return False
        name = (name or '').strip()[:TITLE_MAX * 2]
        if name:
            session.name = name
        return True

    @api.model
    def delete_session(self, session_id):
        session = self.browse(session_id).exists()
        if not session or session.user_id.id != self.env.uid:
            return False
        session.unlink()        # messages + pending actions cascade
        return True


class AIChatMessage(models.Model):
    _name = 'ai.chat.message'
    _description = 'AI Chat Message'
    _order = 'create_date asc'

    session_id = fields.Many2one('ai.chat.session', string="Session", required=True, ondelete='cascade')
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System')
    ], string="Role", required=True)
    content = fields.Html(string="Content", required=True)
    is_summarized = fields.Boolean(string="Is Summarized", default=False)
