import customtkinter as ctk

import state
import storage
from navigation import show_home


def show_nicknames_page():
    render_nickname_list()
    state.nickname_frame.tkraise()


def select_nickname(name):
    state.username_entry.delete(0, "end")
    state.username_entry.insert(0, name)
    show_home()


def on_delete_nickname_click(name):
    storage.delete_nickname(name)
    render_nickname_list()


def build_nickname_row(name):
    row = ctk.CTkFrame(state.nickname_list_frame, fg_color="#1a1d1f", corner_radius=8, border_width=2, border_color="#1a1d1f")
    color = state.ICON_COLORS[hash(name) % len(state.ICON_COLORS)]
    icon_label = ctk.CTkLabel(row, text=name[:1].upper(), width=22, height=22, corner_radius=11, fg_color=color, font=ctk.CTkFont(size=11, weight="bold"))
    icon_label.grid(row=0, column=0, padx=(8, 8), pady=6)
    name_label = ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
    name_label.grid(row=0, column=1, sticky="ew")
    row.grid_columnconfigure(1, weight=1, minsize=50)

    for widget in (row, icon_label, name_label):
        widget.bind("<Button-1>", lambda _e, n=name: select_nickname(n))

    delete_button = ctk.CTkButton(
        row, text="✕", width=24, height=24, fg_color="transparent",
        text_color="#9a9a9a", hover_color="#3a1f1f",
        command=lambda n=name: on_delete_nickname_click(n),
    )
    delete_button.grid(row=0, column=2, padx=(0, 8))
    return row


def render_nickname_list():
    for widget in state.nickname_list_frame.winfo_children():
        widget.destroy()
    nicknames = storage.load_nicknames()
    if not nicknames:
        ctk.CTkLabel(state.nickname_list_frame, text="Пока нет сохранённых ников", text_color="#9a9a9a").pack(pady=20)
        return
    for name in nicknames:
        build_nickname_row(name).pack(fill="x", pady=3)
