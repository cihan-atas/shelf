# -*- coding: utf-8 -*-
"""shelf'in tam ekran interaktif arayüzü (Textual)."""

import collections
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
from textual.widgets import (Checkbox, Footer, Input, OptionList, RichLog,
                             Static, Tree)
from textual.widgets.option_list import Option

from . import ai as ai_mod
from . import config as config_mod
from . import index as idx
from . import keys as keys_mod
from . import providers
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
  F3               AI sağlayıcı, anahtar, model ve tarama sınırı
  F4               Arşivi düzenle (kategorilendirme, kuru çalıştırma)
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
    """Gezilebilir yardım: solda konu listesi, sağda kaydırılabilir metin.

    Eski sürüm herhangi bir tuşta kapanıyordu; bu yüzden uzun metinleri
    kaydırmak mümkün değildi. Artık yalnızca Esc/F1/q kapatır.
    """

    BINDINGS = [
        Binding("escape,f1,q", "kapat", "Kapat"),
        Binding("tab", "odak_degistir", "Panel değiştir", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static("[b cyan]shelf — Yardım[/]  "
                         "[dim]↑↓ konu seç · PgUp/PgDn kaydır · Esc kapat[/]",
                         id="help-title")
            with Horizontal(id="help-cols"):
                yield OptionList(id="help-topics")
                with VerticalScroll(id="help-body-pane"):
                    yield Static("", id="help-body", markup=False)

    def on_mount(self) -> None:
        from . import help as help_mod

        olist = self.query_one("#help-topics", OptionList)
        olist.add_option(Option(Text("Kısayollar", style="bold"), id="_tus"))
        for ad, veri in help_mod.KONULAR.items():
            olist.add_option(Option(Text(veri["baslik"]), id=ad))
        olist.highlighted = 0
        olist.focus()
        self._goster("_tus")

    def _goster(self, ad) -> None:
        from . import help as help_mod

        if ad == "_tus":
            metin = HELP_TEXT
        else:
            metin = help_mod.konu_metni(ad) or ""
        self.query_one("#help-body", Static).update(metin)
        self.query_one("#help-body-pane", VerticalScroll).scroll_home(animate=False)

    def on_option_list_option_highlighted(self, event) -> None:
        secim = event.option_list.get_option_at_index(event.option_index).id
        if secim:
            self._goster(secim)

    def action_odak_degistir(self) -> None:
        olist = self.query_one("#help-topics", OptionList)
        pane = self.query_one("#help-body-pane", VerticalScroll)
        (pane if olist.has_focus else olist).focus()

    def action_kapat(self) -> None:
        self.dismiss()


class KeyPrompt(ModalScreen):
    """Tek bir sağlayıcı için API anahtarı girişi."""

    BINDINGS = [Binding("escape", "iptal", "Vazgeç")]

    def __init__(self, saglayici):
        super().__init__()
        self.saglayici = saglayici
        self.spec = providers.PROVIDERS[saglayici]

    def compose(self) -> ComposeResult:
        mevcut = keys_mod.get(self.saglayici)
        with Vertical(id="key-box"):
            yield Static(f"[b cyan]{self.spec.label}[/] API anahtarı", id="key-title")
            yield Static(
                f"[dim]{self.spec.free_note}[/]\n"
                f"[dim]Anahtar alın:[/] [blue]{self.spec.signup_url}[/]",
                id="key-note")
            if mevcut:
                yield Static(
                    f"[dim]Kayıtlı:[/] [green]{keys_mod.maskele(mevcut)}[/]"
                    f"  [dim](yeni değer eskisini değiştirir)[/]", id="key-current")
            # password=True: anahtar ekranda açıkça görünmez
            yield Input(placeholder=self.spec.env_var, password=True, id="key-input")
            yield Static("[dim]⏎ kaydet ve dene · Esc vazgeç[/]", id="key-hint")

    def on_mount(self) -> None:
        self.query_one("#key-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.dismiss((self.saglayici, event.value.strip()))

    def action_iptal(self) -> None:
        self.dismiss(None)


class AIScreen(ModalScreen):
    """AI sağlayıcı, anahtar ve model yönetimi."""

    BINDINGS = [
        Binding("escape,f3", "kapat", "Kapat"),
        Binding("a", "anahtar", "Anahtar gir"),
        Binding("s", "sil", "Anahtarı sil"),
        Binding("m", "modeller", "Modelleri getir"),
        Binding("d", "dene", "Bağlantıyı dene"),
    ]

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.modeller = []          # (saglayici, model) listesi
        self._yukleniyor = False

    def compose(self) -> ComposeResult:
        with Vertical(id="ai-box"):
            yield Static("[b cyan]AI sağlayıcıları[/]", id="ai-title")
            with Horizontal(id="ai-cols"):
                with Vertical(id="ai-left"):
                    yield Static("[b]Sağlayıcı[/]  [dim](a: anahtar, s: sil)[/]")
                    yield OptionList(id="ai-providers")
                with Vertical(id="ai-right"):
                    yield Static("[b]Model[/]  [dim](m: getir, ⏎: seç)[/]")
                    yield OptionList(id="ai-models")
            with Horizontal(id="ai-limit-row"):
                yield Static("[b]AI kaç sonucu incelesin:[/] ", id="ai-limit-label")
                yield Input(value=str(self.cfg.get("ai_max_candidates") or "hepsi"),
                            id="ai-limit-input")
                yield Static("[dim]sayı ya da 'hepsi' · ⏎ kaydet[/]", id="ai-limit-hint")
            yield Static("", id="ai-status")
            yield Static(
                "[dim]a anahtar · s sil · d dene · m modeller · ⏎ seç · Esc kapat[/]",
                id="ai-hint")

    def on_mount(self) -> None:
        self._saglayicilari_ciz()
        self.query_one("#ai-providers", OptionList).focus()
        self._durum(f"Etkin model: {self.cfg.get('ai_model')}")

    # ---------- çizim ----------

    def _saglayicilari_ciz(self) -> None:
        olist = self.query_one("#ai-providers", OptionList)
        secili = olist.highlighted
        olist.clear_options()
        etkin_s, _ = providers.parse_model(self.cfg.get("ai_model"))
        for ad, spec, anahtar, _kaynak in keys_mod.durum():
            if anahtar:
                isaret = Text("✓ ", style="bold green")
                deger = Text(keys_mod.maskele(anahtar), style="green")
            else:
                isaret = Text("· ", style="dim")
                deger = Text("anahtar yok", style="dim")
            satir = Text.assemble(
                isaret, (spec.label.ljust(15), "bold"), " ", deger,
                (" ← etkin", "magenta bold") if ad == etkin_s else "")
            olist.add_option(Option(satir, id=ad))
        if secili is not None and secili < olist.option_count:
            olist.highlighted = secili

    def _secili_saglayici(self):
        olist = self.query_one("#ai-providers", OptionList)
        if olist.highlighted is None:
            return None
        return olist.get_option_at_index(olist.highlighted).id

    def _durum(self, metin, stil="") -> None:
        self.query_one("#ai-status", Static).update(
            Text(metin, style=stil) if stil else metin)

    # ---------- eylemler ----------

    def action_kapat(self) -> None:
        self.dismiss(self.cfg)

    def action_anahtar(self) -> None:
        ad = self._secili_saglayici()
        if ad:
            self.app.push_screen(KeyPrompt(ad), self._anahtar_geldi)

    def _anahtar_geldi(self, sonuc) -> None:
        if not sonuc:
            return
        ad, anahtar = sonuc
        if not anahtar:
            self._durum("Boş anahtar — kaydedilmedi.", "yellow")
            return
        try:
            keys_mod.set_(ad, anahtar)
        except Exception as e:
            self._durum(f"Kaydedilemedi: {e}", "red")
            return
        self._saglayicilari_ciz()
        self._durum(f"{providers.PROVIDERS[ad].label} kaydedildi — deneniyor…")
        self._dene_worker(ad)

    def action_sil(self) -> None:
        ad = self._secili_saglayici()
        if not ad:
            return
        try:
            if keys_mod.remove(ad):
                self._saglayicilari_ciz()
                self._durum(f"{providers.PROVIDERS[ad].label} anahtarı silindi.", "yellow")
            else:
                self._durum("Bu sağlayıcı için kayıtlı anahtar yok.", "dim")
        except Exception as e:
            self._durum(f"Silinemedi: {e}", "red")

    def action_dene(self) -> None:
        ad = self._secili_saglayici()
        if ad:
            self._durum(f"{providers.PROVIDERS[ad].label} deneniyor…")
            self._dene_worker(ad)

    def action_modeller(self) -> None:
        ad = self._secili_saglayici()
        if not ad:
            return
        if self._yukleniyor:
            return
        if not keys_mod.get(ad):
            self._durum("Önce anahtar girin (a).", "yellow")
            return
        self._yukleniyor = True
        self._durum(f"{providers.PROVIDERS[ad].label} modelleri getiriliyor…")
        self._model_worker(ad)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "ai-limit-input":
            return
        event.stop()
        ham = event.value.strip().lower()
        if ham in ("hepsi", "all", "tum", "tümü", "0", ""):
            deger = 0
        else:
            try:
                deger = int(ham)
                if deger < 0:
                    raise ValueError
            except ValueError:
                self._durum("Sayı ya da 'hepsi' yazın.", "red")
                return
        self.cfg["ai_max_candidates"] = deger
        config_mod.set_key("ai_max_candidates", deger)
        nasil = "tüm sonuçlar" if not deger else f"ilk {deger} sonuç"
        self._durum(f"AI {nasil} inceleyecek  (kaydedildi)", "green")

    def on_option_list_option_selected(self, event) -> None:
        event.stop()
        if event.option_list.id == "ai-providers":
            self.action_modeller()
        elif event.option_list.id == "ai-models":
            secim = event.option_list.get_option_at_index(event.option_index).id
            if secim:
                self.cfg["ai_model"] = secim
                config_mod.set_key("ai_model", secim)
                self._saglayicilari_ciz()
                self._durum(f"Etkin model: {secim}  (kaydedildi)", "green")

    # ---------- arka plan işleri ----------

    @work(thread=True, exclusive=True)
    def _dene_worker(self, ad) -> None:
        spec = providers.PROVIDERS[ad]
        anahtar = keys_mod.get(ad)
        try:
            # Gömülü varsayılan emekliye ayrılmış olabilir; canlı listeden seç
            model = providers.canli_model_sec(ad, anahtar, spec.default_model)
            p = providers.build(ad, anahtar, model)
            ai_mod.complete(p, "Yalnızca 'tamam' yaz.", retries=1)
        except Exception as e:
            self.app.call_from_thread(
                self._durum, f"{spec.label}: {ai_mod.explain(e)}", "red")
            return
        self.app.call_from_thread(
            self._durum, f"{spec.label} çalışıyor ✓  ({model})", "green")

    @work(thread=True, exclusive=True)
    def _model_worker(self, ad) -> None:
        spec = providers.PROVIDERS[ad]
        try:
            p = providers.build(ad, keys_mod.get(ad), spec.default_model or "x")
            adlar = [m for m in p.list_models() if providers.looks_like_chat_model(m)]
        except Exception as e:
            self.app.call_from_thread(self._model_hata, ai_mod.explain(e))
            return
        self.app.call_from_thread(self._modelleri_ciz, ad, adlar)

    def _model_hata(self, mesaj) -> None:
        self._yukleniyor = False
        self._durum(f"Model listesi alınamadı — {mesaj}", "red")

    def _modelleri_ciz(self, ad, adlar) -> None:
        self._yukleniyor = False
        spec = providers.PROVIDERS[ad]
        olist = self.query_one("#ai-models", OptionList)
        olist.clear_options()
        etkin = self.cfg.get("ai_model")
        # Ücretsiz ve önerilen modeller başa alınır; aranan genelde onlar
        def anahtar_sirala(m):
            return (not providers.is_free(ad, m), m not in spec.recommended, m)
        for m in sorted(adlar, key=anahtar_sirala):
            ref = providers.format_model(ad, m)
            satir = Text(m)
            if providers.is_free(ad, m):
                satir.append("  ücretsiz", style="green")
            if m in spec.recommended:
                satir.append("  ★", style="yellow")
            if ref == etkin:
                satir.append("  ← etkin", style="magenta bold")
            olist.add_option(Option(satir, id=ref))
        self._durum(f"{spec.label}: {len(adlar)} model — ⏎ ile seçin")
        if adlar:
            olist.focus()


class OrganizeScreen(ModalScreen):
    """Arşiv düzenleme: kaynak/hedef seçimi, seçenekler, kuru çalıştırma ve uygulama."""

    BINDINGS = [
        Binding("escape", "kapat", "Kapat"),
        Binding("f4", "kapat", "Kapat", show=False),
        Binding("ctrl+r", "calistir", "Çalıştır", priority=True),
    ]

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._eylemler = None      # son kuru çalıştırmanın planı
        self._calisiyor = False

    def compose(self) -> ComposeResult:
        with Vertical(id="org-box"):
            yield Static("[b cyan]Arşivi düzenle[/]", id="org-title")
            yield Static("[dim]Kaynak dizin[/]")
            yield Input(placeholder="/yol/to/dagınık/dizin", id="org-source")
            yield Static("[dim]Hedef arşiv[/]")
            yield Input(placeholder=self.cfg.get("archive_dir") or "~/arsiv",
                        id="org-target")
            with Horizontal(id="org-opts"):
                yield Checkbox("Kuru çalıştırma", value=True, id="org-dry")
                yield Checkbox("Alt klasörler", value=True, id="org-rec")
                yield Checkbox("Taşı (kopyalama)", value=False, id="org-move")
            with Horizontal(id="org-opts2"):
                yield Checkbox("AI ile yeniden adlandır", value=False, id="org-rename")
                yield Checkbox("Sadece AI", value=False, id="org-aionly")
                yield Checkbox("AI yok", value=False, id="org-noai")
            with Horizontal(id="org-opts3"):
                yield Static("[dim]Eşik:[/] ", id="org-th-label")
                yield Input(value=str(self.cfg.get("organize_threshold", 15)),
                            id="org-threshold")
                yield Static(f"[dim]Model: {self.cfg.get('ai_model')}  (F3'ten değişir)[/]",
                             id="org-model")
            yield RichLog(id="org-log", highlight=False, markup=True, wrap=True)
            yield Static(
                "[dim]Ctrl+R çalıştır · Esc kapat  ·  kuru çalıştırma açıkken "
                "hiçbir dosyaya dokunulmaz[/]", id="org-hint")

    def on_mount(self) -> None:
        kaynak = self.query_one("#org-source", Input)
        kaynak.focus()
        gunluk = self.query_one("#org-log", RichLog)
        gunluk.write("[dim]Kaynak dizini yazıp Ctrl+R ile başlatın.[/]")
        gunluk.write("[dim]Önce kuru çalıştırma yapın; sonuç iyiyse "
                     "'Kuru çalıştırma'yı kapatıp tekrar çalıştırın.[/]")

    # ---------- yardımcılar ----------

    def _sec(self, kimlik) -> bool:
        return self.query_one(f"#{kimlik}", Checkbox).value

    def _yaz(self, metin) -> None:
        self.query_one("#org-log", RichLog).write(metin)

    def action_kapat(self) -> None:
        if self._calisiyor:
            self._yaz("[yellow]İşlem sürüyor — bitmesini bekleyin.[/]")
            return
        self.dismiss(None)

    def action_calistir(self) -> None:
        if self._calisiyor:
            self._yaz("[yellow]Zaten çalışıyor.[/]")
            return

        kaynak = os.path.expanduser(self.query_one("#org-source", Input).value.strip())
        hedef = os.path.expanduser(
            self.query_one("#org-target", Input).value.strip()
            or self.cfg.get("archive_dir") or "")

        if not kaynak or not os.path.isdir(kaynak):
            self._yaz(f"[red]Kaynak dizin bulunamadı:[/] {kaynak or '(boş)'}")
            return
        if not hedef:
            self._yaz("[red]Hedef arşiv belirlenmedi.[/]")
            return
        if self._sec("org-aionly") and self._sec("org-noai"):
            self._yaz("[red]'Sadece AI' ile 'AI yok' birlikte seçilemez.[/]")
            return
        try:
            esik = int(self.query_one("#org-threshold", Input).value.strip() or 15)
        except ValueError:
            self._yaz("[red]Eşik bir sayı olmalı.[/]")
            return

        kuru = self._sec("org-dry")
        if not kuru and self._sec("org-move"):
            self._yaz("[yellow b]DİKKAT:[/] taşıma kipi — kaynak dosyalar "
                      "yerinden alınacak.")

        self._calisiyor = True
        self._eylemler = None
        self._yaz("")
        self._yaz(f"[b]{'KURU ÇALIŞTIRMA' if kuru else 'UYGULANIYOR'}[/]  "
                  f"{kaynak} → {hedef}")
        self._is_worker(kaynak, hedef, esik, kuru)

    # ---------- arka plan ----------

    @work(thread=True, exclusive=True)
    def _is_worker(self, kaynak, hedef, esik, kuru) -> None:
        from . import organize as org
        from .rules import Rules, RulesError

        yaz = lambda m: self.app.call_from_thread(self._yaz, m)
        try:
            rules = Rules.load()
        except RulesError as e:
            yaz(f"[red]Kural dosyası okunamadı: {e}[/]")
            self.app.call_from_thread(self._bitti)
            return

        dosyalar = org.list_source_files(kaynak, recursive=self._sec("org-rec"))
        if not dosyalar:
            yaz("[yellow]İşlenecek döküman bulunamadı.[/]")
            self.app.call_from_thread(self._bitti)
            return
        yaz(f"{len(dosyalar)} dosya bulundu.")

        provider = None
        if not self._sec("org-noai"):
            try:
                provider = ai_mod.get_provider(self.cfg["ai_model"])
                yaz(f"[dim]AI: {provider.label}[/]")
            except ai_mod.AIError as e:
                yaz(f"[yellow]AI devre dışı — {str(e).splitlines()[0]}[/]")

        son = [0.0]

        def ilerleme(i, toplam, ad, durum):
            simdi = time.time()
            if simdi - son[0] > 0.4 or i == toplam:
                son[0] = simdi
                self.app.call_from_thread(
                    self._durum_yaz, f"[{i}/{toplam}] {durum}: {ad[:52]}")

        try:
            eylemler, hatalar = org.plan(
                dosyalar, rules, hedef, provider=provider, threshold=esik,
                rename=self._sec("org-rename"), progress=ilerleme,
                ai_only=self._sec("org-aionly"))
        except Exception as e:
            yaz(f"[red]Planlama başarısız: {e}[/]")
            self.app.call_from_thread(self._bitti)
            return

        self.app.call_from_thread(self._plan_bitti, eylemler, hatalar, kuru)

        if not kuru:
            try:
                sonuc = org.apply(eylemler, move=self._sec("org-move"), dry_run=False)
            except Exception as e:
                yaz(f"[red]Uygulama başarısız: {e}[/]")
                self.app.call_from_thread(self._bitti)
                return
            self.app.call_from_thread(self._uygulandi, sonuc)
        else:
            self.app.call_from_thread(self._bitti)

    # ---------- ana iş parçacığı geri çağrıları ----------

    def _durum_yaz(self, metin) -> None:
        self.query_one("#org-log", RichLog).write(f"[dim]{metin}[/]")

    def _plan_bitti(self, eylemler, hatalar, kuru) -> None:
        from . import organize as org

        self._eylemler = eylemler
        ozet = org.summarize(eylemler)
        self._yaz("")
        self._yaz("[b cyan]Kategori dağılımı[/]")
        for kat, bilgi in sorted(ozet.items(), key=lambda x: -x[1]["count"]):
            kaynaklar = ", ".join(f"{n} {k}" for k, n in bilgi.items()
                                  if k != "count" and n)
            renk = "yellow" if kat == "KATEGORISIZ" else "green"
            self._yaz(f"  [{renk}]{bilgi['count']:>4}[/]  {kat:<22} [dim]({kaynaklar})[/]")
        if hatalar:
            sayac = collections.Counter(hatalar)
            self._yaz("")
            self._yaz(f"[yellow]AI {len(hatalar)} kez sonuç veremedi:[/]")
            for sebep, n in sayac.most_common(4):
                self._yaz(f"  [yellow]{n}×  {sebep[:70]}[/]")
        if kuru:
            self._yaz("")
            self._yaz("[b]Kuru çalıştırma bitti — hiçbir dosyaya dokunulmadı.[/]")
            self._yaz("[dim]Uygulamak için 'Kuru çalıştırma'yı kapatıp Ctrl+R.[/]")

    def _uygulandi(self, sonuc) -> None:
        self._yaz("")
        if isinstance(sonuc, dict):
            for k, v in sonuc.items():
                self._yaz(f"  [green]{k}[/]: {v}")
        else:
            self._yaz(f"  [green]{sonuc}[/]")
        self._yaz("[b green]Tamamlandı.[/]")
        self._bitti()

    def _bitti(self) -> None:
        self._calisiyor = False


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

    #ai-box {
        width: 92; height: auto; max-height: 80%; padding: 1 2;
        border: thick $accent; background: $surface; margin: 2 4;
    }
    #ai-title { height: 1; }
    #ai-cols { height: 16; }
    #ai-left { width: 44; }
    #ai-right { width: 1fr; }
    #ai-providers, #ai-models { height: 1fr; border: solid $panel-lighten-2; }
    #ai-limit-row { height: 3; }
    #ai-limit-label { width: 26; padding: 1 0 0 0; }
    #ai-limit-input { width: 16; }
    #ai-limit-hint { width: 1fr; padding: 1 0 0 2; color: $text-muted; }
    #ai-status { height: auto; padding: 1 0 0 0; color: $text-muted; }
    #ai-hint { height: 1; color: $text-muted; }

    #key-box {
        width: 74; height: auto; padding: 1 2;
        border: thick $accent; background: $surface; margin: 4 6;
    }
    #key-title, #key-note, #key-current, #key-hint { height: auto; }
    #key-note { padding: 1 0; }
    #key-input { margin: 1 0 0 0; }

    #org-box {
        width: 100; height: 90%; padding: 1 2;
        border: thick $accent; background: $surface; margin: 1 4;
    }
    #org-title { height: 1; }
    #org-source, #org-target { height: 3; margin: 0 0 1 0; }
    #org-opts, #org-opts2, #org-opts3 { height: 3; }
    #org-opts Checkbox, #org-opts2 Checkbox { width: 1fr; }
    #org-th-label { width: 8; padding: 1 0 0 0; }
    #org-threshold { width: 12; }
    #org-model { width: 1fr; padding: 1 0 0 2; }
    #org-log { height: 1fr; border: solid $panel-lighten-2; margin: 1 0 0 0; }
    #org-hint { height: 1; color: $text-muted; }

    #help-box {
        width: 108; height: 90%; padding: 1 2;
        border: thick $accent; background: $surface; margin: 1 4;
    }
    #help-title { height: 1; }
    #help-cols { height: 1fr; padding: 1 0 0 0; }
    #help-topics { width: 26; border-right: solid $panel-lighten-2; }
    #help-body-pane { width: 1fr; padding: 0 1; }
    #help-body { height: auto; }
    """

    # Not: ctrl+q ve ctrl+t birçok terminal emülatöründe pencere/sekme kısayolu
    # olduğu için uygulamaya hiç ulaşmaz. Çıkış ctrl+c'de, içerik araması F2'de.
    BINDINGS = [
        Binding("ctrl+c", "quit", "Çıkış", priority=True),
        Binding("f1,question_mark", "help", "Yardım"),
        Binding("ctrl+a", "ai_rank", "AI sırala", priority=True),
        Binding("f2", "toggle_content", "İçerik", priority=True),
        Binding("f3", "ai_settings", "AI ayarları", priority=True),
        Binding("f4", "organize", "Düzenle", priority=True),
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

    def action_ai_settings(self) -> None:
        """Sağlayıcı/anahtar/model ekranını açar."""
        self.push_screen(AIScreen(self.cfg), self._ai_ayar_kapandi)

    def _ai_ayar_kapandi(self, cfg) -> None:
        if cfg:
            self.cfg = cfg
        self.set_status()

    def action_organize(self) -> None:
        """Arşiv düzenleme ekranını açar."""
        self.push_screen(OrganizeScreen(self.cfg))

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

        azami = self.cfg.get("ai_max_candidates") or 0
        subset = self.results if not azami else self.results[:azami]

        def progress(i, total, name):
            self.call_from_thread(self._set_busy, f"AI analizi {i}/{total} — {name[:36]}")

        ai_mod.rank(provider, query, subset,
                    lambda r: search_mod.preview_text(self.cfg, r, 2500), progress)
        rest = [] if not azami else self.results[azami:]
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
