"""Tests pour le DataManager."""

import csv
import json
from pathlib import Path

import pytest
from PIL import Image

from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager


@pytest.fixture
def temp_dataset(tmp_path):
    """Crée un mini dataset (2 images PNG) dans un répertoire temporaire."""
    (tmp_path / "img1.png").touch()
    (tmp_path / "img2.png").touch()
    # Créer de vraies images PNG minimales pour que load_dataset les trouve
    img = Image.new("L", (10, 10), color=128)
    img.save(tmp_path / "img1.png")
    img.save(tmp_path / "img2.png")
    return tmp_path


@pytest.fixture
def temp_dataset_with_csv(tmp_path):
    """Dataset avec un CSV type Data_Entry (Image Index, Finding Labels, etc.)."""
    img = Image.new("L", (10, 10), color=128)
    img.save(tmp_path / "a.png")
    img.save(tmp_path / "b.png")
    csv_path = tmp_path / "Data_Entry_2017.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Image Index", "Finding Labels", "Patient ID", "Patient Age", "Patient Gender", "View Position", "Follow-up #"])
        w.writerow(["a.png", "Atelectasis|Effusion", "P001", "45", "M", "PA", "1"])
        w.writerow(["b.png", "No Finding", "P002", "60", "F", "AP", "2"])
    return tmp_path


def test_data_manager_init():
    """DataManager s'initialise avec des listes/dicts vides."""
    dm = DataManager()
    assert dm.images == []
    assert dm.metadata == {}
    assert dm.annotations == {}
    assert dm.current_image_index == 0
    assert dm.annotations_dir.name == "annotations"
    assert dm.reference_images_dir.name == "annotations_visualized"


def test_load_dataset_discovers_images(temp_dataset):
    """load_dataset découvre les images PNG."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    assert len(dm.images) == 2
    stems = {Path(p).stem for p in dm.images}
    assert stems == {"img1", "img2"}
    assert len(dm.metadata) == 2
    assert len(dm.annotations) == 2


def test_load_dataset_with_csv(temp_dataset_with_csv):
    """load_dataset charge les métadonnées depuis un CSV type Data_Entry."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset_with_csv))
    assert len(dm.images) == 2
    for img_path in dm.images:
        meta = dm.get_image_metadata(str(img_path))
        assert "filename" in meta
        assert "pathologies" in meta or "patient_id" in meta


def test_get_statistics_empty():
    """get_statistics sur un DataManager vide."""
    dm = DataManager()
    stats = dm.get_statistics()
    assert stats["total_images"] == 0
    assert stats["annotated_images"] == 0
    assert stats["total_annotations"] == 0
    assert stats["annotations_by_pathology"] == {}
    assert stats["annotations_by_author"] == {}


def test_get_statistics_after_load(temp_dataset):
    """get_statistics après chargement d'un dataset."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    stats = dm.get_statistics()
    assert stats["total_images"] == 2
    assert stats["annotated_images"] == 0
    assert stats["total_annotations"] == 0


def test_get_current_image_empty():
    """get_current_image sans images retourne None."""
    dm = DataManager()
    assert dm.get_current_image() is None


def test_get_current_image(temp_dataset):
    """get_current_image retourne l'image à l'index courant."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    dm.current_image_index = 0
    assert dm.get_current_image() is not None
    assert dm.get_current_image() == str(dm.images[0])


def test_get_image_metadata(temp_dataset):
    """get_image_metadata retourne un dict (défaut ou depuis CSV)."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path = str(dm.images[0])
    meta = dm.get_image_metadata(path)
    assert isinstance(meta, dict)
    assert "filename" in meta


def test_get_image_annotations_empty(temp_dataset):
    """get_image_annotations sans annotations retourne []."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path = str(dm.images[0])
    assert dm.get_image_annotations(path) == []


def test_add_annotation(temp_dataset):
    """add_annotation ajoute une annotation en mémoire."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path = str(dm.images[0])
    dm.add_annotation(path, {"type": "box", "x": 10, "y": 20, "width": 30, "height": 40, "pathology": "Atelectasis"})
    annos = dm.get_image_annotations(path)
    assert len(annos) == 1
    assert annos[0]["pathology"] == "Atelectasis"
    assert annos[0]["x"] == 10


def test_filter_images_all(temp_dataset):
    """filter_images sans critères retourne toutes les images."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    filtered = dm.filter_images({})
    assert len(filtered) == 2


def test_filter_images_pathology(temp_dataset_with_csv):
    """filter_images par pathologie."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset_with_csv))
    filtered = dm.filter_images({"pathology": "Atelectasis"})
    assert len(filtered) >= 1


def test_export_import_json(temp_dataset, tmp_path):
    """Export JSON puis import restaure les annotations."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path = str(dm.images[0])
    dm.add_annotation(path, {"type": "box", "x": 0, "y": 0, "width": 10, "height": 10, "pathology": "Nodule"})
    json_path = tmp_path / "out.json"
    dm.export_annotations(str(json_path), "JSON")

    dm2 = DataManager()
    dm2.load_dataset(str(temp_dataset))
    dm2.import_annotations(str(json_path))
    annos = dm2.get_image_annotations(path)
    assert len(annos) == 1
    assert annos[0]["pathology"] == "Nodule"


def test_export_csv(temp_dataset, tmp_path):
    """Export CSV crée un fichier avec en-têtes."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path = str(dm.images[0])
    dm.add_annotation(path, {"type": "box", "x": 1, "y": 2, "width": 3, "height": 4, "pathology": "Mass"})
    csv_path = tmp_path / "out.csv"
    dm.export_annotations(str(csv_path), "CSV")
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8") as f:
        lines = f.readlines()
    assert "Image" in lines[0] and "Pathology" in lines[0]


def test_get_cooccurrence_data(temp_dataset):
    """get_cooccurrence_data retourne (labels, matrix)."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    labels, matrix = dm.get_cooccurrence_data(from_csv_only=True)
    assert len(labels) == 14
    assert "Atelectasis" in labels
    assert len(matrix) == 14
    assert all(len(row) == 14 for row in matrix)


def test_import_csv(temp_dataset, tmp_path):
    """Import depuis un CSV restaure les annotations."""
    dm = DataManager()
    dm.load_dataset(str(temp_dataset))
    path_str = str(dm.images[0])
    csv_path = tmp_path / "annotations.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Image", "Pathology", "X", "Y", "Width", "Height", "Author", "Date", "Confidence"])
        w.writerow([path_str, "Pneumonia", 5, 10, 20, 30, "test_user", "2025-01-01", "1.0"])
    dm.import_annotations(str(csv_path))
    annos = dm.get_image_annotations(path_str)
    assert len(annos) == 1
    assert annos[0]["pathology"] == "Pneumonia"
    assert annos[0]["x"] == 5.0
    assert annos[0]["width"] == 20.0


def test_pathology_order_constant():
    """PATHOLOGY_ORDER contient les 14 pathologies NIH."""
    assert len(DataManager.PATHOLOGY_ORDER) == 14
    assert "No Finding" not in DataManager.PATHOLOGY_ORDER
    assert "Atelectasis" in DataManager.PATHOLOGY_ORDER
    assert "Hernia" in DataManager.PATHOLOGY_ORDER
