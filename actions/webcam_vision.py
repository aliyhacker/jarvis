"""
Webcam görüntüsü alır ve Gemini Vision ile analiz eder.
"""

from __future__ import annotations

import io
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from PIL import Image

from app_config import get_app_config_value

# ─────────────────────────────────────────────────────────────────────────────
# UI'ın okuyacağı sabit snapshot path'i
LAST_SNAPSHOT = Path(tempfile.gettempdir()) / "jarvis_webcam_last.jpg"

VISION_MODELS = (
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash",
)
MAX_DIMENSION    = 1280
MAX_INLINE_BYTES = 5_500_000

# Webcam ısınma kareleri — ilk kareler genelde karanlık çıkar
WARMUP_FRAMES = 5


# ── Webcam yakalama ───────────────────────────────────────────────────────────

def _capture_frame() -> tuple[bool, str, Path | None]:
    """Webcam'dan tek kare yakalar, geçici PNG olarak kaydeder."""
    try:
        import cv2
    except ImportError:
        return (
            False,
            "opencv-python paketi yüklü değil. "
            "Terminal'de 'pip install opencv-python' çalıştırın.",
            None,
        )

    tmp_path = Path(tempfile.mktemp(prefix="jarvis-cam-", suffix=".png"))

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return (
            False,
            "Webcam açılamadı. Kamera bağlı ve Windows kamera iznine (Ayarlar > Gizlilik > Kamera) sahip mi?",
            None,
        )

    try:
        # Isınma — sensör ilk karelerde otomatik pozlamayı ayarlar
        for _ in range(WARMUP_FRAMES):
            cap.read()

        ret, frame = cap.read()
        if not ret or frame is None:
            return False, "Webcam'dan görüntü alınamadı.", None

        success = cv2.imwrite(str(tmp_path), frame)
        if not success:
            return False, "Görüntü kaydedilemedi.", None

        # UI için sabit konuma da kaydet
        try:
            cv2.imwrite(str(LAST_SNAPSHOT), frame)
        except Exception:
            pass

        return True, "", tmp_path

    except Exception as exc:
        return False, f"Webcam hatası: {exc}", None
    finally:
        cap.release()


# ── Görüntü işleme ────────────────────────────────────────────────────────────

def _build_image_part(image_path: Path) -> types.Part:
    """Görüntüyü Gemini'ye uygun boyuta indirip Part nesnesine çevirir."""
    try:
        with Image.open(image_path) as img:
            work = img.copy()

        if work.mode not in {"RGB", "L"}:
            work = work.convert("RGB")

        if max(work.size) > MAX_DIMENSION:
            work.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        png_buf = io.BytesIO()
        work.save(png_buf, format="PNG", optimize=True)
        png_bytes = png_buf.getvalue()

        if len(png_bytes) <= MAX_INLINE_BYTES:
            return types.Part.from_bytes(data=png_bytes, mime_type="image/png")

        # PNG çok büyükse JPEG'e düş
        jpg_buf = io.BytesIO()
        work.convert("RGB").save(jpg_buf, format="JPEG", quality=85, optimize=True)
        return types.Part.from_bytes(data=jpg_buf.getvalue(), mime_type="image/jpeg")

    except Exception:
        return types.Part.from_bytes(
            data=image_path.read_bytes(), mime_type="image/png"
        )


def _make_prompt(query: str) -> str:
    q = (query or "Kamerada ne görüyorsun?").strip()
    return (
        "Sen JARVIS'in görme modülüsün. Webcam'dan gelen canlı bir kareyi analiz ediyorsun.\n\n"
        f"Kullanıcının sorusu: {q}\n\n"
        "Gördüklerini Türkçe olarak net ve özlü anlat.\n"
        "- Nesne tanıma yapılıyorsa tam adıyla belirt.\n"
        "- Marka, renk, şekil gibi ayırt edici özellikleri say.\n"
        "- Emin olmadığın şeyleri 'büyük ihtimalle' veya 'gibi görünüyor' diyerek belirt.\n"
        "- Uydurma yapma."
    )


def _extract_text(response) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if text:
        return text
    chunks = []
    for cand in getattr(response, "candidates", None) or []:
        for part in getattr(getattr(cand, "content", None), "parts", None) or []:
            t = str(getattr(part, "text", "") or "").strip()
            if t:
                chunks.append(t)
    return "\n".join(chunks).strip()


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (errors.ServerError, TimeoutError)):
        return True
    msg = str(exc).lower()
    return any(
        m in msg
        for m in ("503", "429", "deadline", "timed out", "unavailable",
                   "resource exhausted", "busy", "overloaded")
    )


def _analyze(query: str, image_path: Path) -> str:
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API anahtarı eksik — kamera analizi yapılamıyor."

    prompt     = _make_prompt(query)
    client     = genai.Client(api_key=api_key)
    image_part = _build_image_part(image_path)
    delays     = (0.8, 1.6, 3.0)
    last_exc: Exception | None = None

    for model in VISION_MODELS:
        for attempt, delay in enumerate(delays, start=1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[types.Part.from_text(text=prompt), image_part],
                    config=types.GenerateContentConfig(temperature=0.25),
                )
                text = _extract_text(response)
                if text:
                    return text
                raise RuntimeError("Gemini geçerli bir yanıt döndürmedi.")
            except Exception as exc:
                last_exc = exc
                if attempt < len(delays) and _is_transient(exc):
                    time.sleep(delay)
                    continue
                if not _is_transient(exc):
                    raise RuntimeError(f"Kamera analizi başarısız: {exc}") from exc
                break  # geçici hata, sonraki modeli dene

    raise RuntimeError(f"Tüm modeller başarısız oldu: {last_exc}")


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def analyze_webcam(query: str = "") -> str:
    """
    Webcam'dan bir kare çeker ve Gemini Vision ile analiz eder.
    Kameraya tuttuğun nesneyi tanımlar, ortamı açıklar veya soruya yanıt verir.
    """
    ok, err, tmp = _capture_frame()
    if not ok:
        return err

    assert tmp is not None
    try:
        if not tmp.exists() or tmp.stat().st_size == 0:
            return "Webcam görüntüsü boş geldi. Kamera başka bir uygulama tarafından kullanılıyor olabilir."
        return _analyze(query, tmp)
    except Exception as exc:
        return str(exc)
    finally:
        try:
            if tmp and tmp.exists():
                tmp.unlink()
        except Exception:
            pass
