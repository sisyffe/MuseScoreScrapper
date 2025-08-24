import asyncio
import logging
import multiprocessing as mp
from pathlib import Path, UnsupportedOperation
import re
import sys

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtCore import Qt, QTimer, QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpacerItem, QSizePolicy,
    QProgressBar, QCheckBox
)

import settings
from utils import Message
from worker import Worker, Handler

logger = logging.getLogger(__name__)

button_status = 0b00


def update_button_status(button: QPushButton):
    button.setEnabled(button_status == 0b11)


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.url_type_label: QLabel | None = None
        self.path_valid_label: QLabel | None = None
        self.validate_button: QPushButton | None = None
        self.url_entry: QLineEdit | None = None
        self.path_entry: QLineEdit | None = None
        self.status_debounce: QTimer | None = None
        self.preview_title_label: QLabel | None = None
        self.preview_spinner: QProgressBar | None = None
        self.auto_output: QCheckBox | None = None
        self.previous_path: str | None = None

        self.setWindowTitle("MuseScore scrapper")
        self.setFixedSize(settings.WINDOW_GEOMETRY[0], settings.WINDOW_GEOMETRY[1])
        self.build_gui()
        self.center_window()

    def scrap(self):
        self.app.scrap()

    def fetch_title(self):
        self.app.fetch_title()

    def browse_save_location(self):
        if getattr(self, "auto_output", None) and self.auto_output.isChecked():
            directory = QFileDialog.getExistingDirectory(
                self,
                "Choisir un dossier de destination",
                self.path_entry.text() or QStandardPaths.writableLocation(settings.DEFAULT_FOLDER_LOCATION),
                options=QFileDialog.Option.ShowDirsOnly,
            )
            if directory:
                file = self.path_entry.text().split("/")[-1]
                self.path_entry.setText(str(Path(directory) / file))
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Choisir un fichier de sortie",
                self.path_entry.text() or QStandardPaths.writableLocation(settings.DEFAULT_FOLDER_LOCATION),
            )
            if file_path:
                self.path_entry.setText(file_path)
        self.check_path(self.path_entry.text())

    def check_url(self, text: str):
        url_patterns = [
            ("score utilisateur", re.compile(r"^https://(?:www\.)?musescore\.com/user/[0-9]+/scores/[0-9]+$")),
            ("score officiel", re.compile(r"^https://(?:www\.)?musescore\.com/official_scores/scores/[0-9]+$")),
            ("autre site", re.compile(r"^https://[a-zA-Z0-9\-.]+\.[a-z]{2,}/.*$"))
        ]

        global button_status
        for match_type, pattern in url_patterns:
            if pattern.match(text):
                button_status |= 0b10
                self.url_type_label.setText(f"Type : {match_type}")
                self.url_type_label.setStyleSheet("color: gray")

                self.app.result_url = self.url_entry.text()
                self.status_debounce.start()
                break
        else:
            button_status &= 0b01
            self.url_type_label.setText("URL invalide")
            self.url_type_label.setStyleSheet("color: red")

        update_button_status(self.validate_button)

    def check_path(self, text: str):
        try:
            path = Path(text)
            is_valid = (
                not (path.exists() and path.is_dir()) and
                path.parent.exists() and
                path.suffix == ".pdf"
            )
        except UnsupportedOperation:
            is_valid = False

        global button_status
        if is_valid:
            button_status |= 0b01
            self.path_valid_label.setText("Chemin valide")
            self.path_valid_label.setStyleSheet("color: green")

            self.app.result_path = self.path_entry.text()
        else:
            button_status &= 0b10
            self.path_valid_label.setText("Chemin invalide")
            self.path_valid_label.setStyleSheet("color: red")

        update_button_status(self.validate_button)

    def handle_auto_output(self, state):
        if state == Qt.CheckState.Checked.value:
            self.previous_path = self.path_entry.text()

            current_title = self.preview_title_label.text()
            if current_title and current_title not in ["Veuillez saisir une adresse", "Erreur lors du chargement du titre", "—", ""]:
                self.update_path_with_title(current_title)
        else:
            if self.previous_path:
                self.path_entry.setText(self.previous_path)

    def update_path_with_title(self, title):
        if self.auto_output and self.auto_output.isChecked():
            # Nettoyer le titre pour en faire un nom de fichier valide
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            current_path = Path(self.path_entry.text())
            new_path = current_path.parent / f"{clean_title}.pdf"
            self.path_entry.setText(str(new_path))

    def build_gui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # URL section
        url_label_layout = QHBoxLayout()
        url_label = QLabel("Page Musescore à extraire :")
        url_label.setFont(QFont("Default", 12, QFont.Weight.Bold))
        self.url_type_label = QLabel("URL invalide")
        self.url_type_label.setStyleSheet("color: red")
        url_label_layout.addWidget(url_label)
        url_label_layout.addWidget(self.url_type_label, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(url_label_layout)

        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText(settings.ENTRY_PLACEHOLDER)
        self.url_entry.textChanged.connect(self.check_url)
        self.url_entry.returnPressed.connect(self.scrap)
        main_layout.addWidget(self.url_entry)

        # Status section
        status_layout = QHBoxLayout()

        self.status_debounce = QTimer(self)
        self.status_debounce.setSingleShot(True)
        self.status_debounce.setInterval(settings.FETCH_TITLE_DEBOUNCE_MS)
        self.status_debounce.timeout.connect(self.fetch_title)

        self.preview_title_label = QLabel("Veuillez saisir une adresse", self)
        self.preview_title_label.setStyleSheet("color: cyan")
        self.preview_title_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_layout.addWidget(self.preview_title_label)

        self.preview_spinner = QProgressBar(self)
        self.preview_spinner.setRange(0, 0)
        self.preview_spinner.setTextVisible(False)
        self.preview_spinner.setVisible(False)
        status_layout.addWidget(self.preview_spinner)

        main_layout.addLayout(status_layout)

        # Save section
        save_layout = QHBoxLayout()
        save_layout_vertical = QVBoxLayout()
        save_label_layout = QHBoxLayout()
        save_label = QLabel("Sauvegarder dans :")
        save_label.setFont(QFont("Default", 12, QFont.Weight.Bold))
        self.path_valid_label = QLabel("Chemin invalide")
        self.path_valid_label.setStyleSheet("color: red")
        save_label_layout.addWidget(save_label)
        save_label_layout.addWidget(self.path_valid_label, alignment=Qt.AlignmentFlag.AlignRight)
        save_layout_vertical.addLayout(save_label_layout)

        self.path_entry = QLineEdit()
        self.path_entry.setText(str(Path(QStandardPaths.writableLocation(settings.DEFAULT_FOLDER_LOCATION))
                                    / settings.DEFAULT_FILE_NAME))
        self.previous_path = self.path_entry.text()
        self.path_entry.textChanged.connect(self.check_path)
        save_layout_vertical.addWidget(self.path_entry)

        browse_button = QPushButton("📁")
        browse_button.setFont(QFont("Default", 16))
        browse_button.setToolTip("Ouvrir un dossier")
        browse_button.clicked.connect(self.browse_save_location)
        browse_button.setFixedWidth(50)
        browse_button.setFixedHeight(50)
        save_layout.addLayout(save_layout_vertical)
        save_layout.addWidget(browse_button)
        main_layout.addLayout(save_layout)

        # Auto option section
        auto_output_layout = QHBoxLayout()
        self.auto_output = QCheckBox()
        self.auto_output.setChecked(settings.DEFAULT_AUTO_TITLE_MODE)
        auto_output_label = QLabel("Sortie automatique")
        auto_output_label.setFont(QFont("Default", 12))
        self.auto_output.stateChanged.connect(self.handle_auto_output)
        auto_output_layout.addWidget(self.auto_output)
        auto_output_layout.addWidget(auto_output_label)
        auto_output_layout.addStretch()
        main_layout.addLayout(auto_output_layout)

        # Buttons section
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.close)
        self.validate_button = QPushButton("Récupérer")
        self.validate_button.setDefault(True)
        self.validate_button.clicked.connect(self.scrap)
        self.validate_button.setEnabled(False)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.validate_button)
        main_layout.addLayout(button_layout)


        main_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        # Initial path validation
        self.check_path(self.path_entry.text())

    def center_window(self):
        frame_geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())


