import os
import shutil
from tkinter import filedialog

import customtkinter as ctk

import state


def mods_dir():
    return os.path.join(state.MINECRAFT_DIR, "mods")


def open_mods_folder():
    os.makedirs(mods_dir(), exist_ok=True)
    os.startfile(mods_dir())


def mod_display_name(filename):
    return filename[:-len(".disabled")] if filename.lower().endswith(".disabled") else filename


def is_mod_enabled(filename):
    return not filename.lower().endswith(".disabled")


def toggle_mod_enabled(filename):
    path = os.path.join(mods_dir(), filename)
    if is_mod_enabled(filename):
        os.rename(path, path + ".disabled")
    else:
        os.rename(path, path[:-len(".disabled")])
    render_mods_list()


def delete_mod(filename):
    try:
        os.remove(os.path.join(mods_dir(), filename))
    except OSError:
        pass
    render_mods_list()


def build_mod_row(filename):
    row = ctk.CTkFrame(state.mods_list_frame, fg_color="#1a1d1f", corner_radius=8)
    checkbox = ctk.CTkCheckBox(
        row, text=mod_display_name(filename), font=ctk.CTkFont(size=12),
        command=lambda f=filename: toggle_mod_enabled(f),
    )
    if is_mod_enabled(filename):
        checkbox.select()
    else:
        checkbox.deselect()
    checkbox.pack(side="left", fill="x", expand=True, padx=10, pady=6)
    ctk.CTkButton(
        row, text="✕", width=24, height=24, fg_color="transparent",
        text_color="#9a9a9a", hover_color="#3a1f1f", command=lambda f=filename: delete_mod(f),
    ).pack(side="right", padx=(0, 8))
    return row


def render_mods_list():
    for widget in state.mods_list_frame.winfo_children():
        widget.destroy()
    os.makedirs(mods_dir(), exist_ok=True)
    files = sorted(
        f for f in os.listdir(mods_dir())
        if f.lower().endswith(".jar") or f.lower().endswith(".jar.disabled")
    )
    if not files:
        ctk.CTkLabel(state.mods_list_frame, text="Модов пока нет", text_color="#9a9a9a").pack(pady=20)
        return
    for name in files:
        build_mod_row(name).pack(fill="x", pady=3)


def add_mods():
    paths = filedialog.askopenfilenames(title="Выберите .jar файлы модов", filetypes=[("Jar files", "*.jar")])
    if not paths:
        return
    os.makedirs(mods_dir(), exist_ok=True)
    for path in paths:
        shutil.copy(path, os.path.join(mods_dir(), os.path.basename(path)))
    render_mods_list()


def show_mods_page():
    render_mods_list()
    state.mods_frame.tkraise()
