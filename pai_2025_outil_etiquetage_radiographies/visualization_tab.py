# -*- coding: utf-8 -*-
"""
Onglet de visualisation des radiographies.
"""

from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QImage, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager


class ImageViewer(QScrollArea):
    """Widget pour afficher et manipuler les images (zoom, luminosité, contraste)."""

    def __init__(self) -> None:
        super().__init__()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.original_image: Image.Image | None = None
        self.current_image: np.ndarray | None = None
        self.zoom_factor = 1.0
        self.brightness = 0.0
        self.contrast = 1.0

    def load_image(self, image_path: str) -> None:
        """Charge une image (niveau de gris)."""
        try:
            self.original_image = Image.open(image_path).convert("L")
            self.current_image = np.array(self.original_image)
            self.update_display()
        except Exception as e:
            print(f"Erreur lors du chargement de l'image: {e}")

    def update_display(self) -> None:
        """Met à jour l'affichage avec contraste, luminosité et zoom."""
        if self.current_image is None:
            return
        img = self.current_image.copy().astype(np.float32)
        img = img * self.contrast + self.brightness
        img = np.clip(img, 0, 255).astype(np.uint8)
        height, width = img.shape
        q_image = QImage(
            img.data.tobytes(), width, height, width, QImage.Format.Format_Grayscale8
        )
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            int(width * self.zoom_factor),
            int(height * self.zoom_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())

    def set_zoom(self, factor: float) -> None:
        """Définit le facteur de zoom (0.1 à 5.0)."""
        self.zoom_factor = max(0.1, min(5.0, factor))
        self.update_display()

    def set_brightness(self, value: int) -> None:
        """Définit la luminosité (-100 à 100)."""
        self.brightness = value * 2.55
        self.update_display()

    def set_contrast(self, value: float) -> None:
        """Définit le contraste (0.5 à 2.0)."""
        self.contrast = value
        self.update_display()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom avec Ctrl + molette."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            zoom_delta = delta / 1200.0
            self.set_zoom(self.zoom_factor + zoom_delta)
        else:
            super().wheelEvent(event)


