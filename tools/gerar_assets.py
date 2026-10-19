"""Gera assets/alerta.wav e o ícone (png + ico). Rode uma vez: python tools/gerar_assets.py
Precisa do Pillow só para o ícone (pip install pillow)."""
import math
import struct
import wave
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)


def chime(path: Path, rate=44100):
    """Dois toques suaves (Mi5 e Si5), com ataque curto e decaimento exponencial."""
    notes = [(659.25, 0.00), (987.77, 0.22)]
    dur = 1.15
    n = int(rate * dur)
    samples = []
    for i in range(n):
        t = i / rate
        v = 0.0
        for f, start in notes:
            if t >= start:
                tt = t - start
                env = min(1.0, tt / 0.008) * math.exp(-tt * 4.2)
                v += env * (math.sin(2 * math.pi * f * tt) + 0.25 * math.sin(2 * math.pi * 2 * f * tt))
        samples.append(v)
    peak = max(abs(s) for s in samples) or 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(s / peak * 0.55 * 32767)) for s in samples))


def icon(png: Path, ico: Path):
    from PIL import Image, ImageDraw
    S = 512
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=(20, 29, 43, 255), outline=(38, 52, 76, 255), width=8)
    gold = (228, 173, 85, 255)
    cx, cy = S / 2, S / 2 + 10
    # asas estilizadas: penas em leque dos dois lados
    for side in (-1, 1):
        for k in range(5):
            ang = math.radians(200 + k * 22) if side < 0 else math.radians(-20 - k * 22)
            length = 190 - k * 22
            x2 = cx + side * 18 + math.cos(ang) * length * (1 if side > 0 else 1)
            y2 = cy + math.sin(ang) * length
            d.line((cx + side * 18, cy, x2, y2), fill=gold, width=26 - k * 3)
            d.ellipse((x2 - 12, y2 - 12, x2 + 12, y2 + 12), fill=gold)
    # gema central
    d.polygon([(cx, cy - 70), (cx + 40, cy), (cx, cy + 70), (cx - 40, cy)], fill=(127, 178, 255, 255))
    img.save(png)
    img.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    chime(ASSETS / "alerta.wav")
    icon(ASSETS / "icon.png", ASSETS / "icon.ico")
    print("ok")
