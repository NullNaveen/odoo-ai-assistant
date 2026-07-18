# AI Assistant for Odoo

An agentic AI assistant docked in the Odoo backend. Ask it about your live database in plain
language — it reads records, totals figures, and (with your confirmation) creates and edits data,
all as the logged-in user and always within Odoo's access rights.

Runs on **your own LLM** — local [Ollama](https://ollama.com) for privacy, or Amazon Bedrock.
Works on **Odoo 17, 18 and 19**.

![icon](odoo_ai_chatbot/static/description/icon.png)

## What it can do

- **Answer from your data** — "How many contacts do we have?", "Show the 5 most recent sale orders."
- **Totals & reporting** — sums, averages and counts computed in the database (e.g. total revenue and
  COGS for a period, grouped by account), not by reading thousands of rows.
- **Create & edit** — draft a sales order, update a field, translate a record. Anything that changes
  or deletes data is **proposed first** and only executed after you explicitly confirm.
- **Renders cleanly** — Markdown tables and code with one-click copy; every answer is sanitised HTML.
- **Adjustable panel** — two themes (Classic / Studio), per-window light/dark, text size, and a
  resizable, draggable window. Preferences persist per browser.

### The tools it uses

| Tool | Purpose |
|---|---|
| `get_model_schema` | Inspect a model's fields |
| `read_odoo_records` | Search & read (paged) |
| `count_odoo_records` | Exact counts |
| `aggregate_odoo_records` | SUM / AVG / MIN / MAX / COUNT, with group-by |
| `create_odoo_record` | Create a record |
| `update_odoo_records` | Update (confirmation required) |
| `update_odoo_record_translations` | Field translations (confirmation required) |
| `delete_odoo_records` | Delete (confirmation required) |
| `confirm_pending_action` / `cancel_pending_action` | Execute or drop a proposed change |

## Security

- Every tool runs **as the logged-in user** and calls Odoo's `check_access` — the assistant can
  never see or touch what the user couldn't.
- **Confirmation gate:** updates, translations and deletes are proposed with a count of affected
  records and only run after the user confirms in their own words. The gate is code-enforced — the
  model cannot approve its own proposal in the same turn.
- A **model blocklist** keeps the assistant away from sensitive models (payments, users, etc.) for
  create/write/delete.

## Requirements

- Odoo 17 / 18 / 19
- Python 3.10+
- An LLM endpoint: an [Ollama](https://ollama.com) server, or Amazon Bedrock credentials
- Python packages in [`odoo_ai_chatbot/requirements.txt`](odoo_ai_chatbot/requirements.txt)

## Install

```bash
# 1. Clone into your Odoo addons directory
cd /path/to/your/addons
git clone https://github.com/NullNaveen/odoo-ai-assistant.git

# 2. Install the Python dependencies (into the same environment Odoo runs in)
pip install -r odoo-ai-assistant/odoo_ai_chatbot/requirements.txt

# 3. Make sure the addons path includes the cloned folder, e.g. in odoo.conf:
#    addons_path = ...,/path/to/your/addons/odoo-ai-assistant
```

Then in Odoo: **Apps → Update Apps List**, search **AI Assistant**, and click **Install**.

> The module folder is `odoo_ai_chatbot`; that's the technical name to keep in the addons path.

## Configure

**Settings → AI Assistant** (or search "AI Provider" in Settings):

**Ollama (local, default)**
- AI Provider: `Ollama`
- Ollama Base URL: `http://localhost:11434`
- Ollama Model: e.g. `qwen3:latest` (any tool-calling model)
- Ollama API Key: only if your endpoint is behind a token

**Amazon Bedrock**
- AI Provider: `Bedrock`
- AWS Access Key / Secret Key / Region
- Bedrock Model: e.g. `anthropic.claude-3-5-sonnet-20240620-v1:0`

Open the assistant from the **wand icon** in the systray (top bar) of the Odoo backend.

> A tool-calling capable model is recommended — the assistant relies on function calling to use
> its tools. Small non-tool models will chat but won't act on data reliably.

## Credits

Based on the original **AI Chatbot** by [Tarang Kushwaha](https://github.com/tarang7651/odoo_ai_chatbot),
substantially extended (aggregation, confirmation gate, security hardening, Markdown rendering,
themed & resizable UI, multi-version support).

## License

[LGPL-3](LICENSE).
