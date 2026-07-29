import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta
from tkinter import filedialog

import customtkinter as ctk
import minecraft_launcher_lib as mll

MINECRAFT_DIR = os.path.join(os.environ["APPDATA"], ".minecraft")
APP_DATA_DIR = os.path.join(os.environ["APPDATA"], ".simple_mc_launcher")
CONFIG_PATH = os.path.join(APP_DATA_DIR, "config.json")
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
WEEKDAY_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
ICON_COLORS = ["#e05fa0", "#4caf6d", "#8a6fe0", "#3b82f6", "#e0a75f", "#5fc7e0"]
BAR_MUTED = "#2a4a72"
BAR_WIDTH = 24
BAR_HEIGHT = 26

LOADERS = [("vanilla", "Ванила"), ("fabric", "Fabric"), ("quilt", "Quilt"), ("forge", "Forge"), ("neoforge", "NeoForge"), ("custom", "Свои версии")]

all_versions = []
latest_ids = {}
active_loader = "vanilla"
current_page = 0
total_pages = 1
selected_version = None
version_rows = {}
game_process = None
loader_versions_cache = {}
loader_installing = False
installing_game = False
cancel_requested = False

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
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_launcher_profiles():
    stub = {
        "profiles": {},
        "settings": {
            "crashAssistance": True,
            "enableAdvanced": False,
            "enableAnalytics": True,
            "enableHistorical": False,
            "enableReleases": True,
            "enableSnapshots": False,
            "keepLauncherOpen": False,
            "profileSorting": "ByLastPlayed",
            "showGameLog": False,
            "showMenu": False,
            "soundOn": False,
        },
        "version": 3,
    }
    os.makedirs(MINECRAFT_DIR, exist_ok=True)
    for filename in ("launcher_profiles.json", "launcher_profiles_microsoft_store.json"):
        path = os.path.join(MINECRAFT_DIR, filename)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(stub, f, indent=2)


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

def record_session(version, duration_seconds):
    config = load_config()
    activity = config.setdefault("activity", {})
    today = date.today().isoformat()
    activity[today] = activity.get(today, 0) + duration_seconds
    versions_used = config.setdefault("versions_used", [])
    if version not in versions_used:
        versions_used.append(version)
    write_config(config)

def save_last_version(version):
    config = load_config()
    config["last_version"] = version
    write_config(config)

