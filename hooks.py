# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_DEFAULT_TARGETS = (
    (
        "ghori_quick_search.ghori_quick_search_target_users",
        ("name", "login", "email"),
        ("login", "email"),
        "base.action_res_users",
    ),
    (
        "ghori_quick_search.ghori_quick_search_target_partners",
        ("name", "email", "phone", "mobile", "ref", "vat"),
        ("email", "phone", "mobile"),
        "contacts.action_contacts",
    ),
    (
        "ghori_quick_search.ghori_quick_search_target_products",
        ("name", "default_code", "barcode"),
        ("default_code", "barcode"),
        "product.product_normal_action_sell",
    ),
    (
        "ghori_quick_search.ghori_quick_search_target_product_templates",
        ("name", "default_code", "barcode"),
        ("default_code", "barcode"),
        "product.product_template_action",
    ),
    (
        "ghori_quick_search.ghori_quick_search_target_employees",
        ("name", "work_email", "work_phone", "mobile_phone"),
        ("work_email",),
        "hr.open_view_employee_list",
    ),
)

_OPTIONAL_MODULE_TARGETS = (
    (
        "purchase",
        "purchase.order",
        "Purchase Orders",
        ("name", "partner_ref", "origin"),
        "fa-shopping-cart",
        50,
        "purchase.purchase_rfq",
    ),
    (
        "sale",
        "sale.order",
        "Sales Orders",
        ("name", "client_order_ref", "origin"),
        "fa-file-text-o",
        60,
        "sale.action_orders",
    ),
    (
        "ghori_inventory",
        "ghori.grn",
        "GRNs",
        ("name",),
        "fa-truck",
        70,
        "ghori_inventory.action_ghori_grn",
    ),
    (
        "ghori_purchase",
        "employee.purchase.requisition",
        "Requisitions",
        ("name",),
        "fa-list-alt",
        45,
        "ghori_purchase.employee_purchase_requisition_action",
    ),
)


def _field_records(env, model_id, names):
    if not model_id or not names:
        return env["ir.model.fields"]
    return env["ir.model.fields"].search(
        [
            ("model_id", "=", model_id),
            ("name", "in", list(names)),
        ]
    )


def _action_id(env, xmlid):
    try:
        action = env.ref(xmlid)
    except ValueError:
        return False
    return action.id if action._name == "ir.actions.act_window" else False


def _sync_target(env, target, search_names, subtitle_names=(), action_xmlid=None):
    if not target:
        return
    vals = {}
    if search_names and not target.search_field_ids:
        fields = _field_records(env, target.model_id.id, search_names)
        if fields:
            vals["search_field_ids"] = [(6, 0, fields.ids)]
    if subtitle_names and not target.subtitle_field_ids:
        fields = _field_records(env, target.model_id.id, subtitle_names)
        if fields:
            vals["subtitle_field_ids"] = [(6, 0, fields.ids)]
    if action_xmlid and not target.open_action_id:
        action_id = _action_id(env, action_xmlid)
        if action_id:
            vals["open_action_id"] = action_id
    if vals:
        target.write(vals)


def post_init_hook(env_or_cr, registry=None):
    if registry is not None:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    Target = env["ghori.quick.search.target"].sudo()
    IrModel = env["ir.model"].sudo()

    for target_xmlid, search_names, subtitle_names, action_xmlid in _DEFAULT_TARGETS:
        target = env.ref(target_xmlid, raise_if_not_found=False)
        _sync_target(env, target, search_names, subtitle_names, action_xmlid)

    for (
        module_name,
        model_name,
        label,
        search_names,
        icon,
        seq,
        action_xmlid,
    ) in _OPTIONAL_MODULE_TARGETS:
        mod = env["ir.module.module"].search([("name", "=", module_name)], limit=1)
        if not mod or mod.state != "installed":
            continue
        model = IrModel.search([("model", "=", model_name)], limit=1)
        if not model:
            continue
        existing = Target.search([("model_id", "=", model.id)], limit=1)
        if not existing:
            existing = Target.create(
                {
                    "name": label,
                    "model_id": model.id,
                    "icon": icon,
                    "sequence": seq,
                }
            )
            _logger.info(
                "ghori_quick_search: registered optional target %s (%s)",
                label,
                model_name,
            )
        _sync_target(env, existing, search_names, (), action_xmlid)
