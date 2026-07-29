import os
import sys
import threading

import customtkinter as ctk

import state
import storage
from activity import render_activity_card
from launcher import on_play, stop_game
from mods import add_mods, open_mods_folder, show_mods_page
from navigation import show_home, show_version_page
from nicknames import show_nicknames_page
from settings_page import browse_java, save_settings_and_back, show_settings_page
from versions import (
    cancel_loader_install, first_page, last_page, load_versions,
    next_page, on_search_changed, prev_page, set_active_loader,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
BASE_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")

state.root = ctk.CTk()
root = state.root
root.title("Minecraft Launcher")
root.geometry("400x300")
root.resizable(False, False)
root.iconbitmap(ICON_PATH)
root.after(250, lambda: root.iconbitmap(ICON_PATH))
root.configure(fg_color="#0d0f10")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

state.home_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.home_frame.grid(row=0, column=0, sticky="nsew")
state.version_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.version_frame.grid(row=0, column=0, sticky="nsew")
state.nickname_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.nickname_frame.grid(row=0, column=0, sticky="nsew")
state.settings_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.settings_frame.grid(row=0, column=0, sticky="nsew")
state.logs_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.logs_frame.grid(row=0, column=0, sticky="nsew")
state.mods_frame = ctk.CTkFrame(root, fg_color="#0d0f10", corner_radius=0)
state.mods_frame.grid(row=0, column=0, sticky="nsew")

home_frame = state.home_frame
version_frame = state.version_frame
nickname_frame = state.nickname_frame
settings_frame = state.settings_frame
logs_frame = state.logs_frame
mods_frame = state.mods_frame

ctk.CTkLabel(home_frame, text="Minecraft Launcher", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 4))
state.settings_button = ctk.CTkButton(
    home_frame, text="⚙", width=24, height=20, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#1a1d1f", command=show_settings_page,
)
state.settings_button.place(relx=1.0, x=-10, y=8, anchor="ne")

nickname_row = ctk.CTkFrame(home_frame, fg_color="transparent")
nickname_row.pack(pady=(0, 4), padx=20, fill="x")
saved_nicknames = storage.load_nicknames()
state.username_entry = ctk.CTkEntry(nickname_row, placeholder_text="Никнейм", height=24)
state.username_entry.pack(side="left", fill="x", expand=True)
state.username_entry.insert(0, saved_nicknames[0] if saved_nicknames else "")
state.nicknames_button = ctk.CTkButton(nickname_row, text="☰", width=28, height=24, command=show_nicknames_page)
state.nicknames_button.pack(side="left", padx=(6, 0))

state.version_button = ctk.CTkButton(
    home_frame, text="Выберите версию игры...", anchor="w", height=24,
    fg_color="#141617", hover_color="#1a1d1f", text_color="#e5e5e5",
    command=show_version_page,
)
state.version_button.pack(pady=(0, 4), padx=20, fill="x")

last_version = storage.load_config().get("last_version")
if last_version:
    state.selected_version = last_version
    state.version_button.configure(text=f"Версия: {last_version}")

activity_card = ctk.CTkFrame(home_frame, fg_color="#141617", corner_radius=10)
activity_card.pack(pady=(0, 4), padx=20, fill="x")

activity_header = ctk.CTkFrame(activity_card, fg_color="transparent")
activity_header.pack(fill="x", padx=10, pady=(6, 1))
ctk.CTkLabel(activity_header, text="Активность за неделю", font=ctk.CTkFont(size=10, weight="bold")).pack(side="left")
state.activity_total_label = ctk.CTkLabel(activity_header, text="", font=ctk.CTkFont(size=10), text_color="#9a9a9a")
state.activity_total_label.pack(side="right")

state.bars_row = ctk.CTkFrame(activity_card, fg_color="transparent", height=state.BAR_HEIGHT)
state.bars_row.pack(fill="x", padx=10)
state.bars_row.pack_propagate(False)

state.day_labels_row = ctk.CTkFrame(activity_card, fg_color="transparent", height=12)
state.day_labels_row.pack(fill="x", padx=10, pady=(1, 4))
state.day_labels_row.pack_propagate(False)

stats_row = ctk.CTkFrame(activity_card, fg_color="transparent")
stats_row.pack(fill="x", padx=10, pady=(0, 5))
state.stat_versions_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
state.stat_versions_label.pack(side="left", expand=True)
state.stat_time_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
state.stat_time_label.pack(side="left", expand=True)
state.stat_accounts_label = ctk.CTkLabel(stats_row, text="", font=ctk.CTkFont(size=10))
state.stat_accounts_label.pack(side="left", expand=True)

state.status_label = ctk.CTkLabel(home_frame, text="", font=ctk.CTkFont(size=10))
state.status_label.pack(pady=(0, 2))
state.play_button = ctk.CTkButton(home_frame, text="Играть", height=28, command=on_play)
state.play_button.pack(pady=(0, 8), padx=20, fill="x")

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
state.loader_tabs_buttons = {}
for i, (loader_id, loader_label) in enumerate(state.LOADERS):
    button = ctk.CTkButton(
        tabs, text=loader_label, width=58, height=24, font=ctk.CTkFont(size=9),
        fg_color=state.ACCENT if loader_id == "vanilla" else "transparent",
        text_color="#0d0f10" if loader_id == "vanilla" else "#c9c9c9",
        hover_color="#232628", command=lambda l=loader_id: set_active_loader(l),
    )
    button.pack(side="left", padx=(0 if i == 0 else 2, 0))
    state.loader_tabs_buttons[loader_id] = button

