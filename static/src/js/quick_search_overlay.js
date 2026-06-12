/** @odoo-module **/

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { highlightParts, quickSearchState } from "./quick_search_service";

export class QuickSearchOverlay extends Component {
    static template = "ghori_quick_search.QuickSearchOverlay";
    static props = {};

    setup() {
        this.search = useService("ghori_quick_search");
        this.qs = useState(quickSearchState);
        this.inputRef = useRef("searchInput");

        useEffect(
            () => {
                if (!this.qs.isOpen) {
                    return;
                }
                requestAnimationFrame(() => {
                    this.inputRef.el?.focus({ preventScroll: true });
                    this.inputRef.el?.select();
                });
            },
            () => [this.qs.isOpen]
        );
    }

    get groupedResults() {
        const groups = new Map();
        for (const row of this.qs.results) {
            const key = row.category || "Results";
            if (!groups.has(key)) {
                groups.set(key, []);
            }
            groups.get(key).push(row);
        }
        return [...groups.entries()].map(([category, rows]) => ({ category, rows }));
    }

    flatIndex(category, rowIndex) {
        let idx = 0;
        for (const group of this.groupedResults) {
            if (group.category === category) {
                return idx + rowIndex;
            }
            idx += group.rows.length;
        }
        return 0;
    }

    isSelected(category, rowIndex) {
        return this.flatIndex(category, rowIndex) === this.qs.selectedIndex;
    }

    rowClass(category, rowIndex) {
        const classes = ["ghori-qs-row"];
        if (this.isSelected(category, rowIndex)) {
            classes.push("is-selected");
        }
        return classes.join(" ");
    }

    onBackdropClick(ev) {
        if (ev.target.classList.contains("ghori-qs-overlay")) {
            this.search.close();
        }
    }

    onInput(ev) {
        this.search.setQuery(ev.target.value);
    }

    onRowClick(category, rowIndex) {
        const idx = this.flatIndex(category, rowIndex);
        this.qs.selectedIndex = idx;
        const result = this.qs.results[idx];
        if (result) {
            this.search.openResult(result);
        }
    }

    onRowMouseEnter(category, rowIndex) {
        this.qs.selectedIndex = this.flatIndex(category, rowIndex);
    }

    highlight(text) {
        return highlightParts(text, this.qs.query);
    }

    shortcutHint() {
        const isMac = navigator.platform.toUpperCase().includes("MAC");
        return isMac ? "⌘⇧K" : "Ctrl+Shift+K";
    }

    rowAppIconData(row) {
        return row?.app_icon_data || "";
    }

    rowAppIconBuilt(row) {
        return row?.app_icon || null;
    }

    rowAppIconBgStyle(row) {
        const icon = row?.app_icon;
        if (!icon) {
            return "";
        }
        return `background-color:${icon.backgroundColor || "#875A7B"}`;
    }

    rowAppIconColorStyle(row) {
        const icon = row?.app_icon;
        if (!icon?.color) {
            return "";
        }
        return `color:${icon.color}`;
    }

    rowAppIconClass(row) {
        return row?.app_icon?.iconClass || "fa fa-cube";
    }
}
