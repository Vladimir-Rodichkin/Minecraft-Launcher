import threading

import customtkinter as ctk
import minecraft_launcher_lib as mll

import state
import storage
from java_runtime import InstallCancelled, cancellable, ensure_java_runtime
from navigation import show_home


def load_versions():
    state.all_versions = mll.utils.get_version_list()
    state.latest_ids = mll.utils.get_latest_version()
    state.root.after(0, render_version_list)


def set_active_loader(loader_id):
    if state.loader_installing:
        return
    state.active_loader = loader_id
    state.current_page = 0
    for lid, button in state.loader_tabs_buttons.items():
        if lid == loader_id:
            button.configure(fg_color=state.ACCENT, text_color="#0d0f10")
        else:
            button.configure(fg_color="transparent", text_color="#c9c9c9")
    if loader_id not in ("vanilla", "custom") and loader_id not in state.loader_versions_cache:
        state.install_progress_label.configure(text="Загрузка списка версий...")
        threading.Thread(target=load_loader_versions_thread, args=(loader_id,), daemon=True).start()
    else:
        state.install_progress_label.configure(text="")
    render_version_list()


def load_loader_versions_thread(loader_id):
    try:
        loader = mll.mod_loader.get_mod_loader(loader_id)
        versions = loader.get_minecraft_versions(True)
    except Exception:
        versions = []
    state.loader_versions_cache[loader_id] = versions

    def apply():
        if loader_id == state.active_loader:
            state.install_progress_label.configure(text="")
            render_version_list()
    state.root.after(0, apply)


def on_search_changed(*_args):
    state.current_page = 0
    render_version_list()


def first_page():
    if state.current_page > 0:
        state.current_page = 0
        render_version_list()


def prev_page():
    if state.current_page > 0:
        state.current_page -= 1
        render_version_list()


def next_page():
    if state.current_page < state.total_pages - 1:
        state.current_page += 1
        render_version_list()


def last_page():
    if state.current_page < state.total_pages - 1:
        state.current_page = state.total_pages - 1
        render_version_list()


def select_version(version_id):
    state.selected_version = version_id
    state.version_button.configure(text=f"Версия: {version_id}")
    show_home()


def find_installed_modded_id(loader_id, vanilla_version):
    for v in mll.utils.get_installed_versions(state.MINECRAFT_DIR):
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


def get_custom_installed_versions():
    official_ids = {v["id"] for v in state.all_versions}
    custom = []
    for v in mll.utils.get_installed_versions(state.MINECRAFT_DIR):
        if v["id"] in official_ids:
            continue
        if any(k in v["id"].lower() for k in state.LOADER_KEYWORDS):
            continue
        custom.append(v)
    return custom


def set_loader_page_locked(locked):
    ui_state = "disabled" if locked else "normal"
    for button in state.loader_tabs_buttons.values():
        button.configure(state=ui_state)
    state.search_entry.configure(state=ui_state)
    state.first_button.configure(state="disabled" if locked else ("normal" if state.current_page > 0 else "disabled"))
    state.prev_button.configure(state="disabled" if locked else ("normal" if state.current_page > 0 else "disabled"))
    state.next_button.configure(state="disabled" if locked else ("normal" if state.current_page < state.total_pages - 1 else "disabled"))
    state.last_button.configure(state="disabled" if locked else ("normal" if state.current_page < state.total_pages - 1 else "disabled"))
    state.cancel_loader_button.configure(state="normal" if locked else "disabled")


def cancel_loader_install():
    state.cancel_requested = True
    state.install_progress_label.configure(text="Отмена...")


def install_and_select_thread(loader_id, vanilla_version):
    state.loader_installing = True
    state.cancel_requested = False
    state.root.after(0, lambda: set_loader_page_locked(True))
    state.root.after(0, lambda: state.install_progress_label.configure(text=f"Установка {loader_id} для {vanilla_version}..."))
    try:
        settings = storage.load_settings()
        status_callback = cancellable(lambda text: state.root.after(0, lambda: state.install_progress_label.configure(text=text)))
        if not storage.is_installed(vanilla_version):
            mll.install.install_minecraft_version(vanilla_version, state.MINECRAFT_DIR, callback={"setStatus": status_callback})
        java = settings["java_path"] or ensure_java_runtime(vanilla_version, on_progress=status_callback)
        loader = mll.mod_loader.get_mod_loader(loader_id)
        installed_id = loader.install(
            vanilla_version, state.MINECRAFT_DIR, java=java,
            callback={"setStatus": status_callback},
        )
        state.root.after(0, lambda: state.install_progress_label.configure(text=""))
        state.root.after(0, lambda: select_version(installed_id))
    except InstallCancelled:
        state.root.after(0, lambda: state.install_progress_label.configure(text="Установка отменена"))
    except Exception as exc:
        message = f"Ошибка: {exc}"
        state.root.after(0, lambda: state.install_progress_label.configure(text=message))
    state.loader_installing = False
    state.cancel_requested = False
    state.root.after(0, lambda: set_loader_page_locked(False))


