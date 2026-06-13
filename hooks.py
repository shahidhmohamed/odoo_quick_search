# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, api

from .constants import DEFAULT_FIELDS_BY_MODEL, DEFAULT_TARGET_XMLIDS, OPTIONAL_MODULE_TARGETS

_logger = logging.getLogger(__name__)


def _sync_target(env, target):
    if not target:
        return
    spec = DEFAULT_FIELDS_BY_MODEL.get(target.model_name, {})
    vals = {}
    if not target.search_field_ids and spec.get("search_field_names"):
        fields = target._field_records_for_names(
            target.model_id.id, spec["search_field_names"]
        )
        if fields:
            vals["search_field_ids"] = [(6, 0, fields.ids)]
    if not target.subtitle_field_ids and spec.get("subtitle_field_names"):
        fields = target._field_records_for_names(
            target.model_id.id, spec["subtitle_field_names"]
        )
        if fields:
            vals["subtitle_field_ids"] = [(6, 0, fields.ids)]
    if not target.open_action_id and spec.get("open_action_xmlid"):
        try:
            action = env.ref(spec["open_action_xmlid"])
        except ValueError:
            action = env["ir.actions.act_window"]
        if action._name == "ir.actions.act_window":
            vals["open_action_id"] = action.id
    if vals:
        target.write(vals)


def post_init_hook(env_or_cr, registry=None):
    if registry is not None:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    Target = env["ghori.quick.search.target"].sudo()
    IrModel = env["ir.model"].sudo()

    for target_xmlid in DEFAULT_TARGET_XMLIDS:
        target = env.ref(target_xmlid, raise_if_not_found=False)
        _sync_target(env, target)

    for module_name, model_name, label, icon, seq in OPTIONAL_MODULE_TARGETS:
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
        _sync_target(env, existing)