state.search_var = ctk.StringVar()
state.search_var.trace_add("write", on_search_changed)
state.search_entry = ctk.CTkEntry(version_frame, height=24, placeholder_text="🔍  Поиск версии...", textvariable=state.search_var)
state.search_entry.pack(fill="x", padx=12, pady=4)
state.install_progress_label = ctk.CTkLabel(version_frame, text="", font=ctk.CTkFont(size=10), text_color="#9a9a9a", anchor="w", height=16)
state.install_progress_label.pack(fill="x", padx=12)
state.list_frame = ctk.CTkFrame(version_frame, fg_color="transparent")
state.list_frame.pack(fill="both", expand=True, padx=12)
pagination = ctk.CTkFrame(version_frame, fg_color="transparent")
pagination.pack(fill="x", padx=12, pady=(4, 4))
state.first_button = ctk.CTkButton(pagination, text="|◀", width=26, height=24, font=ctk.CTkFont(size=11), command=first_page)
state.first_button.pack(side="left")
state.prev_button = ctk.CTkButton(pagination, text="◀", width=26, height=24, command=prev_page)
state.prev_button.pack(side="left", padx=(2, 0))
state.page_label = ctk.CTkLabel(pagination, text="", font=ctk.CTkFont(size=11))
state.page_label.pack(side="left", expand=True)
state.last_button = ctk.CTkButton(pagination, text="▶|", width=26, height=24, font=ctk.CTkFont(size=11), command=last_page)
state.last_button.pack(side="right")
state.next_button = ctk.CTkButton(pagination, text="▶", width=26, height=24, command=next_page)
state.next_button.pack(side="right", padx=(0, 2))
state.cancel_loader_button = ctk.CTkButton(
    version_frame, text="✕ Отменить установку", height=24, font=ctk.CTkFont(size=11), state="disabled",
    fg_color="#b23b3b", hover_color="#8f2e2e", command=cancel_loader_install,
)
state.cancel_loader_button.pack(fill="x", padx=12, pady=(0, 8))

nickname_header = ctk.CTkFrame(nickname_frame, fg_color="transparent")
nickname_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    nickname_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(nickname_header, text="Никнеймы", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
state.nickname_list_frame = ctk.CTkScrollableFrame(nickname_frame, fg_color="transparent")
state.nickname_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

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
state.java_path_entry = ctk.CTkEntry(java_path_row, height=26)
state.java_path_entry.pack(side="left", fill="x", expand=True)
ctk.CTkButton(java_path_row, text="...", width=30, height=26, command=browse_java).pack(side="left", padx=(6, 0))

ctk.CTkLabel(settings_frame, text="Память, МБ (мин / макс)", font=ctk.CTkFont(size=11), text_color="#9a9a9a", anchor="w").pack(fill="x", padx=12)
ram_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
ram_row.pack(fill="x", padx=12, pady=(2, 8))
state.min_ram_entry = ctk.CTkEntry(ram_row, height=26)
state.min_ram_entry.pack(side="left", fill="x", expand=True)
state.max_ram_entry = ctk.CTkEntry(ram_row, height=26)
state.max_ram_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

ctk.CTkLabel(settings_frame, text="Аргументы JVM", font=ctk.CTkFont(size=11), text_color="#9a9a9a", anchor="w").pack(fill="x", padx=12)
state.jvm_args_entry = ctk.CTkEntry(settings_frame, height=26, placeholder_text="-Dfoo=bar -Dbaz=qux")
state.jvm_args_entry.pack(fill="x", padx=12, pady=(2, 10))

ctk.CTkButton(settings_frame, text="Сохранить", command=save_settings_and_back).pack(padx=12, pady=(0, 12), fill="x")

logs_header = ctk.CTkFrame(logs_frame, fg_color="transparent")
logs_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    logs_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_home,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(logs_header, text="Логи запуска", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

state.log_textbox = ctk.CTkTextbox(logs_frame, state="disabled", font=ctk.CTkFont(size=10, family="Consolas"))
state.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 6))

state.stop_button = ctk.CTkButton(
    logs_frame, text="Остановить", state="disabled",
    fg_color="#b23b3b", hover_color="#8f2e2e", command=stop_game,
)
state.stop_button.pack(fill="x", padx=12, pady=(0, 12))

mods_header = ctk.CTkFrame(mods_frame, fg_color="transparent")
mods_header.pack(fill="x", padx=12, pady=(10, 6))
ctk.CTkButton(
    mods_header, text="←", width=28, height=24, fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=show_version_page,
).pack(side="left", padx=(0, 8))
ctk.CTkLabel(mods_header, text="Моды", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
ctk.CTkButton(
    mods_header, text="📂 Папка", width=70, height=24, font=ctk.CTkFont(size=11), fg_color="transparent",
    text_color="#c9c9c9", hover_color="#232628", command=open_mods_folder,
).pack(side="right")

ctk.CTkButton(mods_frame, text="+ Добавить .jar", height=28, command=add_mods).pack(fill="x", padx=12, pady=(0, 8))
state.mods_list_frame = ctk.CTkScrollableFrame(mods_frame, fg_color="transparent")
state.mods_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

storage.ensure_launcher_profiles()
render_activity_card()
show_home()
threading.Thread(target=load_versions, daemon=True).start()

root.mainloop()
