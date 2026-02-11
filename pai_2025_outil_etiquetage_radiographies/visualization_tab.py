# -*- coding: utf-8 -*-
"""
Onglet de visualisation des radiographies.
"""

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel, QScrollArea


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
