# -*- coding: utf-8 -*-
"""
Dialogue de statistiques (générales, par pathologie, par auteur).
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from pai_2025_outil_etiquetage_radiographies.data_manager import DataManager


class StatsDialog(QDialog):
    """Dialogue affichant les statistiques du dataset et des annotations."""

    def __init__(self, data_manager: "DataManager", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data_manager = data_manager
        self.setWindowTitle("Statistiques")
        self.setModal(True)
        self.init_ui()
        self.load_stats()

    def init_ui(self) -> None:
        layout = QVBoxLayout()
        general_group = QGroupBox("Statistiques générales")
        general_layout = QVBoxLayout()
        self.general_stats = QLabel()
        general_layout.addWidget(self.general_stats)
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        pathology_group = QGroupBox("Annotations par pathologie")
        pathology_layout = QVBoxLayout()
        self.pathology_table = QTableWidget()
        self.pathology_table.setColumnCount(2)
        self.pathology_table.setHorizontalHeaderLabels(["Pathologie", "Nombre"])
        self.pathology_table.horizontalHeader().setStretchLastSection(True)
        pathology_layout.addWidget(self.pathology_table)
        pathology_group.setLayout(pathology_layout)
        layout.addWidget(pathology_group)
        author_group = QGroupBox("Annotations par auteur")
        author_layout = QVBoxLayout()
        self.author_table = QTableWidget()
        self.author_table.setColumnCount(2)
        self.author_table.setHorizontalHeaderLabels(["Auteur", "Nombre"])
        self.author_table.horizontalHeader().setStretchLastSection(True)
        author_layout.addWidget(self.author_table)
        author_group.setLayout(author_layout)
        layout.addWidget(author_group)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.resize(500, 600)

    def load_stats(self) -> None:
        stats = self.data_manager.get_statistics()
        general_text = f"Total d'images: {stats['total_images']}\n"
        general_text += f"Images annotées: {stats['annotated_images']}\n"
        general_text += f"Total d'annotations: {stats['total_annotations']}\n"
        if stats["total_annotations"] > 0:
            avg = stats["total_annotations"] / stats["annotated_images"]
            general_text += f"Moyenne d'annotations par image: {avg:.2f}"
        self.general_stats.setText(general_text)
        pathology_stats = stats["annotations_by_pathology"]
        self.pathology_table.setRowCount(len(pathology_stats))
        for row, (pathology, count) in enumerate(
            sorted(pathology_stats.items(), key=lambda x: x[1], reverse=True)
        ):
            self.pathology_table.setItem(row, 0, QTableWidgetItem(pathology))
            self.pathology_table.setItem(row, 1, QTableWidgetItem(str(count)))
        author_stats = stats["annotations_by_author"]
        self.author_table.setRowCount(len(author_stats))
        for row, (author, count) in enumerate(
            sorted(author_stats.items(), key=lambda x: x[1], reverse=True)
        ):
            self.author_table.setItem(row, 0, QTableWidgetItem(author))
            self.author_table.setItem(row, 1, QTableWidgetItem(str(count)))
