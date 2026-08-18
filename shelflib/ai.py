# -*- coding: utf-8 -*-
"""AI alaka analizi katmanı.

Sağlayıcıdan bağımsızdır: Groq, OpenRouter, Gemini ve NVIDIA'nın hepsi
providers.py içindeki tek OpenAI uyumlu istemciyle sürülür. Bu modül yalnızca
istemi kurar, yanıtı ayrıştırır ve hataları Türkçeye çevirir.
"""

import json
import re
import time

from . import keys as keys_mod
from . import providers

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


def get_provider(model_reference):
    """'groq:llama-3.3-70b' gibi bir referanstan istemci kurar.

    Önek yoksa varsayılan sağlayıcı kullanılır. Anahtar keys modülünden gelir.
    """
    saglayici, model = providers.parse_model(model_reference)
    spec = providers.PROVIDERS.get(saglayici)
    if spec is None:
        bilinen = ", ".join(providers.PROVIDERS)
        raise AIError(f"Bilinmeyen sağlayıcı: {saglayici} (bilinenler: {bilinen})")

    api_key = keys_mod.get(saglayici)
    if not api_key:
        raise AIError(
            f"{spec.label} için API anahtarı yok.\n"
            f"  Anahtar alın : {spec.signup_url}\n"
            f"  Sonra çalıştırın: shelf keys --set {saglayici}")
    try:
        return providers.build(saglayici, api_key, model)
    except providers.ProviderError as e:
        raise AIError(str(e)) from e


def load_env():
    """Geriye dönük uyumluluk — anahtarlar artık keys modülünden okunur."""
    return None


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


RETRY_HINTS = ("429", "resourceexhausted", "quota", "rate limit", "rate_limit",
               "503", "unavailable", "deadline", "500", "internal",
               "502", "504", "overloaded", "timed out", "timeout")


def _is_retryable(exc):
    text = f"{type(exc).__name__} {exc}".lower()
    return any(h in text for h in RETRY_HINTS)


def explain(exc, provider=None):
    """Bir istisnayı kullanıcıya gösterilecek kısa Türkçe açıklamaya çevirir."""
    text = f"{type(exc).__name__} {exc}".lower()
    spec = getattr(provider, "spec", None)
    etiket = spec.label if spec else "Sağlayıcı"

    if "429" in text or "quota" in text or "rate limit" in text or "rate_limit" in text:
        return f"{etiket} kotası aşıldı — bekleyin ya da başka sağlayıcıya geçin."
    if "404" in text or "notfound" in text or "not found" in text:
        model = getattr(provider, "model_name", "?")
        ad = spec.name if spec else "?"
        return f"Model bulunamadı: {model} ('shelf models --provider {ad}' ile listeleyin)"
    if "401" in text or "403" in text or "permission" in text or "api key" in text:
        ad = spec.name if spec else "?"
        return f"{etiket} anahtarı reddedildi — 'shelf keys --set {ad}' ile yenileyin."
    if "bağlantı kurulamadı" in text or "urlerror" in text:
        return "Ağ bağlantısı kurulamadı."
    detail = " ".join(str(exc).split())[:110]
    return f"{type(exc).__name__}: {detail}"


def complete(provider, prompt, retries=3):
    """Sağlayıcıya istek atar; geçici hatalarda geri çekilerek yeniden dener."""
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
