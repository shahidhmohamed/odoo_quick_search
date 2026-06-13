# -*- coding: utf-8 -*-
{
    "name": "Ghori Quick Search",
    "summary": "Global record search overlay — find users, products, contacts from anywhere",
    "category": "Customizations",
    "version": "18.0.1.0.12",
    "license": "LGPL-3",
    "author": "Ghori",
    "installable": True,
    "application": False,
    "depends": ["web", "base", "product", "hr", "contacts"],
    "post_init_hook": "post_init_hook",
    "data": [
        "security/ir.model.access.csv",
        "data/ghori_quick_search_target_data.xml",
        "views/ghori_quick_search_target_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ghori_quick_search/static/src/scss/quick_search.scss",
            "ghori_quick_search/static/src/xml/quick_search_overlay.xml",
            "ghori_quick_search/static/src/js/quick_search_service.js",
            "ghori_quick_search/static/src/js/quick_search_overlay.js",
            "ghori_quick_search/static/src/js/quick_search_systray.js",
            "ghori_quick_search/static/src/js/quick_search_boot.js",
        ],
    },
}
