# -*- coding: utf-8 -*-
"""
Gestionnaire de données pour l'outil d'étiquetage de radiographies.
"""

from pathlib import Path

from typing import List, Dict, Optional


class DataManager:
    """Gère les données (images, métadonnées, annotations)."""

    def __init__(self) -> None:
        self.dataset_path: Optional[Path] = None
        self.images: List[Path] = []
        self.metadata: Dict[str, Dict] = {}
        self.annotations: Dict[str, list] = {}
        self.current_image_index: int = 0
        self.annotations_dir = Path("annotations")
        self.annotations_dir.mkdir(exist_ok=True)
        self.reference_images_dir = Path("annotations_visualized")
        self.reference_images_dir.mkdir(exist_ok=True)

    def load_dataset(self, dataset_path: str) -> None:
        """Charge un dataset depuis un dossier (découverte des images)."""
        self.dataset_path = Path(dataset_path)
        self.images = []
        self.metadata = {}
        self.annotations = {}

        image_extensions = [".png", ".jpg", ".jpeg"]
        for ext in image_extensions:
            self.images.extend(list(self.dataset_path.glob(f"**/*{ext}")))
            self.images.extend(list(self.dataset_path.glob(f"**/*{ext.upper()}")))
        self.images = sorted(set(self.images))
