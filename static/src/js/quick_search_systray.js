/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class QuickSearchSystray extends Component {
    static template = xml`
        <button type="button"
                class="ghori-qs-systray btn btn-link lh-1 px-2"
                title="Quick search (⌘⇧K)"
                t-on-click="onClick">
            <i class="fa fa-search"/>
        </button>`;
    static props = {};

    setup() {
        this.search = useService("ghori_quick_search");
    }

    onClick() {
        this.search.open();
    }
}

registry.category("systray").add(
    "ghori.quick_search",
    { Component: QuickSearchSystray },
    { sequence: 45 }
);
