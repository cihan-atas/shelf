# -*- coding: utf-8 -*-
"""shelf'in tam ekran interaktif arayüzü (Textual)."""

import os
import subprocess
import sys
import time

from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, OptionList, Static, Tree
from textual.widgets.option_list import Option

from . import ai as ai_mod
from . import index as idx
from . import search as search_mod

HELP_TEXT = """\
[b cyan]shelf — Siber Güvenlik Arşiv Arama Motoru[/]

[b]Gezinme[/]
  ↑ / ↓            Sonuçlar arasında gez (arama kutusundayken de çalışır)
  ⏎                Seçili dosyayı varsayılan uygulamada aç
  Tab / Shift+Tab  Paneller arasında geç
  Esc              Arama kutusuna dön / filtreyi temizle

[b]Komutlar[/]
  Ctrl+A           Sonuçları yapay zeka ile alaka puanına göre sırala
  F2               İçerik araması aç/kapat (dosya adı ↔ dosya içeriği)
  F5               Arşivi yeniden indeksle (değişenleri günceller)
  Ctrl+O           Seçili dosyanın klasörünü aç
  Ctrl+Y           Seçili dosyanın tam yolunu panoya kopyala
  F1 / ?           Bu yardım ekranı
  Ctrl+C           Çıkış

[dim]Ctrl+T ve Ctrl+R de aynı işi yapar, ancak birçok terminal bu tuşları
kendisi kullandığı için uygulamaya ulaşmayabilir.[/]

[b]Arama ipuçları[/]
  kerberos ticket    Tüm terimleri içerenler (VE mantığı)
  "golden ticket"    Tırnak içinde birebir ifade
  Soldaki ağaçtan bir kategori seçerek aramayı daraltabilirsiniz.

[dim]Kapatmak için herhangi bir tuşa basın.[/]"""


class SearchInput(Input):
    """Arama kutusu.

    Input widget'ı ctrl+a'yı "satır başı", ctrl+c'yi "kopyala" olarak bağlar ve
    bunlar uygulama kısayollarını gölgeler; ikisini de burada geri alıyoruz.
    """

    BINDINGS = [
        Binding("ctrl+a", "app.ai_rank", "AI sırala", priority=True),
        Binding("ctrl+c", "app.quit", "Çıkış", priority=True),
    ]


class HelpScreen(ModalScreen):
    BINDINGS = [Binding("escape,q,question_mark,f1", "dismiss_help", "Kapat")]

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-box")

    def on_key(self, event) -> None:
        event.stop()
        self.dismiss()

    def action_dismiss_help(self) -> None:
        self.dismiss()


