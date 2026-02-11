## PAI 2025 - Outil d'étiquetage de radiographies

Outil de visualisation et d'annotation de radiographies (bounding boxes par pathologie), avec export JSON/CSV, statistiques et rapports de co-occurrence.

Projet initialisé avec [supop-pai-cookiecutter-template](https://github.com/ClementPinard/supop-pai-cookiecuttter-template).

**Auteurs :** Mathis Paillard, Cristobal Burton Selva.

## Installation

- Installer [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Cloner le dépôt puis :

```bash
uv sync
```

Sur macOS 12 (x86_64), PySide6 est contraint à une version &lt; 6.10 pour la compatibilité des wheels.

## Lancer l'application (interface Qt)

```bash
uv run main_qt
```

Après connexion (auth), charger un dataset via **Fichier > Charger un dataset** (dossier contenant des images et optionnellement un CSV type Data_Entry). Les onglets **Visualisation** et **Annotations** permettent de parcourir les images, filtrer, dessiner des bounding boxes par pathologie, sauvegarder (Ctrl+S), annuler/refaire (Ctrl+Z / Ctrl+Shift+Z).

### Alternative : NiceGUI

```bash
uv run main_ng
```

## Development

### How to run pre-commit

```bash
uvx pre-commit run -a
```

Alternatively, you can install it so that it runs before every commit :

```bash
uvx pre-commit install
```

### How to run tests

```bash
uv sync --group test
uv run coverage run -m pytest -v
```

### How to run type checking

```bash
uvx pyright pai_2025_outil_etiquetage_radiographies --pythonpath .venv/bin/python
```

### How to build docs

```bash
uv sync --group docs
cd docs && uv run make html
```

#### How to run autobuild for docs

```bash
uv sync --group docs
cd docs && make livehtml
