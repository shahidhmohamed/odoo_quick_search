# -*- coding: utf-8 -*-
"""Populate M2M field pickers and open_action_id from legacy char columns."""

from odoo import SUPERUSER_ID, api

_ACTION_XMLIDS = {
    "ghori_quick_search.ghori_quick_search_target_users": "base.action_res_users",
    "ghori_quick_search.ghori_quick_search_target_partners": "contacts.action_contacts",
    "ghori_quick_search.ghori_quick_search_target_products": "product.product_normal_action_sell",
    "ghori_quick_search.ghori_quick_search_target_product_templates": "product.product_template_action",
    "ghori_quick_search.ghori_quick_search_target_employees": "hr.open_view_employee_list",
}


def _fields_from_names(env, model_id, csv_names):
    if not model_id or not csv_names:
        return env["ir.model.fields"]
    names = [part.strip() for part in csv_names.split(",") if part.strip()]
    return env["ir.model.fields"].search(
        [
            ("model_id", "=", model_id),
            ("name", "in", names),
        ]
    )


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Target = env["ghori.quick.search.target"].sudo()
    for target in Target.search([]):
        vals = {}
        if not target.search_field_ids and target.search_field_names:
            fields = _fields_from_names(
                env, target.model_id.id, target.search_field_names
            )
            if fields:
                vals["search_field_ids"] = [(6, 0, fields.ids)]
        if not target.subtitle_field_ids and target.subtitle_field_names:
            fields = _fields_from_names(
                env, target.model_id.id, target.subtitle_field_names
            )
            if fields:
                vals["subtitle_field_ids"] = [(6, 0, fields.ids)]
        if not target.open_action_id and target.open_action_xmlid:
            try:
                action = env.ref(target.open_action_xmlid.strip())
                if action._name == "ir.actions.act_window":
                    vals["open_action_id"] = action.id
            except ValueError:
                pass
        if vals:
            target.write(vals)

    for xmlid, action_xmlid in _ACTION_XMLIDS.items():
        target = env.ref(xmlid, raise_if_not_found=False)
        if not target or target.open_action_id:
            continue
        try:
            action = env.ref(action_xmlid)
            if action._name == "ir.actions.act_window":
                target.open_action_id = action.id
        except ValueError:
            pass
