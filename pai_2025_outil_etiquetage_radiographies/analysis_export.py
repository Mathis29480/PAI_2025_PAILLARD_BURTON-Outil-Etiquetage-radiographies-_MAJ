"""
Export des analyses (matrice de co-occurrence, rapport HTML exemples de localisation).
"""

import csv
import os
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager

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


def _cooccurrence_from_csv(csv_path: str) -> tuple:
    labels = list(PATHOLOGY_ORDER)
    n = len(labels)
    label_to_idx = {p: i for i, p in enumerate(labels)}
    per_image = defaultdict(set)
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return labels, [[0] * n for _ in range(n)]
        fieldnames = [c.strip() for c in reader.fieldnames]
        has_finding_labels = any(
            "finding" in c.lower() and "label" in c.lower() for c in fieldnames
        )
        if not has_finding_labels:
            for c in fieldnames:
                if c.strip() == "Finding Labels":
                    has_finding_labels = True
                    break
        image_col = "Image Index" if "Image Index" in fieldnames else "Image"
        if image_col not in fieldnames:
            image_col = fieldnames[0]
        for row in reader:
            row = {k.strip(): v for k, v in row.items() if k}
            img = row.get("Image Index", row.get("Image", row.get(image_col, "")))
            if not img:
                continue
            if has_finding_labels:
                raw = ""
                for k, v in row.items():
                    if "finding" in k.lower() and "label" in k.lower():
                        raw = v or ""
                        break
                if not raw:
                    raw = row.get("Finding Labels", "")
                for p in raw.split("|"):
                    p = p.strip()
                    if p and p in label_to_idx:
                        per_image[img].add(p)
            else:
                patho = row.get("Pathology", row.get("pathology", "")) or ""
                patho = patho.strip()
                if patho and patho in label_to_idx:
                    per_image[img].add(patho)
    matrix = [[0] * n for _ in range(n)]
    for pathologies in per_image.values():
        for p1 in pathologies:
            idx1 = label_to_idx[p1]
            for p2 in pathologies:
                idx2 = label_to_idx[p2]
                matrix[idx1][idx2] += 1
    return labels, matrix


def export_cooccurrence_csv(
    data_manager: "DataManager", filepath: str, from_csv_only: bool = True
) -> None:
    labels, matrix = data_manager.get_cooccurrence_data(from_csv_only=from_csv_only)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([""] + labels)
        for i, row in enumerate(matrix):
            w.writerow([labels[i]] + row)


def _draw_heatmap(ax: object, labels: list, matrix: list, title: str) -> None:
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt
    import numpy as np

    n = len(labels)
    arr = np.array(matrix, dtype=float)
    arr_plot = np.where(arr > 0, arr, np.nan)
    if not np.any(arr > 0):
        arr_plot = arr
        im = ax.imshow(arr_plot, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
    else:
        vmax = float(np.nanmax(arr_plot))
        vmin = max(1.0, float(np.nanmin(arr_plot)))
        norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
        im = ax.imshow(arr_plot, cmap="YlOrRd", aspect="auto", norm=norm)
    plt.colorbar(im, ax=ax, label="Co-occurrences (échelle log)")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_title(title)


def export_cooccurrence_heatmap(
    data_manager: "DataManager", filepath: str, from_csv_only: bool = True
) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    labels, matrix = data_manager.get_cooccurrence_data(from_csv_only=from_csv_only)
    n = len(labels)
    if n == 0:
        return False
    fig, ax = plt.subplots(figsize=(10, 8))
    _draw_heatmap(
        ax,
        labels,
        matrix,
        "Matrice de co-occurrence des 14 pathologies thoraciques",
    )
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    return True


def export_localization_report(data_manager: "DataManager", filepath: str) -> None:
    ref_dir = Path(data_manager.reference_images_dir)
    report_dir = Path(filepath).resolve().parent
    pathologies = list(data_manager.PATHOLOGY_ORDER)
    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Exemples de localisation</title>",
        "<style>body{font-family:sans-serif;margin:20px;} h1{color:#333;} "
        "h2{margin-top:24px;color:#555;} .grid{display:flex;flex-wrap:wrap;gap:12px;} "
        ".cell{text-align:center;} .cell img{max-width:200px;height:auto;border:1px solid #ccc;} "
        ".cell p{margin:4px 0;font-size:12px;}</style></head><body>",
        "<h1>Exemples de localisation par pathologie</h1>",
        "<p>Images avec bounding boxes (dossier annotations_visualized).</p>",
    ]
    for patho in pathologies:
        sub = ref_dir / patho
        if not sub.exists():
            continue
        imgs = sorted(sub.glob("*_annotated.png"))[:8]
        if not imgs:
            continue
        lines.append(f"<h2>{patho}</h2><div class='grid'>")
        for img in imgs:
            try:
                rel = os.path.relpath(img.resolve(), report_dir)
            except ValueError:
                rel = str(img)
            lines.append(
                f"<div class='cell'><img src='{rel}' alt='{img.name}'/><p>{img.name}</p></div>"
            )
        lines.append("</div>")
    lines.append("</body></html>")
    out = Path(filepath)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def export_cooccurrence_from_csv_file(csv_path: str, output_dir: str) -> tuple:
    labels, matrix = _cooccurrence_from_csv(csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / "cooccurrence_pathologies.csv"
    with open(csv_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([""] + labels)
        for i, row in enumerate(matrix):
            w.writerow([labels[i]] + row)
    png_out = out_dir / "cooccurrence_heatmap.png"
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if len(labels) > 0:
            fig, ax = plt.subplots(figsize=(10, 8))
            _draw_heatmap(
                ax, labels, matrix, "Matrice de co-occurrence (à partir du CSV)"
            )
            plt.tight_layout()
            plt.savefig(png_out, dpi=150, bbox_inches="tight")
            plt.close()
            return (str(csv_out), str(png_out))
    except ImportError:
        pass
    return (str(csv_out), None)
