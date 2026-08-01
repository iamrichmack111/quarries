from __future__ import annotations

import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.events import Key, MouseDown, MouseMove, MouseUp
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from .cipher import ALPHABET_VERSION, encode_exact, group_345_rtl, normal_hebrew_view
from .clipboard import ClipboardError, copy_text
from .crypto import (
    decrypt_json,
    decrypt_text,
    derive_key,
    encrypt_json,
    encrypt_text,
    make_verifier,
    password_matches,
)
from .ollama_client import chat as ollama_chat, embed as ollama_embed
from .storage import Store
from .watcher import render_watcher

AUTO_LOCK_SECONDS = 15 * 60
MAX_RAG_CHUNKS = 5
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else -1.0


def chunk_text(text: str) -> list[str]:
    """Split a leaf into overlapping semantic chunks."""
    clean = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not clean:
        return []

    paragraphs = [p.strip() for p in clean.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
        if len(candidate) <= CHUNK_SIZE:
            buffer = candidate
            continue

        if buffer:
            chunks.append(buffer)
            overlap = buffer[-CHUNK_OVERLAP:]
            buffer = f"{overlap}\n\n{paragraph}"
        else:
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + CHUNK_SIZE)
                chunks.append(paragraph[start:end])
                if end == len(paragraph):
                    break
                start = max(start + 1, end - CHUNK_OVERLAP)
            buffer = ""

    if buffer:
        chunks.append(buffer)

    return chunks


