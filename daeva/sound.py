"""Som de alerta, com som personalizado por tipo de aviso (WAV ou MP3) e volume.

No Windows toca pelo MCI do próprio sistema (winmm), que abre WAV e MP3 sem instalar nada.
Se o arquivo escolhido sumir ou não abrir, cai no som padrão do app; fora do Windows, no bipe do sistema.
"""
from __future__ import annotations

import sys
from pathlib import Path

SOUND_KINDS = {
    "big": "Bosses e Abismo",
    "hourly": "Eventos de toda hora (Shugo e Invasão)",
    "reset": "Resets diário e semanal",
}
SOUND_EXTS = (".wav", ".mp3")
_ALIAS = "daeva_alerta"


def resource(rel: str) -> Path:
    """Caminho de um arquivo empacotado, tanto rodando do código quanto do .exe (PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def sound_path(kind: str, settings: dict | None) -> Path:
    """Arquivo que vai tocar para este tipo de aviso: o escolhido, se existir, senão o padrão."""
    custom = ((settings or {}).get("sounds") or {}).get(kind) or ""
    p = Path(custom) if custom else None
    if p and p.suffix.lower() in SOUND_EXTS and p.is_file():
        return p
    return resource("assets/alerta.wav")


def _mci(cmd: str) -> int:
    import ctypes
    return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)


def _play_windows(path: Path, volume: int) -> bool:
    _mci(f"close {_ALIAS}")
    if _mci(f'open "{path}" type mpegvideo alias {_ALIAS}') != 0:
        return False
    _mci(f"setaudio {_ALIAS} volume to {max(0, min(100, volume)) * 10}")
    return _mci(f"play {_ALIAS} from 0") == 0


def play_alert(kind: str = "big", settings: dict | None = None) -> None:
    path = sound_path(kind, settings)
    volume = int((settings or {}).get("volume", 80))
    if sys.platform == "win32":
        try:
            if _play_windows(path, volume):
                return
        except Exception:
            pass
        wav = resource("assets/alerta.wav")
        if wav.exists():
            import winsound
            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            return
    from PySide6.QtWidgets import QApplication
    QApplication.beep()
