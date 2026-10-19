"""Gráfico de evolução (CP ou GS) desenhado à mão com QPainter: leve e sem dependências."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from . import theme


def fmt_int(n: int | float | None) -> str:
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", ".")


class GrowthChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: list[tuple[datetime, int]] = []
        self.label = ""
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self._xy: list[QPointF] = []

    def set_series(self, points: list[tuple[datetime, int]], label: str) -> None:
        self.points = sorted(points, key=lambda p: p[0])
        self.label = label
        self.update()

    # ----------------------------------------------------------------- paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.RAISE))
        p.drawRoundedRect(r, 10, 10)

        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1.5))
        p.setFont(small)
        muted = QColor(theme.MUTED)

        if len(self.points) < 2:
            p.setPen(muted)
            msg = ("O gráfico aparece quando houver duas leituras diferentes.\n"
                   "Cada mudança de CP ou de equipamento vira um ponto.")
            p.drawText(r.adjusted(16, 0, -16, 0), Qt.AlignCenter | Qt.TextWordWrap, msg)
            self._xy = []
            return

        pad_l, pad_r, pad_t, pad_b = 64, 18, 18, 28
        plot = QRectF(r.left() + pad_l, r.top() + pad_t, r.width() - pad_l - pad_r, r.height() - pad_t - pad_b)
        t0, t1 = self.points[0][0].timestamp(), self.points[-1][0].timestamp()
        vals = [v for _, v in self.points]
        lo, hi = min(vals), max(vals)
        if lo == hi:
            lo, hi = lo - 1, hi + 1
        margin = (hi - lo) * 0.12
        lo, hi = lo - margin, hi + margin
        span_t = (t1 - t0) or 1.0

        def to_xy(t: datetime, v: float) -> QPointF:
            x = plot.left() + (t.timestamp() - t0) / span_t * plot.width()
            y = plot.bottom() - (v - lo) / (hi - lo) * plot.height()
            return QPointF(x, y)

        # grade horizontal com 3 valores
        grid = QColor(theme.LINE)
        for i in range(3):
            v = lo + (hi - lo) * i / 2
            y = plot.bottom() - plot.height() * i / 2
            p.setPen(QPen(grid, 1, Qt.DashLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(muted)
            p.drawText(QRectF(r.left() + 4, y - 9, pad_l - 10, 18), Qt.AlignRight | Qt.AlignVCenter, fmt_int(v))

        self._xy = [to_xy(t, v) for t, v in self.points]
        line = QPainterPath(self._xy[0])
        for q in self._xy[1:]:
            line.lineTo(q)
        area = QPainterPath(line)
        area.lineTo(self._xy[-1].x(), plot.bottom())
        area.lineTo(self._xy[0].x(), plot.bottom())
        area.closeSubpath()
        accent = QColor(theme.ACCENT)
        grad = QLinearGradient(0, plot.top(), 0, plot.bottom())
        c1 = QColor(accent); c1.setAlpha(70)
        c2 = QColor(accent); c2.setAlpha(0)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(area)
        p.setPen(QPen(accent, 2.2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)
        p.setBrush(accent)
        p.setPen(Qt.NoPen)
        p.drawEllipse(self._xy[-1], 4.5, 4.5)

        # datas da primeira e da última leitura
        p.setPen(muted)
        f = lambda d: d.astimezone().strftime("%d/%m")
        p.drawText(QRectF(plot.left() - 30, plot.bottom() + 6, 60, 18), Qt.AlignHCenter, f(self.points[0][0]))
        p.drawText(QRectF(plot.right() - 30, plot.bottom() + 6, 60, 18), Qt.AlignHCenter, f(self.points[-1][0]))

    def mouseMoveEvent(self, e):
        if not self._xy:
            return
        x = e.position().x()
        i = min(range(len(self._xy)), key=lambda k: abs(self._xy[k].x() - x))
        t, v = self.points[i]
        QToolTip.showText(e.globalPosition().toPoint(),
                          f"{self.label}: {fmt_int(v)}\n{t.astimezone().strftime('%d/%m/%Y %H:%M')}", self)
