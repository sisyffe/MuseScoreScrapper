import logging
import os
from pathlib import Path, UnsupportedOperation
import platform
import re
import tkinter as tk
from tkinter import filedialog
from typing import Any

import settings

logger = logging.getLogger(__name__)

button_status = 0b00


def add_placeholder(entry: tk.Entry, var: tk.StringVar, placeholder_text: str):
    default_fg_color = entry.cget("fg")

    def on_focus_in(*_):
        if entry.get() == placeholder_text:
            var.set("")
            entry.config(fg=default_fg_color)

    def on_focus_out(*_):
        if not entry.get():
            entry.insert(0, placeholder_text)
            entry.config(fg="grey")

    on_focus_out()

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)


def update_button_status(button: tk.Button):
    if button_status == 0b11:
        button.config(state="normal")
    else:
        button.config(state="disabled")


def add_url_typing_listener(var: tk.StringVar, button: tk.Button, type_label: tk.Label):
    url_patterns = [
        ("score utilisateur", re.compile(r"^https://(?:www\.)?musescore\.com/user/[0-9]+/scores/[0-9]+$"))  ,
        ("score officiel", re.compile(r"^https://(?:www\.)?musescore\.com/official_scores/scores/[0-9]+$")),
        ("autre site", re.compile(r"^https://[a-zA-Z0-9\-.]+\.[a-z]{2,}/.*$"))
    ]

    def get_match_type(url: str):
        for match_type, pattern in url_patterns:
            if pattern.match(url):
                return match_type
        return None

    def on_variable_change(*_):
        global button_status
        if match_type := get_match_type(var.get()):
            button_status |= 0b10
            type_label.config(text=f"Type : {match_type}", fg="grey")
        else:
            button_status &= 0b01
            type_label.config(text="URL invalide", fg="red")
        update_button_status(button)
    var.trace_add("write", on_variable_change)


def add_path_typing_listener(var: tk.StringVar, button: tk.Button, path_valid_label: tk.Label):
    def is_valid_path(path: str):
        try:
            path = Path(path)
        except UnsupportedOperation:
            return False
        else:
            if path.exists() and path.is_dir():
                return False
            if not path.parent.exists():
                return False
            if path.suffix != ".pdf":
                return False
            return True

    def on_variable_change(*_):
        global button_status
        if is_valid_path(var.get()):
            button_status |= 0b01
            path_valid_label.config(text="Chemin valide", fg="green")
        else:
            button_status &= 0b10
            path_valid_label.config(text="Chemin invalide", fg="red")
        update_button_status(button)
    var.trace_add("write", on_variable_change)
    on_variable_change()

def browse_save_location(save_path_var: tk.StringVar):
    initial_dir = os.path.dirname(save_path_var.get())
    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialdir=initial_dir,
        initialfile="partition.pdf"
    )
    if file_path:
        save_path_var.set(file_path)


def get_desktop_file(filename: str = "partition.pdf") -> str:
    if platform.system() == "Windows":
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "Bureau"
    elif platform.system() == "Darwin":
        desktop = Path.home() / "Desktop"
    else:
        desktop_dir = os.getenv("XDG_DESKTOP_DIR")
        if desktop_dir:
            desktop = Path(desktop_dir)
        else:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home() / "Bureau"

    return str(desktop / filename)


class GUIElement:
    __slots__ = ("widget",)

    def __init__(
            self,
            widget_class: str,
            init_args: dict[str, Any] | None = None,
            display_method: str | None = "pack",
            display_args: dict[str, Any] | None = None):
        self.widget = getattr(tk, widget_class)(**init_args)
        if display_method is not None:
            getattr(self.widget, display_method)(**display_args)


class GUIManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.running = False
        self.visual_elements: dict[str, tk.Widget | tk.Variable] = {}
        self.result_url: str | None = None
        self.result_path: str | None = None

    def init(self):
        if self.running:
            return
        logger.info("Initialising the GUI")
        self.title("MuseScore scrapper")
        self.geometry(settings.WINDOW_GEOMETRY)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.build_gui()
        self.center_window(self)
        self.running = True

    def close(self):
        if not self.running:
            return
        logger.info("Closing the GUI")
        if hasattr(self, '_tclCommands') and self._tclCommands:
            self.destroy()
        self.quit()
        self.update()
        self.running = False

    def cancel(self):
        logger.info("Canceling the process")
        self.close()

    def validate(self, *_):
        self.result_url = self.visual_elements["link_var"].get()
        self.result_path = self.visual_elements["save_path_var"].get()
        logger.info(f"URL validated : {self.result_url}")
        logger.info(f"Path validated : {self.result_path}")
        self.close()

    def build_gui(self):
        frame = self.visual_elements["frame"] = GUIElement(
            widget_class="Frame",
            init_args={"master": self},
            display_args={"expand": True}
        ).widget

        # URL selector
        ## Labels
        label_frame = self.visual_elements["label_frame"] = GUIElement(
            widget_class="Frame",
            init_args={"master": frame},
            display_args={"side": tk.TOP, "fill": tk.X}
        ).widget
        self.visual_elements["url_label"] = GUIElement(
            widget_class="Label",
            init_args={"master": label_frame, "text": "Page Musescore à extraire :", "font": ("TkDefaultFont", 9, "bold")},
            display_args={"side": tk.LEFT, "anchor": tk.W}
        ).widget
        type_label = self.visual_elements["type_label"] = GUIElement(
            widget_class="Label",
            init_args={"master": label_frame, "text": "URL invalide", "fg": "red"},
            display_args={"side": tk.RIGHT, "anchor": tk.E}
        ).widget

        ## Entry
        link_var = self.visual_elements["link_var"] = tk.StringVar(self)
        link_entry = self.visual_elements["link_entry"] = GUIElement(
            widget_class="Entry",
            init_args={"master": frame, "textvariable": link_var},
            display_args={"side": tk.TOP, "anchor": tk.W, "fill": tk.X}
        ).widget
        add_placeholder(link_entry, link_var, settings.ENTRY_PLACEHOLDER)
        link_entry.bind("<Return>", self.validate)

        # Save selector
        ## Labels
        save_label_frame = self.visual_elements["save_label_frame"] = GUIElement(
            widget_class="Frame",
            init_args={"master": frame},
            display_args={"side": tk.TOP, "fill": tk.X}
        ).widget
        self.visual_elements["save_label"] = GUIElement(
            widget_class="Label",
            init_args={"master": save_label_frame, "text": "Sauvegarder dans :", "font": ("TkDefaultFont", 9, "bold")},
            display_args={"side": tk.LEFT, "anchor": tk.W}
        ).widget
        path_valid_label = self.visual_elements["path_valid_label"] = GUIElement(
            widget_class="Label",
            init_args={"master": save_label_frame, "text": "Chemin invalide", "fg": "red"},
            display_args={"side": tk.RIGHT, "anchor": tk.E}
        ).widget

        ## Entry
        save_frame = self.visual_elements["save_frame"] = GUIElement(
            widget_class="Frame",
            init_args={"master": frame},
            display_args={"side": tk.TOP}
        ).widget
        save_path_var = self.visual_elements["save_path_var"] = tk.StringVar(value=get_desktop_file())
        self.visual_elements["save_entry"] = GUIElement(
            widget_class="Entry",
            init_args={"master": save_frame, "textvariable": save_path_var, "width": 45},
            display_args={"side": tk.LEFT}
        ).widget

        ## Browse button
        self.visual_elements["browse_button"] = GUIElement(
            widget_class="Button",
            init_args={
                "master": save_frame,
                "text": "📁",
                "command": lambda: browse_save_location(save_path_var),
                "width": 1,
            },
            display_args={"side": tk.LEFT, "padx": (5, 0), "fill": tk.Y}
        ).widget

        # Validate button
        commands_frame = self.visual_elements["commands_frame"] = GUIElement(
            widget_class="Frame",
            init_args={"master": frame},
            display_args={"side": tk.TOP, "pady": (5, 0)}
        ).widget
        self.visual_elements["cancel_button"] = GUIElement(
            widget_class="Button",
            init_args={"master": commands_frame, "text": "Annuler", "command": self.cancel},
            display_args={"side": tk.LEFT, "padx": 5}
        ).widget
        validate_button = self.visual_elements["validate_button"] = GUIElement(
            widget_class="Button",
            init_args={"master": commands_frame, "text": "Récupérer", "command": self.validate, "state": tk.DISABLED},
            display_args={"side": tk.RIGHT, "padx": 5}
        ).widget
        add_url_typing_listener(link_var, validate_button, type_label)
        add_path_typing_listener(save_path_var, validate_button, path_valid_label)


    def run_sync(self):
        logger.info("Starting GUI synchronously")
        self.mainloop()
        return self.result_url, self.result_path

    @staticmethod
    def center_window(window):
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        size = tuple(int(x) for x in window.geometry().split('+')[0].split('x'))
        x = screen_width // 2 - size[0] // 2
        y = screen_height // 2 - size[1] // 2
        window.geometry(f"{size[0]}x{size[1]}+{x}+{y}")