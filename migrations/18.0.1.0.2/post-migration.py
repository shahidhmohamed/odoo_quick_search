# -*- coding: utf-8 -*-
"""Fix Users quick-search fields and refresh search domains."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    target = env.ref(
        "ghori_quick_search.ghori_quick_search_target_users",
        raise_if_not_found=False,
    )
    if target:
        target.write(
            {
                "search_field_names": "name,login,email,partner_id.email",
                "subtitle_field_names": "login,email,partner_id.email",
            }
        )
