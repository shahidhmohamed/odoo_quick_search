# -*- coding: utf-8 -*-
"""Default quick-search field and action configuration by model."""

DEFAULT_FIELDS_BY_MODEL = {
    "res.users": {
        "search_field_names": ("name", "login", "email"),
        "subtitle_field_names": ("login", "email"),
        "open_action_xmlid": "base.action_res_users",
    },
    "res.partner": {
        "search_field_names": ("name", "email", "phone", "mobile", "ref", "vat"),
        "subtitle_field_names": ("email", "phone", "mobile"),
        "open_action_xmlid": "contacts.action_contacts",
    },
    "product.product": {
        "search_field_names": ("name", "default_code", "barcode"),
        "subtitle_field_names": ("default_code", "barcode"),
        "open_action_xmlid": "product.product_normal_action_sell",
    },
    "product.template": {
        "search_field_names": ("name", "default_code", "barcode"),
        "subtitle_field_names": ("default_code", "barcode"),
        "open_action_xmlid": "product.product_template_action",
    },
    "hr.employee": {
        "search_field_names": ("name", "work_email", "work_phone", "mobile_phone"),
        "subtitle_field_names": ("work_email",),
        "open_action_xmlid": "hr.open_view_employee_list",
    },
    "purchase.order": {
        "search_field_names": ("name", "partner_ref", "origin"),
        "open_action_xmlid": "purchase.purchase_rfq",
    },
    "sale.order": {
        "search_field_names": ("name", "client_order_ref", "origin"),
        "open_action_xmlid": "sale.action_orders",
    },
    "ghori.grn": {
        "search_field_names": ("name",),
        "open_action_xmlid": "ghori_inventory.action_ghori_grn",
    },
    "employee.purchase.requisition": {
        "search_field_names": ("name",),
        "open_action_xmlid": "ghori_purchase.employee_purchase_requisition_action",
    },
}

DEFAULT_TARGET_XMLIDS = (
    "ghori_quick_search.ghori_quick_search_target_users",
    "ghori_quick_search.ghori_quick_search_target_partners",
    "ghori_quick_search.ghori_quick_search_target_products",
    "ghori_quick_search.ghori_quick_search_target_product_templates",
    "ghori_quick_search.ghori_quick_search_target_employees",
)

OPTIONAL_MODULE_TARGETS = (
    ("purchase", "purchase.order", "Purchase Orders", "fa-shopping-cart", 50),
    ("sale", "sale.order", "Sales Orders", "fa-file-text-o", 60),
    ("ghori_inventory", "ghori.grn", "GRNs", "fa-truck", 70),
    (
        "ghori_purchase",
        "employee.purchase.requisition",
        "Requisitions",
        "fa-list-alt",
        45,
    ),
)
