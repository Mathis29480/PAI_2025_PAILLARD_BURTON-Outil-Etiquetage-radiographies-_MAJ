# -*- coding: utf-8 -*-
"""
Gestionnaire de données pour l'outil d'étiquetage de radiographies.
"""

import csv
from datetime import datetime, timedelta
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

        root_for_csv = self.dataset_path
        if self.dataset_path.name.lower() == "images":
            root_for_csv = self.dataset_path.parent

        csv_files = list(root_for_csv.glob("**/*.csv"))
        if csv_files:
            data_entry = [f for f in csv_files if "Data_Entry" in f.name]
            if data_entry:
                self._load_metadata_from_csv(data_entry[0], root_for_csv)
            else:
                self._load_metadata_from_csv(csv_files[0], root_for_csv)
        else:
            self._generate_default_metadata()

        bbox_files = list(root_for_csv.glob("**/BBox_List_2017.csv"))
        if bbox_files:
            self._load_bbox_from_csv(bbox_files[0])

    def _load_bbox_from_csv(self, csv_path: Path) -> None:
        """Charge les bounding boxes NIH comme annotations initiales."""
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_name = row.get("Image Index")
                    if not image_name:
                        continue
                    image_path = self.dataset_path / image_name
                    if not image_path.exists():
                        image_path = self.dataset_path / "images" / image_name
                    if not image_path.exists():
                        continue
                    key = str(image_path)
                    if key not in self.annotations:
                        self.annotations[key] = []
                    try:
                        bbox_str = row.get("Bbox [x,y,w,h]", "")
                        if not bbox_str:
                            continue
                        parts = bbox_str.split(",")
                        if len(parts) < 4:
                            continue
                        x, y, w, h = (
                            float(parts[0]),
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3]),
                        )
                    except (ValueError, TypeError) as e:
                        print(f"Erreur parsing bbox pour {image_name}: {e}")
                        continue
                    pathology = row.get("Finding Label", "")
                    self.annotations[key].append({
                        "type": "box",
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                        "pathology": pathology,
                        "author": "auto_bbox",
                        "date": datetime.now().isoformat(),
                        "confidence": 0.5,
                    })
        except Exception as e:
            print(f"Erreur lors du chargement des bounding boxes: {e}")

    def _load_metadata_from_csv(self, csv_path: Path, root_for_csv: Path) -> None:
        """Charge les métadonnées depuis un fichier CSV (Data_Entry NIH)."""
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    image_name = row.get("Image Index", row.get("filename", ""))
                    if not image_name:
                        continue
                    image_path = self.dataset_path / image_name
                    if not image_path.exists():
                        image_path = self.dataset_path / "images" / image_name
                    if not image_path.exists():
                        continue
                    follow_up = row.get("Follow-up #", "000")
                    try:
                        follow_num = int(follow_up)
                        base_date = datetime(2000, 1, 1)
                        date = (base_date + timedelta(days=follow_num)).strftime("%Y-%m-%d")
                    except ValueError:
                        date = datetime.now().strftime("%Y-%m-%d")
                    self.metadata[str(image_path)] = {
                        "patient_id": row.get("Patient ID", ""),
                        "age": row.get("Patient Age", ""),
                        "sex": row.get("Patient Gender", ""),
                        "view": row.get("View Position", ""),
                        "date": date,
                        "pathologies": self._parse_pathologies(row),
                        "filename": image_name,
                    }
        except Exception as e:
            print(f"Erreur lors du chargement du CSV: {e}")
            self._generate_default_metadata()

    def _parse_pathologies(self, row: Dict) -> List[str]:
        """Parse les pathologies depuis une ligne CSV (Finding Labels)."""
        labels = row.get("Finding Labels") or row.get("Finding Label") or ""
        labels = labels.strip()
        if not labels or labels == "No Finding":
            return []
        return [lbl.strip() for lbl in labels.split("|") if lbl.strip()]

    def _generate_default_metadata(self) -> None:
        """Génère des métadonnées par défaut pour les images."""
        for img_path in self.images:
            self.metadata[str(img_path)] = {
                "patient_id": f"P{hash(str(img_path)) % 10000:04d}",
                "age": "Unknown",
                "sex": "Unknown",
                "view": "PA",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "pathologies": [],
                "filename": img_path.name,
            }
