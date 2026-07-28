import os
import subprocess
import threading
from datetime import datetime

import customtkinter as ctk
import minecraft_launcher_lib as mll

MINECRAFT_DIR = os.path.join(os.environ["APPDATA"], ".simple_mc_launcher")
PAGE_SIZE = 3

ACCENT = "#3b82f6"
ACCENT_HOVER = "#2f6fd1"
BADGE_BG = "#173350"
BADGE_TEXT = "#6aa8ff"

RU_MONTHS = {
    1: "янв.", 2: "февр.", 3: "мар.", 4: "апр.", 5: "мая", 6: "июн.",
    7: "июл.", 8: "авг.", 9: "сент.", 10: "окт.", 11: "нояб.", 12: "дек.",
}
ICON_COLORS = ["#e05fa0", "#4caf6d", "#8a6fe0", "#3b82f6", "#e0a75f", "#5fc7e0"]

all_versions = []
latest_ids = {}
active_type = "release"
current_page = 0
total_pages = 1
selected_version = None
version_rows = {}


def format_date(value):
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return f"{dt.day} {RU_MONTHS[dt.month]} {dt.year} г."

def is_installed(version):
    return any(v["id"] == version for v in mll.utils.get_installed_versions(MINECRAFT_DIR))

def set_status(text):
    root.after(0, lambda: status_label.configure(text=text))

def load_versions():
    global all_versions, latest_ids
    all_versions = mll.utils.get_version_list()
    latest_ids = mll.utils.get_latest_version()
    root.after(0, render_version_list)

def launch_game():
    username = username_entry.get().strip() or "Player"
    version = selected_version

    root.after(0, lambda: play_button.configure(state="disabled", text="Запуск..."))

    try:
        if not is_installed(version):
            mll.install.install_minecraft_version(
                version, MINECRAFT_DIR,
                callback={"setStatus": set_status},
            )

        options = mll.utils.generate_test_options()
        options["username"] = username

        command = mll.command.get_minecraft_command(version, MINECRAFT_DIR, options)
        subprocess.Popen(command, cwd=MINECRAFT_DIR)
        set_status("Игра запущена")
    except Exception as exc:
        set_status(f"Ошибка: {exc}")

    root.after(0, lambda: play_button.configure(state="normal", text="Играть"))

def on_play():
    if not selected_version:
        status_label.configure(text="Сначала выберите версию")
        return
    threading.Thread(target=launch_game, daemon=True).start()

def show_home():
    home_frame.tkraise()

def show_version_page():
    version_frame.tkraise()

def set_active_type(version_type):
    global active_type, current_page
    active_type = version_type
    current_page = 0
    if version_type == "release":
        releases_tab.configure(fg_color=ACCENT, text_color="#0d0f10")
        snapshots_tab.configure(fg_color="transparent", text_color="#c9c9c9")
    else:
        snapshots_tab.configure(fg_color=ACCENT, text_color="#0d0f10")
        releases_tab.configure(fg_color="transparent", text_color="#c9c9c9")
    render_version_list()

def on_search_changed(*_args):
    global current_page
    current_page = 0
    render_version_list()

def prev_page():
    global current_page
    if current_page > 0:
        current_page -= 1
        render_version_list()


def next_page():
    global current_page
    if current_page < total_pages - 1:
        current_page += 1
        render_version_list()

def select_version(version_id):
    global selected_version
    selected_version = version_id
    version_button.configure(text=f"Версия: {version_id}")
    show_home()

