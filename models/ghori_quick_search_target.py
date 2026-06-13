# -*- coding: utf-8 -*-

import ast
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

from ..constants import DEFAULT_FIELDS_BY_MODEL

_logger = logging.getLogger(__name__)

_SEARCHABLE_FIELD_TYPES = ("char", "text", "html", "selection", "many2one")


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
    search_field_ids = fields.Many2many(
        "ir.model.fields",
        "ghori_quick_search_target_search_field_rel",
        "target_id",
        "field_id",
        string="Search fields",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('char', 'text', 'html', 'selection', 'many2one'))]",
        help="Fields searched with “contains” when the user types in quick search.",
    )
    subtitle_field_ids = fields.Many2many(
        "ir.model.fields",
        "ghori_quick_search_target_subtitle_field_rel",
        "target_id",
        "field_id",
        string="Subtitle fields",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('char', 'text', 'html', 'selection', 'many2one'))]",
        help="First non-empty value is shown under the title in search results.",
    )
    search_field_names = fields.Char(
        string="Search fields (technical)",
        compute="_compute_field_name_strings",
        store=True,
        help="Comma-separated field names — synced from Search fields above.",
    )
    subtitle_field_names = fields.Char(
        string="Subtitle fields (technical)",
        compute="_compute_field_name_strings",
        store=True,
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
    open_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Open action",
        domain="[('res_model', '=', model_name)]",
        help=(
            "Window action used when opening a match — same form as the app "
            "menu (e.g. Settings → Users for res.users)."
        ),
    )
    open_action_xmlid = fields.Char(
        string="Open action (technical)",
        compute="_compute_open_action_xmlid",
        store=True,
        help="External ID synced from Open action — used at runtime.",
    )

    _sql_constraints = [
        (
            "model_id_unique",
            "unique(model_id)",
            "Each model can only be registered once for quick search.",
        ),
    ]

    @api.constrains("search_field_ids", "model_id")
    def _check_search_fields(self):
        for rec in self:
            if not rec.search_field_ids:
                raise UserError(
                    _("Pick at least one Search field for %(label)s.")
                    % {"label": rec.name or rec.model_id.display_name}
                )

    @api.model
    def _field_records_for_names(self, model_id, names):
        if not model_id or not names:
            return self.env["ir.model.fields"]
        return self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model_id),
                ("name", "in", list(names)),
            ]
        )

    @api.model
    def _fallback_search_field(self, model_id):
        return self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model_id),
                ("name", "in", ("name", "display_name")),
                ("ttype", "in", _SEARCHABLE_FIELD_TYPES),
            ],
            limit=1,
        )

    @api.model
    def _apply_target_defaults(self, vals):
        """Populate search/subtitle fields and open action before create."""
        if vals.get("search_field_ids"):
            return
        model_id = vals.get("model_id")
        if not model_id:
            return
        model = self.env["ir.model"].browse(model_id)
        spec = DEFAULT_FIELDS_BY_MODEL.get(model.model, {})
        search_names = spec.get("search_field_names", ("name",))
        fields = self._field_records_for_names(model_id, search_names)
        if not fields:
            fields = self._fallback_search_field(model_id)
        if fields:
            vals["search_field_ids"] = [(6, 0, fields.ids)]
        if not vals.get("subtitle_field_ids") and spec.get("subtitle_field_names"):
            subtitle_fields = self._field_records_for_names(
                model_id, spec["subtitle_field_names"]
            )
            if subtitle_fields:
                vals["subtitle_field_ids"] = [(6, 0, subtitle_fields.ids)]
        if not vals.get("open_action_id") and spec.get("open_action_xmlid"):
            try:
                action = self.env.ref(spec["open_action_xmlid"])
            except ValueError:
                action = self.env["ir.actions.act_window"]
            if action._name == "ir.actions.act_window":
                vals["open_action_id"] = action.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_target_defaults(vals)
        return super().create(vals_list)

    @api.depends("search_field_ids.name", "subtitle_field_ids.name")
    def _compute_field_name_strings(self):
        for rec in self:
            search_names = rec.search_field_ids.mapped("name")
            rec.search_field_names = ",".join(search_names) if search_names else "name"
            subtitle_names = rec.subtitle_field_ids.mapped("name")
            rec.subtitle_field_names = ",".join(subtitle_names) if subtitle_names else ""

    @api.depends("open_action_id")
    def _compute_open_action_xmlid(self):
        IrModelData = self.env["ir.model.data"].sudo()
        for rec in self:
            rec.open_action_xmlid = False
            if not rec.open_action_id:
                continue
            imd = IrModelData.search(
                [
                    ("model", "=", "ir.actions.act_window"),
                    ("res_id", "=", rec.open_action_id.id),
                ],
                limit=1,
            )
            if imd:
                rec.open_action_xmlid = f"{imd.module}.{imd.name}"

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.search_field_ids = False
        self.subtitle_field_ids = False
        self.open_action_id = False
        if not self.model_id:
            return
        default_fields = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", self.model_id.id),
                ("name", "in", ("name", "display_name")),
                ("ttype", "in", ("char", "text", "html", "selection", "many2one")),
            ],
            limit=1,
        )
        if default_fields:
            self.search_field_ids = default_fields

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

    _GHORI_SKIP_MODULE_NAMES = frozenset({"base", "web", "web_studio", "bus"})

    def _ghori_row_model_label(self):
        """Human-readable record type, e.g. Contact, User, Sales Order."""
        self.ensure_one()
        if self.model_name in self.env:
            description = getattr(self.env[self.model_name], "_description", "") or ""
            if description:
                return description
        if self.model_id.name:
            return self.model_id.name
        return self.model_name or ""

    def _ghori_row_app_menu(self):
        """Root app menu for this target (Contacts, Sales, Inventory, …)."""
        self.ensure_one()
        action_dict = (
            {"id": self.open_action_id.id} if self.open_action_id else {}
        )
        app_menu_id = self.env["ghori.quick.search.target"]._ghori_menu_app_id_for_window_action(
            action_dict, self.model_name
        )
        if app_menu_id:
            menu = self.env["ir.ui.menu"].sudo().browse(app_menu_id)
            if menu.exists():
                return menu
        return self.env["ir.ui.menu"]

    @api.model
    def _ghori_menu_web_icon_payload(self, menu):
        """Icon payload for the web client — image URL or FA built icon."""
        if not menu or not menu.exists():
            return {}
        menu = menu.sudo()
        web_icon = (menu.web_icon or "").strip()
        parts = [part.strip() for part in web_icon.split(",") if part.strip()]

        if menu.web_icon_data:
            attachment = self.env["ir.attachment"].sudo().search(
                [
                    ("res_model", "=", "ir.ui.menu"),
                    ("res_id", "=", menu.id),
                    ("res_field", "=", "web_icon_data"),
                ],
                limit=1,
            )
            mimetype = (attachment.mimetype if attachment else None) or "image/png"
            data = menu.web_icon_data
            if isinstance(data, bytes):
                b64 = data.decode("ascii")
            else:
                b64 = data or ""
            if b64:
                return {"app_icon_data": f"data:{mimetype};base64,{b64}"}

        if len(parts) == 2:
            image_data = menu._compute_web_icon_data(web_icon)
            if image_data:
                b64 = (
                    image_data.decode("ascii")
                    if isinstance(image_data, bytes)
                    else image_data
                )
                if b64:
                    return {"app_icon_data": f"data:image/png;base64,{b64}"}

        if len(parts) >= 3:
            return {
                "app_icon": {
                    "iconClass": parts[0],
                    "color": parts[1],
                    "backgroundColor": parts[2],
                }
            }

        return {"app_icon_data": "/web/static/img/default_icon_app.png"}

    def _ghori_row_app_label(self, installed_modules=None, app_menu=None):
        """Odoo app / module name when we can resolve one (Contacts, Sales, …)."""
        self.ensure_one()
        if app_menu is None:
            app_menu = self._ghori_row_app_menu()
        if app_menu and app_menu.name:
            return app_menu.name
        if not self.model_id:
            return ""
        module_names = [
            part.strip()
            for part in (self.model_id.modules or "").split(",")
            if part.strip()
        ]
        if not module_names:
            return ""
        if installed_modules is None:
            installed_modules = {
                mod.name: (mod.shortdesc or mod.name)
                for mod in self.env["ir.module.module"]
                .sudo()
                .search([("state", "=", "installed")])
            }
        for mod_name in module_names:
            if mod_name in self._GHORI_SKIP_MODULE_NAMES:
                continue
            if mod_name in installed_modules:
                return installed_modules[mod_name]
        for mod_name in module_names:
            if mod_name in installed_modules:
                return installed_modules[mod_name]
        return ""

    def _ghori_quick_search_row_meta(self, installed_modules=None):
        self.ensure_one()
        app_menu = self._ghori_row_app_menu()
        icon_payload = self.env["ghori.quick.search.target"]._ghori_menu_web_icon_payload(
            app_menu
        )
        return {
            "model_label": self._ghori_row_model_label(),
            "app_label": self._ghori_row_app_label(
                installed_modules=installed_modules, app_menu=app_menu
            ),
            **icon_payload,
        }

    @api.model
    def _ghori_quick_search_target_meta_cache(self, targets):
        installed_modules = {
            mod.name: (mod.shortdesc or mod.name)
            for mod in self.env["ir.module.module"]
            .sudo()
            .search([("state", "=", "installed")])
        }
        targets.mapped("model_id")
        return {
            target.id: target._ghori_quick_search_row_meta(
                installed_modules=installed_modules
            )
            for target in targets
        }

    @api.model
    def _ghori_quick_search_form_action(self, record, target=None):
        """Build a form-only window action for *record* (menu action when configured)."""
        model = record._name
        action = False
        if target and target.open_action_id:
            action = target.open_action_id.sudo()._get_action_dict()
        elif target:
            xmlid = (target.open_action_xmlid or "").strip()
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
    def _ghori_menu_app_id_for_window_action(self, action_dict, model_name):
        """Root app menu id so the web client navbar shows the correct submenus."""
        Menu = self.env["ir.ui.menu"].sudo()
        menus = Menu.browse()
        action_id = action_dict.get("id")
        if action_id:
            action_ref = f"ir.actions.act_window,{action_id}"
            menus = Menu.search([("action", "=", action_ref)], order="sequence, id")
        if not menus and model_name:
            window_actions = self.env["ir.actions.act_window"].sudo().search(
                [("res_model", "=", model_name)], order="id"
            )
            for act in window_actions:
                action_ref = f"ir.actions.act_window,{act.id}"
                found = Menu.search([("action", "=", action_ref)], limit=1, order="sequence, id")
                if found:
                    menus = found
                    break
        if not menus:
            return False
        app_menu = menus[0]
        while app_menu.parent_id:
            app_menu = app_menu.parent_id
        return app_menu.id

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
        action = self._ghori_quick_search_form_action(record, target)
        return {
            "action": action,
            "menu_app_id": self._ghori_menu_app_id_for_window_action(action, model) or False,
        }

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
        meta_cache = self._ghori_quick_search_target_meta_cache(targets)
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
                row_meta = meta_cache.get(target.id, {})
                results.append(
                    {
                        "model": target.model_name,
                        "id": record.id,
                        "name": display,
                        "subtitle": target._record_subtitle(record),
                        "category": target.name,
                        "icon": target.icon or "fa-search",
                        "model_label": row_meta.get("model_label") or target.model_name,
                        "app_label": row_meta.get("app_label") or "",
                        "app_icon_data": row_meta.get("app_icon_data") or "",
                        "app_icon": row_meta.get("app_icon") or False,
                    }
                )
                remaining -= 1
                if remaining <= 0:
                    break

        return results
