# -*- coding: utf-8 -*-
"""AI sağlayıcıları.

Groq, OpenRouter, Gemini ve NVIDIA'nın dördü de OpenAI uyumlu bir sohbet
tamamlama API'si sunar. Bu yüzden tek bir istemci hepsini sürer; sağlayıcılar
yalnızca taban adres, anahtar değişkeni ve varsayılan modelle ayrışır.

İstemci standart kütüphaneyle (urllib) yazıldı; ek bir HTTP bağımlılığı yok.
"""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "shelf/2.1 (+https://github.com/cihan-atas/shelf)"
TIMEOUT = 90


class ProviderError(Exception):
    """Sağlayıcıya ulaşılamadı ya da istek reddedildi."""


@dataclass
class ProviderSpec:
    name: str
    label: str
    base_url: str
    env_var: str
    default_model: str
    signup_url: str
    free_note: str
    recommended: list = field(default_factory=list)
    extra_headers: dict = field(default_factory=dict)


PROVIDERS = {
    "groq": ProviderSpec(
        name="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        env_var="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        signup_url="https://console.groq.com/keys",
        free_note="Ücretsiz katman: kredi kartı istemez, dakikada sınırlı istek. Çok hızlı.",
        recommended=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-20b",
        ],
    ),
    "openrouter": ProviderSpec(
        name="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_var="OPENROUTER_API_KEY",
        default_model="",   # ücretsiz modeller canlı listeden seçilir
        signup_url="https://openrouter.ai/keys",
        free_note="Adı ':free' ile biten modeller ücretsizdir; tek anahtarla onlarca model.",
        extra_headers={
            "HTTP-Referer": "https://github.com/cihan-atas/shelf",
            "X-Title": "shelf",
        },
    ),
    "gemini": ProviderSpec(
        name="gemini",
        label="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        env_var="GOOGLE_API_KEY",
        default_model="gemini-flash-latest",
        signup_url="https://aistudio.google.com/apikey",
        free_note="Ücretsiz katman: günlük ve dakikalık istek sınırı var.",
        recommended=[
            "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-flash-lite-latest",
        ],
    ),
    "nvidia": ProviderSpec(
        name="nvidia",
        label="NVIDIA NIM",
        base_url="https://integrate.api.nvidia.com/v1",
        env_var="NVIDIA_API_KEY",
        default_model="meta/llama-3.3-70b-instruct",
        signup_url="https://build.nvidia.com/",
        free_note="Kayıt sonrası ücretsiz kredi; barındırılan açık modeller.",
        recommended=[
            "meta/llama-3.3-70b-instruct",
            "qwen/qwen3-next-80b-a3b-instruct",
        ],
    ),
}

DEFAULT_PROVIDER = "gemini"


# ---------- model referansı ----------

def parse_model(reference, default_provider=DEFAULT_PROVIDER):
    """'groq:llama-3.3-70b' -> ('groq', 'llama-3.3-70b')

    Sağlayıcı öneki yoksa varsayılan sağlayıcı kullanılır. OpenRouter model
    adları eğik çizgi ve ':free' soneki içerdiğinden yalnızca ilk iki nokta
    üst üste ayraç sayılır ve yalnızca bilinen sağlayıcı adları önek kabul edilir.
    """
    if not reference:
        spec = PROVIDERS[default_provider]
        return default_provider, spec.default_model
    head, _, tail = reference.partition(":")
    if tail and head in PROVIDERS:
        return head, tail
    return default_provider, reference


def format_model(provider, model):
    return f"{provider}:{model}"


def is_free(provider, model):
    """Modelin bilinen bir ücretsiz seçenek olup olmadığını söyler."""
    if provider == "openrouter":
        return model.endswith(":free")
    # Diğer sağlayıcılarda ücretsizlik model değil hesap katmanı meselesidir
    return None


# ---------- HTTP istemcisi ----------

def _request(url, api_key, payload=None, extra_headers=None, method=None):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    headers.update(extra_headers or {})
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        try:
            message = _extract_error(body) or body or e.reason
        except Exception:
            message = body or e.reason
        raise ProviderError(f"{e.code} {message}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"Bağlantı kurulamadı: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise ProviderError(f"Sunucudan geçersiz yanıt: {e}") from e


def _extract_error(body):
    """Hata gövdesinden okunabilir mesajı çıkarır.

    Sağlayıcılar hatayı tek biçimde döndürmez: sözlük, sözlük listesi ya da
    düz metin gelebilir. Burada patlamak asıl hatayı gizlediği için her
    biçim sessizce tolere edilir.
    """
    try:
        data = json.loads(body)
    except Exception:
        return ""
    if isinstance(data, list):
        # Gemini kesinti sırasında [{"error": {...}}] biçiminde yanıt verebilir
        for item in data:
            mesaj = _extract_error(json.dumps(item))
            if mesaj:
                return mesaj
        return ""
    if not isinstance(data, dict):
        return str(data)[:200]
    error = data.get("error")
    if isinstance(error, dict):
        return error.get("message", "") or error.get("status", "")
    if isinstance(error, str):
        return error
    return data.get("message", "")


class Provider:
    """Bir sağlayıcı + model çiftine bağlı istemci."""

    def __init__(self, spec, api_key, model):
        self.spec = spec
        self.name = spec.name
        self.api_key = api_key
        self.model_name = model or spec.default_model
        if not self.model_name:
            raise ProviderError(
                f"{spec.label} için model belirtilmedi. "
                f"'shelf models --provider {spec.name}' ile listeleyin.")

    @property
    def label(self):
        return f"{self.spec.label} · {self.model_name}"

    def complete(self, prompt, temperature=0.2, max_tokens=1024):
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _request(f"{self.spec.base_url}/chat/completions", self.api_key,
                        payload, self.spec.extra_headers)
        try:
            choice = data["choices"][0]["message"]
            content = choice.get("content") or ""
            if not content and choice.get("reasoning"):
                # Bazı akıl yürütme modelleri yanıtı reasoning alanında döndürür
                content = choice["reasoning"]
            return content.strip()
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"Beklenmeyen yanıt biçimi: {e}") from e

    def list_models(self):
        """Sağlayıcının sunduğu model kimliklerini döner."""
        data = _request(f"{self.spec.base_url}/models", self.api_key,
                        extra_headers=self.spec.extra_headers)
        items = data.get("data") or []
        names = []
        for item in items:
            ident = item.get("id") if isinstance(item, dict) else None
            if ident:
                # Gemini kimlikleri "models/..." önekiyle gelir; sohbet uç
                # noktası her iki biçimi de kabul ettiği için sadeleştiriyoruz
                names.append(ident[7:] if ident.startswith("models/") else ident)
        return sorted(names)


def build(provider_name, api_key, model):
    spec = PROVIDERS.get(provider_name)
    if spec is None:
        known = ", ".join(PROVIDERS)
        raise ProviderError(f"Bilinmeyen sağlayıcı: {provider_name} (bilinenler: {known})")
    if not api_key:
        raise ProviderError(
            f"{spec.label} için API anahtarı yok. "
            f"'shelf keys --set {spec.name}' ile ekleyin ({spec.signup_url}).")
    return Provider(spec, api_key, model)


# ---------- model listesini süzme ----------

_CHAT_UNFRIENDLY = re.compile(
    r"(embed|embedding|rerank|whisper|tts|speech|audio|image|vision-only|"
    r"guard|moderation|safety|ocr|video|imagen|veo|lyria|nano-banana)", re.I)


def looks_like_chat_model(name):
    """Sohbet tamamlama için uygun görünmeyen modelleri eler."""
    return not _CHAT_UNFRIENDLY.search(name)