class GUIManager(Worker, QApplication):
    METHODS = Worker.METHODS + ["mainloop", "set_title"]

    def __init__(self, address: str, handler: Handler):
        QApplication.__init__(self, sys.argv)
        Worker.__init__(self, address, handler)

        self.result_url: str | None = None
        self.result_path: str | None = None
        self.window: MainWindow | None = None

        self._preview_task: asyncio.Task | None = None

    def init(self) -> list[Message]:
        if self._is_init:
            raise RuntimeError("Cannot initialize GUI twice")
        logger.info("Initialising the GUI")
        self.window = MainWindow(self)
        return super().init()

    def close(self) -> list[Message]:
        if not self._is_init or not self._ready:
            raise RuntimeError("Cannot close GUI before initialization")
        logger.info("Closing the GUI")
        if self.window.isActiveWindow():
            self.window.close()
        return super().close()

    def scrap(self):
        logger.info(f"URL validated : {self.result_url}")
        logger.info(f"Path validated : {self.result_path}")
        self._handler.send_message("page", ("scrap", (self.result_url,), {}))

    def fetch_title(self):
        self.window.preview_spinner.setVisible(True)
        self.window.preview_title_label.setText("")
        self._handler.send_message("page", ("fetch_title", (self.result_url,), {}))

    def set_title(self, title: str) -> list[Message]:
        self.window.preview_title_label.setText(title)
        self.window.update_path_with_title(title)
        self.window.preview_spinner.setVisible(False)
        return []

    def mainloop(self) -> list[Message]:
        logger.info("Starting the GUI")
        self.window.show()

        timer = QTimer()
        timer.timeout.connect(self._handler.listen_step)
        timer.start(int(1000 / 60))

        QtAsyncio.run(handle_sigint=True)
        return [(self._address, "manager", "request_shutdown")]


def multiprocess_main(send_queue: mp.Queue, recv_queue: mp.Queue, ppid: int):
    gui_handler = Handler(GUIManager, "gui", send_queue, recv_queue, ppid)
    gui_handler.listen()
