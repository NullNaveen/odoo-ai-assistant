from . import controllers
from . import models


def post_init_seed_models(env):
    """Give the model picker a starting list so it is never empty on a fresh install.

    Odoo 17+ passes the env; older signatures pass (cr, registry).
    """
    if not hasattr(env, 'cr'):            # (cr, registry) form
        from odoo import api, SUPERUSER_ID
        env = api.Environment(env, SUPERUSER_ID, {})
    env['res.config.settings']._seed_fallback_options()
