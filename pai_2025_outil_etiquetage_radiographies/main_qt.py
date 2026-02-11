"""Point d'entrée Qt (PySide6) pour l'outil d'étiquetage de radiographies."""

import sys

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

        placeholder_viz = QWidget()
        layout_viz = QVBoxLayout()
        layout_viz.addWidget(QLabel("Visualisation — à venir"))
        placeholder_viz.setLayout(layout_viz)
        self.tab_widget.addTab(placeholder_viz, "Visualisation")

        placeholder_ann = QWidget()
        layout_ann = QVBoxLayout()
        layout_ann.addWidget(QLabel("Annotations — à venir"))
        placeholder_ann.setLayout(layout_ann)
        self.tab_widget.addTab(placeholder_ann, "Annotations")


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