class PasswordModal(ModalScreen[str | None]):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.title_text = title
        self.subtitle = subtitle

    def compose(self) -> ComposeResult:
        with Container(id="modal-box"):
            yield Static(self.title_text, classes="modal-title")
            if self.subtitle:
                yield Static(self.subtitle, classes="muted")
            yield Input(password=True, placeholder="Password", id="modal-password")
            with Horizontal(classes="button-row"):
                yield Button("Unlock", variant="primary", id="modal-unlock")
                yield Button("Cancel", id="modal-cancel")

    def on_mount(self) -> None:
        self.query_one("#modal-password", Input).focus()

    @on(Button.Pressed, "#modal-unlock")
    @on(Input.Submitted, "#modal-password")
    def unlock(self) -> None:
        self.dismiss(self.query_one("#modal-password", Input).value)

    @on(Button.Pressed, "#modal-cancel")
    def cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self.title_text = title
        self.body = body

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Static(self.title_text, classes="modal-title")
            yield Static(self.body, classes="muted")
            with Horizontal(classes="button-row"):
                yield Button("Confirm", variant="error", id="confirm-yes")
                yield Button("Cancel", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def no(self) -> None:
        self.dismiss(False)


class SetupScreen(Screen):
    def compose(self) -> ComposeResult:
        with Container(id="gate-box"):
            with Horizontal(id="gate-heading"):
                with Vertical():
                    yield Static("Q U A R R I E S", id="gate-brand")
                    yield Static("Create three independent keys.", classes="muted")
                yield Static(render_watcher("open"), id="corner-eyes")
            with Grid(id="setup-grid"):
                yield Label("Application password")
                yield Input(password=True, id="app1")
                yield Label("Confirm application password")
                yield Input(password=True, id="app2")
                yield Label("Archive password")
                yield Input(password=True, id="archive1")
                yield Label("Confirm Archive password")
                yield Input(password=True, id="archive2")
                yield Label("Watcher password")
                yield Input(password=True, id="chat1")
                yield Label("Confirm Watcher password")
                yield Input(password=True, id="chat2")
            yield Button("Prepare the Archive", variant="primary", id="setup-submit")
            yield Static("", id="setup-error", classes="error")

    @on(Button.Pressed, "#setup-submit")
    def submit(self) -> None:
        pairs = [
            ("app", self.query_one("#app1", Input).value, self.query_one("#app2", Input).value),
            ("archive", self.query_one("#archive1", Input).value, self.query_one("#archive2", Input).value),
            ("chat", self.query_one("#chat1", Input).value, self.query_one("#chat2", Input).value),
        ]
        error = self.query_one("#setup-error", Static)
        for role, first, second in pairs:
            if len(first) < 8:
                error.update(f"{role.title()} password must contain at least 8 characters.")
                return
            if first != second:
                error.update(f"{role.title()} passwords do not match.")
                return
        for role, password, _ in pairs:
            salt = os.urandom(16)
            key = derive_key(password, salt)
            self.app.store.set_password(role, salt, make_verifier(key))
        self.app.app_key = self.app.authenticate("app", pairs[0][1])
        self.app.switch_to_main()


class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        with Container(id="gate-box"):
            with Horizontal(id="gate-heading"):
                with Vertical():
                    yield Static("Q U A R R I E S", id="gate-brand")
                    yield Static("The Archive remembers. The Watcher listens.", classes="muted")
                yield Static(render_watcher("locked"), id="corner-eyes")
            yield Input(password=True, placeholder="Application password", id="app-password")
            yield Button("Enter the Gate", variant="primary", id="login-button")
            yield Static("", id="login-error", classes="error")

    def on_mount(self) -> None:
        self.query_one("#app-password", Input).focus()

    @on(Button.Pressed, "#login-button")
    @on(Input.Submitted, "#app-password")
    def login(self) -> None:
        key = self.app.authenticate("app", self.query_one("#app-password", Input).value)
        if key is None:
            self.query_one("#login-error", Static).update("The Gate remains sealed.")
            self.query_one("#corner-eyes", Static).update(render_watcher("error"))
            return
        self.app.app_key = key
        self.app.switch_to_main()


class MainScreen(Screen):
    BINDINGS = [
        ("ctrl+l", "seal", "Seal everything"),
        ("ctrl+n", "new_leaf", "New Leaf"),
        ("ctrl+s", "save_leaf", "Preserve Leaf"),
        ("f6", "copy_hebrew", "Copy Hebrew"),
        ("f7", "copy_grouped_hebrew", "Copy 3-4-5"),
        ("ctrl+q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-strip"):
            yield Static("Q U A R R I E S", id="main-brand")
            yield Static("Archive LOCKED   Watcher LOCKED", id="global-status")
            yield Static(render_watcher("locked"), id="corner-eyes-main")
        with TabbedContent(initial="archive-tab"):
            with TabPane("The Archive", id="archive-tab"):
                yield ArchivePane()
            with TabPane("The Watcher", id="watcher-tab"):
                yield WatcherPane()
            with TabPane("The Vault", id="vault-tab"):
                yield VaultPane()
        yield Footer()

    def action_seal(self) -> None:
        self.app.return_to_gate("The Archive has been sealed.")

    def action_new_leaf(self) -> None:
        self.query_one(ArchivePane).new_leaf()

    def action_save_leaf(self) -> None:
        self.query_one(ArchivePane).preserve()

    def action_copy_hebrew(self) -> None:
        pane = self.query_one(ArchivePane)
        pane.copy_normal_hebrew()

    def action_copy_grouped_hebrew(self) -> None:
        pane = self.query_one(ArchivePane)
        pane.copy_grouped_hebrew()

    def action_quit_app(self) -> None:
        self.app.exit()

    def refresh_global_status(self) -> None:
        archive = "OPEN" if self.app.archive_key else "LOCKED"
        watcher = "OPEN" if self.app.chat_key else "LOCKED"
        self.query_one("#global-status", Static).update(
            f"Archive {archive}   Watcher {watcher}"
        )
        state = "open" if self.app.archive_key or self.app.chat_key else "locked"
        self.query_one("#corner-eyes-main", Static).update(render_watcher(state))


class ArchivePane(Static):
    def __init__(self) -> None:
        super().__init__()
        self.current_id: int | None = None
        self.search_term = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="archive-root"):
            with Horizontal(id="archive-toolbar"):
                yield Button("Unlock Archive", id="archive-unlock", variant="primary")
                yield Button("New", id="new-leaf", disabled=True)
                yield Button("Preserve", id="preserve", variant="primary", disabled=True)
                yield Button("Delete", id="delete-leaf", disabled=True)
                yield Button("Ask Watcher", id="send-current", disabled=True)
                yield Button("Re-index", id="reembed", disabled=True)
                yield Button("Copy Hebrew", id="copy-hebrew", disabled=True)
                yield Button("Copy 3-4-5", id="copy-grouped", disabled=True)
                yield Static("The Archive remains sealed.", id="archive-status")
            with Grid(id="archive-grid"):
                with Vertical(id="leaves-pane", classes="pane"):
                    yield Static("LEAVES", classes="pane-title")
                    yield Input(placeholder="Seek leaves...", id="leaf-search", disabled=True)
                    yield ListView(id="leaf-list")
                with Vertical(id="english-pane", classes="pane"):
                    yield Static("ENGLISH SOURCE", classes="pane-title")
                    yield Input(placeholder="Leaf title", id="leaf-title", disabled=True)
                    yield TextArea(id="english-editor", disabled=True)
                with Vertical(id="encoded-pane", classes="pane"):
                    yield Static("HEBREW LETTER SUBSTITUTION", classes="pane-title")
                    yield Static("", id="normal-hebrew-preview", classes="normal-hebrew-preview")
                    yield Static("RTL 3-4-5", classes="pane-title secondary-title")
                    yield Static("", id="encoded-preview", classes="encoded-preview")
                    yield Static(
                        f"Alphabet v{ALPHABET_VERSION}. Exact English remains encrypted.",
                        classes="muted-small",
                    )

    @on(Button.Pressed, "#archive-unlock")
    def unlock_archive(self) -> None:
        self.app.push_screen(
            PasswordModal("Open the Archive", "Archive authentication is separate."),
            self._unlock_result,
        )

    def _unlock_result(self, password: str | None) -> None:
        if not password:
            return
        key = self.app.authenticate("archive", password)
        if key is None:
            self.query_one("#archive-status", Static).update("The Archive remains sealed.")
            return
        self.app.archive_key = key
        self.query_one("#archive-status", Static).update("The Archive is open.")
        for selector in (
            "#new-leaf",
            "#preserve",
            "#delete-leaf",
            "#send-current",
            "#reembed",
            "#copy-hebrew",
            "#copy-grouped",
        ):
            self.query_one(selector, Button).disabled = False
        for selector in ("#leaf-title", "#leaf-search"):
            self.query_one(selector, Input).disabled = False
        self.query_one("#english-editor", TextArea).disabled = False
        self.query_one("#archive-unlock", Button).label = "Archive Open"
        self.refresh_entries()
        self.app.screen.refresh_global_status()

    @on(Input.Changed, "#leaf-search")
    def search_changed(self, event: Input.Changed) -> None:
        self.search_term = event.value.strip().lower()
        self.refresh_entries()

    def refresh_entries(self) -> None:
        if self.app.archive_key is None:
            return
        listing = self.query_one("#leaf-list", ListView)
        listing.clear()
        for row in self.app.store.list_entries():
            try:
                title = decrypt_text(self.app.archive_key, row["title"], b"journal-title")
                english = decrypt_text(
                    self.app.archive_key, row["english"], b"journal-english"
                )
            except Exception:
                continue
            haystack = f"{title}\n{english}".lower()
            if self.search_term and self.search_term not in haystack:
                continue
            preview = " ".join(english.split())[:42]
            item = ListItem(
                Label(f"{row['updated_at'][:10]}\n{title}\n[dim]{preview}[/]")
            )
            item.entry_id = row["id"]
            listing.append(item)

    @on(Button.Pressed, "#new-leaf")
    def new_leaf(self) -> None:
        if self.app.archive_key is None:
            return
        self.current_id = None
        self.query_one("#leaf-title", Input).value = ""
        self.query_one("#english-editor", TextArea).text = ""
        self.query_one("#normal-hebrew-preview", Static).update("")
        self.query_one("#encoded-preview", Static).update("")
        self.query_one("#english-editor", TextArea).focus()

    @on(TextArea.Changed, "#english-editor")
    def live_encode(self) -> None:
        text = self.query_one("#english-editor", TextArea).text
        self.query_one("#normal-hebrew-preview", Static).update(normal_hebrew_view(text))
        self.query_one("#encoded-preview", Static).update(
            group_345_rtl(encode_exact(text))
        )

    @on(Button.Pressed, "#preserve")
    def preserve(self) -> None:
        if self.app.archive_key is None:
            return
        title = self.query_one("#leaf-title", Input).value.strip() or "Untitled Leaf"
        english = self.query_one("#english-editor", TextArea).text
        if not english.strip():
            self.query_one("#archive-status", Static).update("Nothing was preserved.")
            return
        self.preserve_worker(title, english)

    @work(exclusive=True)
    async def preserve_worker(self, title: str, english: str) -> None:
        key = self.app.archive_key
        status = self.query_one("#archive-status", Static)
        eyes = self.app.screen.query_one("#corner-eyes-main", Static)
        eyes.update(render_watcher("working"))
        status.update("Encrypting and indexing...")

        encoded = encode_exact(english)
        grouped = group_345_rtl(encoded)
        now = now_iso()

        title_blob = encrypt_text(key, title, b"journal-title")
        english_blob = encrypt_text(key, english, b"journal-english")
        encoded_blob = encrypt_text(key, encoded, b"journal-encoded")
        grouped_blob = encrypt_text(key, grouped, b"journal-grouped")

        if self.current_id is None:
            self.current_id = self.app.store.add_entry(
                now,
                title_blob,
                english_blob,
                encoded_blob,
                grouped_blob,
                None,
                ALPHABET_VERSION,
            )
        else:
            self.app.store.update_entry(
                self.current_id,
                now,
                title_blob,
                english_blob,
                encoded_blob,
                grouped_blob,
                None,
                ALPHABET_VERSION,
            )

        indexed = await self._index_entry(self.current_id, english)
        status.update(
            "The Archive remembers. "
            + (f"Indexed {indexed} chunks." if indexed else "Saved without embeddings.")
        )
        self.refresh_entries()
        eyes.update(render_watcher("open"))

    async def _index_entry(self, entry_id: int, english: str) -> int:
        key = self.app.archive_key
        encrypted_chunks = []
        for index, chunk in enumerate(chunk_text(english)):
            try:
                vector = await ollama_embed(chunk)
            except Exception:
                return 0
            encrypted_chunks.append(
                (
                    index,
                    encrypt_text(key, chunk, b"rag-chunk-content"),
                    encrypt_json(key, vector, b"rag-chunk-vector"),
                )
            )
        if encrypted_chunks:
            self.app.store.replace_embedding_chunks(
                entry_id, encrypted_chunks, now_iso()
            )
        return len(encrypted_chunks)

    @on(Button.Pressed, "#reembed")
    def reembed(self) -> None:
        if self.app.archive_key is not None:
            self.reembed_worker()

    @work(exclusive=True)
    async def reembed_worker(self) -> None:
        status = self.query_one("#archive-status", Static)
        rows = self.app.store.entries_without_chunks()
        if not rows:
            status.update("Every Leaf is already indexed.")
            return
        completed = 0
        for row in rows:
            try:
                english = decrypt_text(
                    self.app.archive_key, row["english"], b"journal-english"
                )
                count = await self._index_entry(row["id"], english)
                if count:
                    completed += 1
                status.update(f"Re-indexing Archive: {completed}/{len(rows)}")
            except Exception:
                continue
        status.update(f"Re-index complete. Indexed {completed} Leaves.")

    @on(ListView.Selected, "#leaf-list")
    def select_leaf(self, event: ListView.Selected) -> None:
        if self.app.archive_key is None:
            return
        entry_id = getattr(event.item, "entry_id", None)
        row = self.app.store.get_entry(entry_id)
        if row is None:
            return
        key = self.app.archive_key
        self.current_id = entry_id
        title = decrypt_text(key, row["title"], b"journal-title")
        english = decrypt_text(key, row["english"], b"journal-english")
        self.query_one("#leaf-title", Input).value = title
        self.query_one("#english-editor", TextArea).text = english
        self.query_one("#normal-hebrew-preview", Static).update(
            normal_hebrew_view(english)
        )
        self.query_one("#encoded-preview", Static).update(
            group_345_rtl(encode_exact(english))
        )

    @on(Button.Pressed, "#delete-leaf")
    def delete_leaf(self) -> None:
        if self.current_id is None:
            self.query_one("#archive-status", Static).update("Select a Leaf first.")
            return
        self.app.push_screen(
            ConfirmModal(
                "Burn this Leaf?",
                "This removes the encrypted entry and its embedding chunks. It cannot be restored.",
            ),
            self._delete_result,
        )

    def _delete_result(self, confirmed: bool) -> None:
        if not confirmed or self.current_id is None:
            return
        self.app.store.delete_entry(self.current_id)
        self.current_id = None
        self.new_leaf()
        self.refresh_entries()
        self.query_one("#archive-status", Static).update("The Leaf has been burned.")

    @on(Button.Pressed, "#send-current")
    def send_current_to_watcher(self) -> None:
        if self.app.archive_key is None:
            return
        english = self.query_one("#english-editor", TextArea).text.strip()
        if not english:
            return
        watcher = self.app.screen.query_one(WatcherPane)
        watcher.pending_context = english
        self.query_one("#archive-status", Static).update(
            "Current Leaf is staged at the Memory Gate."
        )


    @on(Button.Pressed, "#copy-hebrew")
    def copy_normal_hebrew(self) -> None:
        if self.app.archive_key is None:
            self.query_one("#archive-status", Static).update("Open the Archive first.")
            return

        english = self.query_one("#english-editor", TextArea).text
        value = encode_exact(english)

        if not value:
            self.query_one("#archive-status", Static).update(
                "There is no Hebrew substitution to copy."
            )
            return

        try:
            copy_text(value)
            self.query_one("#archive-status", Static).update(
                "Hebrew substitution copied. Shortcut: F6"
            )
        except ClipboardError as exc:
            self.query_one("#archive-status", Static).update(str(exc))

    @on(Button.Pressed, "#copy-grouped")
    def copy_grouped_hebrew(self) -> None:
        if self.app.archive_key is None:
            self.query_one("#archive-status", Static).update("Open the Archive first.")
            return

        english = self.query_one("#english-editor", TextArea).text
        value = group_345_rtl(encode_exact(english)).lstrip("\u200f")

        if not value:
            self.query_one("#archive-status", Static).update(
                "There is no RTL 3-4-5 Hebrew to copy."
            )
            return

        try:
            copy_text(value)
            self.query_one("#archive-status", Static).update(
                "RTL 3-4-5 Hebrew copied. Shortcut: F7"
            )
        except ClipboardError as exc:
            self.query_one("#archive-status", Static).update(str(exc))


class WatcherPane(Static):
    def __init__(self) -> None:
        super().__init__()
        self.session_id: int | None = None
        self.messages: list[dict[str, str]] = []
        self.pending_context = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="watcher-root"):
            with Horizontal(id="watcher-toolbar"):
                yield Button("Unlock Watcher", id="watcher-unlock", variant="primary")
                yield Button("New Chat", id="new-chat", disabled=True)
                yield Button("Delete Chat", id="delete-chat", disabled=True)
                yield Select(
                    [
                        ("Empty Mind", "empty"),
                        ("Current Leaf", "current"),
                        ("Similar Leaves", "similar"),
                        ("Current + Similar", "current_similar"),
                    ],
                    value="empty",
                    id="memory-mode",
                    disabled=True,
                )
                yield Static("The Watcher remains silent.", id="watcher-status")
            with Horizontal(id="watcher-layout"):
                with Vertical(id="sessions-pane"):
                    yield Static("CONVERSATIONS", classes="pane-title")
                    yield ListView(id="session-list")
                with Vertical(id="conversation-pane"):
                    yield VerticalScroll(id="chat-history")
                    with Horizontal(id="chat-compose"):
                        yield TextArea(id="chat-input", disabled=True)
                        yield Button(
                            "Speak",
                            id="chat-send",
                            variant="primary",
                            disabled=True,
                        )

    @on(Button.Pressed, "#watcher-unlock")
    def unlock_watcher(self) -> None:
        self.app.push_screen(
            PasswordModal("Awaken The Watcher", "Watcher authentication is separate."),
            self._unlock_result,
        )

    def _unlock_result(self, password: str | None) -> None:
        if not password:
            return
        key = self.app.authenticate("chat", password)
        if key is None:
            self.query_one("#watcher-status", Static).update(
                "The Watcher remains silent."
            )
            return
        self.app.chat_key = key
        self.query_one("#watcher-status", Static).update("The Watcher is listening.")
        self.query_one("#chat-input", TextArea).disabled = False
        self.query_one("#chat-send", Button).disabled = False
        self.query_one("#memory-mode", Select).disabled = False
        self.query_one("#new-chat", Button).disabled = False
        self.query_one("#delete-chat", Button).disabled = False
        self.query_one("#watcher-unlock", Button).label = "Watcher Open"
        self.refresh_sessions()
        if self.session_id is None:
            sessions = self.app.store.list_chat_sessions()
            if sessions:
                self.load_session(sessions[0]["id"])
            else:
                self.new_chat()
        self.app.screen.refresh_global_status()

    def refresh_sessions(self) -> None:
        if self.app.chat_key is None:
            return
        listing = self.query_one("#session-list", ListView)
        listing.clear()
        for row in self.app.store.list_chat_sessions():
            try:
                title = decrypt_text(
                    self.app.chat_key, row["title"], b"chat-title"
                )
            except Exception:
                title = "Unreadable Conversation"
            item = ListItem(Label(f"{title}\n[dim]{row['updated_at'][:16]}[/]"))
            item.session_id = row["id"]
            listing.append(item)

    @on(ListView.Selected, "#session-list")
    def session_selected(self, event: ListView.Selected) -> None:
        session_id = getattr(event.item, "session_id", None)
        if session_id is not None:
            self.load_session(session_id)

    @on(Button.Pressed, "#new-chat")
    def new_chat(self) -> None:
        if self.app.chat_key is None:
            return
        now = now_iso()
        self.session_id = self.app.store.add_chat_session(
            now, encrypt_text(self.app.chat_key, "New Conversation", b"chat-title")
        )
        self.messages = []
        self.clear_history()
        self._append("The Watcher", "What shall we examine today?")
        self.refresh_sessions()
        self.query_one("#chat-input", TextArea).focus()

    def load_session(self, session_id: int) -> None:
        if self.app.chat_key is None:
            return
        self.session_id = session_id
        self.messages = []
        self.clear_history()
        rows = self.app.store.list_chat_messages(session_id)
        if not rows:
            self._append("The Watcher", "What shall we examine today?")
        for row in rows:
            try:
                content = decrypt_text(
                    self.app.chat_key, row["content"], b"chat-message"
                )
            except Exception:
                continue
            self.messages.append({"role": row["role"], "content": content})
            self._append("You" if row["role"] == "user" else "The Watcher", content)

    def clear_history(self) -> None:
        history = self.query_one("#chat-history", VerticalScroll)
        for child in list(history.children):
            child.remove()

    def _append(self, speaker: str, text: str) -> None:
        history = self.query_one("#chat-history", VerticalScroll)
        history.mount(
            Markdown(f"**{speaker}**\n\n{text}", classes="chat-message")
        )
        history.call_after_refresh(history.scroll_end, animate=False)

    @on(Button.Pressed, "#delete-chat")
    def delete_chat(self) -> None:
        if self.session_id is None:
            return
        self.app.push_screen(
            ConfirmModal(
                "Delete this conversation?",
                "The encrypted chat and all of its messages will be permanently removed.",
            ),
            self._delete_chat_result,
        )

    def _delete_chat_result(self, confirmed: bool) -> None:
        if not confirmed or self.session_id is None:
            return
        self.app.store.delete_chat_session(self.session_id)
        self.session_id = None
        self.messages = []
        self.clear_history()
        self.refresh_sessions()
        sessions = self.app.store.list_chat_sessions()
        if sessions:
            self.load_session(sessions[0]["id"])
        else:
            self.new_chat()

    @on(Button.Pressed, "#chat-send")
    def send(self) -> None:
        if self.app.chat_key is None or self.session_id is None:
            return
        area = self.query_one("#chat-input", TextArea)
        question = area.text.strip()
        if not question:
            return
        area.text = ""
        self._append("You", question)
        self.messages.append({"role": "user", "content": question})
        now = now_iso()
        self.app.store.add_chat_message(
            self.session_id,
            "user",
            encrypt_text(self.app.chat_key, question, b"chat-message"),
            now,
        )

        # Automatically title a new chat from the first question.
        if len([m for m in self.messages if m["role"] == "user"]) == 1:
            title = " ".join(question.split())[:48] or "New Conversation"
            self.app.store.rename_chat_session(
                self.session_id,
                encrypt_text(self.app.chat_key, title, b"chat-title"),
                now,
            )
            self.refresh_sessions()

        self.send_worker(question)

    async def _memory_context(self, question: str) -> tuple[str, str]:
        mode = self.query_one("#memory-mode", Select).value or "empty"
        if mode == "empty":
            return "", "Empty Mind"

        parts: list[str] = []
        labels: list[str] = []

        if mode in ("current", "current_similar") and self.pending_context:
            parts.append("CURRENT LEAF:\n" + self.pending_context)
            labels.append("Current Leaf")

        if mode in ("similar", "current_similar"):
            if self.app.archive_key is None:
                labels.append("Similar unavailable: Archive locked")
            else:
                try:
                    query_vector = await ollama_embed(question)
                    scored = []
                    for row in self.app.store.list_embedding_chunks():
                        try:
                            vector = decrypt_json(
                                self.app.archive_key,
                                row["embedding"],
                                b"rag-chunk-vector",
                            )
                            score = cosine(query_vector, vector)
                            scored.append((score, row))
                        except Exception:
                            continue

                    scored.sort(key=lambda pair: pair[0], reverse=True)
                    used_entries: set[int] = set()
                    selected_count = 0

                    for score, row in scored:
                        if selected_count >= MAX_RAG_CHUNKS:
                            break
                        try:
                            content = decrypt_text(
                                self.app.archive_key,
                                row["content"],
                                b"rag-chunk-content",
                            )
                            title = decrypt_text(
                                self.app.archive_key,
                                row["title"],
                                b"journal-title",
                            )
                        except Exception:
                            continue

                        parts.append(
                            f"RETRIEVED LEAF: {title}\n"
                            f"Similarity: {score:.3f}\n{content}"
                        )
                        used_entries.add(row["entry_id"])
                        selected_count += 1

                    labels.append(
                        f"RAG: {selected_count} chunks / {len(used_entries)} Leaves"
                    )
                except Exception:
                    labels.append("RAG unavailable")

        return "\n\n---\n\n".join(parts), " + ".join(labels) or "Empty Mind"

    @work(exclusive=True)
    async def send_worker(self, question: str) -> None:
        status = self.query_one("#watcher-status", Static)
        eyes = self.app.screen.query_one("#corner-eyes-main", Static)
        eyes.update(render_watcher("thinking"))
        status.update("The Watcher is considering...")

        context, label = await self._memory_context(question)
        try:
            reply = await ollama_chat(self.messages[-24:], context=context)
        except Exception:
            reply = (
                "The local model could not be reached. Confirm that Ollama is running "
                "and that huihui_ai/qwen3.5-abliterated:4b is installed."
            )

        self.messages.append({"role": "assistant", "content": reply})
        self._append("The Watcher", reply)
        self.app.store.add_chat_message(
            self.session_id,
            "assistant",
            encrypt_text(self.app.chat_key, reply, b"chat-message"),
            now_iso(),
        )
        status.update(f"The Watcher is listening. Context: {label}")
        eyes.update(render_watcher("open"))
        self.refresh_sessions()