def on_version_row_click(vanilla_version):
    if state.active_loader in ("vanilla", "custom"):
        select_version(vanilla_version)
        return
    if state.loader_installing:
        return
    existing = find_installed_modded_id(state.active_loader, vanilla_version)
    if existing:
        select_version(existing)
        return
    threading.Thread(target=install_and_select_thread, args=(state.active_loader, vanilla_version), daemon=True).start()


def build_version_row(version_id, is_latest, release_time, is_installed_modded):
    row = ctk.CTkFrame(state.list_frame, fg_color="#1a1d1f", corner_radius=8, border_width=2, border_color="#1a1d1f")
    color = state.ICON_COLORS[hash(version_id) % len(state.ICON_COLORS)]
    ctk.CTkLabel(row, text="", width=22, height=22, corner_radius=5, fg_color=color).grid(row=0, column=0, padx=(8, 8), pady=6)
    ctk.CTkLabel(row, text=version_id, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").grid(row=0, column=1, sticky="ew")
    col = 2
    if is_latest:
        ctk.CTkLabel(
            row, text="последняя", font=ctk.CTkFont(size=10),
            fg_color=state.BADGE_BG, text_color=state.BADGE_TEXT, corner_radius=5,
        ).grid(row=0, column=col, padx=(6, 0))
        col += 1
    if is_installed_modded:
        ctk.CTkLabel(
            row, text="установлено", font=ctk.CTkFont(size=10),
            fg_color="#173a2b", text_color="#4caf6d", corner_radius=5,
        ).grid(row=0, column=col, padx=(6, 0))
        col += 1
    if release_time:
        ctk.CTkLabel(row, text=storage.format_date(release_time), text_color="#9a9a9a", font=ctk.CTkFont(size=11)).grid(row=0, column=col, padx=(6, 6))
    col += 1
    check_label = ctk.CTkLabel(row, text="", width=14, text_color=state.ACCENT, font=ctk.CTkFont(size=13, weight="bold"))
    check_label.grid(row=0, column=col, padx=(0, 8))
    row.grid_columnconfigure(1, weight=1, minsize=50)
    for widget in row.winfo_children():
        widget.bind("<Button-1>", lambda _e, vid=version_id: on_version_row_click(vid))
    row.bind("<Button-1>", lambda _e, vid=version_id: on_version_row_click(vid))
    return row, check_label


def render_version_list():
    for widget in state.list_frame.winfo_children():
        widget.destroy()
    state.version_rows.clear()
    query = state.search_var.get().strip().lower()
    versions_by_id = {v["id"]: v for v in state.all_versions}

    if state.active_loader == "vanilla":
        latest_for_type = state.latest_ids.get("release")
        filtered_ids = [v["id"] for v in state.all_versions if v["type"] == "release" and query in v["id"].lower()]
    elif state.active_loader == "custom":
        latest_for_type = None
        custom_versions = get_custom_installed_versions()
        for v in custom_versions:
            versions_by_id[v["id"]] = v
        filtered_ids = [v["id"] for v in custom_versions if query in v["id"].lower()]
    else:
        latest_for_type = None
        filtered_ids = [vid for vid in state.loader_versions_cache.get(state.active_loader, []) if query in vid.lower()]

    state.total_pages = max(1, -(-len(filtered_ids) // state.PAGE_SIZE))
    state.current_page = min(state.current_page, state.total_pages - 1)
    start = state.current_page * state.PAGE_SIZE
    page_items = filtered_ids[start:start + state.PAGE_SIZE]

    is_direct_select = state.active_loader in ("vanilla", "custom")
    for version_id in page_items:
        meta = versions_by_id.get(version_id)
        release_time = meta["releaseTime"] if meta else None
        installed_modded_id = None if is_direct_select else find_installed_modded_id(state.active_loader, version_id)
        row, check_label = build_version_row(
            version_id, version_id == latest_for_type, release_time,
            installed_modded_id is not None,
        )
        row.pack(fill="x", pady=3)
        state.version_rows[version_id] = (row, check_label)
        is_selected = version_id == state.selected_version if is_direct_select else installed_modded_id == state.selected_version
        if is_selected:
            row.configure(border_color=state.ACCENT)
            check_label.configure(text="✓")
    state.page_label.configure(text=f"Стр. {state.current_page + 1} из {state.total_pages}")
    state.first_button.configure(state="normal" if state.current_page > 0 else "disabled")
    state.prev_button.configure(state="normal" if state.current_page > 0 else "disabled")
    state.next_button.configure(state="normal" if state.current_page < state.total_pages - 1 else "disabled")
    state.last_button.configure(state="normal" if state.current_page < state.total_pages - 1 else "disabled")
