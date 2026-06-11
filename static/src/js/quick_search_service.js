/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

const OPEN_HOTKEYS = new Set(["control+shift+k", "control+alt+k"]);
const SEARCH_DEBOUNCE_MS = 180;
const MIN_QUERY_LENGTH = 2;

export const quickSearchState = reactive({
    isOpen: false,
    query: "",
    results: [],
    selectedIndex: 0,
    loading: false,
    error: "",
    searched: false,
});

export const quickSearchService = {
    dependencies: ["hotkey", "orm", "action", "notification"],

    start(env, { hotkey, orm, action, notification }) {
        /** @type {HTMLElement[]} */
        let inertTargets = [];
        let previouslyFocused = null;
        let debounceTimer = null;
        let searchToken = 0;

        const lockBackground = () => {
            const webClient = document.querySelector(".o_web_client");
            if (webClient) {
                for (const child of [...webClient.children]) {
                    if (child.classList.contains("o-main-components-container")) {
                        for (const mcChild of [...child.children]) {
                            if (mcChild.querySelector(".ghori-qs-overlay")) {
                                continue;
                            }
                            mcChild.setAttribute("inert", "");
                            mcChild.setAttribute("aria-hidden", "true");
                            inertTargets.push(mcChild);
                        }
                        continue;
                    }
                    child.setAttribute("inert", "");
                    child.setAttribute("aria-hidden", "true");
                    inertTargets.push(child);
                }
            }
            document.body.classList.add("ghori-qs-open");
        };

        const unlockBackground = () => {
            for (const el of inertTargets) {
                el.removeAttribute("inert");
                el.removeAttribute("aria-hidden");
            }
            inertTargets = [];
            document.body.classList.remove("ghori-qs-open");
        };

        const resetResults = () => {
            quickSearchState.results = [];
            quickSearchState.selectedIndex = 0;
            quickSearchState.loading = false;
            quickSearchState.error = "";
            quickSearchState.searched = false;
        };

        const close = () => {
            if (debounceTimer) {
                browser.clearTimeout(debounceTimer);
                debounceTimer = null;
            }
            searchToken += 1;
            quickSearchState.isOpen = false;
            quickSearchState.query = "";
            resetResults();
            unlockBackground();
            if (previouslyFocused instanceof HTMLElement && document.contains(previouslyFocused)) {
                previouslyFocused.focus({ preventScroll: true });
            }
            previouslyFocused = null;
        };

        const open = () => {
            previouslyFocused = document.activeElement;
            if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
            }
            quickSearchState.isOpen = true;
            quickSearchState.query = "";
            resetResults();
            lockBackground();
        };

        const runSearch = async (query) => {
            const token = ++searchToken;
            const trimmed = (query || "").trim();
            if (trimmed.length < MIN_QUERY_LENGTH) {
                resetResults();
                return;
            }
            quickSearchState.loading = true;
            quickSearchState.error = "";
            try {
                const results = await orm.call(
                    "ghori.quick.search.target",
                    "ghori_quick_search",
                    [trimmed],
                    { limit: 30 }
                );
                if (token !== searchToken) {
                    return;
                }
                quickSearchState.results = results || [];
                quickSearchState.selectedIndex = 0;
                quickSearchState.searched = true;
            } catch (error) {
                if (token !== searchToken) {
                    return;
                }
                const message =
                    error?.data?.message || error?.message || _t("Search failed. Try again.");
                quickSearchState.error = message;
                quickSearchState.results = [];
                notification.add(message, { type: "danger" });
            } finally {
                if (token === searchToken) {
                    quickSearchState.loading = false;
                }
            }
        };

        const scheduleSearch = (query) => {
            if (debounceTimer) {
                browser.clearTimeout(debounceTimer);
            }
            const trimmed = (query || "").trim();
            if (trimmed.length < MIN_QUERY_LENGTH) {
                resetResults();
                return;
            }
            debounceTimer = browser.setTimeout(() => {
                debounceTimer = null;
                runSearch(trimmed);
            }, SEARCH_DEBOUNCE_MS);
        };

        const setQuery = (query) => {
            quickSearchState.query = query;
            scheduleSearch(query);
        };

        const selectedResult = () => quickSearchState.results[quickSearchState.selectedIndex] || null;

        const selectRelative = (delta) => {
            const total = quickSearchState.results.length;
            if (!total) {
                return;
            }
            let idx = quickSearchState.selectedIndex + delta;
            if (idx < 0) {
                idx = total - 1;
            }
            if (idx >= total) {
                idx = 0;
            }
            quickSearchState.selectedIndex = idx;
            browser.requestAnimationFrame(() => {
                const row = document.querySelector(".ghori-qs-row.is-selected");
                row?.scrollIntoView({ block: "nearest" });
            });
        };

        const openResult = async (result) => {
            if (!result?.model || !result?.id) {
                return;
            }
            close();
            const actionDict = await orm.call(
                "ghori.quick.search.target",
                "ghori_quick_search_open_action",
                [result.model, result.id]
            );
            await action.doAction(actionDict);
        };

        const onOpenShortcut = (ev) => {
            if (quickSearchState.isOpen) {
                return;
            }
            const hotkeyStr = getActiveHotkey(ev);
            if (!hotkeyStr || !OPEN_HOTKEYS.has(hotkeyStr)) {
                return;
            }
            ev.preventDefault();
            ev.stopImmediatePropagation();
            open();
        };

        const stopKey = (ev) => {
            ev.preventDefault();
            ev.stopImmediatePropagation();
        };

        const onGlobalKeydown = (ev) => {
            onOpenShortcut(ev);
            if (!quickSearchState.isOpen) {
                return;
            }
            if (ev.key === "Escape") {
                stopKey(ev);
                close();
                return;
            }
            if (ev.key === "ArrowDown") {
                stopKey(ev);
                selectRelative(1);
                return;
            }
            if (ev.key === "ArrowUp") {
                stopKey(ev);
                selectRelative(-1);
                return;
            }
            if (ev.key === "Enter") {
                stopKey(ev);
                const result = selectedResult();
                if (result) {
                    openResult(result);
                }
            }
        };

        const onFocusIn = (ev) => {
            if (!quickSearchState.isOpen) {
                return;
            }
            const overlay = document.querySelector(".ghori-qs-overlay");
            if (!overlay || overlay.contains(ev.target)) {
                return;
            }
            browser.requestAnimationFrame(() => {
                const input = document.querySelector(".ghori-qs-input");
                input?.focus({ preventScroll: true });
            });
        };

        browser.addEventListener("keydown", onGlobalKeydown, true);
        browser.addEventListener("focusin", onFocusIn, true);

        const hotkeyOptions = { global: true, bypassEditableProtection: true };
        hotkey.add("control+shift+k", () => open(), hotkeyOptions);
        hotkey.add("control+alt+k", () => open(), hotkeyOptions);

        return {
            state: quickSearchState,
            open,
            close,
            setQuery,
            selectRelative,
            selectedResult,
            openResult,
            runSearch,
        };
    },
};

registry.category("services").add("ghori_quick_search", quickSearchService);

/**
 * @returns {{text: string, match: boolean}[]}
 */
export function highlightParts(text, query) {
    const source = text || "";
    const terms = (query || "")
        .trim()
        .split(/\s+/)
        .filter((t) => t.length >= 2);
    if (!terms.length || !source) {
        return [{ text: source, match: false }];
    }
    const pattern = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
    const re = new RegExp(`(${pattern})`, "gi");
    const parts = [];
    let last = 0;
    let match;
    while ((match = re.exec(source)) !== null) {
        if (match.index > last) {
            parts.push({ text: source.slice(last, match.index), match: false });
        }
        parts.push({ text: match[0], match: true });
        last = re.lastIndex;
    }
    if (last < source.length) {
        parts.push({ text: source.slice(last), match: false });
    }
    return parts.length ? parts : [{ text: source, match: false }];
}
