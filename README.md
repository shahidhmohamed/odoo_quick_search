# Ghori Quick Search

Global record search for Odoo 18 — find **users**, **products**, **contacts**, and more from anywhere without opening each app first.

## Open search

| Platform | Shortcut |
|----------|----------|
| Mac | **⌘⇧K** (Cmd+Shift+K) |
| Mac (alternate) | **Ctrl+Option+K** |
| Windows / Linux | **Ctrl+Shift+K** |
| Alternate | **Ctrl+Alt+K** |

Also: **search icon** in the top bar, user menu → **Quick search**.

> Uses **Cmd+Shift+K** so it does not replace Odoo’s built-in **Cmd+K** menu search.

## Example

Type `shahidh` → matches user **Shahidh** by name, login, or email → **Enter** opens the user form.

## Configure searchable models

**Settings → Technical → Quick Search Targets** (administrators only)

Each row defines:

- **Model** (e.g. `res.users`, `product.product`)
- **Search fields** — comma-separated (`name,login,email`)
- **Subtitle fields** — shown under the title
- **Extra domain** — e.g. `[('share','=',False)]` for internal users only
- **Max results** per model

Optional targets for Purchase Orders, Sales Orders, GRNs, and Requisitions are added automatically when those Ghori modules are installed.

## Security

Search respects **access rights** and **record rules**. Users only see records they are allowed to read.
