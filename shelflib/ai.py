# -*- coding: utf-8 -*-
"""AI alaka analizi katmanı.

Şimdilik tek sağlayıcı (Google Gemini) var; sağlayıcı arayüzü çoklu model
desteği eklenebilecek şekilde ayrıştırıldı.
"""

import json
import os
import re
import time

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

PROMPT = """Sen bir siber güvenlik uzmanı asistanısın. Kullanıcı "{query}" konusunda araştırma yapıyor.
Aşağıda bir dökümanın adı ve içerik özeti var. Bu dökümanın kullanıcının aramasıyla
ne kadar alakalı olduğunu 1-10 arası puanla ve nedenini tek cümleyle Türkçe açıkla.
SADECE şu JSON formatında cevap ver, başka hiçbir şey yazma:
{{"score": <1-10 arası sayı>, "justification": "<tek cümle>"}}

DOSYA ADI: {name}
ÖZET:
---
{summary}
---"""


class AIError(Exception):
    pass


class GeminiProvider:
    name = "gemini"

    def __init__(self, model_name):
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise AIError("'google-generativeai' kütüphanesi kurulu değil.") from e
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise AIError("GOOGLE_API_KEY bulunamadı (.env dosyasına ekleyin).")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self._model = genai.GenerativeModel(model_name)

    def complete(self, prompt):
        resp = self._model.generate_content(prompt)
        return (resp.text or "").strip()


def load_env():
    if DOTENV_AVAILABLE:
        # Önce çalışma dizini, sonra scriptin bulunduğu dizin
        load_dotenv()
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(here, ".env"))


def get_provider(model_name):
    """Model adına göre uygun sağlayıcıyı döner."""
    load_env()
    return GeminiProvider(model_name)


def _parse(raw):
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            raise
        data = json.loads(m.group())
    score = int(data.get("score", 0))
    return max(0, min(10, score)), str(data.get("justification", "")).strip()


RETRY_HINTS = ("429", "resourceexhausted", "quota", "rate limit",
               "503", "unavailable", "deadline", "500", "internal")


def _is_retryable(exc):
    text = f"{type(exc).__name__} {exc}".lower()
    return any(h in text for h in RETRY_HINTS)


def explain(exc, provider=None):
    """Bir istisnayı kullanıcıya gösterilecek kısa Türkçe açıklamaya çevirir."""
    text = f"{type(exc).__name__} {exc}".lower()
    if "429" in text or "quota" in text or "resourceexhausted" in text:
        return "API kotası aşıldı — biraz bekleyip tekrar deneyin."
    if "404" in text or "notfound" in text:
        model = getattr(provider, "model_name", "?")
        return f"Model bulunamadı: {model}"
    if "permission" in text or "401" in text or "403" in text or "api key" in text:
        return "API anahtarı reddedildi — GOOGLE_API_KEY'i kontrol edin."
    detail = " ".join(str(exc).split())[:110]
    return f"{type(exc).__name__}: {detail}"


def complete(provider, prompt, retries=3):
    """Sağlayıcıya istek atar; geçici hatalarda geri çekilerek yeniden dener.

    Başarısız olursa son istisnayı yükseltir.
    """
    last = None
    for attempt in range(retries):
        try:
            return provider.complete(prompt)
        except Exception as e:
            last = e
            if attempt < retries - 1 and _is_retryable(e):
                time.sleep(2 ** attempt * 2)  # 2sn, 4sn
                continue
            break
    raise last


def score_one(provider, query, name, summary, retries=3):
    """Tek bir döküman için (puan, gerekçe) döner. Geçici hatalarda yeniden dener."""
    if not summary:
        return 0, "Dosya içeriği okunamadı veya boş."
    prompt = PROMPT.format(query=query, name=name, summary=summary[:2500])
    try:
        return _parse(complete(provider, prompt, retries))
    except Exception as e:
        return 1, "AI analizi başarısız — " + explain(e, provider)


def rank(provider, query, results, get_summary, progress=None):
    """Sonuçları AI puanına göre sıralar. Listeyi yerinde günceller."""
    for i, r in enumerate(results, 1):
        if progress:
            progress(i, len(results), r.name)
        r.ai_score, r.ai_reason = score_one(provider, query, r.name, get_summary(r))
    results.sort(key=lambda r: (-r.ai_score, r.rank))
    return results