def format_duration(seconds):
    total_minutes = int(seconds // 60)
    h, m = divmod(total_minutes, 60)
    return f"{h}ч {m}м" if h else f"{m}м"

def format_date(value):
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return f"{dt.day} {RU_MONTHS[dt.month]} {dt.year} г."

def is_installed(version):
    return any(v["id"] == version for v in mll.utils.get_installed_versions(MINECRAFT_DIR))

class InstallCancelled(Exception):
    pass

def cancellable(fn):
    def wrapper(text):
        if cancel_requested:
            raise InstallCancelled()
        fn(text)
    return wrapper

def ensure_java_runtime(version, on_progress=None):
    try:
        info = mll.runtime.get_version_runtime_information(version, MINECRAFT_DIR)
    except Exception:
        return None
    if not info:
        return None
    component = info["name"]
    path = mll.runtime.get_executable_path(component, MINECRAFT_DIR)
    if path:
        return path
    try:
        mll.runtime.install_jvm_runtime(component, MINECRAFT_DIR, callback={"setStatus": on_progress} if on_progress else None)
    except InstallCancelled:
        raise
    except Exception:
        return None
    return mll.runtime.get_executable_path(component, MINECRAFT_DIR)

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

def set_home_locked(locked):
    state = "disabled" if locked else "normal"
    username_entry.configure(state=state)
    nicknames_button.configure(state=state)
    version_button.configure(state=state)
    settings_button.configure(state=state)

def cancel_launch():
    global cancel_requested
    cancel_requested = True
    status_label.configure(text="Отмена...")

def launch_game():
    global game_process, installing_game, cancel_requested

    username = username_entry.get().strip() or "Player"
    version = selected_version
    settings = load_settings()

    installing_game = True
    cancel_requested = False
    root.after(0, lambda: play_button.configure(state="normal", text="Отменить", command=cancel_launch))
    root.after(0, lambda: set_home_locked(True))
    save_nickname(username)

    try:
        if not is_installed(version):
            mll.install.install_minecraft_version(
                version, MINECRAFT_DIR,
                callback={"setStatus": cancellable(set_status)},
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
        else:
            runtime_java = ensure_java_runtime(version, on_progress=cancellable(set_status))
            if runtime_java:
                options["executablePath"] = runtime_java

        command = mll.command.get_minecraft_command(version, MINECRAFT_DIR, options)
        installing_game = False
        root.after(0, lambda: set_home_locked(False))
        start_ts = time.time()
        game_process = subprocess.Popen(
            command, cwd=MINECRAFT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        save_last_version(version)
        root.after(0, clear_logs)
        root.after(0, show_logs_page)
        root.after(0, lambda: stop_button.configure(state="normal"))
        root.after(0, lambda: play_button.configure(state="normal", text="Показать логи", command=show_logs_page))

        for line in game_process.stdout:
            root.after(0, lambda l=line: append_log(l))
        game_process.wait()
        record_session(version, time.time() - start_ts)
        root.after(0, render_activity_card)
        set_status("Игра завершена")
    except InstallCancelled:
        set_status("Установка отменена")
    except Exception as exc:
        message = f"Ошибка: {exc}"
        set_status(message)

    installing_game = False
    cancel_requested = False
    game_process = None
    root.after(0, lambda: set_home_locked(False))
    root.after(0, lambda: stop_button.configure(state="disabled"))
    root.after(0, lambda: play_button.configure(state="normal", text="Играть", command=on_play))

def on_play():
    if installing_game:
        return
    if not selected_version:
        status_label.configure(text="Сначала выберите версию")
        return
    if game_process and game_process.poll() is None:
        show_logs_page()
        return
    threading.Thread(target=launch_game, daemon=True).start()

def render_activity_card():
    config = load_config()
    activity = config.get("activity", {})
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    values = [activity.get(d.isoformat(), 0) for d in days]
    max_value = max(values) or 1

    activity_total_label.configure(text=format_duration(sum(values)))

    for widget in bars_row.winfo_children():
        widget.destroy()
    for widget in day_labels_row.winfo_children():
        widget.destroy()

    n = len(days)
    for i, (d, value) in enumerate(zip(days, values)):
        is_today = d == today
        bar_h = max(3, int(BAR_HEIGHT * value / max_value)) if value else 3
        bar = ctk.CTkFrame(bars_row, fg_color=ACCENT if is_today else BAR_MUTED, corner_radius=4, width=BAR_WIDTH, height=bar_h)
        bar.place(relx=(i + 0.5) / n, rely=1.0, anchor="s")
        bar.bind("<Enter>", lambda _e, dd=d, vv=value: status_label.configure(text=f"{WEEKDAY_RU[dd.weekday()]}: {format_duration(vv)}"))

        label = ctk.CTkLabel(
            day_labels_row, text=WEEKDAY_RU[d.weekday()], font=ctk.CTkFont(size=9, weight="bold" if is_today else "normal"),
            text_color=ACCENT if is_today else "#9a9a9a",
        )
        label.place(relx=(i + 0.5) / n, rely=0.5, anchor="c")

    stat_versions_label.configure(text=f"🧩 {len(config.get('versions_used', []))}")
    stat_time_label.configure(text=f"⏱ {format_duration(sum(activity.values()))}")
    stat_accounts_label.configure(text=f"👤 {len(config.get('nicknames', []))}")

def show_home():
    home_frame.tkraise()

def show_version_page():
    version_frame.tkraise()

def mods_dir():
    return os.path.join(MINECRAFT_DIR, "mods")

def build_mod_row(name):
    row = ctk.CTkFrame(mods_list_frame, fg_color="#1a1d1f", corner_radius=8)
    ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=12), anchor="w").pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)
    ctk.CTkButton(
        row, text="✕", width=24, height=24, fg_color="transparent",
        text_color="#9a9a9a", hover_color="#3a1f1f", command=lambda n=name: delete_mod(n),
    ).pack(side="right", padx=(0, 8))
    return row

