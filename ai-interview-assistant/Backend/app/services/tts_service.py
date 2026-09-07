"""Local Text-to-Speech using Microsoft SpeechT5 (Workshop 3).

SpeechT5 runs through standard `transformers`, works on CPU, and needs no special
library or GPU. The model, vocoder, and speaker embedding are loaded once and reused.
Synthesised audio is cached to disk as WAV, keyed by text + speaker + model, so a
given question is generated at most once (and the browser caches it too).

Note: SpeechT5 is an English model. Non-English text will be mispronounced.
"""
from __future__ import annotations

import hashlib
import io
import threading
from functools import lru_cache
from pathlib import Path

from app.config.settings import get_settings

MAX_TTS_CHARS = 2000

_inference_lock = threading.Lock()


class TtsUnavailableError(RuntimeError):
    """TTS is disabled, or the model / libraries could not be loaded."""


def _resolve_speaker_index(speaker: str | None) -> int:
    # `?voice=<n>` lets you pick an x-vector index; otherwise use the configured default.
    if speaker is not None and str(speaker).strip().isdigit():
        return int(str(speaker).strip())
    return get_settings().tts_speaker_index


def cache_key(text: str, language_code: str | None, speaker: str | None) -> str:
    settings = get_settings()
    parts = [settings.tts_model_id, str(_resolve_speaker_index(speaker)), (text or "").strip()]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    cache_dir = Path(get_settings().tts_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.wav"


def _resolve_device(pref: str):
    import os

    import torch

    p = str(pref).lower()
    if p.startswith("cuda") and torch.cuda.is_available():
        return torch.device(pref)
    # Apple Silicon (M1/M2/M3) GPU is Metal (MPS), not CUDA.
    mps = getattr(torch.backends, "mps", None)
    if p in ("mps", "gpu") and mps is not None and mps.is_available():
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")  # unsupported ops fall back to CPU
        return torch.device("mps")
    return torch.device("cpu")


@lru_cache(maxsize=1)
def _pipeline():
    """Load the SpeechT5 processor, model, and vocoder once."""
    settings = get_settings()
    try:
        from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Processor
    except ImportError as exc:
        raise TtsUnavailableError(
            "TTS libraries are not installed "
            "(pip install transformers torch soundfile sentencepiece datasets)."
        ) from exc

    device = _resolve_device(settings.tts_device)
    processor = SpeechT5Processor.from_pretrained(settings.tts_model_id)
    model = SpeechT5ForTextToSpeech.from_pretrained(settings.tts_model_id).to(device)
    vocoder = SpeechT5HifiGan.from_pretrained(settings.tts_vocoder_id).to(device)
    return processor, model, vocoder, device


@lru_cache(maxsize=8)
def _speaker_embedding(index: int):
    """A 512-dim speaker embedding (the 'voice').

    Priority: a real x-vector file (TTS_SPEAKER_EMBEDDING_PATH) -> CMU-Arctic x-vectors via
    `datasets` (best effort; only works on datasets < 3) -> a deterministic generated voice
    (always works, no download).
    """
    import numpy as np
    import torch

    # 1) A real x-vector saved as .npy or .pt (best voice quality).
    path = get_settings().tts_speaker_embedding_path
    if path and Path(path).exists():
        p = Path(path)
        if p.suffix.lower() == ".npy":
            return torch.tensor(np.load(p).astype("float32")).reshape(1, -1)
        return torch.load(p).float().reshape(1, -1)

    # 2) Real CMU-Arctic x-vectors (newer `datasets` drops script datasets, so this may fail).
    try:
        from datasets import load_dataset

        dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        return torch.tensor(dataset[index]["xvector"]).unsqueeze(0)
    except Exception:  # noqa: BLE001 - unsupported datasets version, or offline
        pass

    # 3) Deterministic fallback: a stable generated voice, no download required.
    rng = np.random.default_rng(index)
    vec = rng.standard_normal(512).astype("float32")
    vec = vec / (float(np.linalg.norm(vec)) + 1e-9)
    return torch.tensor(vec).unsqueeze(0)


def _synthesize_wav(text: str, speaker_index: int) -> bytes:
    import torch

    try:
        import soundfile as sf
    except ImportError as exc:
        raise TtsUnavailableError("soundfile is not installed (pip install soundfile).") from exc

    processor, model, vocoder, device = _pipeline()
    speaker = _speaker_embedding(speaker_index).to(device)
    input_ids = processor(text=text, return_tensors="pt")["input_ids"].to(device)

    with _inference_lock, torch.no_grad():  # serialise inference to one job at a time
        speech = model.generate_speech(input_ids, speaker, vocoder=vocoder)

    import numpy as np

    wav = speech.detach().to("cpu").float().numpy()

    settings = get_settings()
    if settings.tts_normalize:
        peak = float(np.max(np.abs(wav))) if wav.size else 0.0
        if peak > 1e-6:
            wav = wav / peak * 0.97  # peak-normalise -> as loud as possible without clipping
    if settings.tts_gain != 1.0:
        wav = wav * settings.tts_gain  # extra boost (may clip if too high)
    wav = np.clip(wav, -1.0, 1.0)

    buffer = io.BytesIO()
    sf.write(buffer, wav, 16000, format="WAV")  # SpeechT5 outputs 16 kHz
    return buffer.getvalue()


def get_or_create_audio(text: str, language: str | None = "en", speaker: str | None = None) -> bytes:
    """Return WAV bytes for `text`, from the disk cache or a fresh synthesis."""
    settings = get_settings()
    if not settings.tts_enabled:
        raise TtsUnavailableError("Text-to-speech is disabled.")

    clean = (text or "").strip()
    if not clean:
        raise ValueError("Cannot synthesise empty text.")
    if len(clean) > MAX_TTS_CHARS:
        raise ValueError(f"Text is too long to synthesise (max {MAX_TTS_CHARS} characters).")

    path = _cache_path(cache_key(clean, language, speaker))
    if path.exists():
        return path.read_bytes()

    audio = _synthesize_wav(clean, _resolve_speaker_index(speaker))
    path.write_bytes(audio)  # cache so any user / refresh replays instantly
    return audio


def warm_up() -> None:
    """Pre-load the model and default voice so the first request is not a cold start."""
    if get_settings().tts_enabled:
        _pipeline()
        _speaker_embedding(get_settings().tts_speaker_index)
