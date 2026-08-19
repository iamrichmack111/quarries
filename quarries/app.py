from __future__ import annotations

import base64
import csv
import math
import os
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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
    decrypt_bytes,
    decrypt_json,
    decrypt_text,
    derive_key,
    encrypt_bytes,
    encrypt_json,
    encrypt_text,
    make_verifier,
    password_matches,
)
from .ollama_client import (
    EMBED_INDEX_VERSION,
    EMBED_MODEL,
    REFERENCE_MODEL,
    chat as ollama_chat,
    embed as ollama_embed,
)
from .hebrew_lexicon import HebrewLexicon
from .gematria import mispar_gadol, breakdown, method_results, number_explanation, factorization_text, reduction_chain
from .observatory import HOUSE_SYSTEMS, SIDEREAL_MODES, calculate_chart, format_chart
from .storage import Store
from .torahcalc_reference import TorahCalcReference
from .watcher import render_watcher

DEFAULT_AUTO_LOCK_SECONDS = 10 * 60
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
                    yield Static("Create three independent keys. The application gate, Archive, and Watcher each remain separately locked.", classes="muted")
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
        self.app.archive_key = None
        self.app.chat_key = None
        self.app.switch_to_main()


class MainScreen(Screen):
    BINDINGS = [
        ("ctrl+l", "seal", "Seal everything"),
        ("ctrl+n", "new_leaf", "New Leaf"),
        ("ctrl+s", "save_leaf", "Preserve Leaf"),
        ("f6", "copy_hebrew", "Copy Hebrew"),
        ("f7", "copy_grouped_hebrew", "Copy 3-4-5"),
        ("f8", "copy_watcher_response", "Copy Watcher"),
        ("ctrl+q", "quit_app", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-strip"):
            yield Static("Q U A R R I E S", id="main-brand")
            yield Static("Archive LOCKED   Watcher LOCKED", id="global-status")
            yield Button("Lock All", id="lock-all", variant="error")
            yield Static(render_watcher("locked"), id="corner-eyes-main")
        with TabbedContent(initial="archive-tab"):
            with TabPane("The Archive", id="archive-tab"):
                yield ArchivePane()
            with TabPane("The Watcher", id="watcher-tab"):
                yield WatcherPane()
            with TabPane("Hebrew / Strong's", id="hebrew-tab"):
                yield HebrewPane()
            with TabPane("Gematria Dictionary", id="gematria-dict-tab"):
                yield GematriaDictionaryPane()
            with TabPane("Observatory", id="observatory-tab"):
                yield ObservatoryPane()
            with TabPane("The Vault", id="vault-tab"):
                yield VaultPane()
        yield Footer()

    @on(Button.Pressed, "#lock-all")
    def lock_all_button(self) -> None:
        self.app.return_to_gate("All Quarries modules have been locked.")

    def action_seal(self) -> None:
        self.app.return_to_gate("All Quarries modules have been locked.")

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

    def action_copy_watcher_response(self) -> None:
        self.query_one(WatcherPane).copy_last_response()

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

    def on_mount(self) -> None:
        if self.app.archive_key is not None:
            self._apply_open_state()

    def _apply_open_state(self) -> None:
        self.query_one("#archive-status", Static).update("The Archive is open — unlocked by session login.")
        for selector in (
            "#new-leaf", "#preserve", "#delete-leaf", "#send-current",
            "#reembed", "#copy-hebrew", "#copy-grouped",
        ):
            self.query_one(selector, Button).disabled = False
        for selector in ("#leaf-title", "#leaf-search"):
            self.query_one(selector, Input).disabled = False
        self.query_one("#english-editor", TextArea).disabled = False
        self.query_one("#archive-unlock", Button).label = "Archive Open"
        self.query_one("#archive-unlock", Button).disabled = True
        self.refresh_entries()

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
        self._apply_open_state()
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
                entry_id,
                encrypted_chunks,
                now_iso(),
                EMBED_MODEL,
                len(vector),
                EMBED_INDEX_VERSION,
            )
        return len(encrypted_chunks)

    @on(Button.Pressed, "#reembed")
    def reembed(self) -> None:
        if self.app.archive_key is not None:
            self.reembed_worker()

    @work(exclusive=True)
    async def reembed_worker(self) -> None:
        status = self.query_one("#archive-status", Static)
        rows = self.app.store.entries_needing_index(EMBED_MODEL, EMBED_INDEX_VERSION)
        if not rows:
            status.update(f"Every Leaf is indexed with {EMBED_MODEL} v{EMBED_INDEX_VERSION}.")
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


class HebrewPane(Static):
    """Local Strong's / Hebrew Fuzzy lookup. Does not touch encrypted Leaves."""

    def __init__(self) -> None:
        super().__init__()
        self.lexicon: HebrewLexicon | None = None
        self.current_word_id: int | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="hebrew-root"):
            yield Static(
                "[b]HEBREW / STRONG'S[/b]\n"
                "Search the preserved Hebrew Fuzzy lexicon, calculate Mispar Gadol, "
                "save words to a study list, export them, and calculate Mispar Gadol locally.",
                id="hebrew-intro",
            )
            with Horizontal(id="hebrew-toolbar"):
                yield Input(
                    placeholder="Search Hebrew, H####, transliteration, pronunciation, or definition…",
                    id="hebrew-search",
                )
                yield Button("Save Word", id="hebrew-save-word")
                yield Button("Send Entry to Watcher", id="hebrew-to-watcher")
                yield Static("Local lexicon", id="hebrew-status")
            with Horizontal(id="hebrew-layout"):
                with Vertical(id="hebrew-results-pane", classes="pane"):
                    yield Static("STRONG'S RESULTS", classes="pane-title")
                    yield ListView(id="hebrew-results")
                with VerticalScroll(id="hebrew-detail-pane", classes="pane"):
                    yield Static(
                        "Select a result to see Hebrew, transliteration, your preserved gloss, "
                        "Mispar Gadol, definitions, morphology, and notes.",
                        id="hebrew-detail",
                    )
                with Vertical(id="hebrew-saved-pane", classes="pane"):
                    yield Static("SAVED HEBREW WORDS", classes="pane-title")
                    yield ListView(id="hebrew-saved-list")
                    with Horizontal(id="hebrew-saved-actions"):
                        yield Button("Remove", id="hebrew-remove-word")
                        yield Button("Export CSV", id="hebrew-export-csv")
                    yield Static(
                        "Export includes Hebrew, Strong's, transliteration, preserved gloss/definitions/notes, and Mispar Gadol.",
                        id="hebrew-list-status",
                    )
            with Horizontal(id="gematria-toolbar"):
                yield Static("MISPAR GADOL", id="gematria-title")
                yield Input(
                    placeholder="Paste or type Hebrew — calculates automatically",
                    id="gematria-input",
                )
                yield Static(
                    "Paste Hebrew to calculate. Final forms: ך500 ם600 ן700 ף800 ץ900.",
                    id="gematria-result",
                )

    def on_mount(self) -> None:
        try:
            self.lexicon = HebrewLexicon()
            stats = self.lexicon.stats()
            self.query_one("#hebrew-status", Static).update(
                f"{stats.words:,} words • {stats.verses:,} verses • local/read-only"
            )
            self._run_search("")
            self._refresh_saved_words()
        except Exception as exc:
            self.query_one("#hebrew-status", Static).update(f"Lexicon unavailable: {exc}")

    def _refresh_saved_words(self) -> None:
        if self.lexicon is None:
            return
        listing = self.query_one("#hebrew-saved-list", ListView)
        listing.clear()
        for saved in self.app.store.list_saved_hebrew_words():
            row = self.lexicon.get_word(int(saved["word_id"]))
            if row is None:
                continue
            item = ListItem(Label(
                f"{row['strong_id']}  {row['hebrew'] or row['lemma'] or '—'}\n"
                f"[dim]{row['transliteration'] or ''} • Gadol {mispar_gadol(row['hebrew'] or row['lemma'] or '')}[/]"
            ))
            item.word_id = int(saved["word_id"])
            listing.append(item)

    @on(Input.Changed, "#gematria-input")
    def calculate_gematria_live(self, event: Input.Changed) -> None:
        value = event.value.strip()
        if not value:
            self.query_one("#gematria-result", Static).update(
                "Paste Hebrew to calculate. Final forms: ך500 ם600 ן700 ף800 ץ900."
            )
            return
        total = mispar_gadol(value)
        if total <= 0:
            self.query_one("#gematria-result", Static).update("No Hebrew letters detected.")
            return
        self.query_one("#gematria-result", Static).update(
            f"[b]Mispar Gadol: {total}[/b]  •  {breakdown(value)}"
        )

    @on(Input.Submitted, "#gematria-input")
    def calculate_gematria_enter(self) -> None:
        self.calculate_gematria()

    def calculate_gematria(self) -> None:
        value = self.query_one("#gematria-input", Input).value.strip()
        if not value:
            self.query_one("#gematria-result", Static).update("Enter Hebrew text first.")
            return
        total = mispar_gadol(value)
        self.query_one("#gematria-result", Static).update(
            f"[b]Mispar Gadol: {total}[/b]\n{breakdown(value)}"
        )

    @on(Button.Pressed, "#hebrew-save-word")
    def save_current_word(self) -> None:
        if self.lexicon is None or self.current_word_id is None:
            self.query_one("#hebrew-list-status", Static).update("Select a Hebrew entry first.")
            return
        self.app.store.save_hebrew_word(self.current_word_id, now_iso())
        self._refresh_saved_words()
        row = self.lexicon.get_word(self.current_word_id)
        self.query_one("#hebrew-list-status", Static).update(
            f"Saved {row['strong_id'] if row else self.current_word_id} to your local Hebrew study list."
        )

    @on(Button.Pressed, "#hebrew-remove-word")
    def remove_saved_word(self) -> None:
        listing = self.query_one("#hebrew-saved-list", ListView)
        item = listing.highlighted_child
        word_id = getattr(item, "word_id", None) if item else None
        if word_id is None:
            self.query_one("#hebrew-list-status", Static).update("Highlight a saved word first.")
            return
        self.app.store.remove_hebrew_word(int(word_id))
        self._refresh_saved_words()
        self.query_one("#hebrew-list-status", Static).update("Removed from saved Hebrew words.")

    @on(Button.Pressed, "#hebrew-export-csv")
    def export_saved_words(self) -> None:
        if self.lexicon is None:
            return
        rows = []
        for saved in self.app.store.list_saved_hebrew_words():
            row = self.lexicon.get_word(int(saved["word_id"]))
            if row is None:
                continue
            heb = row["hebrew"] or row["lemma"] or ""
            rows.append({
                "strong_id": row["strong_id"] or "",
                "hebrew": heb,
                "lemma": row["lemma"] or "",
                "pronunciation": row["pronunciation"] or "",
                "transliteration": row["transliteration"] or "",
                "morphology": row["morphology"] or "",
                "gloss": row["gloss"] or "",
                "definitions": row["definitions"] or "",
                "notes": row["notes"] or "",
                "mispar_gadol": mispar_gadol(heb),
                "saved_at": saved["saved_at"],
            })
        if not rows:
            self.query_one("#hebrew-list-status", Static).update("There are no saved words to export.")
            return
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        out = downloads / f"quarries-hebrew-study-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        with out.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        try:
            os.chmod(out, 0o600)
        except OSError:
            pass
        self.query_one("#hebrew-list-status", Static).update(
            f"Exported {len(rows)} saved word(s) to {out}"
        )

    @on(Input.Changed, "#hebrew-search")
    def search_changed(self, event: Input.Changed) -> None:
        self._run_search(event.value)

    def _run_search(self, raw: str) -> None:
        if self.lexicon is None:
            return
        results = self.query_one("#hebrew-results", ListView)
        results.clear()
        rows = self.lexicon.search(raw)
        for row in rows:
            first = (row["definitions"] or "—").splitlines()[0]
            item = ListItem(
                Label(
                    f"{row['strong_id']}  {row['hebrew'] or row['lemma'] or '—'}\n"
                    f"[dim]{row['transliteration'] or row['pronunciation'] or ''} • {first[:58]}[/]"
                )
            )
            item.word_id = row["id"]
            results.append(item)
        if rows:
            self.current_word_id = rows[0]["id"]
            self.query_one("#hebrew-detail", Static).update(
                self.lexicon.format_word(rows[0])
            )
        elif raw.strip():
            self.query_one("#hebrew-detail", Static).update("No lexical match found.")

    @on(ListView.Selected, "#hebrew-results")
    def select_word(self, event: ListView.Selected) -> None:
        if self.lexicon is None:
            return
        word_id = getattr(event.item, "word_id", None)
        if word_id is None:
            return
        row = self.lexicon.get_word(word_id)
        self.current_word_id = word_id
        self.query_one("#hebrew-detail", Static).update(self.lexicon.format_word(row))

    @on(Button.Pressed, "#hebrew-to-watcher")
    def stage_in_watcher(self) -> None:
        if self.lexicon is None or self.current_word_id is None:
            self.query_one("#hebrew-status", Static).update("Select a Hebrew entry first.")
            return
        watcher = self.app.screen.query_one(WatcherPane)
        tabs = self.app.screen.query_one(TabbedContent)
        if self.app.chat_key is None:
            self.query_one("#hebrew-status", Static).update(
                "Watcher is locked. Unlock The Watcher first, then send this entry."
            )
            tabs.active = "watcher-tab"
            watcher.query_one("#watcher-status", Static).update(
                "Unlock Watcher, then return to Hebrew / Strong's and choose Send Entry to Watcher."
            )
            return
        row = self.lexicon.get_word(self.current_word_id)
        if row is None:
            return
        heb = row['hebrew'] or row['lemma'] or ''
        gadol = mispar_gadol(heb)
        content = (
            "BIBLICAL HEBREW LEXICAL EVIDENCE — AUTHORITATIVE SOURCE FIELDS\n"
            f"Strong's: {row['strong_id'] or '—'}\n"
            f"Hebrew: {heb or '—'}\n"
            f"Lemma: {row['lemma'] or '—'}\n"
            f"Pronunciation: {row['pronunciation'] or '—'}\n"
            f"Transliteration: {row['transliteration'] or '—'}\n"
            f"Morphology: {row['morphology'] or '—'}\n"
            f"PRESERVED CUSTOM GLOSS: {row['gloss'] or '—'}\n"
            f"MISPAR GADOL: {gadol}\n"
            f"GEMATRIA BREAKDOWN: {breakdown(heb)}\n"
            f"Preserved definitions: {row['definitions'] or '—'}\n"
            f"Preserved notes: {row['notes'] or '—'}\n\n"
            "WATCHER RULES FOR HEBREW:\n"
            "1. Always include the preserved custom gloss in the response when discussing this entry.\n"
            "2. Always include Mispar Gadol and the supplied letter-by-letter breakdown.\n"
            "3. Do not overwrite the custom gloss with a generic Strong's definition.\n"
            "4. Treat lexical glosses and gematria as study evidence, not as a guaranteed contextual translation."
        )
        title = f"Hebrew {row['strong_id'] or ''} — {heb or 'entry'}"
        preview = (
            f"Gloss: {row['gloss'] or '—'}\n"
            f"Mispar Gadol: {gadol}  •  {breakdown(heb)}"
        )
        watcher.set_reference_context(title, content, preview=preview)
        self.query_one("#hebrew-status", Static).update(
            f"{row['strong_id']} sent to Watcher. Reference Context is now active."
        )
        tabs.active = "watcher-tab"