def render_mods_list():
    for widget in mods_list_frame.winfo_children():
        widget.destroy()
    os.makedirs(mods_dir(), exist_ok=True)
    files = sorted(f for f in os.listdir(mods_dir()) if f.lower().endswith(".jar"))
    if not files:
        ctk.CTkLabel(mods_list_frame, text="Модов пока нет", text_color="#9a9a9a").pack(pady=20)
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

def delete_mod(name):
    try:
        os.remove(os.path.join(mods_dir(), name))
    except OSError:
        pass
    render_mods_list()

def show_mods_page():
    render_mods_list()
    mods_frame.tkraise()

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

def set_active_loader(loader_id):
    global active_loader, current_page
    if loader_installing:
        return
    active_loader = loader_id
    current_page = 0
    for lid, button in loader_tabs_buttons.items():
        if lid == loader_id:
            button.configure(fg_color=ACCENT, text_color="#0d0f10")
        else:
            button.configure(fg_color="transparent", text_color="#c9c9c9")
    if loader_id not in ("vanilla", "custom") and loader_id not in loader_versions_cache:
        install_progress_label.configure(text="Загрузка списка версий...")
        threading.Thread(target=load_loader_versions_thread, args=(loader_id,), daemon=True).start()
    else:
        install_progress_label.configure(text="")
    render_version_list()

def load_loader_versions_thread(loader_id):
    try:
        loader = mll.mod_loader.get_mod_loader(loader_id)
        versions = loader.get_minecraft_versions(True)
    except Exception:
        versions = []
    loader_versions_cache[loader_id] = versions
    def apply():
        if loader_id == active_loader:
            install_progress_label.configure(text="")
            render_version_list()
    root.after(0, apply)

def on_search_changed(*_args):
    global current_page
    current_page = 0
    render_version_list()

def first_page():
    global current_page
    if current_page > 0:
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

def last_page():
    global current_page
    if current_page < total_pages - 1:
        current_page = total_pages - 1
        render_version_list()

def select_version(version_id):
    global selected_version
    selected_version = version_id
    version_button.configure(text=f"Версия: {version_id}")
    show_home()

def find_installed_modded_id(loader_id, vanilla_version):
    for v in mll.utils.get_installed_versions(MINECRAFT_DIR):
        vid = v["id"].lower()
        if vanilla_version not in v["id"]:
            continue
        if loader_id == "forge" and "forge" in vid and "neoforge" not in vid:
            return v["id"]
        if loader_id == "neoforge" and "neoforge" in vid:
            return v["id"]
        if loader_id in ("fabric", "quilt") and loader_id in vid:
            return v["id"]
    return None

def set_loader_page_locked(locked):
    state = "disabled" if locked else "normal"
    for button in loader_tabs_buttons.values():
        button.configure(state=state)
    search_entry.configure(state=state)
    first_button.configure(state="disabled" if locked else ("normal" if current_page > 0 else "disabled"))
    prev_button.configure(state="disabled" if locked else ("normal" if current_page > 0 else "disabled"))
    next_button.configure(state="disabled" if locked else ("normal" if current_page < total_pages - 1 else "disabled"))
    last_button.configure(state="disabled" if locked else ("normal" if current_page < total_pages - 1 else "disabled"))
    cancel_loader_button.configure(state="normal" if locked else "disabled")

def cancel_loader_install():
    global cancel_requested
    cancel_requested = True
    install_progress_label.configure(text="Отмена...")

