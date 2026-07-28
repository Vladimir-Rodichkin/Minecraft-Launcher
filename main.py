import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
import minecraft_launcher_lib as mll

MINECRAFT_DIR = os.path.join(os.environ["APPDATA"], ".simple_mc_launcher")
CONFIG_PATH = os.path.join(MINECRAFT_DIR, "config.json")
PAGE_SIZE = 3
MAX_SAVED_NICKNAMES = 8
DEFAULT_SETTINGS = {"java_path": "", "min_ram": "512", "max_ram": "2048", "jvm_args": ""}
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
game_process = None

def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("nicknames", [])
    data.setdefault("settings", dict(DEFAULT_SETTINGS))
    return data

def write_config(data):
    os.makedirs(MINECRAFT_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_nicknames():
    return load_config()["nicknames"]

def save_nickname(name):
    config = load_config()
    nicknames = [n for n in config["nicknames"] if n != name]
    nicknames.insert(0, name)
    config["nicknames"] = nicknames[:MAX_SAVED_NICKNAMES]
    write_config(config)

def delete_nickname(name):
    config = load_config()
    config["nicknames"] = [n for n in config["nicknames"] if n != name]
    write_config(config)
    render_nickname_list()

def load_settings():
    return load_config()["settings"]

def save_settings(settings):
    config = load_config()
    config["settings"] = settings
    write_config(config)

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

def clear_logs():
    log_textbox.configure(state="normal")
    log_textbox.delete("1.0", "end")
    log_textbox.configure(state="disabled")

def append_log(line):
    log_textbox.configure(state="normal")
    log_textbox.insert("end", line)
    log_textbox.see("end")
    log_textbox.configure(state="disabled")

def show_logs_page():
    logs_frame.tkraise()

def stop_game():
    if game_process and game_process.poll() is None:
        game_process.terminate()
        set_status("Останавливаем...")
        stop_button.configure(state="disabled")

def launch_game():
    global game_process

    username = username_entry.get().strip() or "Player"
    version = selected_version
    settings = load_settings()

    root.after(0, lambda: play_button.configure(state="disabled", text="Запуск..."))
    save_nickname(username)

    try:
        if not is_installed(version):
            mll.install.install_minecraft_version(
                version, MINECRAFT_DIR,
                callback={"setStatus": set_status},
            )

        options = mll.utils.generate_test_options()
        options["username"] = username

        try:
            min_ram = int(settings["min_ram"])
        except ValueError:
            min_ram = int(DEFAULT_SETTINGS["min_ram"])
        try:
            max_ram = int(settings["max_ram"])
        except ValueError:
            max_ram = int(DEFAULT_SETTINGS["max_ram"])

        jvm_args = [f"-Xms{min_ram}M", f"-Xmx{max_ram}M"] + settings["jvm_args"].split()
        options["jvmArguments"] = jvm_args
        if settings["java_path"]:
            options["executablePath"] = settings["java_path"]

        command = mll.command.get_minecraft_command(version, MINECRAFT_DIR, options)
        game_process = subprocess.Popen(
            command, cwd=MINECRAFT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        root.after(0, clear_logs)
        root.after(0, show_logs_page)
        root.after(0, lambda: stop_button.configure(state="normal"))

        for line in game_process.stdout:
            root.after(0, lambda l=line: append_log(l))
        game_process.wait()
        set_status("Игра завершена")
    except Exception as exc:
        set_status(f"Ошибка: {exc}")

    game_process = None
    root.after(0, lambda: stop_button.configure(state="disabled"))
    root.after(0, lambda: play_button.configure(state="normal", text="Играть"))

def on_play():
    if not selected_version:
        status_label.configure(text="Сначала выберите версию")
        return
    if game_process and game_process.poll() is None:
        status_label.configure(text="Игра уже запущена")
        return
    threading.Thread(target=launch_game, daemon=True).start()

def show_home():
    home_frame.tkraise()

def show_version_page():
    version_frame.tkraise()

def show_settings_page():
    settings = load_settings()
    java_path_entry.delete(0, "end")
    java_path_entry.insert(0, settings["java_path"])
    min_ram_entry.delete(0, "end")
    min_ram_entry.insert(0, settings["min_ram"])
    max_ram_entry.delete(0, "end")
    max_ram_entry.insert(0, settings["max_ram"])
    jvm_args_entry.delete(0, "end")
    jvm_args_entry.insert(0, settings["jvm_args"])
    settings_frame.tkraise()

def browse_java():
    path = filedialog.askopenfilename(title="Выберите java.exe", filetypes=[("java.exe", "java.exe"), ("Все файлы", "*.*")])
    if path:
        java_path_entry.delete(0, "end")
        java_path_entry.insert(0, path)

def save_settings_and_back():
    save_settings({
        "java_path": java_path_entry.get().strip(),
        "min_ram": min_ram_entry.get().strip() or DEFAULT_SETTINGS["min_ram"],
        "max_ram": max_ram_entry.get().strip() or DEFAULT_SETTINGS["max_ram"],
        "jvm_args": jvm_args_entry.get().strip(),
    })
    show_home()

def show_nicknames_page():
    render_nickname_list()
    nickname_frame.tkraise()

def select_nickname(name):
    username_entry.delete(0, "end")
    username_entry.insert(0, name)
    show_home()

def build_nickname_row(name):
    row = ctk.CTkFrame(nickname_list_frame, fg_color="#1a1d1f", corner_radius=8, border_width=2, border_color="#1a1d1f")
    color = ICON_COLORS[hash(name) % len(ICON_COLORS)]
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
        command=lambda n=name: delete_nickname(n),
    )
    delete_button.grid(row=0, column=2, padx=(0, 8))
    return row

def render_nickname_list():
    for widget in nickname_list_frame.winfo_children():
        widget.destroy()
    nicknames = load_nicknames()
    if not nicknames:
        ctk.CTkLabel(nickname_list_frame, text="Пока нет сохранённых ников", text_color="#9a9a9a").pack(pady=20)
        return
    for name in nicknames:
        build_nickname_row(name).pack(fill="x", pady=3)

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
BASE_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")

root = ctk.CTk()
root.title("Minecraft Launcher")
root.geometry("400x300")
root.resizable(False, False)
root.iconbitmap(ICON_PATH)
root.after(250, lambda: root.iconbitmap(ICON_PATH))
root.configure(fg_color="#0d0f10")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
home_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
home_frame.grid(row=0, column=0, sticky="nsew")
version_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
version_frame.grid(row=0, column=0, sticky="nsew")
nickname_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
nickname_frame.grid(row=0, column=0, sticky="nsew")
settings_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
settings_frame.grid(row=0, column=0, sticky="nsew")
logs_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
logs_frame.grid(row=0, column=0, sticky="nsew")

ctk.CTkLabel(home_frame, text="Minecraft Launcher", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
ctk.CTkButton(
    home_frame, text="⚙", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#1a1d1f", command=show_settings_page,
).place(relx=1.0, x=-14, y=14, anchor="ne")

nickname_row = ctk.CTkFrame(home_frame, fg_color="transparent")
nickname_row.pack(pady=(0, 10), padx=25, fill="x")
saved_nicknames = load_nicknames()
username_entry = ctk.CTkEntry(nickname_row, placeholder_text="Никнейм")
username_entry.pack(side="left", fill="x", expand=True)
username_entry.insert(0, saved_nicknames[0] if saved_nicknames else "")
ctk.CTkButton(nickname_row, text="☰", width=32, command=show_nicknames_page).pack(side="left", padx=(6, 0))

version_button = ctk.CTkButton(
    home_frame, text="Выберите версию игры...", anchor="w",
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

nickname_header = ctk.CTkFrame(nickname_frame, fg_color="transparent")
nickname_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    nickname_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(nickname_header, text="Никнеймы", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
nickname_list_frame = ctk.CTkScrollableFrame(nickname_frame, fg_color="transparent")
nickname_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

settings_header = ctk.CTkFrame(settings_frame, fg_color="transparent")
settings_header.pack(fill="x", padx=12, pady=(10, 10))
ctk.CTkButton(
    settings_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(settings_header, text="Настройки", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

ctk.CTkLabel(settings_frame, text="Путь к Java (пусто = по умолчанию)", font=ctk.CTkFont(size=11), text_color="#9a9a9a", anchor="w").pack(fill="x", padx=12)
java_path_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
java_path_row.pack(fill="x", padx=12, pady=(2, 8))
java_path_entry = ctk.CTkEntry(java_path_row, height=26)
java_path_entry.pack(side="left", fill="x", expand=True)
ctk.CTkButton(java_path_row, text="...", width=30, height=26, command=browse_java).pack(side="left", padx=(6, 0))

ctk.CTkLabel(settings_frame, text="Память, МБ (мин / макс)", font=ctk.CTkFont(size=11), text_color="#9a9a9a", anchor="w").pack(fill="x", padx=12)
ram_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
ram_row.pack(fill="x", padx=12, pady=(2, 8))
min_ram_entry = ctk.CTkEntry(ram_row, height=26)
min_ram_entry.pack(side="left", fill="x", expand=True)
max_ram_entry = ctk.CTkEntry(ram_row, height=26)
max_ram_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

ctk.CTkLabel(settings_frame, text="Аргументы JVM", font=ctk.CTkFont(size=11), text_color="#9a9a9a", anchor="w").pack(fill="x", padx=12)
jvm_args_entry = ctk.CTkEntry(settings_frame, height=26, placeholder_text="-Dfoo=bar -Dbaz=qux")
jvm_args_entry.pack(fill="x", padx=12, pady=(2, 10))

ctk.CTkButton(settings_frame, text="Сохранить", command=save_settings_and_back).pack(padx=12, pady=(0, 12), fill="x")

logs_header = ctk.CTkFrame(logs_frame, fg_color="transparent")
logs_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    logs_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(logs_header, text="Логи запуска", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

log_textbox = ctk.CTkTextbox(logs_frame, state="disabled", font=ctk.CTkFont(size=10, family="Consolas"))
log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 6))

stop_button = ctk.CTkButton(
    logs_frame, text="Остановить", state="disabled",
    fg_color="#b23b3b", hover_color="#8f2e2e", command=stop_game,
)
stop_button.pack(fill="x", padx=12, pady=(0, 12))

show_home()
threading.Thread(target=load_versions, daemon=True).start()

root.mainloop()
