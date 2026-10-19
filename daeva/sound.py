"""Som de alerta. No Windows usa o winsound (já vem com o Python); fora dele, o bipe do sistema."""
from __future__ import annotations

import sys
from pathlib import Path


def resource(rel: str) -> Path:
    """Caminho de um arquivo empacotado, tanto rodando do código quanto do .exe (PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def play_alert() -> None:
    wav = resource("assets/alerta.wav")
    if sys.platform == "win32" and wav.exists():
        import winsound
        winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return
    from PySide6.QtWidgets import QApplication
    QApplication.beep()