class VaultPane(Static):
    def compose(self) -> ComposeResult:
        with Container(id="vault-box"):
            yield Static("PASSWORD-ENCRYPTED ARCHIVE EXPORT", classes="pane-title")
            yield Input(password=True, placeholder="Export password", id="export-password")
            yield Input(password=True, placeholder="Confirm export password", id="export-confirm")
            yield Button("Seal Export", variant="primary", id="export-button")
            yield Static("", id="export-status")

    @on(Button.Pressed, "#export-button")
    def export(self) -> None:
        if self.app.archive_key is None:
            self.query_one("#export-status", Static).update("Open the Archive first.")
            return

        password = self.query_one("#export-password", Input).value
        confirm = self.query_one("#export-confirm", Input).value
        if len(password) < 8 or password != confirm:
            self.query_one("#export-status", Static).update(
                "Passwords must match and contain at least 8 characters."
            )
            return

        rows = []
        for row in self.app.store.list_entries():
            key = self.app.archive_key
            rows.append(
                {
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "title": decrypt_text(key, row["title"], b"journal-title"),
                    "english": decrypt_text(key, row["english"], b"journal-english"),
                    "encoded": (
                        decrypt_text(key, row["hebrew"], b"journal-encoded")
                        if row["hebrew"]
                        else encode_exact(
                            decrypt_text(key, row["english"], b"journal-english")
                        )
                    ),
                    "alphabet_version": row["alphabet_version"] or "legacy",
                }
            )

        salt = os.urandom(16)
        export_key = derive_key(password, salt)
        payload = encrypt_json(
            export_key,
            {"version": 4, "entries": rows},
            b"quarries-export",
        )
        destination = (
            Path.home()
            / "Downloads"
            / f"quarries-{datetime.now():%Y%m%d-%H%M%S}.qryx"
        )
        destination.write_bytes(b"QRYX4" + salt + payload)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass

        self.query_one("#export-status", Static).update(
            f"The Vault has been sealed:\n{destination}"
        )


