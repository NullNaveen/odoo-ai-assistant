from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class AIChatbotController(http.Controller):
    """Legacy JSON-RPC endpoints.

    The OWL panel talks to the ORM directly (``this.orm.call``) and does not use these
    routes; they are kept for backwards compatibility with existing integrations.

    SECURITY: both routes are ``auth='user'``, which in Odoo includes PORTAL users, and
    the ACL on ``ai.chat.session`` is not group-scoped. The ``base.group_user`` record
    rules therefore do NOT constrain a portal account, so any ownership check has to be
    explicit here (and in ``ai.chatbot.agent.process_message``). Without it, a session id
    is just an integer to increment.
    """

    @staticmethod
    def _own_session(session_id):
        """Return the caller's session for ``session_id``, or raise.

        Deliberately raises the same error for "does not exist" and "belongs to someone
        else" so the endpoint cannot be used to probe which session ids are in use.
        """
        session = request.env['ai.chat.session'].browse(session_id)
        if not session.exists() or session.user_id.id != request.env.uid:
            raise AccessError("You do not have access to this conversation.")
        return session

    @http.route('/ai_chatbot/send_message', type='jsonrpc', auth='user')
    def send_message(self, session_id, message):
        """Send a message to the AI Chatbot."""
        if session_id:
            self._own_session(session_id)
        return request.env['ai.chatbot.agent'].process_message(session_id, message)

    @http.route('/ai_chatbot/get_history', type='jsonrpc', auth='user')
    def get_history(self, session_id):
        if not session_id:
            return []
        session = self._own_session(session_id)
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in session.message_ids
        ]
