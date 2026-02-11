"""Point d'entrée Qt (PySide6) pour l'outil d'étiquetage de radiographies."""

import sys

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pai_2025_outil_etiquetage_radiographies.auth_dialog import AuthDialog
from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager
from pai_2025_outil_etiquetage_radiographies.visualization_tab import VisualizationTab


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""

    def __init__(self, data_manager: DataManager, current_user: str) -> None:
        super().__init__()
        self.data_manager = data_manager
        self.current_user = current_user
        self.init_ui()

    def init_ui(self) -> None:
        """Initialise l'interface (titre, taille, onglets)."""
        self.setWindowTitle("Outil d'étiquetage de radiographies")
        self.setGeometry(100, 100, 1400, 900)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.visualization_tab = VisualizationTab(self.data_manager, self.current_user)
        self.tab_widget.addTab(self.visualization_tab, "Visualisation")

        placeholder_ann = QWidget()
        layout_ann = QVBoxLayout()
        layout_ann.addWidget(QLabel("Annotations — à venir"))
        placeholder_ann.setLayout(layout_ann)
        self.annotations_tab = placeholder_ann
        self.tab_widget.addTab(self.annotations_tab, "Annotations")

        self.create_menu_bar()
        self.setup_shortcuts()

        self.statusBar().showMessage(f"Connecté en tant que: {self.current_user}")

    def setup_shortcuts(self) -> None:
        """Raccourcis clavier (sauvegarde, undo, redo, export)."""
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_current)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._redo)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self._export_annotations)

    def _save_current(self) -> None:
        pass  # Phase 4 (AnnotationsTab)

    def _undo(self) -> None:
        pass  # Phase 4

    def _redo(self) -> None:
        pass  # Phase 4

    def create_menu_bar(self) -> None:
        """Crée la barre de menu (Fichier, Outils, Aide)."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Fichier")
        file_menu.addAction("Charger un dataset").triggered.connect(self._load_dataset)
        file_menu.addAction("Recharger le dataset (nouvelles images)").triggered.connect(
            self._reload_dataset
        )
        file_menu.addSeparator()
        file_menu.addAction("Exporter les annotations").triggered.connect(
            self._export_annotations
        )
        file_menu.addAction("Importer des annotations").triggered.connect(
            self._import_annotations
        )
        file_menu.addSeparator()
        file_menu.addAction("Quitter").triggered.connect(self.close)

        tools_menu = menubar.addMenu("Outils")
        tools_menu.addAction("Statistiques").triggered.connect(self._show_stats)
        tools_menu.addSeparator()
        tools_menu.addAction(
            "Exporter co-occurrence (depuis le dataset chargé)"
        ).triggered.connect(self._export_cooccurrence)
        tools_menu.addAction(
            "Co-occurrence à partir d'un CSV"
        ).triggered.connect(self._export_cooccurrence_from_csv)
        tools_menu.addAction(
            "Générer rapport exemples de localisation (HTML)"
        ).triggered.connect(self._export_localization_report)

        help_menu = menubar.addMenu("Aide")
        help_menu.addAction("À propos").triggered.connect(self._show_about)

    def _load_dataset(self) -> None:
        pass  # Phase 5

    def _reload_dataset(self) -> None:
        pass  # Phase 5

    def _export_annotations(self) -> None:
        pass  # Phase 5

    def _import_annotations(self) -> None:
        pass  # Phase 5

    def _show_stats(self) -> None:
        pass  # Phase 6

    def _export_cooccurrence(self) -> None:
        pass  # Phase 6

    def _export_cooccurrence_from_csv(self) -> None:
        pass  # Phase 6

    def _export_localization_report(self) -> None:
        pass  # Phase 6

    def _show_about(self) -> None:
        pass  # Phase 6


def run() -> None:
    """Lance l'application Qt."""
    app = QApplication(sys.argv)

    auth_dialog = AuthDialog()
    if auth_dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    current_user = auth_dialog.get_user()
    if not current_user:
        sys.exit(0)

    data_manager = DataManager()
    window = MainWindow(data_manager, current_user)
    window.show()
    sys.exit(app.exec())
