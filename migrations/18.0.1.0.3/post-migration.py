# -*- coding: utf-8 -*-
"""Set open_action_xmlid on quick search targets."""

from odoo import SUPERUSER_ID, api

_TARGET_ACTIONS = {
    "ghori_quick_search.ghori_quick_search_target_users": "base.action_res_users",
    "ghori_quick_search.ghori_quick_search_target_partners": "contacts.action_contacts",
    "ghori_quick_search.ghori_quick_search_target_products": "product.product_normal_action_sell",
    "ghori_quick_search.ghori_quick_search_target_product_templates": "product.product_template_action",
    "ghori_quick_search.ghori_quick_search_target_employees": "hr.open_view_employee_list",
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, action_xmlid in _TARGET_ACTIONS.items():
        target = env.ref(xmlid, raise_if_not_found=False)
        if target and not target.open_action_xmlid:
            target.write({"open_action_xmlid": action_xmlid})
