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


# YouTube'un kendi klavye kısayolları (video oynatıcı odaktayken çalışır).
# https://support.google.com/youtube/answer/7631406
_ACTION_KEYS: dict[str, tuple[str, ...] | str] = {
    "play_pause": "k",
    "next": ("shift", "n"),
    "previous": ("shift", "p"),
    "seek_forward": "l",      # 10 saniye ileri
    "seek_backward": "j",     # 10 saniye geri
    "volume_up": "up",        # ~%5 ses artışı
    "volume_down": "down",    # ~%5 ses azalışı
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
        "quieter": "volume_down",
        "unmute": "mute",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized not in _ACTION_KEYS:
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
        key = _ACTION_KEYS[normalized]
        if isinstance(key, tuple):
            pyautogui.hotkey(*key)
        else:
            pyautogui.press(key)
        return f"Tamam, YouTube'da '{normalized}' komutu gönderildi."
    except Exception as exc:
        return f"YouTube komutu gönderilemedi: {exc}"
