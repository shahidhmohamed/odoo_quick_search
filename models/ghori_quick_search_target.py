# -*- coding: utf-8 -*-

import ast
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class GhoriQuickSearchTarget(models.Model):
    _name = "ghori.quick.search.target"
    _description = "Quick Search — searchable model"
    _order = "sequence, name, id"

    name = fields.Char(
        string="Label",
        required=True,
        translate=True,
        help="Category shown in the search palette (e.g. Users, Products).",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(related="model_id.model", store=True, readonly=True, string="Technical model")
    search_field_names = fields.Char(
        string="Search fields",
        required=True,
        default="name",
        help="Comma-separated field names searched with ilike (e.g. name,login,email).",
    )
    subtitle_field_names = fields.Char(
        string="Subtitle fields",
        help="Comma-separated fields; first non-empty value is shown under the title.",
    )
    extra_domain = fields.Char(
        string="Extra domain",
        default="[]",
        help="Python list domain AND-ed with the text search (e.g. [('active','=',True)]).",
    )
    icon = fields.Char(
        string="Icon",
        default="fa-search",
        help="Font Awesome 4 class (e.g. fa-user, fa-cube).",
    )
    result_limit = fields.Integer(
        string="Max results",
        default=8,
        help="Maximum matches returned for this model per search.",
    )
    group_ids = fields.Many2many(
        "res.groups",
        string="Allowed groups",
        help="Leave empty to allow all internal users who can read the model.",
    )
    open_action_xmlid = fields.Char(
        string="Open action",
        help=(
            "Optional window action xmlid used when opening a match "
            "(e.g. base.action_res_users). Ensures the same form as the "
            "app menu instead of a generic default form view."
        ),
    )

    _sql_constraints = [
        (
            "model_id_unique",
            "unique(model_id)",
            "Each model can only be registered once for quick search.",
        ),
    ]

    @api.constrains("extra_domain")
    def _check_extra_domain(self):
        for rec in self:
            rec._parse_domain(rec.extra_domain)

    @api.model
    def _parse_domain(self, domain_text):
        text = (domain_text or "[]").strip()
        if not text:
            return []
        try:
            domain = ast.literal_eval(text)
        except (SyntaxError, ValueError) as exc:
            raise UserError(
                _("Extra domain must be a valid Python list: %s") % exc
            ) from exc
        if not isinstance(domain, list):
            raise UserError(_("Extra domain must be a list."))
        return domain

    @api.model
    def _split_field_names(self, value):
        return [part.strip() for part in (value or "").split(",") if part.strip()]

    def _user_may_search_target(self, user):
        self.ensure_one()
        if not self.active:
            return False
        if self.group_ids and not (self.group_ids & user.groups_id):
            return False
        Model = self.env[self.model_name]
        return Model.has_access("read")

    def _build_search_domain(self, query):
        self.ensure_one()
        terms = self._split_field_names(self.search_field_names)
        if not terms:
            terms = ["name"]
        Model = self.env[self.model_name]
        valid_terms = [f for f in terms if f in Model._fields]
        if not valid_terms:
            valid_terms = ["name"] if "name" in Model._fields else []
        extra = self._parse_domain(self.extra_domain)
        if not valid_terms:
            return extra or [("id", "=", 0)]
        # Each OR branch must be a domain (list of leaves), not a bare leaf list.
        leaf_domains = [[(field, "ilike", query)] for field in valid_terms]
        text_domain = leaf_domains[0] if len(leaf_domains) == 1 else expression.OR(leaf_domains)
        if extra:
            return expression.AND([extra, text_domain])
        return text_domain

    def _record_subtitle(self, record):
        self.ensure_one()
        Model = self.env[self.model_name]
        for field_name in self._split_field_names(self.subtitle_field_names):
            if field_name not in Model._fields:
                continue
            value = record[field_name]
            if isinstance(value, models.BaseModel):
                value = value.display_name
            if value not in (False, None, ""):
                return str(value)
        return ""

    @api.model
    def _ghori_quick_search_form_action(self, record, target=None):
        """Build a form-only window action for *record* (menu action when configured)."""
        model = record._name
        action = False
        xmlid = (target.open_action_xmlid or "").strip() if target else ""
        if xmlid:
            try:
                action = dict(self.env["ir.actions.actions"]._for_xml_id(xmlid))
            except ValueError:
                _logger.warning(
                    "ghori_quick_search: unknown open action xmlid %r for %s",
                    xmlid,
                    model,
                )
        if not action:
            action = {
                "type": "ir.actions.act_window",
                "name": record.display_name,
                "res_model": model,
                "view_mode": "form",
                "views": [[False, "form"]],
            }
        action = dict(action)
        action["res_id"] = record.id
        action["view_mode"] = "form"
        action["target"] = "current"
        views = action.get("views") or [[False, "form"]]
        form_views = [view for view in views if view[1] == "form"]
        action["views"] = form_views or [[False, "form"]]
        action.pop("domain", None)
        action.pop("search_view_id", None)
        return action

    @api.model
    def ghori_quick_search_open_action(self, model, res_id):
        """Return the window action dict to open one search result."""
        record = self.env[model].browse(int(res_id)).exists()
        if not record:
            raise UserError(_("Record not found or you cannot open it."))
        record.check_access("read")
        target = self.search(
            [("model_name", "=", model), ("active", "=", True)], limit=1
        )
        return self._ghori_quick_search_form_action(record, target)

    @api.model
    def ghori_quick_search(self, query, limit=30):
        """Search configured models; respects access rights and record rules."""
        query = (query or "").strip()
        if len(query) < 2:
            return []

        user = self.env.user
        if user.share:
            return []

        targets = self.search([("active", "=", True)], order="sequence, id")
        results = []
        remaining = max(1, min(int(limit or 30), 50))

        for target in targets:
            if remaining <= 0:
                break
            if not target._user_may_search_target(user):
                continue
            Model = self.env[target.model_name]
            try:
                domain = target._build_search_domain(query)
                per_model = min(target.result_limit or 8, remaining)
                records = Model.search(domain, limit=per_model, order="id desc")
            except Exception:
                _logger.exception(
                    "ghori_quick_search: search failed for %s", target.model_name
                )
                continue

            for record in records:
                try:
                    record.check_access_rule("read")
                except Exception:
                    continue
                display = record.display_name
                if not display:
                    continue
                results.append(
                    {
                        "model": target.model_name,
                        "id": record.id,
                        "name": display,
                        "subtitle": target._record_subtitle(record),
                        "category": target.name,
                        "icon": target.icon or "fa-search",
                    }
                )
                remaining -= 1
                if remaining <= 0:
                    break

        return results