def build_version_row(version, is_latest):
    row = ctk.CTkFrame(list_frame, fg_color="#1a1d1f", corner_radius=8, border_width=2, border_color="#1a1d1f")
    color = ICON_COLORS[hash(version["id"]) % len(ICON_COLORS)]
    ctk.CTkLabel(row, text="", width=22, height=22, corner_radius=5, fg_color=color).grid(row=0, column=0, padx=(8, 8), pady=6)
    ctk.CTkLabel(row, text=version["id"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=1, sticky="ew")
    col = 2
    if is_latest:
        ctk.CTkLabel(
            row, text="последняя", font=ctk.CTkFont(size=10),
            fg_color=BADGE_BG, text_color=BADGE_TEXT, corner_radius=5,
        ).grid(row=0, column=col, padx=(6, 0))
        col += 1
    ctk.CTkLabel(row, text=format_date(version["releaseTime"]), text_color="#9a9a9a", font=ctk.CTkFont(size=11)).grid(row=0, column=col, padx=(6, 6))
    col += 1
    check_label = ctk.CTkLabel(row, text="", width=14, text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold"))
    check_label.grid(row=0, column=col, padx=(0, 8))
    row.grid_columnconfigure(1, weight=1, minsize=50)
    for widget in row.winfo_children():
        widget.bind("<Button-1>", lambda _e, vid=version["id"]: select_version(vid))
    row.bind("<Button-1>", lambda _e, vid=version["id"]: select_version(vid))
    return row, check_label

def render_version_list():
    global total_pages, current_page
    for widget in list_frame.winfo_children():
        widget.destroy()
    version_rows.clear()
    query = search_var.get().strip().lower()
    latest_for_type = latest_ids.get(active_type)
    filtered = [v for v in all_versions if v["type"] == active_type and query in v["id"].lower()]
    total_pages = max(1, -(-len(filtered) // PAGE_SIZE))
    current_page = min(current_page, total_pages - 1)
    start = current_page * PAGE_SIZE
    page_items = filtered[start:start + PAGE_SIZE]
    for version in page_items:
        row, check_label = build_version_row(version, version["id"] == latest_for_type)
        row.pack(fill="x", pady=3)
        version_rows[version["id"]] = (row, check_label)
        if version["id"] == selected_version:
            row.configure(border_color=ACCENT)
            check_label.configure(text="✓")
    page_label.configure(text=f"Стр. {current_page + 1} из {total_pages}")
    prev_button.configure(state="normal" if current_page > 0 else "disabled")
    next_button.configure(state="normal" if current_page < total_pages - 1 else "disabled")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.title("Minecraft Launcher")
root.geometry("400x300")
root.resizable(False, False)
root.configure(fg_color="#0d0f10")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
home_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
home_frame.grid(row=0, column=0, sticky="nsew")
version_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
version_frame.grid(row=0, column=0, sticky="nsew")

ctk.CTkLabel(home_frame, text="Minecraft Launcher", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
username_entry = ctk.CTkEntry(home_frame, placeholder_text="Никнейм")
username_entry.pack(pady=(0, 10), padx=25, fill="x")

version_button = ctk.CTkButton(
    home_frame, text="Версия: ...", anchor="w",
    fg_color="#141617", hover_color="#1a1d1f", text_color="#e5e5e5",
    command=show_version_page,
)
version_button.pack(pady=(0, 10), padx=25, fill="x")
status_label = ctk.CTkLabel(home_frame, text="", font=ctk.CTkFont(size=11))
status_label.pack(pady=(0, 20))
play_button = ctk.CTkButton(home_frame, text="Играть", command=on_play)
play_button.pack(pady=(0, 20), padx=25, fill="x")

header = ctk.CTkFrame(version_frame, fg_color="transparent")
header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(header, text="Версия Minecraft", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

tabs = ctk.CTkFrame(version_frame, fg_color="transparent")
tabs.pack(fill="x", padx=12)
releases_tab = ctk.CTkButton(
    tabs, text="Релизы", width=80, height=26, fg_color=ACCENT, text_color="#0d0f10",
    hover_color=ACCENT_HOVER, command=lambda: set_active_type("release"),
)
releases_tab.pack(side="left")
snapshots_tab = ctk.CTkButton(
    tabs, text="Снапшоты", width=80, height=26, fg_color="transparent", text_color="#c9c9c9",
    hover_color="#232628", command=lambda: set_active_type("snapshot"),
)
snapshots_tab.pack(side="left", padx=(6, 0))

search_var = ctk.StringVar()
search_var.trace_add("write", on_search_changed)
search_entry = ctk.CTkEntry(version_frame, height=26, placeholder_text="🔍  Поиск версии...", textvariable=search_var)
search_entry.pack(fill="x", padx=12, pady=6)
list_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
list_frame.pack(fill="both", expand=True, padx=12)
pagination = ctk.CTkFrame(version_frame, fg_color="transparent")
pagination.pack(fill="x", padx=12, pady=(4, 10))
prev_button = ctk.CTkButton(pagination, text="◀", width=30, height=24, command=prev_page)
prev_button.pack(side="left")
page_label = ctk.CTkLabel(pagination, text="", font=ctk.CTkFont(size=11))
page_label.pack(side="left", expand=True)
next_button = ctk.CTkButton(pagination, text="▶", width=30, height=24, command=next_page)
next_button.pack(side="right")
show_home()
threading.Thread(target=load_versions, daemon=True).start()

root.mainloop()
