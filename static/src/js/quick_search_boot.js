/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { QuickSearchOverlay } from "./quick_search_overlay";

registry.category("main_components").add("ghori_quick_search_overlay", {
    Component: QuickSearchOverlay,
});

registry.category("user_menuitems").add("ghori.quick_search", (env) => ({
    type: "item",
    id: "ghori_quick_search",
    description: _t("Quick search"),
    callback: () => {
        env.services.ghori_quick_search.open();
    },
    sequence: 12,
}));

patch(WebClient.prototype, {
    setup() {
        super.setup();
        useService("ghori_quick_search");
    },
});