class ShelfApp(App):
    TITLE = "shelf"
    SUB_TITLE = "Siber Güvenlik Arşivi"

    CSS = """
    Screen { layers: base overlay; }

    #search { dock: top; height: 3; border: tall $accent; }

    #statusbar {
        dock: top; height: 1; padding: 0 1;
        background: $panel; color: $text-muted;
    }

    #body { height: 1fr; }

    #tree-pane { width: 28; border-right: solid $panel-lighten-2; }
    #tree { height: 1fr; padding: 0 1; }

    #results { width: 1fr; padding: 0 1; }
    #results:focus { border-left: thick $accent; }

    #preview-pane { width: 34%; border-left: solid $panel-lighten-2; padding: 0 1; }
    #preview-title { height: auto; color: $accent; text-style: bold; }
    #preview-meta { height: auto; color: $text-muted; }
    #preview-body { height: 1fr; }

    #help-box {
        width: 78; height: auto; padding: 1 2;
        border: thick $accent; background: $surface;
        margin: 2 4;
    }
    """

    # Not: ctrl+q ve ctrl+t birçok terminal emülatöründe pencere/sekme kısayolu
    # olduğu için uygulamaya hiç ulaşmaz. Çıkış ctrl+c'de, içerik araması F2'de.
    BINDINGS = [
        Binding("ctrl+c", "quit", "Çıkış", priority=True),
        Binding("f1,question_mark", "help", "Yardım"),
        Binding("ctrl+a", "ai_rank", "AI sırala", priority=True),
        Binding("f2", "toggle_content", "İçerik", priority=True),
        Binding("f5", "reindex", "İndeksle", priority=True),
        Binding("ctrl+o", "open_folder", "Klasör", priority=True),
        Binding("ctrl+y", "copy_path", "Yolu kopyala", priority=True),
        Binding("escape", "focus_search", "Ara", show=False),
        Binding("down", "cursor_down", "Aşağı", show=False),
        Binding("up", "cursor_up", "Yukarı", show=False),
        # Terminali tuşu kaptırmayan kullanıcılar için eski kısayollar da çalışsın
        Binding("ctrl+q", "quit", "Çıkış", show=False, priority=True),
        Binding("ctrl+t", "toggle_content", "İçerik", show=False, priority=True),
        Binding("ctrl+r", "reindex", "İndeksle", show=False, priority=True),
    ]

    def __init__(self, cfg, initial_query="", content=False, ai=False):
        super().__init__()
        self.cfg = cfg
        self.initial_query = initial_query
        self.content_mode = content
        self.want_ai = ai
        self.results = []
        self.category_filter = None
        self.subcategory_filter = None
        self.backend = "index" if idx.exists(cfg["index_path"]) else "live"
        self._debounce = None
        self._busy = ""

    # ---------- kurulum ----------

    def compose(self) -> ComposeResult:
        yield SearchInput(placeholder="Ara…  (kerberos ticket · \"golden ticket\")",
                          id="search", value=self.initial_query)
        yield Static("", id="statusbar")
        with Horizontal(id="body"):
            with Vertical(id="tree-pane"):
                yield Tree("Arşiv", id="tree")
            yield OptionList(id="results")
            with VerticalScroll(id="preview-pane"):
                yield Static("", id="preview-title")
                yield Static("", id="preview-meta")
                yield Static("", id="preview-body")
        yield Footer()

    def on_mount(self) -> None:
        self._build_tree()
        self.set_status()
        self.query_one("#search", Input).focus()
        if self.initial_query:
            self.run_search()
        elif self.backend == "index":
            self.run_search()
        if self.backend == "live":
            self.notify("İndeks yok — arama diski tarayacak. Ctrl+R ile indeksleyin.",
                        severity="warning", timeout=8)

    def _build_tree(self) -> None:
        tree = self.query_one("#tree", Tree)
        tree.guide_depth = 2
        tree.clear()
        tree.root.data = {"category": None, "subcategory": None}
        tree.root.expand()
        cats = idx.categories(self.cfg["index_path"])
        if not cats:
            tree.root.label = "Arşiv (indekssiz)"
            return
        total = sum(c[2] for c in cats)
        tree.root.label = Text.assemble(("Tüm arşiv ", "bold"), (f"({total})", "dim"))
        grouped = {}
        for cat, sub, n in cats:
            grouped.setdefault(cat, []).append((sub, n))
        for cat, subs in grouped.items():
            cat_total = sum(n for _, n in subs)
            label = Text.assemble((_pretty(cat) or "(kök)", ""), (f"  {cat_total}", "dim"))
            node = tree.root.add(label, data={"category": cat, "subcategory": None})
            for sub, n in subs:
                if not sub:
                    continue
                node.add_leaf(
                    Text.assemble((_pretty(sub), ""), (f"  {n}", "dim")),
                    data={"category": cat, "subcategory": sub})

    # ---------- durum çubuğu ----------

    def set_status(self) -> None:
        bits = []
        bits.append(f"[b]{len(self.results)}[/] sonuç")
        bits.append("içerik: [b green]açık[/]" if self.content_mode else "içerik: [dim]kapalı[/]")
        source = {"index": "indeks", "index-or": "indeks",
                  "live": "canlı tarama"}.get(self.backend, self.backend)
        bits.append(f"kaynak: [b]{source}[/]")
        if self.backend == "index-or":
            bits.append("[b yellow]gevşek eşleşme (terimlerden herhangi biri)[/]")
        if self.category_filter:
            f = _pretty(self.category_filter)
            if self.subcategory_filter:
                f += " / " + _pretty(self.subcategory_filter)
            bits.append(f"filtre: [b yellow]{f}[/]")
        if any(r.ai_score for r in self.results):
            bits.append(f"[b magenta]AI: {self.cfg['ai_model']}[/]")
        if self._busy:
            bits.append(f"[b cyan]{self._busy}[/]")
        self.query_one("#statusbar", Static).update("  ·  ".join(bits))

    def _set_busy(self, text) -> None:
        self._busy = text
        self.set_status()

    # ---------- arama ----------

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._debounce is not None:
            self._debounce.stop()
        self._debounce = self.set_timer(0.28, self.run_search)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_open()

    def run_search(self) -> None:
        query = self.query_one("#search", Input).value.strip()
        self._search_worker(query)

    @work(exclusive=True, thread=True, group="search")
    def _search_worker(self, query) -> None:
        self.call_from_thread(self._set_busy, "aranıyor…")
        try:
            results, backend = search_mod.search(
                self.cfg, query,
                content=self.content_mode,
                category=self.category_filter,
                subcategory=self.subcategory_filter,
                limit=self.cfg["limit"],
            )
        except Exception as e:
            self.call_from_thread(self.notify, f"Arama hatası: {e}", severity="error")
            results, backend = [], self.backend
        self.call_from_thread(self._apply_results, results, backend)

    def _apply_results(self, results, backend) -> None:
        self.results = results
        self.backend = backend
        self._busy = ""
        self._repopulate(keep_position=False)
        if not results:
            self._clear_preview()
        self.set_status()

    def _option_width(self) -> int:
        """Sonuç satırlarının sığabileceği karakter genişliği."""
        olist = self.query_one("#results", OptionList)
        return max(20, olist.content_size.width - 4)

    def _repopulate(self, keep_position=True) -> None:
        """Sonuç listesini mevcut genişliğe göre yeniden çizer."""
        olist = self.query_one("#results", OptionList)
        position = olist.highlighted if keep_position else 0
        terms = search_mod.tokenize(self.query_one("#search", Input).value)
        width = self._option_width()
        olist.clear_options()
        olist.add_options([Option(_render_option(r, terms, width)) for r in self.results])
        if self.results:
            olist.highlighted = min(position or 0, len(self.results) - 1)
            if not keep_position:
                self._load_preview(0)

    def on_resize(self, event) -> None:
        if self.results:
            self.call_after_refresh(self._repopulate)

    # ---------- önizleme ----------

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_index is not None:
            self._load_preview(event.option_index)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.action_open()

    def _clear_preview(self) -> None:
        self.query_one("#preview-title", Static).update("")
        self.query_one("#preview-meta", Static).update("")
        self.query_one("#preview-body", Static).update(
            Text("Sonuç yok.", style="dim") if self.query_one("#search", Input).value
            else Text("Aramaya başlamak için yazın.", style="dim"))

    def _load_preview(self, position) -> None:
        if not (0 <= position < len(self.results)):
            return
        r = self.results[position]
        self.query_one("#preview-title", Static).update(Text(r.name, overflow="fold"))
        meta = [r.relpath]
        info = [search_mod.human_size(r.size)]
        if r.pages:
            info.append(f"{r.pages} sayfa")
        meta.append(" · ".join(info))
        if r.ai_score:
            meta.append(f"AI: {r.ai_score}/10 — {r.ai_reason}")
        self.query_one("#preview-meta", Static).update(
            Text("\n".join(meta), style="dim", overflow="fold"))
        self.query_one("#preview-body", Static).update(Text("yükleniyor…", style="dim"))
        self._preview_worker(position, r)

    @work(exclusive=True, thread=True, group="preview")
    def _preview_worker(self, position, result) -> None:
        text = search_mod.preview_text(self.cfg, result)
        terms = search_mod.tokenize(self.query_one("#search", Input).value)
        self.call_from_thread(self._apply_preview, position, text, terms)

    def _apply_preview(self, position, text, terms) -> None:
        olist = self.query_one("#results", OptionList)
        if olist.highlighted != position:
            return  # kullanıcı bu arada başka satıra geçti
        body = self.query_one("#preview-body", Static)
        if not text:
            body.update(Text("Bu dosyadan metin çıkarılamadı (taranmış PDF olabilir).",
                             style="dim italic"))
            return
        rendered = Text(text, overflow="fold")
        for t in terms:
            rendered.highlight_words([t], "black on yellow", case_sensitive=False)
        body.update(rendered)

    # ---------- ağaç filtresi ----------

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data or {}
        self.category_filter = data.get("category")
        self.subcategory_filter = data.get("subcategory")
        self.run_search()

    # ---------- eylemler ----------

    def action_focus_search(self) -> None:
        search = self.query_one("#search", Input)
        if search.has_focus and (self.category_filter or self.subcategory_filter):
            self.category_filter = self.subcategory_filter = None
            self.query_one("#tree", Tree).select_node(self.query_one("#tree", Tree).root)
            self.run_search()
        else:
            search.focus()

    def action_cursor_down(self) -> None:
        self._move(1)

    def action_cursor_up(self) -> None:
        self._move(-1)

    def _move(self, delta) -> None:
        olist = self.query_one("#results", OptionList)
        if not self.results:
            return
        cur = olist.highlighted if olist.highlighted is not None else -1
        olist.highlighted = max(0, min(len(self.results) - 1, cur + delta))

    def _current(self):
        olist = self.query_one("#results", OptionList)
        if olist.highlighted is None or not self.results:
            return None
        return self.results[olist.highlighted]

    def action_open(self) -> None:
        r = self._current()
        if not r:
            return
        _open_path(r.path)
        self.notify(f"Açılıyor: {r.name}")

    def action_open_folder(self) -> None:
        r = self._current()
        if not r:
            return
        _open_path(os.path.dirname(r.path))
        self.notify(f"Klasör açılıyor: {os.path.dirname(r.relpath)}")

    def action_copy_path(self) -> None:
        r = self._current()
        if not r:
            return
        try:
            self.copy_to_clipboard(r.path)
            self.notify("Yol panoya kopyalandı.")
        except Exception:
            self.notify("Pano kullanılamadı.", severity="warning")

    def action_toggle_content(self) -> None:
        self.content_mode = not self.content_mode
        self.notify("İçerik araması " + ("açıldı" if self.content_mode else "kapatıldı"))
        self.run_search()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    # ---------- indeksleme ----------

    def action_reindex(self) -> None:
        if not self.cfg.get("archive_dir"):
            self.notify("Arşiv dizini ayarlı değil (shelf config --archive …).",
                        severity="error")
            return
        self._reindex_worker()

    @work(exclusive=True, thread=True, group="index")
    def _reindex_worker(self) -> None:
        last = [0.0]

        def progress(i, total, relpath, state):
            now = time.monotonic()
            if now - last[0] > 0.15 or i == total:
                last[0] = now
                self.call_from_thread(
                    self._set_busy, f"indeksleniyor {i}/{total} — {os.path.basename(relpath)[:40]}")

        try:
            stats = idx.build(self.cfg, progress=progress)
        except Exception as e:
            self.call_from_thread(self.notify, f"İndeksleme hatası: {e}", severity="error")
            self.call_from_thread(self._set_busy, "")
            return
        self.call_from_thread(self._after_reindex, stats)

    def _after_reindex(self, stats) -> None:
        self._busy = ""
        self.backend = "index"
        self._build_tree()
        self.notify(
            f"İndeks güncellendi: {stats['added']} yeni, {stats['updated']} güncel, "
            f"{stats['removed']} silinmiş, {stats['skipped']} değişmemiş.")
        self.run_search()

    # ---------- AI ----------

    def action_ai_rank(self) -> None:
        if not self.results:
            self.notify("Önce bir arama yapın.", severity="warning")
            return
        query = self.query_one("#search", Input).value.strip()
        if not query:
            self.notify("AI sıralaması için bir arama sorgusu gerekli.", severity="warning")
            return
        self._ai_worker(query)

    @work(exclusive=True, thread=True, group="ai")
    def _ai_worker(self, query) -> None:
        try:
            provider = ai_mod.get_provider(self.cfg["ai_model"])
        except ai_mod.AIError as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return

        subset = self.results[: self.cfg["ai_max_candidates"]]

        def progress(i, total, name):
            self.call_from_thread(self._set_busy, f"AI analizi {i}/{total} — {name[:36]}")

        ai_mod.rank(provider, query, subset,
                    lambda r: search_mod.preview_text(self.cfg, r, 2500), progress)
        rest = self.results[self.cfg["ai_max_candidates"]:]
        self.call_from_thread(self._apply_ai, subset + rest)

    def _apply_ai(self, results) -> None:
        self._busy = ""
        self.results = results
        self._repopulate(keep_position=False)
        self.set_status()
        self.notify("AI sıralaması tamamlandı.")