class GematriaDictionaryPane(Static):
    """Structured number/value dictionary derived from the supplied TorahCalc PDF."""

    def __init__(self) -> None:
        super().__init__()
        self.ref: TorahCalcReference | None = None
        self.current_id: int | None = None
        self.current_value: int | None = None
        self.last_method_rows: list[dict[str, object]] = []
        self.last_hebrew_input: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="gemdict-root"):
            yield Static(
                "[b]GEMATRIA DICTIONARY[/b]  Exact value lookup + concept search + local related recommendations",
                id="gemdict-intro",
            )
            with Horizontal(id="gemdict-toolbar"):
                yield Input(
                    placeholder="Enter a number, e.g. 408",
                    id="gemdict-value",
                )
                yield Input(
                    placeholder="Search definitions/concepts, e.g. wisdom",
                    id="gemdict-text",
                )
                yield Button("Methods", id="gemdict-methods")
                yield Static("Local structured reference", id="gemdict-status")
            with Horizontal(id="gemdict-calc-toolbar"):
                yield Input(
                    placeholder="Paste/type Hebrew to calculate all supported methods",
                    id="gemdict-hebrew",
                )
                yield Button("Calculate All", id="gemdict-calc-all")
                yield Button("Export Methods CSV", id="gemdict-export-methods")
                yield Static("Hechrachi • Gadol • Siduri • Katan • Perati • Shemi • transforms…", id="gemdict-calc-status")
            with Horizontal(id="gemdict-layout"):
                with Vertical(id="gemdict-results-pane", classes="pane"):
                    yield Static("VALUE / SEARCH RESULTS", classes="pane-title")
                    yield ListView(id="gemdict-results")
                with VerticalScroll(id="gemdict-detail-pane", classes="pane"):
                    yield Static(
                        "Enter a gematria number to retrieve every definition stored under that value, "
                        "or search the source definitions by concept.",
                        id="gemdict-detail",
                    )
                with Vertical(id="gemdict-related-pane", classes="pane"):
                    yield Static("RELATED CONCEPTS", classes="pane-title")
                    yield ListView(id="gemdict-related")
                    yield Static(
                        "Recommendations use local text-similarity across the structured dictionary. "
                        "Exact-number matches remain separate and authoritative.",
                        id="gemdict-related-note",
                    )

    def on_mount(self) -> None:
        try:
            self.ref=TorahCalcReference()
            rows, values=self.ref.stats()
            self.query_one("#gemdict-status", Static).update(
                f"{rows:,} sections • {values:,} values • local/read-only"
            )
        except Exception as exc:
            self.query_one("#gemdict-status", Static).update(f"Reference unavailable: {exc}")

    def _populate(self, rows) -> None:
        listing=self.query_one("#gemdict-results", ListView)
        listing.clear()
        self.query_one("#gemdict-related", ListView).clear()
        for row in rows:
            first=" ".join(str(row["body"]).split())[:115]
            item=ListItem(Label(
                f"[b]{row['value']}[/b]  •  PDF p.{row['source_page']}\n[dim]{first}[/]"
            ))
            item.ref_id=int(row["id"])
            item.value=int(row["value"])
            listing.append(item)
        if rows:
            self._show_row(rows[0])
        else:
            self.current_id=None
            self.current_value=None
            self.query_one("#gemdict-detail", Static).update("No matching dictionary section found.")

    def _show_row(self, row) -> None:
        if self.ref is None:
            return
        self.current_id=int(row["id"])
        self.current_value=int(row["value"])
        self.query_one("#gemdict-detail", Static).update(
            number_explanation(int(row["value"])) + "\n\n" + self.ref.format_hit(row)
        )
        related=self.query_one("#gemdict-related", ListView)
        related.clear()
        for r,score in self.ref.related(self.current_id, limit=12):
            first=" ".join(str(r["body"]).split())[:72]
            item=ListItem(Label(
                f"[b]{r['value']}[/b]  {score:.2f}\n[dim]{first}[/]"
            ))
            item.ref_id=int(r["id"])
            item.value=int(r["value"])
            related.append(item)

    @on(Input.Changed, "#gemdict-value")
    def value_changed(self, event: Input.Changed) -> None:
        if self.ref is None:
            return
        raw=event.value.strip()
        if not raw:
            return
        if not raw.isdigit():
            self.query_one("#gemdict-detail", Static).update("Enter a whole-number gematria value.")
            return
        value=int(raw)
        rows=self.ref.lookup_value(value)
        self._populate(rows)
        self.query_one("#gemdict-status", Static).update(
            f"Value {value}: {len(rows)} source section(s)"
        )

    @on(Input.Submitted, "#gemdict-value")
    def value_submitted(self, event: Input.Submitted) -> None:
        self.value_changed(Input.Changed(event.input, event.value))

    @on(Input.Submitted, "#gemdict-text")
    def text_submitted(self, event: Input.Submitted) -> None:
        if self.ref is None:
            return
        q=event.value.strip()
        if not q:
            return
        rows=self.ref.search_text(q)
        self._populate(rows)
        self.query_one("#gemdict-status", Static).update(
            f"Concept search: {q!r} • {len(rows)} result(s)"
        )

    @on(ListView.Selected, "#gemdict-results")
    def select_result(self, event: ListView.Selected) -> None:
        if self.ref is None:
            return
        ref_id=getattr(event.item,"ref_id",None)
        if ref_id is None:
            return
        row=self.ref.conn.execute(
            "SELECT id,value,source_page,body FROM value_sections WHERE id=?",(int(ref_id),)
        ).fetchone()
        if row:
            self._show_row(row)

    @on(ListView.Selected, "#gemdict-related")
    def select_related(self, event: ListView.Selected) -> None:
        if self.ref is None:
            return
        ref_id=getattr(event.item,"ref_id",None)
        if ref_id is None:
            return
        row=self.ref.conn.execute(
            "SELECT id,value,source_page,body FROM value_sections WHERE id=?",(int(ref_id),)
        ).fetchone()
        if row:
            self._show_row(row)

    def _calculate_all_methods(self, text: str) -> None:
        rows=method_results(text)
        self.last_hebrew_input=text
        self.last_method_rows=rows
        if not rows:
            self.query_one("#gemdict-calc-status", Static).update("No Hebrew letters detected.")
            return
        lines=[
            f"[b]ALL GEMATRIA METHODS[/b]  Hebrew: {text}",
            "",
            "Spelling-dependent methods (Shemi / Ne'elam) use the exact letter-name spellings shown in the source chart.",
            "",
        ]
        for row in rows:
            transformed=f"  → {row['transformed']}" if row.get("transformed") else ""
            lines.append(
                f"[b]{row['method']}[/b] {row['hebrew_name']} = [b]{row['value']}[/b]{transformed}\\n"
                f"[dim]{row['rule']}[/]"
            )
        self.query_one("#gemdict-detail", Static).update("\\n\\n".join(lines))
        self.query_one("#gemdict-related", ListView).clear()
        self.query_one("#gemdict-calc-status", Static).update(
            f"{len(rows)} methods calculated • ready to export"
        )

    @on(Input.Changed, "#gemdict-hebrew")
    def gemdict_hebrew_changed(self, event: Input.Changed) -> None:
        value=event.value.strip()
        if not value:
            self.last_hebrew_input=""
            self.last_method_rows=[]
            self.query_one("#gemdict-calc-status", Static).update(
                "Paste Hebrew to calculate all supported methods."
            )
            return
        self._calculate_all_methods(value)

    @on(Button.Pressed, "#gemdict-calc-all")
    def calculate_all_methods_button(self) -> None:
        self._calculate_all_methods(self.query_one("#gemdict-hebrew", Input).value.strip())

    @on(Button.Pressed, "#gemdict-export-methods")
    def export_method_results(self) -> None:
        if not self.last_method_rows:
            self.query_one("#gemdict-calc-status", Static).update(
                "Calculate a Hebrew word or phrase before exporting."
            )
            return
        downloads=Path.home()/"Downloads"
        downloads.mkdir(parents=True,exist_ok=True)
        out=downloads/f"quarries-gematria-methods-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        with out.open("w",encoding="utf-8-sig",newline="") as fh:
            fields=["input","method","hebrew_name","value","rule","transformed"]
            writer=csv.DictWriter(fh,fieldnames=fields)
            writer.writeheader()
            for row in self.last_method_rows:
                writer.writerow({
                    "input":self.last_hebrew_input,
                    "method":row["method"],
                    "hebrew_name":row["hebrew_name"],
                    "value":row["value"],
                    "rule":row["rule"],
                    "transformed":row.get("transformed",""),
                })
        try:
            os.chmod(out,0o600)
        except OSError:
            pass
        self.query_one("#gemdict-calc-status", Static).update(
            f"Exported {len(self.last_method_rows)} method calculations to {out}"
        )

    @on(Button.Pressed, "#gemdict-methods")
    def show_methods(self) -> None:
        if self.ref is None:
            return
        lines=["[b]GEMATRIA METHODS IN THE SOURCE[/b]",""]
        for row in self.ref.methods():
            lines.append(
                f"[b]{row['name']}[/b]  {row['hebrew_name'] or ''}\n"
                f"{row['description']}  [dim](PDF p.{row['source_page']})[/]\n"
            )
        self.query_one("#gemdict-detail", Static).update("\n".join(lines))
        self.query_one("#gemdict-related", ListView).clear()

