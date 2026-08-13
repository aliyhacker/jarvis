"""
JARVIS kısayol yardımcıları — Windows sürümü.

macOS sürümü .app/.command ve LaunchAgent plist üretiyordu; Windows'ta
bunların karşılığı .lnk kısayollarıdır:
  - Masaüstü kısayolu  → Desktop\\JARVIS.lnk
  - Açılışta başlat     → Başlangıç klasörü\\JARVIS.lnk

PowerShell WScript.Shell kullanılır, ek bağımlılık gerekmez.
Kısayollar pythonw.exe ile main.py'yi konsolsuz başlatır.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _desktop_dir() -> Path:
    """OneDrive masaüstü veya klasik masaüstünü bulur."""
    candidates = []
    one = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if one:
        candidates.append(Path(one) / "Desktop")
    candidates.append(Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _startup_dir() -> Path:
    """Windows Başlangıç klasörü (açılışta otomatik çalışanlar)."""
    return (
        Path(os.environ.get("APPDATA", str(Path.home())))
        / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )


def _pythonw() -> str:
    """Konsolsuz başlatma için pythonw.exe, yoksa python.exe."""
    exe = Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    return str(pyw if pyw.exists() else exe)


def _write_shortcut(link_path: Path) -> Path:
    """Verilen yola JARVIS .lnk kısayolu yazar."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    target = _pythonw()
    main_py = BASE_DIR / "main.py"

    icon_line = ""
    ico_candidate = BASE_DIR / "Icon" / "jarvis.ico"
    if ico_candidate.exists():
        icon_line = f"$s.IconLocation = '{ico_candidate}'; "

    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{link_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Arguments = '\"{main_py}\"'; "
        f"$s.WorkingDirectory = '{BASE_DIR}'; "
        f"$s.Description = 'J.A.R.V.I.S'; "
        f"{icon_line}"
        "$s.Save()"
    )

    result = subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=_CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or "Kısayol oluşturulamadı.")
    return link_path


# ── Masaüstü kısayolu ────────────────────────────────────────────────────────
def desktop_shortcut_path() -> Path:
    return _desktop_dir() / "JARVIS.lnk"


def create_desktop_shortcut() -> Path:
    return _write_shortcut(desktop_shortcut_path())


# ── Açılışta başlat (Başlangıç klasörü) ──────────────────────────────────────
def startup_shortcut_path() -> Path:
    return _startup_dir() / "JARVIS.lnk"


def create_startup_shortcut() -> Path:
    return _write_shortcut(startup_shortcut_path())


def remove_startup_shortcut() -> None:
    path = startup_shortcut_path()
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    created = create_desktop_shortcut()
    print(f"Masaüstü kısayolu oluşturuldu: {created}")