def install_and_select_thread(loader_id, vanilla_version):
    global loader_installing, cancel_requested
    loader_installing = True
    cancel_requested = False
    root.after(0, lambda: set_loader_page_locked(True))
    root.after(0, lambda: install_progress_label.configure(text=f"Установка {loader_id} для {vanilla_version}..."))
    try:
        settings = load_settings()
        status_callback = cancellable(lambda text: root.after(0, lambda: install_progress_label.configure(text=text)))
        if not is_installed(vanilla_version):
            mll.install.install_minecraft_version(vanilla_version, MINECRAFT_DIR, callback={"setStatus": status_callback})
        java = settings["java_path"] or ensure_java_runtime(vanilla_version, on_progress=status_callback)
        loader = mll.mod_loader.get_mod_loader(loader_id)
        installed_id = loader.install(
            vanilla_version, MINECRAFT_DIR, java=java,
            callback={"setStatus": status_callback},
        )
        root.after(0, lambda: install_progress_label.configure(text=""))
        root.after(0, lambda: select_version(installed_id))
    except InstallCancelled:
        root.after(0, lambda: install_progress_label.configure(text="Установка отменена"))
    except Exception as exc:
        message = f"Ошибка: {exc}"
        root.after(0, lambda: install_progress_label.configure(text=message))
    loader_installing = False
    cancel_requested = False
    root.after(0, lambda: set_loader_page_locked(False))

def on_version_row_click(vanilla_version):
    if active_loader in ("vanilla", "custom"):
        select_version(vanilla_version)
        return
    if loader_installing:
        return
    existing = find_installed_modded_id(active_loader, vanilla_version)
    if existing:
        select_version(existing)
        return
    threading.Thread(target=install_and_select_thread, args=(active_loader, vanilla_version), daemon=True).start()

LOADER_KEYWORDS = ("fabric", "quilt", "forge", "neoforge")

def get_custom_installed_versions():
    official_ids = {v["id"] for v in all_versions}
    custom = []
    for v in mll.utils.get_installed_versions(MINECRAFT_DIR):
        if v["id"] in official_ids:
            continue
        if any(k in v["id"].lower() for k in LOADER_KEYWORDS):
            continue
        custom.append(v)
    return custom

