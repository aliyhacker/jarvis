"""
YouTube oynatma kontrolü — Windows için.

YouTube videosunu duraklat/oynat, ileri/geri sar, sonraki/önceki videoya geç,
ses aç/kıs, sessize al gibi işlemler; tarayıcıdaki YouTube sekmesini öne
getirip YouTube'un kendi klavye kısayollarını göndererek yapılır. Bu yüzden
komut çalışmadan önce tarayıcıda bir YouTube videosu açık olmalıdır
(örn. play_media veya browser_control ile açılmış olabilir).

Not: 'next' / 'previous' yalnızca bir oynatma listesi (playlist) veya karışım
(mix) içindeyken YouTube tarafında etkin olur; tek başına açılmış tekil bir
videoda bu kısayolların görünür bir etkisi olmayabilir.

Ses (volume) hakkında: Yukarı/Aşağı ok tuşunun YouTube'daki GERÇEK adımı
ölçüldü: %2 (20% iken 1 basış -> %22). Ama "volume_up"/"volume_down" komutu
tek çağrıda %10'luk bir değişim yapsın isteniyor. Bu yüzden fonksiyon dışarıya
hiçbir sayı (amount) almaz — her çağrıda ok tuşuna otomatik olarak 5 kere
basar (5 x %2 = %10). Basit kullanım, sabit %10 adım.
"""

from __future__ import annotations

import time

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False


_SECONDS_PER_SEEK_PRESS = 10   # J / L tuşu -> sabit 10 saniye (YouTube'un resmi kısayolu)

_VOLUME_PRESS_COUNT = 5        # volume_up/volume_down çağrısı başına kaç kere ok tuşuna basılır
_VOLUME_KEY_DELAY = 0.06       # Ardışık basışlar arasında bekleme (YouTube'un her basışı ayrı algılaması için)

# Tek basışlık (sabit) komutlar — volume_up / volume_down burada YOK,
# çünkü onlar birden fazla basış gerektiriyor ve ayrıca ele alınıyor.
_SIMPLE_ACTION_KEYS: dict[str, tuple[str, ...] | str] = {
    "play_pause": "k",
    "next": ("shift", "n"),
    "previous": ("shift", "p"),
    "seek_forward": "l",      # 10 saniye ileri
    "seek_backward": "j",     # 10 saniye geri
    "mute": "m",
    "fullscreen": "f",
    "theater_mode": "t",
}


def _focus_youtube_window() -> bool:
    """Başlığında 'youtube' geçen tarayıcı penceresini öne getirmeye çalışır (best-effort)."""
    if not HAS_PYGETWINDOW:
        return False
    try:
        candidates = [
            win for win in gw.getAllWindows()
            if "youtube" in (win.title or "").lower()
        ]
        if not candidates:
            return False

        win = candidates[0]
        try:
            if win.isMinimized:
                win.restore()
        except Exception:
            pass
        try:
            win.activate()
        except Exception:
            pass
        time.sleep(0.35)
        return True
    except Exception:
        return False


def control_youtube(action: str) -> str:
    normalized = (action or "").strip().lower()

    # Kullanıcının farklı ifadelerini normalize et
    aliases = {
        "play": "play_pause",
        "pause": "play_pause",
        "resume": "play_pause",
        "skip": "next",
        "next_video": "next",
        "previous_video": "previous",
        "prev": "previous",
        "forward": "seek_forward",
        "forward_10": "seek_forward",
        "back": "seek_backward",
        "backward": "seek_backward",
        "back_10": "seek_backward",
        "rewind": "seek_backward",
        "louder": "volume_up",
        "increase_volume": "volume_up",
        "quieter": "volume_down",
        "decrease_volume": "volume_down",
        "unmute": "mute",
    }
    normalized = aliases.get(normalized, normalized)

    all_actions = set(_SIMPLE_ACTION_KEYS) | {"volume_up", "volume_down"}
    if normalized not in all_actions:
        return (
            f"Bilinmeyen YouTube komutu: '{action}'. "
            "Geçerli komutlar: play_pause, next, previous, seek_forward, "
            "seek_backward, volume_up, volume_down, mute, fullscreen, theater_mode."
        )

    if not HAS_PYAUTOGUI:
        return "pyautogui kurulu değil — YouTube kontrolü için gerekli (requirements.txt içinde mevcut)."

    focused = _focus_youtube_window()
    if not focused:
        return (
            "YouTube sekmesini içeren bir tarayıcı penceresi bulunamadı. "
            "Önce bir video açık olmalı (play_media veya browser_control ile aç)."
        )

    try:
        # --- Ses: sabit %10 değişim için ok tuşuna 5 kere basılır (5 x %2 = %10) ---
        if normalized in ("volume_up", "volume_down"):
            key = "up" if normalized == "volume_up" else "down"
            for _ in range(_VOLUME_PRESS_COUNT):
                pyautogui.press(key)
                time.sleep(_VOLUME_KEY_DELAY)
            yon = "arttırıldı" if normalized == "volume_up" else "azaltıldı"
            return f"Tamam, ses %10 {yon}."

        # --- Sarma ve diğer tüm sabit tek-basışlık komutlar ---
        key = _SIMPLE_ACTION_KEYS[normalized]
        if isinstance(key, tuple):
            pyautogui.hotkey(*key)
        else:
            pyautogui.press(key)

        if normalized == "seek_forward":
            return f"Tamam, video {_SECONDS_PER_SEEK_PRESS} saniye ileri sarıldı."
        if normalized == "seek_backward":
            return f"Tamam, video {_SECONDS_PER_SEEK_PRESS} saniye geri sarıldı."
        return f"Tamam, YouTube'da '{normalized}' komutu gönderildi."

    except Exception as exc:
        return f"YouTube komutu gönderilemedi: {exc}"
