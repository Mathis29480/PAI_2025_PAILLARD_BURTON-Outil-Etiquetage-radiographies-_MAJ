"""Point d'entrée Qt (PySide6) pour l'outil d'étiquetage de radiographies."""

import sys
from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pai_2025_outil_etiquetage_radiographies import analysis_export

from pai_2025_outil_etiquetage_radiographies.annotations_tab import AnnotationsTab
from pai_2025_outil_etiquetage_radiographies.auth_dialog import AuthDialog
from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager
from pai_2025_outil_etiquetage_radiographies.stats_dialog import StatsDialog
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

        self.annotations_tab = AnnotationsTab(self.data_manager, self.current_user)
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
        if hasattr(self.annotations_tab, "save_annotations"):
            self.annotations_tab.save_annotations()
        self.statusBar().showMessage("Annotations sauvegardées", 2000)

    def _undo(self) -> None:
        if hasattr(self.annotations_tab, "undo"):
            self.annotations_tab.undo()

    def _redo(self) -> None:
        if hasattr(self.annotations_tab, "redo"):
            self.annotations_tab.redo()

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
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier du dataset")
        if folder:
            self.data_manager.load_dataset(folder)
            self.visualization_tab.refresh_data()
            self.statusBar().showMessage(f"Dataset chargé depuis: {folder}")

    def _reload_dataset(self) -> None:
        if not self.data_manager.dataset_path or not self.data_manager.dataset_path.exists():
            QMessageBox.information(
                self,
                "Recharger",
                "Aucun dataset chargé. Utilisez Fichier > Charger un dataset d'abord.",
            )
            return
        folder = str(self.data_manager.dataset_path)
        self.data_manager.load_dataset(folder)
        self.visualization_tab.refresh_data()
        n = len(self.data_manager.images)
        self.statusBar().showMessage(f"Dataset rechargé : {n} image(s)")

    def _export_annotations(self) -> None:
        formats = ["JSON", "CSV", "COCO", "YOLO"]
        format_dialog = QDialog(self)
        format_dialog.setWindowTitle("Format d'export")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Format:"))
        format_combo = QComboBox()
        format_combo.addItems(formats)
        layout.addWidget(format_combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(format_dialog.accept)
        buttons.rejected.connect(format_dialog.reject)
        layout.addWidget(buttons)
        format_dialog.setLayout(layout)
        if format_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        format_type = format_combo.currentText()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Exporter en {format_type}",
            "",
            f"{format_type} Files (*.{format_type.lower()})",
        )
        if filename:
            self.data_manager.export_annotations(filename, format_type)
            QMessageBox.information(
                self, "Succès", f"Annotations exportées en {format_type}"
            )

    def _import_annotations(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Importer des annotations",
            "",
            "Fichiers supportés (*.json *.csv);;JSON (*.json);;CSV (*.csv)",
        )
        if filename:
            try:
                self.data_manager.import_annotations(filename)
                if hasattr(self.annotations_tab, "refresh_annotations"):
                    self.annotations_tab.refresh_annotations()
                QMessageBox.information(self, "Succès", "Annotations importées avec succès")
            except Exception as e:
                QMessageBox.critical(
                    self, "Erreur", f"Erreur lors de l'import: {str(e)}"
                )

    def _show_stats(self) -> None:
        StatsDialog(self.data_manager, self).exec()

    def _export_cooccurrence(self) -> None:
        if not self.data_manager.images:
            QMessageBox.information(
                self, "Analyse", "Chargez d'abord un dataset (avec le CSV Data_Entry)."
            )
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Dossier pour enregistrer (CSV + heatmap)"
        )
        if not folder:
            return
        folder = Path(folder)
        csv_path = folder / "cooccurrence_pathologies.csv"
        png_path = folder / "cooccurrence_heatmap.png"
        try:
            analysis_export.export_cooccurrence_csv(
                self.data_manager, str(csv_path), from_csv_only=True
            )
            ok = analysis_export.export_cooccurrence_heatmap(
                self.data_manager, str(png_path), from_csv_only=True
            )
            msg = f"Matrice (depuis le CSV du dataset) :\n{csv_path}\n"
            msg += f"Heatmap :\n{png_path}" if ok else "Heatmap : installez matplotlib."
            QMessageBox.information(self, "Co-occurrence", msg)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _export_cooccurrence_from_csv(self) -> None:
        csv_path, _ = QFileDialog.getOpenFileName(
            self, "Choisir le CSV", "", "CSV (*.csv);;Tous (*)"
        )
        if not csv_path:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Dossier pour enregistrer (CSV + heatmap)"
        )
        if not folder:
            return
        try:
            csv_out, png_out = analysis_export.export_cooccurrence_from_csv_file(
                csv_path, folder
            )
            msg = f"Matrice exportée :\n{csv_out}\n"
            msg += f"Heatmap :\n{png_out}" if png_out else "Heatmap : installez matplotlib."
            QMessageBox.information(self, "Co-occurrence depuis CSV", msg)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _export_localization_report(self) -> None:
        if not self.data_manager.images:
            QMessageBox.information(self, "Rapport", "Chargez d'abord un dataset.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le rapport", "exemples_localisation.html", "HTML (*.html)"
        )
        if not path:
            return
        try:
            analysis_export.export_localization_report(self.data_manager, path)
            QMessageBox.information(
                self,
                "Rapport",
                f"Rapport généré :\n{path}\n\nOuvre-le dans un navigateur.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "À propos",
            "Outil d'étiquetage de radiographies in-house\n\n"
            "Auteurs: Mathis Paillard - Cristobal Burton Selva\n\n"
            "Outil de visualisation et d'annotation de radiographies\n"
            "pour la recherche et l'entraînement de modèles d'IA.",
        )


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
