# -*- coding: utf-8 -*-
"""
Gestionnaire de données pour l'outil d'étiquetage de radiographies.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtGui import QColor
from typing import Dict, List, Optional, Tuple


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

        self._load_existing_annotations()

    def _load_existing_annotations(self) -> None:
        """Charge les annotations existantes depuis le dossier annotations."""
        for img_path in self.images:
            annotation_file = self.annotations_dir / f"{Path(img_path).stem}.json"
            if annotation_file.exists():
                try:
                    with open(annotation_file, encoding="utf-8") as f:
                        data = json.load(f)
                        annotations = data.get("annotations", [])
                        for ann in annotations:
                            if "color" in ann and isinstance(ann["color"], dict):
                                c = ann["color"]
                                ann["color"] = QColor(
                                    c.get("r", 255),
                                    c.get("g", 0),
                                    c.get("b", 0),
                                    c.get("a", 255),
                                )
                        self.annotations[str(img_path)] = annotations
                except Exception as e:
                    print(f"Erreur lors du chargement des annotations pour {img_path}: {e}")
                    self.annotations[str(img_path)] = []
            else:
                self.annotations[str(img_path)] = []

    def save_annotations(self, image_path: str) -> None:
        """Sauvegarde les annotations d'une image en JSON."""
        if image_path not in self.annotations:
            return
        serializable_annotations = []
        for ann in self.annotations[image_path]:
            ann_copy = ann.copy()
            if "color" in ann_copy:
                color = ann_copy["color"]
                if hasattr(color, "red"):
                    ann_copy["color"] = {
                        "r": color.red(),
                        "g": color.green(),
                        "b": color.blue(),
                        "a": color.alpha(),
                    }
            serializable_annotations.append(ann_copy)
        annotation_file = self.annotations_dir / f"{Path(image_path).stem}.json"
        data = {
            "image_path": image_path,
            "metadata": self.metadata.get(image_path, {}),
            "annotations": serializable_annotations,
            "last_modified": datetime.now().isoformat(),
        }
        with open(annotation_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if serializable_annotations:
            self._generate_reference_image(image_path, serializable_annotations)

    def _generate_reference_image(self, image_path: str, annotations: List[Dict]) -> None:
        """Génère une image de référence avec les annotations dessinées."""
        try:
            img = Image.open(image_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            colors = {
                "Atelectasis": (255, 0, 0),
                "Cardiomegaly": (0, 255, 0),
                "Effusion": (0, 0, 255),
                "Infiltration": (255, 255, 0),
                "Mass": (255, 0, 255),
                "Nodule": (0, 255, 255),
                "Pneumonia": (255, 165, 0),
                "Pneumothorax": (255, 20, 147),
                "Consolidation": (128, 0, 128),
                "Edema": (0, 128, 255),
                "Emphysema": (128, 255, 0),
                "Fibrosis": (255, 128, 0),
                "Pleural_Thickening": (128, 128, 255),
                "Hernia": (255, 128, 128),
                "No Finding": (128, 128, 128),
            }
            pathologies_in_image = set()
            for ann in annotations:
                if ann.get("type") != "box":
                    continue
                x = int(ann.get("x", 0))
                y = int(ann.get("y", 0))
                w = int(ann.get("width", 0))
                h = int(ann.get("height", 0))
                pathology = ann.get("pathology", "Unknown")
                pathologies_in_image.add(pathology)
                if pathology in colors:
                    color = colors[pathology]
                elif isinstance(ann.get("color"), dict):
                    c = ann["color"]
                    color = (c.get("r", 255), c.get("g", 0), c.get("b", 0))
                else:
                    color = (255, 0, 0)
                draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
                try:
                    try:
                        font = ImageFont.truetype(
                            "/System/Library/Fonts/Helvetica.ttc", 16
                        )
                    except OSError:
                        font = ImageFont.load_default()
                    label = pathology
                    if ann.get("author"):
                        label += f" ({ann['author']})"
                    bbox = draw.textbbox((x, y - 20), label, font=font)
                    bbox = (bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2)
                    draw.rectangle(bbox, fill=(0, 0, 0))
                    draw.text((x, y - 20), label, fill=color, font=font)
                except Exception:
                    pass
            image_stem = Path(image_path).stem
            for pathology in pathologies_in_image:
                if pathology and pathology != "Unknown":
                    pathology_dir = self.reference_images_dir / pathology
                    pathology_dir.mkdir(exist_ok=True)
                    output_path = pathology_dir / f"{image_stem}_annotated.png"
                    img.save(output_path, "PNG")
            if not pathologies_in_image or all(p == "Unknown" for p in pathologies_in_image):
                output_path = self.reference_images_dir / f"{image_stem}_annotated.png"
                img.save(output_path, "PNG")
        except Exception as e:
            print(f"Erreur lors de la génération de l'image de référence: {e}")

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

    def get_current_image(self) -> Optional[str]:
        """Retourne le chemin de l'image actuelle."""
        if 0 <= self.current_image_index < len(self.images):
            return str(self.images[self.current_image_index])
        return None

    def get_image_metadata(self, image_path: str) -> Dict:
        """Retourne les métadonnées d'une image."""
        return self.metadata.get(image_path, {})

    def get_image_annotations(self, image_path: str) -> List[Dict]:
        """Retourne les annotations d'une image."""
        return self.annotations.get(image_path, [])

    def get_statistics(self) -> Dict:
        """Retourne les statistiques des annotations."""
        stats = {
            "total_images": len(self.images),
            "annotated_images": sum(1 for annos in self.annotations.values() if annos),
            "total_annotations": sum(len(annos) for annos in self.annotations.values()),
            "annotations_by_pathology": {},
            "annotations_by_author": {},
            "average_time": 0,
        }
        for annotations in self.annotations.values():
            for ann in annotations:
                path = ann.get("pathology", "Unknown")
                stats["annotations_by_pathology"][path] = (
                    stats["annotations_by_pathology"].get(path, 0) + 1
                )
                author = ann.get("author", "Unknown")
                stats["annotations_by_author"][author] = (
                    stats["annotations_by_author"].get(author, 0) + 1
                )
        return stats

    def filter_images(self, filters: Dict) -> List[str]:
        """Filtre les images selon les critères."""
        filtered = []
        for img_path in self.images:
            metadata = self.get_image_metadata(str(img_path))
            match = True
            if filters.get("pathology") and filters["pathology"] != "Toutes":
                if filters["pathology"] not in metadata.get("pathologies", []):
                    match = False
            if filters.get("sex") and filters["sex"] != "Tous":
                if metadata.get("sex", "").upper() != filters["sex"].upper():
                    match = False
            if filters.get("view") and filters["view"] != "Toutes":
                if metadata.get("view", "").strip().upper() != filters["view"].strip().upper():
                    match = False
            if filters.get("date_min"):
                if (metadata.get("date", "") or "") < filters["date_min"]:
                    match = False
            if filters.get("date_max"):
                if (metadata.get("date", "") or "") > filters["date_max"]:
                    match = False
            if filters.get("age_min"):
                try:
                    age = int(str(metadata.get("age", "0")).replace("Y", ""))
                    if age < filters["age_min"]:
                        match = False
                except ValueError:
                    pass
            if filters.get("age_max"):
                try:
                    age = int(str(metadata.get("age", "0")).replace("Y", ""))
                    if age > filters["age_max"]:
                        match = False
                except ValueError:
                    pass
            if filters.get("has_annotations") is not None:
                has_annos = len(self.get_image_annotations(str(img_path))) > 0
                if has_annos != filters["has_annotations"]:
                    match = False
            if match:
                filtered.append(str(img_path))
        return filtered

    PATHOLOGY_ORDER = [
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
    ]

    def get_cooccurrence_data(
        self, from_csv_only: bool = True
    ) -> Tuple[List[str], List[List[int]]]:
        """Matrice de co-occurrence des pathologies (métadonnées CSV ou annotations)."""
        labels = list(self.PATHOLOGY_ORDER)
        n = len(labels)
        label_to_idx = {p: i for i, p in enumerate(labels)}
        matrix = [[0] * n for _ in range(n)]
        for img_path in self.images:
            path_str = str(img_path)
            pathologies = set(self.metadata.get(path_str, {}).get("pathologies", []))
            if not pathologies and not from_csv_only:
                for ann in self.annotations.get(path_str, []):
                    p = ann.get("pathology")
                    if p and p in label_to_idx:
                        pathologies.add(p)
            for p1 in pathologies:
                if p1 not in label_to_idx:
                    continue
                idx1 = label_to_idx[p1]
                for p2 in pathologies:
                    if p2 not in label_to_idx:
                        continue
                    idx2 = label_to_idx[p2]
                    matrix[idx1][idx2] += 1
        return labels, matrix