class ObservatoryPane(Static):
    """Local astronomical + zodiac workbench powered by Swiss Ephemeris."""

    def __init__(self) -> None:
        super().__init__()
        self.last_report = ""

    def compose(self) -> ComposeResult:
        now = datetime.now().astimezone()
        with Vertical(id="observatory-root"):
            yield Static(
                "[b]OBSERVATORY[/b]  Local Swiss Ephemeris chart calculator. Calculated chart data stays in Observatory.",
                id="obs-intro",
            )
            with Horizontal(id="observatory-chart-type"):
                yield Select(
                    [("Current / Event Chart", "Current"), ("Natal / Birth Chart", "Natal")],
                    value="Current", id="obs-chart-mode", allow_blank=False
                )
                yield Input(placeholder="Chart name (optional)", id="obs-chart-name")
                yield Input(placeholder="Birth date YYYY-MM-DD", id="obs-birth-date")
                yield Input(placeholder="Birth time HH:MM", id="obs-birth-time")
            yield Static(
                "Natal: use birth date/time + birth-location coordinates/timezone. Exact time affects ASC and houses.",
                id="obs-natal-help",
            )
            with Horizontal(id="observatory-toolbar"):
                yield Input(value="33.7490", placeholder="Latitude / birth latitude", id="obs-lat")
                yield Input(value="-84.3880", placeholder="Longitude / birth longitude", id="obs-lon")
                yield Input(value="America/New_York", placeholder="Timezone / birth timezone", id="obs-tz")
                yield Input(value=now.strftime("%Y-%m-%d %H:%M"), placeholder="Event YYYY-MM-DD HH:MM", id="obs-datetime")
            yield Static(
                "Coordinates = geographic location • Timezone = clock rules (e.g. America/New_York), not the city name.",
                id="obs-location-help",
            )
            with Horizontal(id="observatory-options"):
                yield Select(
                    [("Tropical","Tropical"), ("Sidereal","Sidereal")],
                    value="Tropical", id="obs-zodiac", allow_blank=False
                )
                yield Select(
                    [(name, name) for name in SIDEREAL_MODES],
                    value="Lahiri", id="obs-sidereal", allow_blank=False
                )
                yield Select(
                    [(name, name) for name in HOUSE_SYSTEMS],
                    value="Placidus", id="obs-houses", allow_blank=False
                )
                yield Button("Calculate", variant="primary", id="obs-calculate")
                yield Button("Now", id="obs-now")
                yield Static("Local Swiss Ephemeris", id="obs-status")
            yield Static(
                "Tropical/Sidereal = zodiac placement • Lahiri = sidereal ayanamsa (offset) • Placidus/Whole Sign/etc. = house division.",
                id="obs-options-help",
            )
            yield VerticalScroll(
                Static(
                    "Set location and time, choose a zodiac and house system, then Calculate.\n\n"
                    "[b]Reading the report[/b]\n"
                    "• Ascendant — zodiac degree rising on the eastern horizon.\n"
                    "• MC (Midheaven) — degree crossing the local meridian near the top of the chart.\n"
                    "• House — one of twelve chart sectors traditionally associated with areas of life.\n"
                    "• Retrograde — apparent backward motion against the background stars.\n"
                    "• Dignity — traditional classification such as domicile, exaltation, detriment or fall.\n"
                    "• Aspect — angular relationship between two bodies.\n"
                    "• Orb — distance from an exact aspect; a smaller orb is closer to exact.\n"
                    "• Applying — the bodies are moving toward exactness; separating means moving away.\n"
                    "• Moon illumination — estimated percentage of the lunar disk lit from Earth's view.",
                    id="obs-report",
                ),
                id="obs-scroll",
            )

    @on(Button.Pressed, "#obs-now")
    def use_now(self) -> None:
        tz_name=self.query_one("#obs-tz", Input).value.strip() or "UTC"
        try: now=datetime.now(ZoneInfo(tz_name))
        except Exception: now=datetime.now().astimezone()
        self.query_one("#obs-chart-mode", Select).value="Current"
        self.query_one("#obs-datetime", Input).value=now.strftime("%Y-%m-%d %H:%M")
        self.calculate()

    @on(Button.Pressed, "#obs-calculate")
    def calculate(self) -> None:
        status=self.query_one("#obs-status", Static)
        try:
            lat=float(self.query_one("#obs-lat", Input).value)
            lon=float(self.query_one("#obs-lon", Input).value)
            tz_name=self.query_one("#obs-tz", Input).value.strip()
            tz=ZoneInfo(tz_name)
            chart_mode = str(self.query_one("#obs-chart-mode", Select).value)
            if chart_mode == "Natal":
                birth_date = self.query_one("#obs-birth-date", Input).value.strip()
                birth_time = self.query_one("#obs-birth-time", Input).value.strip()
                if not birth_date or not birth_time:
                    raise ValueError("Natal chart requires birth date and birth time.")
                dt=datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            else:
                dt=datetime.strptime(self.query_one("#obs-datetime", Input).value.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            zodiac=str(self.query_one("#obs-zodiac", Select).value)
            sidereal=str(self.query_one("#obs-sidereal", Select).value)
            houses=str(self.query_one("#obs-houses", Select).value)
            chart=calculate_chart(local_dt=dt, latitude=lat, longitude=lon, timezone_name=tz_name, zodiac_mode=zodiac, sidereal_mode=sidereal, house_system=houses)
            self.last_report=format_chart(chart)
            self.query_one("#obs-report", Static).update(self.last_report)
            status.update(f"Calculated locally • {chart_mode} • {zodiac} • {houses}")
        except Exception as exc:
            status.update(f"Cannot calculate: {exc}")




class WatcherPane(Static):
    def __init__(self) -> None:
        super().__init__()
        self.session_id: int | None = None
        self.messages: list[dict[str, str]] = []
        self.pending_context = ""
        self.pending_context_title = ""

    def on_mount(self) -> None:
        if self.app.chat_key is not None:
            self._apply_open_state()

    def _apply_open_state(self) -> None:
        self.query_one("#watcher-status", Static).update("The Watcher is listening — unlocked by session login.")
        self.query_one("#chat-input", TextArea).disabled = False
        self.query_one("#chat-send", Button).disabled = False
        self.query_one("#memory-mode", Select).disabled = False
        self.query_one("#new-chat", Button).disabled = False
        self.query_one("#delete-chat", Button).disabled = False
        self.query_one("#copy-watcher-response", Button).disabled = False
        self.query_one("#watcher-unlock", Button).label = "Watcher Open"
        self.query_one("#watcher-unlock", Button).disabled = True
        if self.pending_context:
            self.query_one("#memory-mode", Select).value = "current"
            self.query_one("#watcher-clear-reference", Button).disabled = False
        self.refresh_sessions()
        if self.session_id is None:
            sessions = self.app.store.list_chat_sessions()
            if sessions:
                self.load_session(sessions[0]["id"])
            else:
                self.new_chat()

    def compose(self) -> ComposeResult:
        with Vertical(id="watcher-root"):
            with Horizontal(id="watcher-toolbar"):
                yield Button("Unlock Watcher", id="watcher-unlock", variant="primary")
                yield Button("New Chat", id="new-chat", disabled=True)
                yield Button("Delete Chat", id="delete-chat", disabled=True)
                yield Button("Copy Last Response [F8]", id="copy-watcher-response", disabled=True)
                yield Select(
                    [
                        ("Empty Mind", "empty"),
                        ("Reference Context", "current"),
                        ("Similar Leaves", "similar"),
                        ("Reference + Similar Leaves", "current_similar"),
                    ],
                    value="empty",
                    id="memory-mode",
                    disabled=True,
                )
                yield Static("The Watcher remains silent.", id="watcher-status")
            yield Static(
                "[b]REFERENCE CONTEXT[/b]\nNone attached. Send an Observatory chart or Hebrew entry here to analyze it.",
                id="watcher-reference-context",
            )
            with Horizontal(id="watcher-reference-actions"):
                yield Button("Clear Reference", id="watcher-clear-reference", disabled=True)
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

    def set_reference_context(self, title: str, content: str, preview: str = "") -> None:
        """Attach ephemeral reference material for the next Watcher questions."""
        self.pending_context_title = title
        self.pending_context = content
        card = self.query_one("#watcher-reference-context", Static)
        detail = f"\n{preview}" if preview else ""
        card.update(
            f"[b]REFERENCE CONTEXT[/b]\n✓ {title}{detail}\n"
            "This material will be included with your Watcher question while Reference Context is selected."
        )
        self.query_one("#watcher-clear-reference", Button).disabled = False
        memory = self.query_one("#memory-mode", Select)
        if not memory.disabled:
            memory.value = "current"
        self.query_one("#watcher-status", Static).update(
            f"Reference attached: {title}. Ask a question about it."
        )

    def clear_reference_context(self) -> None:
        self.pending_context = ""
        self.pending_context_title = ""
        self.query_one("#watcher-reference-context", Static).update(
            "[b]REFERENCE CONTEXT[/b]\nNone attached. Send an Observatory chart or Hebrew entry here to analyze it."
        )
        self.query_one("#watcher-clear-reference", Button).disabled = True

    @on(Button.Pressed, "#watcher-clear-reference")
    def clear_reference(self) -> None:
        self.clear_reference_context()
        self.query_one("#watcher-status", Static).update("Reference context cleared.")

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
        self._apply_open_state()
        self.app.screen.refresh_global_status()

    @on(Button.Pressed, "#copy-watcher-response")
    def copy_last_response_button(self) -> None:
        self.copy_last_response()

    def copy_last_response(self) -> None:
        if self.app.chat_key is None:
            try:
                self.query_one("#watcher-status", Static).update(
                    "Unlock Watcher before copying a response."
                )
            except Exception:
                pass
            return
        last = next(
            (m["content"] for m in reversed(self.messages) if m.get("role") == "assistant"),
            "",
        )
        if not last:
            self.query_one("#watcher-status", Static).update(
                "There is no Watcher response to copy yet."
            )
            return
        try:
            copy_text(last)
            self.query_one("#watcher-status", Static).update(
                "Last Watcher response copied to clipboard. Shortcut: F8"
            )
        except ClipboardError as exc:
            self.query_one("#watcher-status", Static).update(str(exc))

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
            title = self.pending_context_title or "Attached reference"
            parts.append(
                "REFERENCE INTERPRETATION CONTRACT\n"
                "The attached Quarries fields are immutable. Interpret them; do not recalculate or "
                "replace signs, houses, dignities, aspects, elements, modalities, polarity, glosses, "
                "or gematria from model memory. If discussing a supplied field, quote its supplied "
                "value exactly. Do not introduce a house/domain that is not present in the supplied record.\n\n"
                f"REFERENCE CONTEXT — {title}:\n" + self.pending_context
            )
            labels.append(f"Reference: {title}")

        if mode in ("similar", "current_similar"):
            if self.app.archive_key is None:
                labels.append("Similar unavailable: Archive locked")
            else:
                try:
                    query_vector = await ollama_embed(question)
                    scored = []
                    for row in self.app.store.list_embedding_chunks():
                        if (row["embedding_model"] != EMBED_MODEL or
                                row["index_version"] != EMBED_INDEX_VERSION or
                                int(row["embedding_dim"] or 0) != len(query_vector)):
                            continue
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

    def validate_reference_reply(self, reply: str) -> tuple[bool, list[str]]:
        """Catch deterministic contradictions before a reference answer is displayed."""
        if not self.pending_context:
            return True, []
        ctx = self.pending_context.lower()
        out = reply.lower()
        errors: list[str] = []

        # Dignities explicitly supplied by Quarries must not be contradicted.
        for body in ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"):
            match = re.search(
                rf"{body}[^\\n]*?(?:•|dignity[: ]+)(domicile|exaltation|detriment|fall|peregrine)",
                ctx,
            )
            if match:
                expected = match.group(1)
                segment_match = re.search(rf"{body}.{{0,180}}", out, re.S)
                if segment_match:
                    segment = segment_match.group(0)
                    for dignity in ("domicile","exaltation","detriment","fall","peregrine"):
                        if dignity != expected and dignity in segment:
                            errors.append(f"{body.title()} dignity must remain {expected.title()}.")
                            break

        # Protect especially common sign-fact hallucinations.
        if "aries = fire / cardinal / yang" in ctx and re.search(r"aries.{0,50}earth", out, re.S):
            errors.append("Aries must remain Fire/Cardinal/Yang.")

        # Preserve Hebrew fields when Hebrew reference material is attached.
        if "preserved custom gloss:" in ctx and "mispar gadol:" in ctx:
            gloss_match = re.search(r"preserved custom gloss:\s*([^\\n]+)", self.pending_context, re.I)
            gadol_match = re.search(r"mispar gadol:\s*([^\\n]+)", self.pending_context, re.I)
            if gloss_match and gloss_match.group(1).strip() not in reply:
                errors.append("The preserved custom gloss is missing.")
            if gadol_match and gadol_match.group(1).strip().split()[0] not in reply:
                errors.append("The supplied Mispar Gadol value is missing.")

        return not errors, errors

    @work(exclusive=True)
    async def send_worker(self, question: str) -> None:
        status = self.query_one("#watcher-status", Static)
        eyes = self.app.screen.query_one("#corner-eyes-main", Static)
        eyes.update(render_watcher("thinking"))
        mode = self.query_one("#memory-mode", Select).value or "empty"
        active_model = REFERENCE_MODEL if mode in ("current", "current_similar") and self.pending_context else "default Watcher model"
        status.update(f"The Watcher is considering... Model: {active_model}")

        context, label = await self._memory_context(question)
        selected_mode = self.query_one("#memory-mode", Select).value or "empty"
        selected_model = (
            REFERENCE_MODEL
            if context and selected_mode in ("current", "current_similar")
            else None
        )
        try:
            reply = await ollama_chat(
                self.messages[-24:],
                context=context,
                model=selected_model,
            )
            if selected_model == REFERENCE_MODEL:
                valid, errors = self.validate_reference_reply(reply)
                if not valid:
                    correction = (
                        context
                        + "\n\nVALIDATION FAILURE — CORRECT THESE BEFORE ANSWERING:\n- "
                        + "\n- ".join(errors)
                        + "\nReturn an interpretation that preserves every Quarries-owned field exactly."
                    )
                    reply = await ollama_chat(
                        self.messages[-24:],
                        context=correction,
                        model=selected_model,
                    )
                    valid, errors = self.validate_reference_reply(reply)
                    if not valid:
                        reply = (
                            "[Reference validation warning: the local model continued to contradict "
                            "Quarries-owned data. The generated interpretation was withheld.]\n\n"
                            "Conflicts detected:\n- " + "\n- ".join(errors)
                        )
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
        model_label = selected_model or "default Watcher model"
        status.update(f"The Watcher is listening. Context: {label} • Model: {model_label}")
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
            yield Static("SESSION SECURITY", classes="pane-title")
            yield Label("Auto-lock after inactivity")
            yield Select([("1 minute",60),("5 minutes",300),("10 minutes",600),("15 minutes",900),("30 minutes",1800),("60 minutes",3600)], value=self.app.auto_lock_seconds, id="auto-lock-select", allow_blank=False)
            yield Static("Ctrl+L seals Quarries immediately and clears all in-memory keys.", id="security-status")

    @on(Select.Changed, "#auto-lock-select")
    def change_auto_lock(self, event: Select.Changed) -> None:
        try:
            seconds = int(event.value)
        except (TypeError, ValueError):
            return
        self.app.auto_lock_seconds = seconds
        self.app.store.set_preference("auto_lock_seconds", str(seconds))
        self.app.last_activity = time.monotonic()
        self.query_one("#security-status", Static).update(f"Auto-lock set to {seconds // 60} minute(s). Ctrl+L seals immediately.")

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
        try:
            self.auto_lock_seconds = int(self.store.get_preference("auto_lock_seconds", str(DEFAULT_AUTO_LOCK_SECONDS)))
        except (TypeError, ValueError):
            self.auto_lock_seconds = DEFAULT_AUTO_LOCK_SECONDS

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
        if time.monotonic() - self.last_activity >= self.auto_lock_seconds:
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
        # Reference Context is intentionally session-only and is destroyed on seal.
        try:
            watcher = self.screen.query_one(WatcherPane)
            watcher.clear_reference_context()
        except Exception:
            pass
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
