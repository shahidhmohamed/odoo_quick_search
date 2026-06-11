# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_OPTIONAL_MODULE_TARGETS = (
    ("purchase", "purchase.order", "Purchase Orders", "name,partner_ref,origin", "fa-shopping-cart", 50, "purchase.purchase_rfq"),
    ("sale", "sale.order", "Sales Orders", "name,client_order_ref,origin", "fa-file-text-o", 60, "sale.action_orders"),
    ("ghori_inventory", "ghori.grn", "GRNs", "name", "fa-truck", 70, "ghori_inventory.action_ghori_grn"),
    ("ghori_purchase", "employee.purchase.requisition", "Requisitions", "name", "fa-list-alt", 45, "ghori_purchase.employee_purchase_requisition_action"),
)


def post_init_hook(env_or_cr, registry=None):
    if registry is not None:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    Target = env["ghori.quick.search.target"].sudo()
    IrModel = env["ir.model"].sudo()
    for module_name, model_name, label, fields, icon, seq, open_action in _OPTIONAL_MODULE_TARGETS:
        mod = env["ir.module.module"].search([("name", "=", module_name)], limit=1)
        if not mod or mod.state != "installed":
            continue
        model = IrModel.search([("model", "=", model_name)], limit=1)
        if not model:
            continue
        existing = Target.search([("model_id", "=", model.id)], limit=1)
        if existing:
            continue
        Target.create(
            {
                "name": label,
                "model_id": model.id,
                "search_field_names": fields,
                "icon": icon,
                "sequence": seq,
                "open_action_xmlid": open_action,
            }
        )
        _logger.info(
            "ghori_quick_search: registered optional target %s (%s)",
            label,
            model_name,
        )
