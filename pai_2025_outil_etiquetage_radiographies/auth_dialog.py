"""
Dialogue d'authentification pour l'outil d'étiquetage.
"""

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class AuthDialog(QDialog):
    """Dialogue d'authentification simple (utilisateurs stockés dans users.json)."""

    def __init__(self) -> None:
        super().__init__()
        self.user: str | None = None
        self.users_file = Path("users.json")
        self.users: dict = {}
        self.init_ui()
        self.load_users()

    def init_ui(self) -> None:
        """Initialise l'interface."""
        self.setWindowTitle("Authentification")
        self.setModal(True)
        layout = QVBoxLayout()

        title = QLabel("Connexion")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Nom d'utilisateur:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Entrez votre nom")
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)

        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Mot de passe (optionnel):"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Laissez vide pour nouveau compte")
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.authenticate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_users(self) -> None:
        """Charge la liste des utilisateurs depuis users.json."""
        if self.users_file.exists():
            try:
                with open(self.users_file, encoding="utf-8") as f:
                    self.users = json.load(f)
            except Exception:
                self.users = {}
        else:
            self.users = {}

    def save_users(self) -> None:
        """Sauvegarde la liste des utilisateurs."""
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def authenticate(self) -> None:
        """Vérifie les identifiants et accepte le dialogue."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom d'utilisateur")
            return

        if username in self.users:
            if (
                self.users[username].get("password")
                and password != self.users[username]["password"]
            ):
                QMessageBox.warning(self, "Erreur", "Mot de passe incorrect")
                return
        else:
            self.users[username] = {
                "password": password if password else None,
                "created": datetime.now().isoformat(),
            }
            self.save_users()

        self.user = username
        self.accept()

    def get_user(self) -> str | None:
        """Retourne le nom d'utilisateur connecté."""
        return self.user
