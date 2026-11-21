# -*- coding: utf-8 -*-
"""
AI 2D Avatar Studio v5.0
Ручная разметка глаз и рта + плавное 2D-моргание и формы рта.
Для качественного восстановления фона желательно: pip install opencv-python numpy
"""
import sys
import math
import json
import base64
import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QElapsedTimer
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QImage, QPolygonF,
    QPainterPath, QLinearGradient
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QTextEdit, QLabel, QSlider, QGroupBox
)

try:
    import cv2
    import numpy as np
    HAS_INPAINT = True
except Exception:
    cv2 = None
    np = None
    HAS_INPAINT = False

# NumPy также нужна для передачи изображения в MediaPipe.
if np is None:
    try:
        import numpy as np
    except Exception:
        pass

# MediaPipe намеренно не используется: FaceMesh предназначен для человеческих лиц
# на фотографиях и часто не распознаёт стилизованные anime-иллюстрации.
HAS_FACE_MESH = False


APP_NAME = "AI 2D Avatar Studio"
VERSION = "5.3-integrated"

ZONE_NAMES = {
    "Left Eye": "Левый глаз",
    "Right Eye": "Правый глаз",
    "Mouth": "Рот",
}
ZONE_COLORS = {
    "Left Eye": QColor(0, 170, 255),
    "Right Eye": QColor(255, 190, 0),
    "Mouth": QColor(255, 0, 160),
}


def polygon_mask(size, polygon, expand=3):
    """Создаёт маску зоны в координатах исходного изображения."""
    w, h = size
    mask = np.zeros((h, w), dtype=np.uint8)
    pts = np.array([[round(p.x()), round(p.y())] for p in polygon], dtype=np.int32)
    cv2.fillPoly(mask, [pts], 255)
    if expand:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (expand * 2 + 1, expand * 2 + 1))
        mask = cv2.dilate(mask, k, iterations=1)
    return mask


class AvatarCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)
        self.setStyleSheet("background:#202033;")
        self.pixmap = None
        self.clean_pixmap = None
        self.clean_eye_pixmap = None
        self.clean_mouth_pixmap = None
        self.image_path = ""
        self.polygons = {}
        self.blink = 0.0
        self.talk = 0.0
        self.active_zone = "Left Eye"
        self.current_points = []
        self.is_drawing = False
        self.show_guides = True
        self.mouth_color = QColor("#713c3d")
        self.face_select_mode = False
        self.face_drag_start = None
        self.face_rect = QRectF()

    def load_image(self, path):
        pm = QPixmap(path)
        if pm.isNull():
            raise ValueError("Не удалось открыть изображение.")
        self.pixmap = pm
        self.clean_pixmap = pm
        self.image_path = path
        self.polygons.clear()
        self.current_points.clear()
        self.is_drawing = False
        self.blink = self.talk = 0.0
        self.update()

    def get_display_rect(self):
        if not self.pixmap:
            return QRectF()
        iw, ih = self.pixmap.width(), self.pixmap.height()
        scale = min(self.width() / iw, self.height() / ih)
        w, h = iw * scale, ih * scale
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def screen_to_img(self, pt):
        r = self.get_display_rect()
        if r.isEmpty():
            return QPointF()
        return QPointF((pt.x() - r.x()) * self.pixmap.width() / r.width(),
                       (pt.y() - r.y()) * self.pixmap.height() / r.height())

    def img_to_screen(self, pt):
        r = self.get_display_rect()
        return QPointF(r.x() + pt.x() * r.width() / self.pixmap.width(),
                       r.y() + pt.y() * r.height() / self.pixmap.height())

    def rebuild_clean_image(self):
        """Создаёт отдельные чистые копии: глаза и рот не стирают друг друга."""
        self.clean_pixmap = self.pixmap
        self.clean_eye_pixmap = self.pixmap
        self.clean_mouth_pixmap = self.pixmap
        if not self.pixmap or not HAS_INPAINT:
            return

        image = self.pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        w, h = image.width(), image.height()
        # В PySide6/Qt6 image.bits() возвращает memoryview, у которого
        # нет setsize() (в отличие от старых версий PyQt). Учитываем
        # также возможное выравнивание строк QImage через bytesPerLine().
        ptr = image.bits()
        raw = np.frombuffer(ptr, dtype=np.uint8, count=image.sizeInBytes())
        arr = raw.reshape((h, image.bytesPerLine()))[:, :w * 4]
        arr = arr.reshape((h, w, 4)).copy()
        bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)

        def make_clean(zones):
            mask = np.zeros((h, w), dtype=np.uint8)
            for zone in zones:
                poly = self.polygons.get(zone)
                if poly and len(poly) >= 3:
                    mask = cv2.bitwise_or(mask, polygon_mask((w, h), poly, 4))
            if not np.any(mask):
                return self.pixmap
            result = cv2.inpaint(bgr, mask, 5, cv2.INPAINT_TELEA)
            rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            rgba = np.dstack((rgb, arr[:, :, 3])).copy()
            out = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
            return QPixmap.fromImage(out)

        self.clean_eye_pixmap = make_clean(("Left Eye", "Right Eye"))
        self.clean_mouth_pixmap = make_clean(("Mouth",))

    def mousePressEvent(self, event):
        if not self.pixmap:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.get_display_rect().contains(event.position()):
                return
            if self.face_select_mode:
                self.face_drag_start = self.screen_to_img(event.position())
                self.face_rect = QRectF(self.face_drag_start, self.face_drag_start)
                self.update()
                return
            self.current_points.append(self.screen_to_img(event.position()))
            self.is_drawing = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton and self.is_drawing:
            if len(self.current_points) >= 3:
                poly = QPolygonF(self.current_points)
                self.polygons[self.active_zone] = poly
                if self.active_zone == "Mouth":
                    self.mouth_color = self.sample_color(poly.boundingRect().center())
                self.rebuild_clean_image()
            self.current_points.clear()
            self.is_drawing = False
            self.update()

    def mouseMoveEvent(self, event):
        if self.face_select_mode and self.face_drag_start is not None:
            end = self.screen_to_img(event.position())
            self.face_rect = QRectF(self.face_drag_start, end).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if (self.face_select_mode and self.face_drag_start is not None
                and event.button() == Qt.MouseButton.LeftButton):
            end = self.screen_to_img(event.position())
            self.face_rect = QRectF(self.face_drag_start, end).normalized()
            self.face_drag_start = None
            self.face_select_mode = False
            self.update()
            self.parent_window().on_face_region_selected(self.face_rect)

    def parent_window(self):
        widget = self.parent()
        while widget is not None and not hasattr(widget, "on_face_region_selected"):
            widget = widget.parent()
        return widget

    def sample_color(self, pt):
        if not self.pixmap:
            return QColor("#c98779")
        img = self.pixmap.toImage()
        x, y = int(pt.x()), int(pt.y())
        if 0 <= x < img.width() and 0 <= y < img.height():
            return img.pixelColor(x, y)
        return QColor("#c98779")

    def eye_path(self, rect, openness):
        """Контур закрывающегося века в локальных координатах изображения."""
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        cy = y + h * 0.53
        path = QPainterPath()
        path.moveTo(x + w * 0.04, cy)
        # Верхнее веко — мягкая дуга, а не прямоугольная черта.
        path.cubicTo(x + w * 0.28, cy - h * 0.10 * openness,
                     x + w * 0.70, cy - h * 0.10 * openness,
                     x + w * 0.96, cy)
        if openness < 0.16:
            # При полном закрытии остаётся выразительная линия верхнего века.
            return path
        path.cubicTo(x + w * 0.72, cy + h * 0.12 * openness,
                     x + w * 0.28, cy + h * 0.12 * openness,
                     x + w * 0.04, cy)
        path.closeSubpath()
        return path

    def draw_closed_eye(self, painter, rect, amount):
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        # Линия века плавно перемещается от открытого состояния к закрытому.
        cy = y + h * (0.50 + 0.05 * amount)
        lid = QPainterPath()
        lid.moveTo(x + w * 0.03, cy)
        lid.cubicTo(x + w * 0.28, cy - h * (0.10 + 0.06 * amount),
                    x + w * 0.72, cy - h * (0.10 + 0.06 * amount),
                    x + w * 0.97, cy)
        painter.setPen(QPen(QColor("#24191b"), max(1.5, h * 0.075), Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(lid)
        # Ресницы на внешней стороне глаза.
        lash_pen = QPen(QColor("#211719"), max(1.0, h * 0.035), Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap)
        painter.setPen(lash_pen)
        for t, dx, dy in [(0.10, -0.035, -0.11), (0.20, -0.02, -0.09),
                          (0.88, 0.02, -0.08), (0.96, 0.04, -0.10)]:
            px = x + w * t
            py = cy - h * (0.10 + 0.06 * amount)
            painter.drawLine(QPointF(px, py), QPointF(px + w * dx, py + h * dy))

    def draw_mouth(self, painter, rect, level):
        """Четыре стилизованные формы рта вместо растягивания овала."""
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        cx = x + w / 2
        base_y = y + h * 0.53
        # level 0 — закрытые губы, 1 — маленькое «а», 2 — открытая речь.
        if level < 0.12:
            p = QPainterPath()
            p.moveTo(x + w * .08, base_y)
            p.cubicTo(x + w * .32, base_y - h * .17, x + w * .68, base_y - h * .17,
                      x + w * .92, base_y)
            painter.setPen(QPen(self.mouth_color, max(1.4, h * .09), Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(p)
            return

        openness = 0.16 + 0.62 * level
        mw = w * (0.48 + 0.20 * level)
        mh = h * openness
        top = base_y - mh * .48
        left = cx - mw / 2
        mouth = QPainterPath()
        mouth.moveTo(cx, top)
        mouth.cubicTo(left + mw * .24, top - mh * .20,
                      left + mw * .78, top - mh * .20, cx + mw / 2, top)
        mouth.cubicTo(cx + mw * .43, top + mh * .82,
                      cx - mw * .43, top + mh * .82, cx - mw / 2, top)
        mouth.closeSubpath()
        painter.setPen(QPen(QColor("#633638"), max(1.0, h * .035)))
        painter.setBrush(QColor("#35191e"))
        painter.drawPath(mouth)

        if level > .22:
            teeth = QPainterPath()
            teeth.moveTo(cx - mw * .31, top + mh * .08)
            teeth.cubicTo(cx - mw * .14, top + mh * .02,
                          cx + mw * .14, top + mh * .02, cx + mw * .31, top + mh * .08)
            teeth.lineTo(cx + mw * .27, top + mh * .28)
            teeth.cubicTo(cx, top + mh * .34, cx, top + mh * .34,
                          cx - mw * .27, top + mh * .28)
            teeth.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#f1e9df"))
            painter.drawPath(teeth)

        if level > .58:
            tongue = QPainterPath()
            tongue.moveTo(cx - mw * .22, top + mh * .66)
            tongue.cubicTo(cx - mw * .10, top + mh * .52,
                           cx + mw * .10, top + mh * .52, cx + mw * .22, top + mh * .66)
            tongue.cubicTo(cx + mw * .12, top + mh * .92,
                           cx - mw * .12, top + mh * .92, cx - mw * .22, top + mh * .66)
            tongue.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#bd5968"))
            painter.drawPath(tongue)

        # Верхняя и нижняя губы — тонкая обводка, не геометрический овал.
        lip = QPainterPath()
        lip.moveTo(cx - mw * .51, top + mh * .02)
        lip.cubicTo(cx - mw * .20, top - mh * .20,
                    cx + mw * .20, top - mh * .20, cx + mw * .51, top + mh * .02)
        lip.cubicTo(cx + mw * .34, top + mh * 1.02,
                    cx - mw * .34, top + mh * 1.02, cx - mw * .51, top + mh * .02)
        painter.setPen(QPen(self.mouth_color, max(1.2, h * .055)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(lip)

    def paintEvent(self, event):
        if not self.pixmap:
            painter = QPainter(self)
            painter.setPen(QColor("#aaaaBB"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Загрузите изображение")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        dr = self.get_display_rect()
        # PySide6 не принимает пару (QRectF, QPixmap): указываем sourceRect явно.
        painter.drawPixmap(dr, self.pixmap, QRectF(self.pixmap.rect()))

        # Рисуем анимацию в исходных координатах — масштабирование единообразно.
        if self.blink > 0 or self.talk > 0:
            painter.save()
            painter.translate(dr.topLeft())
            painter.scale(dr.width() / self.pixmap.width(),
                          dr.height() / self.pixmap.height())
            if HAS_INPAINT:
                # При моргании очищаются только глаза; при речи — только рот.
                if self.blink > 0:
                    painter.drawPixmap(QPointF(0, 0), self.clean_eye_pixmap)
                elif self.talk > 0:
                    painter.drawPixmap(QPointF(0, 0), self.clean_mouth_pixmap)

            if self.blink > 0:
                for zone in ("Left Eye", "Right Eye"):
                    poly = self.polygons.get(zone)
                    if poly and len(poly) >= 3:
                        self.draw_closed_eye(painter, poly.boundingRect(), self.blink)

            if self.talk > 0 and "Mouth" in self.polygons:
                self.draw_mouth(painter, self.polygons["Mouth"].boundingRect(), self.talk)
            painter.restore()

        if self.show_guides:
            for zone, poly in self.polygons.items():
                color = ZONE_COLORS[zone]
                sp = QPolygonF([self.img_to_screen(p) for p in poly])
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(color, 1.5, Qt.PenStyle.DashLine))
                painter.drawPolygon(sp)
                painter.setBrush(QBrush(color))
                for point in sp:
                    painter.drawEllipse(point, 3, 3)

        if not self.face_rect.isEmpty():
            painter.setPen(QPen(QColor("#ffd166"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            top_left = self.img_to_screen(self.face_rect.topLeft())
            bottom_right = self.img_to_screen(self.face_rect.bottomRight())
            painter.drawRect(QRectF(top_left, bottom_right))

        if self.current_points:
            painter.setPen(QPen(QColor("#00ff88"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(self.current_points) - 1):
                painter.drawLine(self.current_points[i], self.current_points[i + 1])
            painter.setBrush(QColor("#00ff88"))
            for point in self.current_points:
                painter.drawEllipse(self.img_to_screen(point), 3.5, 3.5)


class Avatar2DWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1250, 850)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_time = 0.0
        self.anim_state = "idle"
        self.is_speaking = False
        self._blink_phase = "idle"
        self._blink_elapsed = 0.0
        self._next_blink_ms = random.randint(2200, 5200)
        self._speech_phase = 0.0
        self.setup_ui()
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)
        self.auto_timer.start(30)
        self._auto_clock = QElapsedTimer()
        self._auto_clock.start()

    def set_emotion(self, name: str, weight: float):
        self.emotion = (name, max(0., min(1., weight)))

    def get_canvas(self):
        return self.canvas

    def load_ai2d(self, path):
        """Загружает экспортированный проект .ai2d вместе с исходным изображением и ригом."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        raw = base64.b64decode(data["base_image_b64"])
        from PySide6.QtGui import QPixmap
        pm = QPixmap()
        if not pm.loadFromData(raw):
            raise ValueError("Не удалось декодировать изображение из .ai2d")
        self.canvas.pixmap = pm
        self.canvas.clean_pixmap = pm
        self.canvas.image_path = str(path)
        self.canvas.polygons = {
            zone: QPolygonF([QPointF(float(p[0]), float(p[1])) for p in points])
            for zone, points in data.get("rigging", {}).items()
        }
        self.canvas.rebuild_clean_image()
        self.canvas.show_guides = False
        self.canvas.update()
        self.setWindowTitle(f"{APP_NAME} — {Path(path).name}")

    def set_speaking(self, speaking):
        self.is_speaking = bool(speaking)
        if not self.is_speaking:
            self.canvas.talk = 0.0
        self.canvas.update()

    def _auto_tick(self):
        dt = min(0.08, self._auto_clock.restart() / 1000.0)
        # Нерегулярное моргание, без вмешательства в исходные черты лица.
        if self._blink_phase == "idle":
            self._next_blink_ms -= int(dt * 1000)
            if self._next_blink_ms <= 0 and all(z in self.canvas.polygons for z in ("Left Eye", "Right Eye")):
                self._blink_phase = "closing"
                self._blink_elapsed = 0.0
        else:
            self._blink_elapsed += dt
            close_d, hold_d, open_d = 0.09, 0.045, 0.13
            if self._blink_phase == "closing":
                p = min(1.0, self._blink_elapsed / close_d)
                self.canvas.blink = p * p * (3 - 2 * p)
                if p >= 1.0:
                    self._blink_phase = "hold"; self._blink_elapsed = 0.0
            elif self._blink_phase == "hold":
                self.canvas.blink = 1.0
                if self._blink_elapsed >= hold_d:
                    self._blink_phase = "opening"; self._blink_elapsed = 0.0
            elif self._blink_phase == "opening":
                p = min(1.0, self._blink_elapsed / open_d)
                self.canvas.blink = 1.0 - p * p * (3 - 2 * p)
                if p >= 1.0:
                    self.canvas.blink = 0.0
                    self._blink_phase = "idle"
                    self._next_blink_ms = random.randint(2200, 5200)
        if self.is_speaking and "Mouth" in self.canvas.polygons:
            self._speech_phase += dt
            # Непрерывная, но неритмичная артикуляция на протяжении всего TTS.
            wave = 0.5 + 0.5 * math.sin(self._speech_phase * 17.0 + 0.7 * math.sin(self._speech_phase * 3.1))
            syllable = 0.35 + 0.65 * max(0.0, math.sin(self._speech_phase * 6.4))
            self.canvas.talk = min(1.0, 0.06 + 0.78 * wave * syllable)
        else:
            self.canvas.talk = 0.0
        self.canvas.update()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        left = QWidget()
        left.setFixedWidth(270)
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("<h2>AI 2D Studio 5.2</h2>"))

        load = QPushButton("🖼 Загрузить оригинал")
        load.clicked.connect(self.load_image)
        ll.addWidget(load)
        load_project = QPushButton("📦 Открыть проект .ai2d")
        load_project.clicked.connect(self.open_ai2d)
        ll.addWidget(load_project)

        auto = QPushButton("🎯 Выделить область лица")
        auto.clicked.connect(self.begin_face_region_selection)
        ll.addWidget(auto)
        self.auto_hint = QLabel(
            "Выдели лицо мышью: зажми ЛКМ и протяни рамку от лба до подбородка."
        )
        self.auto_hint.setWordWrap(True)
        ll.addWidget(self.auto_hint)
        starter = QPushButton("✨ Создать стартовую разметку")
        starter.clicked.connect(self.create_starter_rig)
        ll.addWidget(starter)

        ll.addWidget(QLabel("<b>Разметка зон</b>"))
        self.list_zones = QListWidget()
        for zone, name in ZONE_NAMES.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, zone)
            self.list_zones.addItem(item)
        self.list_zones.setCurrentRow(0)
        self.list_zones.currentItemChanged.connect(self.on_zone_change)
        ll.addWidget(self.list_zones)

        ll.addWidget(QLabel("ЛКМ — точки по контуру.\nПКМ — завершить область.\nОбводите глаз целиком, включая ресницы;\nрот — по внешнему контуру губ."))
        clear = QPushButton("Удалить разметку зоны")
        clear.clicked.connect(self.clear_zone)
        ll.addWidget(clear)

        self.guides = QPushButton("Скрыть контуры разметки")
        self.guides.setCheckable(True)
        self.guides.setChecked(True)
        self.guides.clicked.connect(self.toggle_guides)
        ll.addWidget(self.guides)

        ll.addSpacing(12)
        ll.addWidget(QLabel("<b>Проверка анимации</b>"))
        blink = QPushButton("👁 Моргание")
        blink.clicked.connect(self.do_blink)
        ll.addWidget(blink)
        talk = QPushButton("🗣 Движение рта")
        talk.clicked.connect(self.do_talk)
        ll.addWidget(talk)

        export = QPushButton("💾 Экспорт .ai2d")
        export.clicked.connect(self.export_for_ai)
        ll.addWidget(export)
        ll.addStretch()

        self.canvas = AvatarCanvas()
        right = QWidget()
        right.setFixedWidth(235)
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("<b>Журнал</b>"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background:#111120;color:#ddd;font-family:Consolas;font-size:11px;")
        rl.addWidget(self.log)
        rl.addWidget(QLabel(
            "Восстановление областей: " +
            ("OpenCV включён" if HAS_INPAINT else "OpenCV не найден — поставьте opencv-python")
        ))

        layout.addWidget(left)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(right)
        self.setStyleSheet("""
            QMainWindow,QWidget { background:#1a1a2e;color:#e5e5ed;font-family:'Segoe UI',Arial; }
            QPushButton { background:#30304a;border:1px solid #50506b;border-radius:5px;padding:9px;font-weight:600; }
            QPushButton:hover { background:#414160;border-color:#8c8cc0; }
            QListWidget { background:#111120;border:1px solid #44445c; }
            QListWidget::item:selected { background:#55557b; }
        """)
        self.on_zone_change(self.list_zones.currentItem())

    def begin_face_region_selection(self):
        if not self.canvas.pixmap:
            QMessageBox.information(self, "Нет изображения", "Сначала загрузи изображение.")
            return
        self.canvas.current_points.clear()
        self.canvas.is_drawing = False
        self.canvas.face_select_mode = True
        self.auto_hint.setText("Режим выбора: зажми ЛКМ и протяни рамку вокруг лица.")
        self.log_msg("Выдели прямоугольную область лица.")

    def on_face_region_selected(self, rect):
        if rect.width() < 30 or rect.height() < 30:
            self.auto_hint.setText("Рамка слишком маленькая. Повтори выделение.")
            self.log_msg("Область лица слишком мала.")
            return
        self.canvas.face_rect = rect
        self.auto_hint.setText("Область задана. Нажми «Создать стартовую разметку».")
        self.log_msg(f"Область лица: {rect.width():.0f} × {rect.height():.0f} px.")
        self.canvas.update()

    def create_starter_rig(self):
        """Создаёт редактируемые стартовые контуры внутри выбранной области лица."""
        r = self.canvas.face_rect
        if r.isEmpty() or r.width() < 30 or r.height() < 30:
            QMessageBox.information(self, "Сначала выдели лицо",
                                    "Нажми «Выделить область лица» и обведи рамкой лицо.")
            return
        # Относительные координаты — только стартовые ориентиры, не выдаются за распознавание.
        def oval(cx, cy, rx, ry, count=24):
            return QPolygonF([
                QPointF(cx + rx * math.cos(2 * math.pi * i / count),
                        cy + ry * math.sin(2 * math.pi * i / count))
                for i in range(count)
            ])
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        self.canvas.polygons["Left Eye"] = oval(x + w * .34, y + h * .39, w * .16, h * .055)
        self.canvas.polygons["Right Eye"] = oval(x + w * .66, y + h * .39, w * .16, h * .055)
        self.canvas.polygons["Mouth"] = oval(x + w * .50, y + h * .73, w * .105, h * .035)
        self.canvas.current_points.clear()
        self.canvas.is_drawing = False
        self.canvas.rebuild_clean_image()
        self.canvas.update()
        self.auto_hint.setText("Стартовые зоны созданы. Подгони каждый контур по рисунку персонажа.")
        self.log_msg("Созданы стартовые контуры глаз и рта по рамке лица; это ориентиры, не AI-детекция.")
        QMessageBox.information(
            self, "Стартовая разметка готова",
            "Созданы три отдельные зоны. Это начальные ориентиры по пропорциям рамки, "
            "а не распознавание деталей рисунка. Проверь и подгони их по контуру персонажа."
        )

    def log_msg(self, msg):
        self.log.append("> " + msg)

    def on_zone_change(self, item):
        if item:
            # Незавершённый контур нельзя переносить в другую зону.
            if self.canvas.is_drawing or self.canvas.current_points:
                self.canvas.current_points.clear()
                self.canvas.is_drawing = False
                self.canvas.update()
                self.log_msg("Незавершённая разметка отменена при переключении зоны.")
            self.canvas.active_zone = item.data(Qt.ItemDataRole.UserRole)
            self.log_msg("Выбрана зона: " + item.text())

    def open_ai2d(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть проект аватара", "", "AI Avatar (*.ai2d)")
        if not path:
            return
        try:
            self.load_ai2d(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка проекта", str(e))

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "",
                                              "Изображения (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        try:
            self.canvas.load_image(path)
            self.log_msg("Загружено: " + path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def auto_detect_face(self):
        # Совместимость со старым именем обработчика; теперь используем
        # полуавтоматический выбор области, поскольку FaceMesh не рассчитан на anime art.
        self.begin_face_region_selection()

    def clear_zone(self):
        zone = self.canvas.active_zone
        self.canvas.polygons.pop(zone, None)
        self.canvas.rebuild_clean_image()
        self.canvas.update()
        self.log_msg(f"Удалена зона: {ZONE_NAMES[zone]}")

    def toggle_guides(self):
        self.canvas.show_guides = self.guides.isChecked()
        self.guides.setText("Скрыть контуры разметки" if self.guides.isChecked()
                            else "Показать контуры разметки")
        self.canvas.update()

    def do_blink(self):
        if not all(z in self.canvas.polygons for z in ("Left Eye", "Right Eye")):
            QMessageBox.warning(self, "Не хватает разметки",
                                "Разметьте оба глаза. Для синхронного моргания нужны обе зоны.")
            return
        self.start_animation("blink")

    def do_talk(self):
        if "Mouth" not in self.canvas.polygons:
            QMessageBox.warning(self, "Не хватает разметки", "Сначала разметьте рот.")
            return
        self.set_speaking(True)
        self.start_animation("talk")

    def start_animation(self, state):
        self.anim_state = state
        self.anim_time = 0.0
        self.anim_timer.start(16)
        self.log_msg("Запущена анимация: " + state)

    def update_animation(self):
        self.anim_time += 0.016
        if self.anim_state == "blink":
            # Короткое закрытие с небольшим удержанием и плавным открытием.
            t = self.anim_time
            close_time, hold_time, open_time = 0.085, 0.045, 0.12
            if t < close_time:
                v = t / close_time
                self.canvas.blink = v * v * (3 - 2 * v)
            elif t < close_time + hold_time:
                self.canvas.blink = 1.0
            elif t < close_time + hold_time + open_time:
                v = (t - close_time - hold_time) / open_time
                self.canvas.blink = 1.0 - v * v * (3 - 2 * v)
            else:
                self.canvas.blink = 0.0
                self.finish_animation()
        elif self.anim_state == "talk":
            t = self.anim_time
            # Неравномерные слоги: короткие закрытия чередуются с разными гласными.
            cycle = (0.5 + 0.5 * math.sin(t * 8.2 + 0.7 * math.sin(t * 2.1)))
            pulse = max(0.0, math.sin(t * 5.4 + 0.6)) ** 1.7
            self.canvas.talk = min(1.0, 0.08 + 0.72 * cycle * pulse)
            if t >= 3.0:
                self.canvas.talk = 0.0
                self.finish_animation()
        self.canvas.update()

    def finish_animation(self):
        self.anim_state = "idle"
        self.anim_timer.stop()
        self.canvas.blink = 0.0
        if not self.is_speaking:
            self.canvas.talk = 0.0
        self.canvas.update()

    def export_for_ai(self):
        if not self.canvas.pixmap or not self.canvas.polygons:
            QMessageBox.warning(self, "Экспорт", "Сначала загрузите изображение и разметьте зоны.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "avatar.ai2d",
                                              "AI Avatar (*.ai2d)")
        if not path:
            return
        if not path.lower().endswith(".ai2d"):
            path += ".ai2d"
        try:
            with open(self.canvas.image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("ascii")
            rigging = {
                zone: [[float(p.x()), float(p.y())] for p in poly]
                for zone, poly in self.canvas.polygons.items()
            }
            data = {
                "format": "AI2D",
                "version": "1.0",
                "base_image_b64": img_b64,
                "original_width": self.canvas.pixmap.width(),
                "original_height": self.canvas.pixmap.height(),
                "rigging": rigging,
                "animation": {
                    "eye_method": "inpaint_background_and_bezier_eyelid",
                    "mouth_method": "viseme_like_vector_shapes",
                    "coordinate_system": "original_image_pixels"
                }
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_msg("Экспортировано: " + path)
            QMessageBox.information(self, "Готово", "Проект .ai2d сохранён.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))



class CompanionAvatarWindow(Avatar2DWindow):
    """Компактное отдельное окно персонажа; редактор остаётся самостоятельным."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCP-079 · Аватар")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(380, 540)
        self.setMinimumSize(260, 340)
        self.setMaximumSize(900, 1100)
        self.setWindowOpacity(0.97)
        self._drag_offset = None

        # Заменяем интерфейс редактора на компактное окно-компаньон.
        old_canvas = self.canvas
        self.canvas = AvatarCanvas(self)
        self.canvas.setMinimumSize(100, 100)
        self.canvas.setStyleSheet("background:#10101b;border:0;")
        self.canvas.show_guides = False

        root = QWidget(self)
        root.setObjectName("companionRoot")
        root.setStyleSheet("""
            QWidget#companionRoot { background:#11111d; color:#e9e7f2; }
            QLabel#companionStatus { color:#aaa6c2; padding:5px 9px; }
            QPushButton { background:#28263d; color:#eee; border:1px solid #45415f;
                          border-radius:6px; padding:5px 9px; }
            QPushButton:hover { background:#393452; }
        """)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        top = QHBoxLayout()
        name = QLabel("✦  SCP-079 · DERENGUH")
        name.setStyleSheet("font-weight:700;letter-spacing:1px;color:#c9b8ff;padding:5px;")
        top.addWidget(name, 1)
        minimize = QPushButton("—")
        minimize.setFixedWidth(32)
        minimize.clicked.connect(self.showMinimized)
        close = QPushButton("×")
        close.setFixedWidth(32)
        close.clicked.connect(self.hide)
        top.addWidget(minimize)
        top.addWidget(close)
        outer.addLayout(top)
        outer.addWidget(self.canvas, 1)
        self.status_label = QLabel("● Ожидаю")
        self.status_label.setObjectName("companionStatus")
        outer.addWidget(self.status_label)
        self.setCentralWidget(root)
        self.canvas.show_guides = False
        self.canvas.update()
        self._old_canvas = old_canvas

    def set_speaking(self, speaking):
        super().set_speaking(speaking)
        if hasattr(self, "status_label"):
            self.status_label.setText("● Говорю" if self.is_speaking else "● Ожидаю")
            self.status_label.setStyleSheet(
                "color:#d7aaff;padding:5px 9px;" if self.is_speaking
                else "color:#aaa6c2;padding:5px 9px;"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

def main():
    app = QApplication(sys.argv)
    window = Avatar2DWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
