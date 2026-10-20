"""Peças visuais do layout novo, desenhadas com as cores do tema atual."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import theme


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def restyle(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


def _dotted(color: str, width: float = 2.0) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setStyle(Qt.CustomDashLine)
    pen.setDashPattern([0.6, 2.4])
    pen.setCapStyle(Qt.RoundCap)
    return pen


class Trail(QWidget):
    """Linha pontilhada do timer: começo, trecho percorrido, losango no 'agora' e fim."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.setFixedHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_progress(self, p: float | None):
        p = 0.0 if p is None else max(0.0, min(1.0, p))
        if abs(p - self.progress) > 0.001:
            self.progress = p
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        y, r = h / 2, 3.5
        x0, x1 = r + 1, w - r - 1
        xm = x0 + (x1 - x0) * self.progress
        p.setPen(_dotted(theme.TRACK))
        p.drawLine(QPointF(x0, y), QPointF(xm - 6, y))
        p.setPen(_dotted(theme.DIM))
        p.drawLine(QPointF(xm + 6, y), QPointF(x1, y))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.TRACK))
        if theme.BORDER > 1:
            p.drawRect(QRectF(x0 - r, y - r, 2 * r, 2 * r))
        else:
            p.drawEllipse(QPointF(x0, y), r, r)
        diamond = QPainterPath()
        diamond.moveTo(xm, y - 7)
        diamond.lineTo(xm + 4, y)
        diamond.lineTo(xm, y + 7)
        diamond.lineTo(xm - 4, y)
        diamond.closeSubpath()
        p.setBrush(QColor(theme.FG))
        p.drawPath(diamond)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(theme.TRACK), 1.5))
        if theme.BORDER > 1:
            p.drawRect(QRectF(x1 - r, y - r, 2 * r, 2 * r))
        else:
            p.drawEllipse(QPointF(x1, y), r, r)


class DottedBar(QWidget):
    """Barra de progresso pontilhada (título alvo, energia)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_progress(self, p: float | None):
        self.progress = 0.0 if p is None else max(0.0, min(1.0, p))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        y, w = self.height() / 2, self.width()
        xm = w * self.progress
        if xm > 1:
            p.setPen(_dotted(theme.TRACK))
            p.drawLine(QPointF(1, y), QPointF(xm, y))
        p.setPen(_dotted(theme.DIM))
        p.drawLine(QPointF(max(1, xm + 3), y), QPointF(w - 1, y))


class Leader(QWidget):
    """Pontilhado que liga o nome do evento ao horário, como num índice."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(12)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def sizeHint(self):
        return QSize(40, 12)

    def paintEvent(self, _):
        p = QPainter(self)
        pen = QPen(QColor(theme.LINE), 1)
        pen.setStyle(Qt.DotLine)
        p.setPen(pen)
        y = int(self.height() * 0.72)
        p.drawLine(0, y, self.width(), y)


class Pips(QWidget):
    """Losangos de chaves: cheios até `n`, vazios até `cap`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.n, self.cap = 0, 7
        self.setFixedHeight(14)

    def set_value(self, n: int, cap: int):
        self.n, self.cap = max(0, n), max(1, cap)
        self.setFixedWidth(min(self.cap, 21) * 12 + 2)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(theme.TRACK)
        for i in range(min(self.cap, 21)):
            x, y = 7 + i * 12, self.height() / 2
            path = QPainterPath()
            path.moveTo(x, y - 5)
            path.lineTo(x + 5, y)
            path.lineTo(x, y + 5)
            path.lineTo(x - 5, y)
            path.closeSubpath()
            p.setPen(QPen(c, 1.4))
            p.setBrush(c if i < self.n else Qt.NoBrush)
            p.drawPath(path)


class GrimFrame(QFrame):
    """Moldura dupla de grimório: borda de fora e uma segunda borda por dentro."""

    def __init__(self, parent=None, margin: int = 4):
        super().__init__(parent)
        self.setObjectName("hero")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(margin, margin, margin, margin)
        self.inner = QFrame(objectName="heroInner")
        outer.addWidget(self.inner)
        self.body = QVBoxLayout(self.inner)
        self.body.setContentsMargins(14, 12, 14, 12)
        self.body.setSpacing(8)
