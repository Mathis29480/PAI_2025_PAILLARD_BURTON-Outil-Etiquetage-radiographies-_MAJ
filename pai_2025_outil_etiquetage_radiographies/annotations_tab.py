"""
Onglet d'annotation des radiographies (canvas, liste, références, undo/redo).
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager

PATHOLOGY_COLORS = {
    "Atelectasis": QColor(255, 0, 0),
    "Cardiomegaly": QColor(0, 255, 0),
    "Effusion": QColor(0, 0, 255),
    "Infiltration": QColor(255, 255, 0),
    "Mass": QColor(255, 0, 255),
    "Nodule": QColor(0, 255, 255),
    "Pneumonia": QColor(255, 165, 0),
    "Pneumothorax": QColor(255, 20, 147),
    "Consolidation": QColor(128, 0, 128),
    "Edema": QColor(0, 128, 255),
    "Emphysema": QColor(128, 255, 0),
    "Fibrosis": QColor(255, 128, 0),
    "Pleural_Thickening": QColor(128, 128, 255),
    "Hernia": QColor(255, 128, 128),
    "No Finding": QColor(128, 128, 128),
}


def _annotation_color(ann: dict) -> QColor:
    c = ann.get("color")
    if c is None:
        return PATHOLOGY_COLORS.get(ann.get("pathology", ""), QColor(255, 0, 0))
    if hasattr(c, "red"):
        return c
    if isinstance(c, dict):
        return QColor(c.get("r", 255), c.get("g", 0), c.get("b", 0), c.get("a", 255))
    return QColor(255, 0, 0)


class ReferenceImageCell(QWidget):
    """Cellule affichant une image de référence avec ses bounding boxes."""

    def __init__(self, image_path: str = "", annotations: list | None = None) -> None:
        super().__init__()
        self.image_path = str(image_path) if image_path else ""
        self.annotations = annotations or []
        self.pixmap: QPixmap | None = None
        self.setMinimumSize(120, 120)
        self.setMaximumSize(280, 280)
        self.setFixedSize(200, 200)
        self._load_image()

    def set_reference(self, image_path: str, annotations: list) -> None:
        self.image_path = str(image_path)
        self.annotations = annotations or []
        self._load_image()
        self.update()

    def _load_image(self) -> None:
        try:
            p = Path(self.image_path)
            if not p.exists():
                self.pixmap = None
                return
            img = Image.open(self.image_path).convert("RGB")
            w, h = img.size
            bpl = w * 3
            qimg = QImage(img.tobytes(), w, h, bpl, QImage.Format.Format_RGB888)
            self.pixmap = QPixmap.fromImage(qimg.copy())
        except Exception as e:
            print(f"Erreur chargement ref {self.image_path}: {e}")
            self.pixmap = None

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        if not self.pixmap or self.pixmap.isNull():
            painter.fillRect(r, Qt.GlobalColor.darkGray)
            painter.setPen(Qt.GlobalColor.gray)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "Réf.")
            return
        pw, ph = self.pixmap.width(), self.pixmap.height()
        if pw <= 0 or ph <= 0:
            return
        scale = min(r.width() / pw, r.height() / ph)
        w, h = int(pw * scale), int(ph * scale)
        x0, y0 = (r.width() - w) // 2, (r.height() - h) // 2
        painter.drawPixmap(x0, y0, w, h, self.pixmap)
        for ann in self.annotations:
            if ann.get("type") != "box":
                continue
            x = ann.get("x", 0)
            y = ann.get("y", 0)
            wb = ann.get("width", 0)
            hb = ann.get("height", 0)
            if wb <= 0 or hb <= 0:
                continue
            sx = x0 + (x / pw) * w
            sy = y0 + (y / ph) * h
            sw, sh = (wb / pw) * w, (hb / ph) * h
            pen = QPen(_annotation_color(ann), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(sx), int(sy), int(sw), int(sh))


class ReferenceImagesPanel(QWidget):
    """Panneau références : une image à la fois, Précédent/Suivant."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(260)
        self.setMinimumHeight(280)
        layout = QVBoxLayout(self)
        self.title = QLabel("Références : pathologie")
        self.title.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title)
        nav = QHBoxLayout()
        self.prev_btn = QPushButton("← Précédent")
        self.prev_btn.clicked.connect(self._prev)
        nav.addWidget(self.prev_btn)
        self.index_label = QLabel("Réf. 0 / 0")
        self.index_label.setStyleSheet("font-weight: bold;")
        nav.addWidget(self.index_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.next_btn = QPushButton("Suivant →")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)
        self.cell = ReferenceImageCell("", [])
        layout.addWidget(self.cell, alignment=Qt.AlignmentFlag.AlignCenter)
        self.placeholder = QLabel(
            "Aucune référence pour cette pathologie.\n"
            "Annotez des images puis sauvegardez pour en créer."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: gray; padding: 20px;")
        self.placeholder.setWordWrap(True)
        self.refs: list[tuple[str, list]] = []
        self.ref_index = 0

    def _prev(self) -> None:
        if not self.refs:
            return
        self.ref_index = (self.ref_index - 1) % len(self.refs)
        self._show_current()

    def _next(self) -> None:
        if not self.refs:
            return
        self.ref_index = (self.ref_index + 1) % len(self.refs)
        self._show_current()

    def _show_current(self) -> None:
        if not self.refs:
            return
        self.ref_index = max(0, min(self.ref_index, len(self.refs) - 1))
        path, anns = self.refs[self.ref_index]
        self.cell.set_reference(path, anns)
        self.index_label.setText(f"Réf. {self.ref_index + 1} / {len(self.refs)}")
        self.prev_btn.setEnabled(len(self.refs) > 1)
        self.next_btn.setEnabled(len(self.refs) > 1)

    def set_pathology(self, pathology: str) -> None:
        self.title.setText(f"Références : {pathology}")

    def set_references(self, refs: list[tuple[str, list]]) -> None:
        self.refs = refs
        self.ref_index = 0
        if not refs:
            self.cell.hide()
            if self.placeholder.parent() is None:
                self.layout().addWidget(self.placeholder)
            self.placeholder.show()
            self.index_label.setText("Réf. 0 / 0")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        else:
            self.placeholder.hide()
            if self.placeholder.parent():
                self.layout().removeWidget(self.placeholder)
            self.cell.show()
            self._show_current()
        self.update()


class AnnotationCanvas(QWidget):
    """Canvas pour dessiner des bounding boxes sur l'image."""

    def __init__(self) -> None:
        super().__init__()
        self.image: Image.Image | None = None
        self.image_pixmap: QPixmap | None = None
        self.annotations: list = []
        self.current_annotation: dict | None = None
        self.drawing_mode: str | None = None
        self.start_point: QPoint | None = None
        self.current_pathology = "Atelectasis"
        self.current_color = QColor(255, 0, 0)
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.last_pan_point: QPoint | None = None
        self.annotation_created: Callable[[dict], None] | None = None
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)

    def load_image(self, image_path: str) -> None:
        try:
            self.image = Image.open(image_path).convert("RGB")
            w, h = self.image.size
            bpl = w * 3
            qimg = QImage(self.image.tobytes(), w, h, bpl, QImage.Format.Format_RGB888)
            self.image_pixmap = QPixmap.fromImage(qimg.copy())
            self.zoom_factor = 1.0
            self.pan_offset = QPoint(0, 0)
            self.update()
        except Exception as e:
            print(f"Erreur chargement image: {e}")

    def set_annotations(self, annotations: list) -> None:
        self.annotations = annotations
        self.update()

    def set_drawing_mode(self, mode: str) -> None:
        self.drawing_mode = mode

    def set_pathology(self, pathology: str) -> None:
        self.current_pathology = pathology

    def set_color(self, color: QColor) -> None:
        self.current_color = color

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drawing_mode == "box":
                img_point = self._screen_to_image(event.position().toPoint())
                if self.start_point is None:
                    self.start_point = img_point
                    self.current_annotation = {
                        "type": "box",
                        "x": self.start_point.x(),
                        "y": self.start_point.y(),
                        "width": 0,
                        "height": 0,
                        "pathology": self.current_pathology,
                        "color": self.current_color,
                    }
                    self.update()
                else:
                    x = min(self.start_point.x(), img_point.x())
                    y = min(self.start_point.y(), img_point.y())
                    width = abs(img_point.x() - self.start_point.x())
                    height = abs(img_point.y() - self.start_point.y())
                    if width > 1 and height > 1:
                        annotation = {
                            "type": "box",
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "pathology": self.current_pathology,
                            "color": self.current_color,
                        }
                        if callable(self.annotation_created):
                            self.annotation_created(annotation)
                    self.current_annotation = None
                    self.start_point = None
                    self.update()
        elif event.button() in (Qt.MouseButton.MiddleButton,) or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.last_pan_point = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drawing_mode == "box" and self.current_annotation and self.start_point:
            end_point = self._screen_to_image(event.position().toPoint())
            x = min(self.start_point.x(), end_point.x())
            y = min(self.start_point.y(), end_point.y())
            width = abs(end_point.x() - self.start_point.x())
            height = abs(end_point.y() - self.start_point.y())
            self.current_annotation["x"] = x
            self.current_annotation["y"] = y
            self.current_annotation["width"] = width
            self.current_annotation["height"] = height
            self.update()
        elif self.last_pan_point:
            delta = event.position().toPoint() - self.last_pan_point
            self.pan_offset += delta
            self.last_pan_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.last_pan_point = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor + delta / 1200.0))
            self.update()
        else:
            super().wheelEvent(event)

    def _screen_to_image(self, screen_point: QPoint) -> QPoint:
        if not self.image_pixmap or not self.image:
            return QPoint(0, 0)
        dw = self.image_pixmap.width() * self.zoom_factor
        dh = self.image_pixmap.height() * self.zoom_factor
        ox = (self.width() - dw) / 2 + self.pan_offset.x()
        oy = (self.height() - dh) / 2 + self.pan_offset.y()
        rel_x = screen_point.x() - ox
        rel_y = screen_point.y() - oy
        if dw > 0 and dh > 0:
            img_x = (rel_x / dw) * self.image.size[0]
            img_y = (rel_y / dh) * self.image.size[1]
        else:
            img_x = img_y = 0
        img_x = max(0, min(self.image.size[0] - 1, img_x))
        img_y = max(0, min(self.image.size[1] - 1, img_y))
        return QPoint(int(img_x), int(img_y))

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.image_pixmap or not self.image:
            painter.fillRect(self.rect(), Qt.GlobalColor.lightGray)
            return
        iw, ih = self.image.size[0], self.image.size[1]
        dw = self.image_pixmap.width() * self.zoom_factor
        dh = self.image_pixmap.height() * self.zoom_factor
        cx = (self.width() - dw) / 2 + self.pan_offset.x()
        cy = (self.height() - dh) / 2 + self.pan_offset.y()
        painter.drawPixmap(int(cx), int(cy), int(dw), int(dh), self.image_pixmap)
        for ann in self.annotations:
            if ann.get("type") != "box":
                continue
            color = ann.get("color", self.current_color)
            if hasattr(color, "red"):
                pen = QPen(color, 2)
            else:
                pen = QPen(_annotation_color(ann), 2)
            painter.setPen(pen)
            x = cx + (ann["x"] / iw) * dw
            y = cy + (ann["y"] / ih) * dh
            w = (ann["width"] / iw) * dw
            h = (ann["height"] / ih) * dh
            painter.drawRect(int(x), int(y), int(w), int(h))
        if self.current_annotation and self.current_annotation.get("type") == "box":
            pen = QPen(self.current_color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            x = cx + (self.current_annotation["x"] / iw) * dw
            y = cy + (self.current_annotation["y"] / ih) * dh
            w = (self.current_annotation["width"] / iw) * dw
            h = (self.current_annotation["height"] / ih) * dh
            painter.drawRect(int(x), int(y), int(w), int(h))


class AnnotationsTab(QWidget):
    """Onglet Annotations : liste images, canvas, pathologie, références, undo/redo."""

    def __init__(self, data_manager: "DataManager", current_user: str) -> None:
        super().__init__()
        self.data_manager = data_manager
        self.current_user = current_user
        self.current_image_path: str | None = None
        self.current_annotations: list = []
        self.history: list[dict] = []
        self.history_index = -1
        self.init_ui()

    def init_ui(self) -> None:
        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        main_area = QWidget()
        main_layout = QVBoxLayout()
        self.central_display = QWidget()
        self.central_layout = QVBoxLayout(self.central_display)
        self.central_layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = AnnotationCanvas()
        self.canvas.annotation_created = self.on_annotation_created
        self.reference_images_panel = ReferenceImagesPanel()
        self.double_view_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.central_layout.addWidget(self.canvas)
        main_layout.addWidget(self.central_display, 1)

        nav_layout = QHBoxLayout()
        self.prev_image_btn = QPushButton("← Image précédente")
        self.prev_image_btn.clicked.connect(self.go_to_previous_image)
        nav_layout.addWidget(self.prev_image_btn)
        self.image_nav_label = QLabel("Image 0 / 0")
        self.image_nav_label.setStyleSheet("font-weight: bold;")
        nav_layout.addWidget(
            self.image_nav_label, alignment=Qt.AlignmentFlag.AlignCenter
        )
        self.next_image_btn = QPushButton("Image suivante →")
        self.next_image_btn.clicked.connect(self.go_to_next_image)
        nav_layout.addWidget(self.next_image_btn)
        main_layout.addLayout(nav_layout)

        tools_layout = QHBoxLayout()
        self.box_button = QPushButton("Bounding Box")
        self.box_button.setCheckable(True)
        self.box_button.clicked.connect(lambda: self.set_drawing_mode("box"))
        tools_layout.addWidget(self.box_button)
        self.pathology_combo = QComboBox()
        self.pathology_combo.addItems(
            [
                "Atelectasis",
                "Cardiomegaly",
                "Effusion",
                "Infiltration",
                "Mass",
                "Nodule",
                "Pneumonia",
                "Pneumothorax",
                "Consolidation",
                "Edema",
                "Emphysema",
                "Fibrosis",
                "Pleural_Thickening",
                "Hernia",
                "No Finding",
            ]
        )
        self.pathology_combo.currentTextChanged.connect(self.on_pathology_changed)
        tools_layout.addWidget(QLabel("Pathologie:"))
        tools_layout.addWidget(self.pathology_combo)
        self.color_button = QPushButton("Couleur")
        self.color_button.clicked.connect(self.choose_color)
        tools_layout.addWidget(self.color_button)
        tools_layout.addStretch()
        self.double_view_check = QPushButton("Vue double")
        self.double_view_check.setCheckable(True)
        self.double_view_check.clicked.connect(self.toggle_double_view)
        tools_layout.addWidget(self.double_view_check)
        main_layout.addLayout(tools_layout)

        action_layout = QHBoxLayout()
        self.save_button = QPushButton("Sauvegarder")
        self.save_button.clicked.connect(self.save_annotations)
        action_layout.addWidget(self.save_button)
        self.undo_button = QPushButton("Annuler (Ctrl+Z)")
        self.undo_button.clicked.connect(self.undo)
        action_layout.addWidget(self.undo_button)
        self.redo_button = QPushButton("Refaire (Ctrl+Shift+Z)")
        self.redo_button.clicked.connect(self.redo)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        main_area.setLayout(main_layout)
        splitter.addWidget(main_area)
        side_panel = self._create_side_panel()
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        layout.addWidget(splitter)
        self.setLayout(layout)
        self.set_drawing_mode("box")

    def _create_side_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout()
        annotations_group = QGroupBox("Annotations")
        annotations_layout = QVBoxLayout()
        self.annotations_list = QListWidget()
        self.annotations_list.itemClicked.connect(self.on_annotation_selected)
        annotations_layout.addWidget(self.annotations_list)
        edit_layout = QHBoxLayout()
        self.edit_button = QPushButton("Modifier")
        self.edit_button.clicked.connect(self.edit_annotation)
        edit_layout.addWidget(self.edit_button)
        self.delete_button = QPushButton("Supprimer")
        self.delete_button.clicked.connect(self.delete_annotation)
        edit_layout.addWidget(self.delete_button)
        annotations_layout.addLayout(edit_layout)
        annotations_group.setLayout(annotations_layout)
        layout.addWidget(annotations_group)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def set_drawing_mode(self, mode: str) -> None:
        self.canvas.set_drawing_mode(mode)
        self.box_button.setChecked(mode == "box")

    def on_pathology_changed(self, pathology: str) -> None:
        self.canvas.set_pathology(pathology)
        self.refresh_reference_panel()

    def choose_color(self) -> None:
        color = QColorDialog.getColor(
            self.canvas.current_color, self, "Choisir une couleur"
        )
        if color.isValid():
            self.canvas.set_color(color)

    def load_image(self, image_path: str) -> None:
        self.current_image_path = image_path
        self.canvas.load_image(image_path)
        if self.double_view_check.isChecked():
            self.refresh_reference_panel()
        self.refresh_annotations()
        self._update_image_nav()

    def _update_image_nav(self) -> None:
        images = self.data_manager.images
        n = len(images)
        if n == 0:
            self.image_nav_label.setText("Image 0 / 0")
            self.prev_image_btn.setEnabled(False)
            self.next_image_btn.setEnabled(False)
            return
        try:
            idx = next(
                i
                for i, p in enumerate(images)
                if str(p) == str(self.current_image_path)
            )
        except StopIteration:
            idx = self.data_manager.current_image_index
            if idx < 0 or idx >= n:
                idx = 0
        self.data_manager.current_image_index = idx
        self.image_nav_label.setText(f"Image {idx + 1} / {n}")
        self.prev_image_btn.setEnabled(True)
        self.next_image_btn.setEnabled(True)

    def go_to_previous_image(self) -> None:
        images = self.data_manager.images
        if not images:
            return
        n = len(images)
        if self.current_image_path is None:
            new_idx = n - 1
        else:
            try:
                idx = next(
                    i
                    for i, p in enumerate(images)
                    if str(p) == str(self.current_image_path)
                )
            except StopIteration:
                idx = self.data_manager.current_image_index
            new_idx = (idx - 1) % n
        self.data_manager.current_image_index = new_idx
        self.load_image(str(images[new_idx]))

    def go_to_next_image(self) -> None:
        images = self.data_manager.images
        if not images:
            return
        n = len(images)
        if self.current_image_path is None:
            new_idx = 0
        else:
            try:
                idx = next(
                    i
                    for i, p in enumerate(images)
                    if str(p) == str(self.current_image_path)
                )
            except StopIteration:
                idx = self.data_manager.current_image_index
            new_idx = (idx + 1) % n
        self.data_manager.current_image_index = new_idx
        self.load_image(str(images[new_idx]))

    def refresh_annotations(self) -> None:
        if not self.current_image_path:
            return
        self.current_annotations = self.data_manager.get_image_annotations(
            self.current_image_path
        )
        self.canvas.set_annotations(self.current_annotations)
        self.update_annotations_list()

    def update_annotations_list(self) -> None:
        self.annotations_list.clear()
        for idx, ann in enumerate(self.current_annotations):
            text = f"{ann.get('pathology', 'Unknown')} - "
            text += f"({ann.get('x', 0):.0f}, {ann.get('y', 0):.0f}, "
            text += f"{ann.get('width', 0):.0f}x{ann.get('height', 0):.0f})"
            if ann.get("author"):
                text += f" - {ann['author']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.annotations_list.addItem(item)

    def on_annotation_selected(self, item: QListWidgetItem) -> None:
        pass

    def edit_annotation(self) -> None:
        current_item = self.annotations_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Attention", "Sélectionnez une annotation à modifier"
            )
            return
        idx = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.current_annotations):
            ann = self.current_annotations[idx]
            pathology, ok = QInputDialog.getItem(
                self,
                "Modifier annotation",
                "Pathologie:",
                [
                    "Atelectasis",
                    "Cardiomegaly",
                    "Effusion",
                    "Infiltration",
                    "Mass",
                    "Nodule",
                    "Pneumonia",
                    "Pneumothorax",
                    "Consolidation",
                    "Edema",
                    "Emphysema",
                    "Fibrosis",
                    "Pleural_Thickening",
                    "Hernia",
                    "No Finding",
                ],
                current=ann.get("pathology", "Atelectasis"),
            )
            if ok:
                self.save_state()
                ann["pathology"] = pathology
                self.refresh_annotations()

    def delete_annotation(self) -> None:
        current_item = self.annotations_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Attention", "Sélectionnez une annotation à supprimer"
            )
            return
        idx = current_item.data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.current_annotations):
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Supprimer cette annotation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_state()
                del self.current_annotations[idx]
                if self.current_image_path:
                    self.data_manager.annotations[self.current_image_path] = (
                        self.current_annotations
                    )
                self.refresh_annotations()

    def save_annotations(self) -> None:
        if not self.current_image_path:
            return
        self.data_manager.annotations[self.current_image_path] = (
            self.current_annotations
        )
        self.data_manager.save_annotations(self.current_image_path)
        QMessageBox.information(self, "Succès", "Annotations sauvegardées")

    def save_state(self) -> None:
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]
        state = {
            "annotations": [ann.copy() for ann in self.current_annotations],
            "image_path": self.current_image_path,
        }
        self.history.append(state)
        self.history_index = len(self.history) - 1
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self) -> None:
        if self.history_index > 0:
            self.history_index -= 1
            state = self.history[self.history_index]
            self.current_annotations = [ann.copy() for ann in state["annotations"]]
            if self.current_image_path:
                self.data_manager.annotations[self.current_image_path] = (
                    self.current_annotations
                )
            self.refresh_annotations()

    def redo(self) -> None:
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state = self.history[self.history_index]
            self.current_annotations = [ann.copy() for ann in state["annotations"]]
            if self.current_image_path:
                self.data_manager.annotations[self.current_image_path] = (
                    self.current_annotations
                )
            self.refresh_annotations()

    def on_annotation_created(self, annotation: dict) -> None:
        self.save_state()
        annotation["author"] = self.current_user
        annotation["date"] = datetime.now().isoformat()
        annotation["confidence"] = 1.0
        self.current_annotations.append(annotation)
        if self.current_image_path:
            self.data_manager.annotations[self.current_image_path] = (
                self.current_annotations
            )
        self.refresh_annotations()

    def toggle_double_view(self) -> None:
        checked = self.double_view_check.isChecked()
        if checked:
            self.central_layout.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.double_view_splitter.addWidget(self.canvas)
            self.double_view_splitter.addWidget(self.reference_images_panel)
            self.central_layout.addWidget(self.double_view_splitter)
            self.double_view_splitter.setStretchFactor(0, 11)
            self.double_view_splitter.setStretchFactor(1, 9)
            self.reference_images_panel.show()
            self.refresh_reference_panel()
        else:
            self.central_layout.removeWidget(self.double_view_splitter)
            self.double_view_splitter.removeWidget(self.canvas)
            self.double_view_splitter.removeWidget(self.reference_images_panel)
            self.central_layout.addWidget(self.canvas)
        self.central_display.update()
        self.update()

    def refresh_reference_panel(self) -> None:
        if not self.double_view_check.isChecked():
            return
        pathology = self.pathology_combo.currentText()
        self.reference_images_panel.set_pathology(pathology)
        refs = self.data_manager.get_reference_images_for_pathology(
            pathology, limit=4, exclude_path=self.current_image_path
        )
        self.reference_images_panel.set_references(refs)