# ---------- yardımcılar ----------

def _pretty(name):
    """01_OFANSIF_GUVENLIK_(RED_TEAM) -> OFANSIF GUVENLIK (RED TEAM)"""
    if not name:
        return ""
    out = name
    if len(out) > 3 and out[:2].isdigit() and out[2] == "_":
        out = out[3:]
    return out.replace("_", " ")


def _trunc(text, width, marked=False):
    """Metni verilen genişliğe kısaltır. marked=True ise \x01/\x02 işaretleri sayılmaz."""
    if width < 8:
        width = 8
    if not marked:
        return text if len(text) <= width else text[: width - 1] + "…"
    out = []
    shown = 0
    for ch in text:
        if ch in ("\x01", "\x02"):
            out.append(ch)
            continue
        if shown >= width - 1:
            out.append("…")
            break
        out.append(ch)
        shown += 1
    return "".join(out)


def _render_option(r, terms, width=80):
    """Bir sonuç satırını üç satırlık Rich metnine dönüştürür."""
    out = Text()

    title = Text(_trunc(r.name, width))
    for t in terms:
        title.highlight_words([t], "bold red", case_sensitive=False)
    out.append_text(title)

    meta_parts = []
    loc = " / ".join(p for p in (_pretty(r.category), _pretty(r.subcategory)) if p)
    if loc:
        meta_parts.append(loc)
    meta_parts.append(search_mod.human_size(r.size))
    if r.pages:
        meta_parts.append(f"{r.pages} s.")
    if r.matched_content:
        meta_parts.append("içerik eşleşmesi")
    meta = " · ".join(meta_parts)

    ai_tag = ""
    if r.ai_score:
        ai_tag = f"  AI {r.ai_score}/10"
    out.append("\n  " + _trunc(meta, width - 2 - len(ai_tag)), style="dim")
    if ai_tag:
        color = "green" if r.ai_score >= 7 else "yellow" if r.ai_score >= 4 else "red"
        out.append(ai_tag, style=f"bold {color}")

    if r.ai_reason and r.ai_score:
        out.append("\n  " + _trunc(r.ai_reason, width - 2), style="dim italic")
    elif r.snippet.strip():
        out.append("\n  ")
        snip = _trunc(" ".join(r.snippet.split()), width - 2, marked=True)
        for part, hot in _split_snippet(snip):
            out.append(part, style="bold yellow" if hot else "dim italic")
    return out


def _split_snippet(snippet):
    """FTS5 snippet işaretlerini (parça, vurgulu_mu) çiftlerine ayırır."""
    parts = []
    buf = ""
    hot = False
    for ch in snippet:
        if ch == "\x01":
            if buf:
                parts.append((buf, hot))
            buf, hot = "", True
        elif ch == "\x02":
            if buf:
                parts.append((buf, hot))
            buf, hot = "", False
        else:
            buf += ch
    if buf:
        parts.append((buf, hot))
    return parts


def _open_path(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        pass


def run(cfg, query="", content=False, ai=False):
    ShelfApp(cfg, query, content, ai).run()