def build_version_row(version_id, is_latest, release_time, is_installed_modded):
    row = ctk.CTkFrame(list_frame, fg_color="#1a1d1f", corner_radius=8, border_width=2, border_color="#1a1d1f")
    color = ICON_COLORS[hash(version_id) % len(ICON_COLORS)]
    ctk.CTkLabel(row, text="", width=22, height=22, corner_radius=5, fg_color=color).grid(row=0, column=0, padx=(8, 8), pady=6)
    ctk.CTkLabel(row, text=version_id, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=1, sticky="ew")
    col = 2
    if is_latest:
        ctk.CTkLabel(
            row, text="последняя", font=ctk.CTkFont(size=10),
            fg_color=BADGE_BG, text_color=BADGE_TEXT, corner_radius=5,
        ).grid(row=0, column=col, padx=(6, 0))
        col += 1
    if is_installed_modded:
        ctk.CTkLabel(
            row, text="установлено", font=ctk.CTkFont(size=10),
            fg_color="#173a2b", text_color="#4caf6d", corner_radius=5,
        ).grid(row=0, column=col, padx=(6, 0))
        col += 1
    if release_time:
        ctk.CTkLabel(row, text=format_date(release_time), text_color="#9a9a9a", font=ctk.CTkFont(size=11)).grid(row=0, column=col, padx=(6, 6))
    col += 1
    check_label = ctk.CTkLabel(row, text="", width=14, text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold"))
    check_label.grid(row=0, column=col, padx=(0, 8))
    row.grid_columnconfigure(1, weight=1, minsize=50)
    for widget in row.winfo_children():
        widget.bind("<Button-1>", lambda _e, vid=version_id: on_version_row_click(vid))
    row.bind("<Button-1>", lambda _e, vid=version_id: on_version_row_click(vid))
    return row, check_label

def render_version_list():
    global total_pages, current_page
    for widget in list_frame.winfo_children():
        widget.destroy()
    version_rows.clear()
    query = search_var.get().strip().lower()
    versions_by_id = {v["id"]: v for v in all_versions}

    if active_loader == "vanilla":
        latest_for_type = latest_ids.get("release")
        filtered_ids = [v["id"] for v in all_versions if v["type"] == "release" and query in v["id"].lower()]
    elif active_loader == "custom":
        latest_for_type = None
        custom_versions = get_custom_installed_versions()
        for v in custom_versions:
            versions_by_id[v["id"]] = v
        filtered_ids = [v["id"] for v in custom_versions if query in v["id"].lower()]
    else:
        latest_for_type = None
        filtered_ids = [vid for vid in loader_versions_cache.get(active_loader, []) if query in vid.lower()]

    total_pages = max(1, -(-len(filtered_ids) // PAGE_SIZE))
    current_page = min(current_page, total_pages - 1)
    start = current_page * PAGE_SIZE
    page_items = filtered_ids[start:start + PAGE_SIZE]

    is_direct_select = active_loader in ("vanilla", "custom")
    for version_id in page_items:
        meta = versions_by_id.get(version_id)
        release_time = meta["releaseTime"] if meta else None
        installed_modded_id = None if is_direct_select else find_installed_modded_id(active_loader, version_id)
        row, check_label = build_version_row(
            version_id, version_id == latest_for_type, release_time,
            installed_modded_id is not None,
        )
        row.pack(fill="x", pady=3)
        version_rows[version_id] = (row, check_label)
        is_selected = version_id == selected_version if is_direct_select else installed_modded_id == selected_version
        if is_selected:
            row.configure(border_color=ACCENT)
            check_label.configure(text="✓")
    page_label.configure(text=f"Стр. {current_page + 1} из {total_pages}")
    first_button.configure(state="normal" if current_page > 0 else "disabled")
    prev_button.configure(state="normal" if current_page > 0 else "disabled")
    next_button.configure(state="normal" if current_page < total_pages - 1 else "disabled")
    last_button.configure(state="normal" if current_page < total_pages - 1 else "disabled")

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
mods_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
mods_frame.grid(row=0, column=0, sticky="nsew")

ctk.CTkLabel(home_frame, text="Minecraft Launcher", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 4))
settings_button = ctk.CTkButton(
    home_frame, text="⚙", width=24, height=20, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#1a1d1f", command=show_settings_page,
)
settings_button.place(relx=1.0, x=-10, y=8, anchor="ne")

nickname_row = ctk.CTkFrame(home_frame, fg_color="transparent")
nickname_row.pack(pady=(0, 4), padx=20, fill="x")
saved_nicknames = load_nicknames()
username_entry = ctk.CTkEntry(nickname_row, placeholder_text="Никнейм", height=24)
username_entry.pack(side="left", fill="x", expand=True)
username_entry.insert(0, saved_nicknames[0] if saved_nicknames else "")
nicknames_button = ctk.CTkButton(nickname_row, text="☰", width=28, height=24, command=show_nicknames_page)
nicknames_button.pack(side="left", padx=(6, 0))

version_button = ctk.CTkButton(
    home_frame, text="Выберите версию игры...", anchor="w", height=24,
    fg_color="#141617", hover_color="#1a1d1f", text_color="#e5e5e5",
    command=show_version_page,
)
version_button.pack(pady=(0, 4), padx=20, fill="x")

last_version = load_config().get("last_version")
if last_version:
    selected_version = last_version
    version_button.configure(text=f"Версия: {last_version}")

activity_card = ctk.CTkFrame(home_frame, fg_color="#141617", corner_radius=10)
activity_card.pack(pady=(0, 4), padx=20, fill="x")

activity_header = ctk.CTkFrame(activity_card, fg_color="transparent")
activity_header.pack(fill="x", padx=10, pady=(6, 1))
ctk.CTkLabel(activity_header, text="Активность за неделю", font=ctk.CTkFont(size=10, weight="bold")).pack(side="left")
activity_total_label = ctk.CTkLabel(activity_header, text="", font=ctk.CTkFont(size=10), text_color="#9a9a9a")
activity_total_label.pack(side="right")

bars_row = ctk.CTkFrame(activity_card, fg_color="transparent", height=BAR_HEIGHT)
bars_row.pack(fill="x", padx=10)
bars_row.pack_propagate(False)

day_labels_row = ctk.CTkFrame(activity_card, fg_color="transparent", height=12)
day_labels_row.pack(fill="x", padx=10, pady=(1, 4))
day_labels_row.pack_propagate(False)

stats_row = ctk.CTkFrame(activity_card, fg_color="transparent")
stats_row.pack(fill="x", padx=10, pady=(0, 5))
stat_versions_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
stat_versions_label.pack(side="left", expand=True)
stat_time_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
stat_time_label.pack(side="left", expand=True)
stat_accounts_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
stat_accounts_label.pack(side="left", expand=True)

status_label = ctk.CTkLabel(home_frame, text="", font=ctk.CTkFont(size=10))
status_label.pack(pady=(0, 2))
play_button = ctk.CTkButton(home_frame, text="Играть", height=28, command=on_play)
play_button.pack(pady=(0, 8), padx=20, fill="x")

header = ctk.CTkFrame(version_frame, fg_color="transparent")
header.pack(fill="x", padx=12, pady=(8, 4))
ctk.CTkButton(
    header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(header, text="Версия Minecraft", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
ctk.CTkButton(
    header, text="🧩 Моды", width=70, height=24, font=ctk.CTkFont(size=11), fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_mods_page,
).pack(side="right")

tabs = ctk.CTkFrame(version_frame, fg_color="transparent")
tabs.pack(fill="x", padx=12)
loader_tabs_buttons = {}
for i, (loader_id, loader_label) in enumerate(LOADERS):
    button = ctk.CTkButton(
        tabs, text=loader_label, width=58, height=24, font=ctk.CTkFont(size=9),
        fg_color=ACCENT if loader_id == "vanilla" else "transparent",
        text_color="#0d0f10" if loader_id == "vanilla" else "#c9c9c9",
        hover_color="#232628", command=lambda l=loader_id: set_active_loader(l),
    )
    button.pack(side="left", padx=(0 if i == 0 else 2, 0))
    loader_tabs_buttons[loader_id] = button

search_var = ctk.StringVar()
search_var.trace_add("write", on_search_changed)
search_entry = ctk.CTkEntry(version_frame, height=24, placeholder_text="🔍  Поиск версии...", textvariable=search_var)
search_entry.pack(fill="x", padx=12, pady=4)
install_progress_label = ctk.CTkLabel(version_frame, text="", font=ctk.CTkFont(size=10), text_color="#9a9a9a", anchor="w", height=16)
install_progress_label.pack(fill="x", padx=12)
list_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
list_frame.pack(fill="both", expand=True, padx=12)
pagination = ctk.CTkFrame(version_frame, fg_color="transparent")
pagination.pack(fill="x", padx=12, pady=(4, 4))
first_button = ctk.CTkButton(pagination, text="|◀", width=26, height=24, font=ctk.CTkFont(size=11), command=first_page)
first_button.pack(side="left")
prev_button = ctk.CTkButton(pagination, text="◀", width=26, height=24, command=prev_page)
prev_button.pack(side="left", padx=(2, 0))
page_label = ctk.CTkLabel(pagination, text="", font=ctk.CTkFont(size=11))
page_label.pack(side="left", expand=True)
last_button = ctk.CTkButton(pagination, text="▶|", width=26, height=24, font=ctk.CTkFont(size=11), command=last_page)
last_button.pack(side="right")
next_button = ctk.CTkButton(pagination, text="▶", width=26, height=24, command=next_page)
next_button.pack(side="right", padx=(0, 2))
cancel_loader_button = ctk.CTkButton(
    version_frame, text="✕ Отменить установку", height=24, font=ctk.CTkFont(size=11), state="disabled",
    fg_color="#b23b3b", hover_color="#8f2e2e", command=cancel_loader_install,
)
cancel_loader_button.pack(fill="x", padx=12, pady=(0, 8))

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

mods_header = ctk.CTkFrame(mods_frame, fg_color="transparent")
mods_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    mods_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_version_page,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(mods_header, text="Моды", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

ctk.CTkButton(mods_frame, text="+ Добавить .jar", height=28, command=add_mods).pack(fill="x", padx=12, pady=(0, 8))
mods_list_frame = ctk.CTkScrollableFrame(mods_frame, fg_color="transparent")
mods_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

ensure_launcher_profiles()
render_activity_card()
show_home()
threading.Thread(target=load_versions, daemon=True).start()

root.mainloop()