class QuarriesApp(App):
    CSS_PATH = "styles.tcss"
    TITLE = "Quarries"
    SUB_TITLE = "The Archive remembers. The Watcher listens."

    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.app_key: bytes | None = None
        self.archive_key: bytes | None = None
        self.chat_key: bytes | None = None
        self.last_activity = time.monotonic()

    def on_mount(self) -> None:
        self.set_interval(10, self._check_auto_lock)
        self.push_screen(LoginScreen() if self.store.initialized() else SetupScreen())

    async def on_event(self, event) -> None:
        if isinstance(event, (Key, MouseDown, MouseMove, MouseUp)):
            self.last_activity = time.monotonic()
        await super().on_event(event)

    def _check_auto_lock(self) -> None:
        if self.app_key is None:
            return
        if time.monotonic() - self.last_activity >= AUTO_LOCK_SECONDS:
            self.return_to_gate("No movement detected. The Archive has been sealed.")

    def switch_to_main(self) -> None:
        self.last_activity = time.monotonic()
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(MainScreen())

    def return_to_gate(self, message: str = "") -> None:
        self.seal_all()
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(LoginScreen())
        if message:
            try:
                self.screen.query_one("#login-error", Static).update(message)
            except Exception:
                pass

    def authenticate(self, role: str, password: str) -> bytes | None:
        record = self.store.auth_record(role)
        if record is None:
            return None
        try:
            key = derive_key(password, record["salt"])
            return key if password_matches(key, record["verifier"]) else None
        except Exception:
            return None

    def seal_all(self) -> None:
        self.archive_key = None
        self.chat_key = None
        self.app_key = None

    def on_unmount(self) -> None:
        self.seal_all()
        self.store.close()


def main() -> None:
    QuarriesApp().run()


if __name__ == "__main__":
    main()
