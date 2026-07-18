/** @odoo-module **/

import {
    Component, useState, onWillStart, onWillUnmount,
    useRef, useEffect, useExternalListener, markup,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Copy affordance injected around every code block / table in an assistant reply.
const COPY_ICON = `<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.6" stroke="currentColor" stroke-width="1.3" fill="none"/><path d="M10.5 5.5V4A1.5 1.5 0 0 0 9 2.5H4A1.5 1.5 0 0 0 2.5 4v5A1.5 1.5 0 0 0 4 10.5h1.5" stroke="currentColor" stroke-width="1.3" fill="none" stroke-linecap="round"/></svg>`;
const DONE_ICON = `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// Persisted preferences. Bumping the key is a clean migration if the shape ever changes.
const PREFS_KEY = "aichat_prefs_v1";
// classic/ocean/sunset share the bubble layout; studio/terminal share the ledger layout.
const THEMES = ["classic", "ocean", "sunset", "studio", "terminal"];
const BUBBLE_THEMES = ["classic", "ocean", "sunset"];
const SIZES = ["s", "m", "l"];
const DEFAULTS = {
    theme: "classic",     // the repo-original widget look is the default
    dark: false,
    textSize: "m",
    enterToSend: true,
    width: 400,           // classic default footprint (~ the original 380x600 card)
    height: 620,
    maximized: false,
};
// Resize floors. The panel is anchored bottom-right; the ceiling is the live viewport,
// computed in JS because libsass forbids CSS min()/max()/clamp() in this stylesheet.
const MIN_W = 328;
const MIN_H = 380;
const VIEWPORT_MARGIN = 24;

export class AIChatbot extends Component {
    setup() {
        this.orm = useService("orm");
        this.messagesContainerRef = useRef("messagesContainer");

        const prefs = this._loadPrefs();
        this.state = useState({
            messages: [],
            inputValue: "",
            isLoading: false,
            sessionId: null,
            isOpen: false,
            settingsOpen: false,
            historyOpen: false,
            history: [],
            historyQuery: "",
            historyLoading: false,
            renamingId: null,
            renameValue: "",
            error: null,
            // appearance / layout, all persisted
            theme: prefs.theme,
            dark: prefs.dark,
            textSize: prefs.textSize,
            enterToSend: prefs.enterToSend,
            width: prefs.width,
            height: prefs.height,
            maximized: prefs.maximized,
        });

        // Openers for the empty state. Deliberately concrete and answerable by the tools we
        // actually ship — a generic "How can I help?" teaches the user nothing about what this
        // thing can do. Not invented data: these are prompts, not claims.
        this.starters = [
            "How many contacts do we have?",
            "Show the 5 most recent sale orders",
            "Which products are out of stock?",
        ];

        // Bound once so add/removeEventListener pair up during a drag.
        this._onDragMove = this._onDragMove.bind(this);
        this._onDragUp = this._onDragUp.bind(this);
        this._drag = null;

        onWillStart(async () => {
            try {
                const latestSession = await this.orm.call("ai.chat.session", "get_current_session", []);
                if (latestSession && latestSession.session_id) {
                    this.state.sessionId = latestSession.session_id;
                    if (latestSession.messages?.length) {
                        this.state.messages = latestSession.messages.map((msg) => this._toMessage(msg.role, msg.content, true));
                    }
                }
            } catch (e) {
                console.warn("AI Assistant: failed to load previous session", e);
            }
        });

        // Keep pinned to the newest message, and decorate any rich blocks that just rendered.
        useEffect(
            () => {
                const el = this.messagesContainerRef.el;
                if (!el) return;
                this._decorateRichBlocks(el);
                el.scrollTop = el.scrollHeight;
            },
            () => [this.state.messages.length, this.state.isOpen, this.state.isLoading, this.state.theme]
        );

        // Close the settings popover on an outside click.
        useExternalListener(document, "pointerdown", this._onDocPointerDown.bind(this));
        // A shrinking window must never leave the panel larger than the screen.
        useExternalListener(window, "resize", this._onViewportResize.bind(this));

        onWillUnmount(() => this._endDrag());
    }

    // ---- preferences ---------------------------------------------------------
    _loadPrefs() {
        try {
            const raw = window.localStorage.getItem(PREFS_KEY);
            if (!raw) return { ...DEFAULTS };
            const saved = JSON.parse(raw);
            const p = { ...DEFAULTS, ...saved };
            // Validate: a corrupt/legacy value must never break the panel.
            if (!THEMES.includes(p.theme)) p.theme = DEFAULTS.theme;
            if (!SIZES.includes(p.textSize)) p.textSize = DEFAULTS.textSize;
            p.dark = !!p.dark;
            p.enterToSend = p.enterToSend !== false;
            p.maximized = !!p.maximized;
            p.width = Number.isFinite(p.width) ? p.width : DEFAULTS.width;
            p.height = Number.isFinite(p.height) ? p.height : DEFAULTS.height;
            return p;
        } catch (e) {
            return { ...DEFAULTS };
        }
    }

    _savePrefs() {
        try {
            const { theme, dark, textSize, enterToSend, width, height, maximized } = this.state;
            window.localStorage.setItem(
                PREFS_KEY,
                JSON.stringify({ theme, dark, textSize, enterToSend, width, height, maximized })
            );
        } catch (e) {
            /* storage disabled/full — appearance simply won't persist; not fatal. */
        }
    }

    setPref(key, value) {
        this.state[key] = value;
        this._savePrefs();
    }

    toggleSettings() {
        this.state.settingsOpen = !this.state.settingsOpen;
        if (this.state.settingsOpen) this.state.historyOpen = false;
    }

    _onDocPointerDown(ev) {
        if (!this.state.settingsOpen) return;
        const t = ev.target;
        if (t?.closest && (t.closest(".o_aichat_settings") || t.closest(".o_aichat_gear"))) return;
        this.state.settingsOpen = false;
    }

    get isBubbleTheme() {
        return BUBBLE_THEMES.includes(this.state.theme);
    }

    // ---- conversation history -------------------------------------------------
    async toggleHistory() {
        this.state.historyOpen = !this.state.historyOpen;
        if (!this.state.historyOpen) return;
        this.state.settingsOpen = false;
        this.state.historyQuery = "";
        this.state.renamingId = null;
        this.state.historyLoading = true;
        try {
            this.state.history = await this.orm.call("ai.chat.session", "get_sessions", []);
        } catch (e) {
            console.warn("AI Assistant: failed to load history", e);
            this.state.history = [];
        } finally {
            this.state.historyLoading = false;
        }
    }

    get filteredHistory() {
        const q = this.state.historyQuery.trim().toLowerCase();
        if (!q) return this.state.history;
        return this.state.history.filter((s) => (s.title || "").toLowerCase().includes(q));
    }

    async selectSession(id) {
        if (this.state.renamingId === id) return;      // a rename in progress owns the row
        try {
            const data = await this.orm.call("ai.chat.session", "get_session_messages", [id]);
            if (!data?.session_id) return;
            this.state.sessionId = data.session_id;
            this.state.messages = (data.messages || []).map((m) => this._toMessage(m.role, m.content, true));
            this.state.error = null;
            this.state.historyOpen = false;
        } catch (e) {
            console.warn("AI Assistant: failed to open conversation", e);
        }
    }

    async deleteSession(id, ev) {
        ev?.stopPropagation();
        try {
            await this.orm.call("ai.chat.session", "delete_session", [id]);
            this.state.history = this.state.history.filter((s) => s.id !== id);
            if (this.state.sessionId === id) {
                // the open conversation is gone — fall back to the most recent one, or start fresh
                const next = this.state.history[0];
                if (next) await this.selectSession(next.id);
                else await this.startNewChat();
            }
        } catch (e) {
            console.warn("AI Assistant: failed to delete conversation", e);
        }
    }

    startRename(s, ev) {
        ev?.stopPropagation();
        this.state.renamingId = s.id;
        this.state.renameValue = s.title || "";
    }

    async commitRename(s) {
        const name = this.state.renameValue.trim();
        this.state.renamingId = null;
        if (!name || name === s.title) return;
        try {
            await this.orm.call("ai.chat.session", "rename_session", [s.id, name]);
            s.title = name;
        } catch (e) {
            console.warn("AI Assistant: failed to rename conversation", e);
        }
    }

    onRenameKeydown(s, ev) {
        if (ev.key === "Enter") { ev.preventDefault(); this.commitRename(s); }
        if (ev.key === "Escape") this.state.renamingId = null;
    }

    /** "2m ago"-style stamp for the history list; server datetimes are naive UTC. */
    relTime(dt) {
        if (!dt) return "";
        const then = new Date(dt.replace(" ", "T") + "Z").getTime();
        const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
        if (mins < 1) return "now";
        if (mins < 60) return `${mins}m`;
        if (mins < 1440) return `${Math.round(mins / 60)}h`;
        if (mins < 43200) return `${Math.round(mins / 1440)}d`;
        return new Date(then).toLocaleDateString();
    }

    // ---- per-message copy -----------------------------------------------------
    async copyMessage(ev) {
        const btn = ev.currentTarget;
        const prose = btn.closest(".o_aichat_row")?.querySelector(".o_aichat_prose");
        if (!prose) return;
        try {
            await navigator.clipboard.writeText(prose.innerText.trim());
            btn.classList.add("is-done");
            setTimeout(() => btn.classList.remove("is-done"), 1400);
        } catch (e) {
            console.warn("AI Assistant: copy failed", e);
        }
    }

    // ---- layout / resize -----------------------------------------------------
    get isMobile() {
        return window.innerWidth < 768;
    }

    get panelStyle() {
        // Maximized and mobile are laid out entirely in CSS (four insets); leave inline style off
        // so the class/media rules win. Otherwise pin the persisted footprint.
        if (this.state.maximized || this.isMobile) return "";
        return `width:${this.state.width}px;height:${this.state.height}px;`;
    }

    _maxW() {
        return Math.max(MIN_W, window.innerWidth - VIEWPORT_MARGIN);
    }
    _maxH() {
        return Math.max(MIN_H, window.innerHeight - VIEWPORT_MARGIN);
    }
    _clampW(w) {
        return Math.min(Math.max(Math.round(w), MIN_W), this._maxW());
    }
    _clampH(h) {
        return Math.min(Math.max(Math.round(h), MIN_H), this._maxH());
    }

    _onViewportResize() {
        // Keep the stored footprint inside the (possibly smaller) viewport.
        this.state.width = this._clampW(this.state.width);
        this.state.height = this._clampH(this.state.height);
    }

    // mode: "x" (left edge → width), "y" (top edge → height), "xy" (corner → both).
    // The panel is anchored bottom-right, so dragging the top/left edge OUTWARD (negative delta)
    // grows it — width leftward, height upward. Exactly "extend it horizontally / upside".
    onGripDown(ev, mode) {
        if (this.state.maximized || this.isMobile) return;
        ev.preventDefault();
        this._drag = {
            mode,
            x: ev.clientX,
            y: ev.clientY,
            w: this.state.width,
            h: this.state.height,
        };
        document.body.classList.add("o_aichat_resizing");
        window.addEventListener("pointermove", this._onDragMove);
        window.addEventListener("pointerup", this._onDragUp);
        window.addEventListener("pointercancel", this._onDragUp);
    }

    _onDragMove(ev) {
        const d = this._drag;
        if (!d) return;
        if (d.mode.includes("x")) this.state.width = this._clampW(d.w - (ev.clientX - d.x));
        if (d.mode.includes("y")) this.state.height = this._clampH(d.h - (ev.clientY - d.y));
    }

    _onDragUp() {
        this._endDrag();
        this._savePrefs();
    }

    _endDrag() {
        if (!this._drag) return;
        this._drag = null;
        document.body.classList.remove("o_aichat_resizing");
        window.removeEventListener("pointermove", this._onDragMove);
        window.removeEventListener("pointerup", this._onDragUp);
        window.removeEventListener("pointercancel", this._onDragUp);
    }

    resetSize() {
        this.state.width = DEFAULTS.width;
        this.state.height = DEFAULTS.height;
        this.state.maximized = false;
        this._savePrefs();
    }

    /**
     * Assistant content is server-rendered + bleach-sanitised HTML, so it is marked up.
     * User content is NOT: markup() on the user's own input would render whatever they typed
     * as live HTML (`<img src=x onerror=...>`), which is a self-XSS. Owl escapes plain
     * strings, so we pass it through as text.
     *
     * `fromHistory` matters: ai.chat.message.content is an Odoo Html field, which normalises
     * stored plain text by wrapping it in <p>…</p>. Rendering that as text (correctly, for
     * safety) showed the user their own message as a literal "<p>How many contacts…</p>".
     * So for history we decode the HTML back to text — parsing into a detached element and
     * reading textContent only, which never executes anything and never re-introduces the XSS.
     * Live messages are used verbatim: they are exactly what the user typed.
     */
    _toMessage(role, content, fromHistory = false) {
        if (role !== "user") return { role, content: markup(content) };
        if (!fromHistory) return { role, content };
        const el = document.createElement("div");
        el.innerHTML = content ?? "";
        return { role, content: (el.textContent || "").trim() };
    }

    /**
     * Wrap <pre> and <table> in a chrome that carries a Copy button.
     * Runs after render because the reply HTML comes from the server, not from a template.
     */
    _decorateRichBlocks(root) {
        for (const node of root.querySelectorAll(".o_aichat_prose pre, .o_aichat_prose table")) {
            if (node.closest(".o_aichat_block")) continue;      // already decorated

            const isTable = node.tagName === "TABLE";
            const block = document.createElement("div");
            block.className = "o_aichat_block";

            const bar = document.createElement("div");
            bar.className = "o_aichat_block__bar";
            const label = document.createElement("span");
            const lang = node.querySelector?.("code")?.className?.match(/language-([\w+#-]+)/)?.[1];
            label.textContent = isTable ? "Table" : (lang || "Code");
            const btn = document.createElement("button");
            btn.className = "o_aichat_block__copy";
            btn.type = "button";
            btn.innerHTML = `${COPY_ICON}<span>Copy</span>`;
            btn.addEventListener("click", () => this._copyBlock(node, btn, isTable));
            bar.append(label, btn);

            const scroll = document.createElement("div");
            scroll.className = "o_aichat_block__scroll";

            node.parentNode.insertBefore(block, node);
            scroll.appendChild(node);
            block.append(bar, scroll);
        }
    }

    async _copyBlock(node, btn, isTable) {
        try {
            if (isTable) {
                // Write BOTH flavours: text/html so Excel/Sheets/Docs paste a real table with
                // its structure intact, and a tab-separated text/plain fallback for editors.
                const tsv = [...node.rows]
                    .map((r) => [...r.cells].map((c) => c.innerText.trim().replace(/\s+/g, " ")).join("\t"))
                    .join("\n");
                if (window.ClipboardItem && navigator.clipboard?.write) {
                    await navigator.clipboard.write([
                        new ClipboardItem({
                            "text/html": new Blob([node.outerHTML], { type: "text/html" }),
                            "text/plain": new Blob([tsv], { type: "text/plain" }),
                        }),
                    ]);
                } else {
                    await navigator.clipboard.writeText(tsv);   // Firefox: no ClipboardItem
                }
            } else {
                await navigator.clipboard.writeText(node.innerText.replace(/\n$/, ""));
            }
            btn.classList.add("is-done");
            btn.innerHTML = `${DONE_ICON}<span>Copied</span>`;
            setTimeout(() => {
                btn.classList.remove("is-done");
                btn.innerHTML = `${COPY_ICON}<span>Copy</span>`;
            }, 1600);
        } catch (e) {
            console.warn("AI Assistant: copy failed", e);
        }
    }

    useStarter(text) {
        this.state.inputValue = text;
        this.sendMessage();
    }

    async toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (!this.state.isOpen) this.state.settingsOpen = false;
        if (this.state.isOpen && !this.state.sessionId) {
            await this.startNewChat();
        }
    }

    closeChat() {
        this.state.isOpen = false;
        this.state.settingsOpen = false;
        this.state.historyOpen = false;
    }

    toggleMaximize() {
        this.state.maximized = !this.state.maximized;
        this._savePrefs();
    }

    async startNewChat() {
        try {
            const sessionId = await this.orm.create("ai.chat.session", [{}]);
            this.state.sessionId = sessionId[0];
            // No canned greeting — the template's empty state explains what this can do,
            // which is more useful than a wave and costs no round-trip.
            this.state.messages = [];
            this.state.error = null;
            this.state.settingsOpen = false;
            this.state.historyOpen = false;
        } catch (e) {
            console.error("AI Assistant: failed to create session", e);
        }
    }

    async sendMessage() {
        if (!this.state.inputValue.trim() || this.state.isLoading) return;

        const userMessage = this.state.inputValue;
        this.state.messages.push(this._toMessage("user", userMessage));
        this.state.inputValue = "";
        this.state.isLoading = true;
        this.state.error = null;

        try {
            const response = await this.orm.call("ai.chatbot.agent", "process_message", [
                this.state.sessionId,
                userMessage,
            ]);
            if (response?.session_id) {
                this.state.sessionId = response.session_id;
            }
            this.state.messages.push(this._toMessage("assistant", response.response));
        } catch (error) {
            console.error("AI Assistant error:", error);
            // Surfaced as a dedicated error row rather than a fake assistant reply — an error is
            // not something the assistant said.
            this.state.error = "That request didn't go through. Try again, or rephrase it.";
        } finally {
            this.state.isLoading = false;
        }
    }

    onInputKeydown(ev) {
        // "Enter to send" is a user setting. When off, Enter inserts a newline and only
        // Ctrl/Cmd+Enter sends — the convention users expect from that mode.
        const enterSends = this.state.enterToSend
            ? !ev.shiftKey
            : (ev.ctrlKey || ev.metaKey);
        if (ev.key === "Enter" && enterSends) {
            ev.preventDefault();
            this.sendMessage();
        }
        // grow the composer with the text, up to the CSS max-height
        const ta = ev.target;
        requestAnimationFrame(() => {
            ta.style.height = "auto";
            ta.style.height = `${Math.min(ta.scrollHeight, 132)}px`;
        });
    }
}

AIChatbot.template = "odoo_ai_chatbot.SystrayItem";

export const systrayItem = { Component: AIChatbot };

registry.category("systray").add("odoo_ai_chatbot.AIChatbot", systrayItem, { sequence: 100 });
