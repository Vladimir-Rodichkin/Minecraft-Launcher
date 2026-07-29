from tkinter import filedialog

import state
import storage
from navigation import show_home


def show_settings_page():
    settings = storage.load_settings()
    state.java_path_entry.delete(0, "end")
    state.java_path_entry.insert(0, settings["java_path"])
    state.min_ram_entry.delete(0, "end")
    state.min_ram_entry.insert(0, settings["min_ram"])
    state.max_ram_entry.delete(0, "end")
    state.max_ram_entry.insert(0, settings["max_ram"])
    state.jvm_args_entry.delete(0, "end")
    state.jvm_args_entry.insert(0, settings["jvm_args"])
    state.settings_frame.tkraise()


def browse_java():
    path = filedialog.askopenfilename(title="Выберите java.exe", filetypes=[("java.exe", "java.exe"), ("Все файлы", "*.*")])
    if path:
        state.java_path_entry.delete(0, "end")
        state.java_path_entry.insert(0, path)


def save_settings_and_back():
    storage.save_settings({
        "java_path": state.java_path_entry.get().strip(),
        "min_ram": state.min_ram_entry.get().strip() or state.DEFAULT_SETTINGS["min_ram"],
        "max_ram": state.max_ram_entry.get().strip() or state.DEFAULT_SETTINGS["max_ram"],
        "jvm_args": state.jvm_args_entry.get().strip(),
    })
    show_home()