class VisualizationTab(QWidget):
    """Onglet de visualisation (filtres, viewer, navigation)."""

    def __init__(self, data_manager: "DataManager", current_user: str) -> None:
        super().__init__()
        self.data_manager = data_manager
        self.current_user = current_user
        self.filtered_images: list[str] = []
        self.current_filter_index = 0
        self.init_ui()

    def init_ui(self) -> None:
        """Initialise le layout (splitter, panneau latéral, zone image, contrôles, nav)."""
        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        side_panel = self._create_side_panel()
        splitter.addWidget(side_panel)

        main_area = QWidget()
        main_layout = QVBoxLayout()
        self.image_viewer = ImageViewer()
        main_layout.addWidget(self.image_viewer, 1)

        controls_group = QGroupBox("Contrôles d'affichage")
        controls_layout = QVBoxLayout()
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)
        controls_layout.addLayout(zoom_layout)
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Luminosité:"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(-100)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_label = QLabel("0")
        brightness_layout.addWidget(self.brightness_label)
        controls_layout.addLayout(brightness_layout)
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Contraste:"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setMinimum(50)
        self.contrast_slider.setMaximum(200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self._on_contrast_changed)
        contrast_layout.addWidget(self.contrast_slider)
        self.contrast_label = QLabel("1.0")
        contrast_layout.addWidget(self.contrast_label)
        controls_layout.addLayout(contrast_layout)
        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("◀ Précédent")
        self.prev_button.clicked.connect(self.previous_image)
        nav_layout.addWidget(self.prev_button)
        self.image_info_label = QLabel("Aucune image chargée")
        nav_layout.addWidget(self.image_info_label, 1)
        self.next_button = QPushButton("Suivant ▶")
        self.next_button.clicked.connect(self.next_image)
        nav_layout.addWidget(self.next_button)
        self.annotate_button = QPushButton("Annoter")
        self.annotate_button.clicked.connect(self.go_to_annotations)
        nav_layout.addWidget(self.annotate_button)
        main_layout.addLayout(nav_layout)

        main_area.setLayout(main_layout)
        splitter.addWidget(main_area)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        self.setLayout(layout)

    def _create_side_panel(self) -> QWidget:
        """Panneau latéral: infos patient + filtres."""
        panel = QWidget()
        layout = QVBoxLayout()
        info_group = QGroupBox("Informations patient")
        info_layout = QVBoxLayout()
        self.patient_info = QTextEdit()
        self.patient_info.setReadOnly(True)
        self.patient_info.setMaximumHeight(200)
        info_layout.addWidget(self.patient_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        filters_group = QGroupBox("Filtres")
        filters_layout = QVBoxLayout()
        filters_layout.addWidget(QLabel("Pathologie:"))
        self.pathology_filter = QComboBox()
        self.pathology_filter.addItems([
            "Toutes", "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration",
            "Mass", "Nodule", "Pneumonia", "Pneumothorax", "Consolidation",
            "Edema", "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia", "No Finding",
        ])
        filters_layout.addWidget(self.pathology_filter)
        filters_layout.addWidget(QLabel("Sexe:"))
        self.sex_filter = QComboBox()
        self.sex_filter.addItems(["Tous", "M", "F"])
        filters_layout.addWidget(self.sex_filter)
        filters_layout.addWidget(QLabel("Vue:"))
        self.view_filter = QComboBox()
        self.view_filter.addItems(["Toutes", "PA", "AP", "AP Supine"])
        filters_layout.addWidget(self.view_filter)
        age_layout = QHBoxLayout()
        age_layout.addWidget(QLabel("Âge:"))
        self.age_min = QSpinBox()
        self.age_min.setMinimum(0)
        self.age_min.setMaximum(120)
        self.age_min.setSpecialValueText("Min")
        age_layout.addWidget(self.age_min)
        age_layout.addWidget(QLabel("-"))
        self.age_max = QSpinBox()
        self.age_max.setMinimum(0)
        self.age_max.setMaximum(120)
        self.age_max.setSpecialValueText("Max")
        self.age_max.setValue(120)
        age_layout.addWidget(self.age_max)
        filters_layout.addLayout(age_layout)
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(2000, 1, 1))
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel("-"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate(2005, 1, 1))
        date_layout.addWidget(self.date_to)
        filters_layout.addLayout(date_layout)
        self.has_annotations_check = QCheckBox("Avec annotations")
        filters_layout.addWidget(self.has_annotations_check)
        apply_btn = QPushButton("Appliquer les filtres")
        apply_btn.clicked.connect(self.apply_filters)
        filters_layout.addWidget(apply_btn)
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def apply_filters(self) -> None:
        """Applique les filtres et charge la première image."""
        filters: dict[str, Any] = {
            "pathology": self.pathology_filter.currentText(),
            "sex": self.sex_filter.currentText(),
            "view": self.view_filter.currentText(),
            "age_min": self.age_min.value() if self.age_min.value() > 0 else None,
            "age_max": self.age_max.value() if self.age_max.value() < 120 else None,
            "date_min": self.date_from.date().toString("yyyy-MM-dd") if self.date_from.date().isValid() else None,
            "date_max": self.date_to.date().toString("yyyy-MM-dd") if self.date_to.date().isValid() else None,
            "has_annotations": self.has_annotations_check.isChecked() if self.has_annotations_check.isChecked() else None,
        }
        self.filtered_images = self.data_manager.filter_images(filters)
        self.current_filter_index = 0
        if self.filtered_images:
            self.load_current_image()
        else:
            self.image_info_label.setText("Aucune image ne correspond aux filtres")

    def load_current_image(self) -> None:
        """Charge l'image courante et met à jour les infos."""
        if not self.filtered_images:
            self.filtered_images = [str(img) for img in self.data_manager.images]
        if not (0 <= self.current_filter_index < len(self.filtered_images)):
            return
        image_path = self.filtered_images[self.current_filter_index]
        self.image_viewer.load_image(image_path)
        metadata = self.data_manager.get_image_metadata(image_path)
        annotations = self.data_manager.get_image_annotations(image_path)
        info_text = f"Fichier: {metadata.get('filename', 'N/A')}\n"
        info_text += f"Patient ID: {metadata.get('patient_id', 'N/A')}\n"
        info_text += f"Date: {metadata.get('date', 'N/A')}\n"
        info_text += f"Sexe: {metadata.get('sex', 'N/A')}\n"
        info_text += f"Âge: {metadata.get('age', 'N/A')}\n"
        info_text += f"Vue: {metadata.get('view', 'N/A')}\n"
        info_text += f"Pathologies: {', '.join(metadata.get('pathologies', [])) or 'Aucune'}\n"
        info_text += f"Annotations: {len(annotations)}"
        self.patient_info.setText(info_text)
        self.image_info_label.setText(
            f"Image {self.current_filter_index + 1}/{len(self.filtered_images)}"
        )

    def previous_image(self) -> None:
        """Image précédente."""
        if self.filtered_images:
            self.current_filter_index = (self.current_filter_index - 1) % len(self.filtered_images)
            self.load_current_image()

    def next_image(self) -> None:
        """Image suivante."""
        if self.filtered_images:
            self.current_filter_index = (self.current_filter_index + 1) % len(self.filtered_images)
            self.load_current_image()

    def go_to_annotations(self) -> None:
        """Passe à l'onglet Annotations et sélectionne l'image courante."""
        if not self.filtered_images or not (0 <= self.current_filter_index < len(self.filtered_images)):
            return
        image_path = self.filtered_images[self.current_filter_index]
        try:
            idx = next(i for i, img in enumerate(self.data_manager.images) if str(img) == image_path)
            self.data_manager.current_image_index = idx
        except StopIteration:
            pass
        parent = self.parent()
        while parent and not hasattr(parent, "tab_widget"):
            parent = parent.parent()
        if parent and hasattr(parent, "tab_widget"):
            parent.tab_widget.setCurrentIndex(1)
            if hasattr(parent, "annotations_tab") and hasattr(parent.annotations_tab, "load_image"):
                parent.annotations_tab.load_image(image_path)

    def _on_zoom_changed(self, value: int) -> None:
        self.zoom_label.setText(f"{value}%")
        self.image_viewer.set_zoom(value / 100.0)

    def _on_brightness_changed(self, value: int) -> None:
        self.brightness_label.setText(str(value))
        self.image_viewer.set_brightness(value)

    def _on_contrast_changed(self, value: int) -> None:
        factor = value / 100.0
        self.contrast_label.setText(f"{factor:.2f}")
        self.image_viewer.set_contrast(factor)

    def refresh_data(self) -> None:
        """Rafraîchit après chargement d'un dataset."""
        self.filtered_images = [str(img) for img in self.data_manager.images]
        self.current_filter_index = 0
        if self.filtered_images:
            self.load_current_image()
