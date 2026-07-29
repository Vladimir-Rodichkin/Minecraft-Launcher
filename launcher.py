import subprocess
import threading
import time

import minecraft_launcher_lib as mll

import state
import storage
from activity import render_activity_card
from java_runtime import InstallCancelled, cancellable, ensure_java_runtime
from navigation import show_logs_page


def set_status(text):
    state.root.after(0, lambda: state.status_label.configure(text=text))


def clear_logs():
    state.log_textbox.configure(state="normal")
    state.log_textbox.delete("1.0", "end")
    state.log_textbox.configure(state="disabled")


def append_log(line):
    state.log_textbox.configure(state="normal")
    state.log_textbox.insert("end", line)
    state.log_textbox.see("end")
    state.log_textbox.configure(state="disabled")


def stop_game():
    if state.game_process and state.game_process.poll() is None:
        state.game_process.terminate()
        set_status("Останавливаем...")
        state.stop_button.configure(state="disabled")


def set_home_locked(locked):
    ui_state = "disabled" if locked else "normal"
    state.username_entry.configure(state=ui_state)
    state.nicknames_button.configure(state=ui_state)
    state.version_button.configure(state=ui_state)
    state.settings_button.configure(state=ui_state)


def cancel_launch():
    state.cancel_requested = True
    state.status_label.configure(text="Отмена...")


def launch_game():
    username = state.username_entry.get().strip() or "Player"
    version = state.selected_version
    settings = storage.load_settings()

    state.installing_game = True
    state.cancel_requested = False
    state.root.after(0, lambda: state.play_button.configure(state="normal", text="Отменить", command=cancel_launch))
    state.root.after(0, lambda: set_home_locked(True))
    storage.save_nickname(username)

    try:
        if not storage.is_installed(version):
            mll.install.install_minecraft_version(
                version, state.MINECRAFT_DIR,
                callback={"setStatus": cancellable(set_status)},
            )

        options = mll.utils.generate_test_options()
        options["username"] = username

        try:
            min_ram = int(settings["min_ram"])
        except ValueError:
            min_ram = int(state.DEFAULT_SETTINGS["min_ram"])
        try:
            max_ram = int(settings["max_ram"])
        except ValueError:
            max_ram = int(state.DEFAULT_SETTINGS["max_ram"])

        jvm_args = [f"-Xms{min_ram}M", f"-Xmx{max_ram}M"] + settings["jvm_args"].split()
        options["jvmArguments"] = jvm_args
        if settings["java_path"]:
            options["executablePath"] = settings["java_path"]
        else:
            runtime_java = ensure_java_runtime(version, on_progress=cancellable(set_status))
            if runtime_java:
                options["executablePath"] = runtime_java

        command = mll.command.get_minecraft_command(version, state.MINECRAFT_DIR, options)
        state.installing_game = False
        state.root.after(0, lambda: set_home_locked(False))
        start_ts = time.time()
        state.game_process = subprocess.Popen(
            command, cwd=state.MINECRAFT_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        storage.save_last_version(version)
        state.root.after(0, clear_logs)
        state.root.after(0, show_logs_page)
        state.root.after(0, lambda: state.stop_button.configure(state="normal"))
        state.root.after(0, lambda: state.play_button.configure(state="normal", text="Показать логи", command=show_logs_page))

        for line in state.game_process.stdout:
            state.root.after(0, lambda l=line: append_log(l))
        state.game_process.wait()
        storage.record_session(version, time.time() - start_ts)
        state.root.after(0, render_activity_card)
        set_status("Игра завершена")
    except InstallCancelled:
        set_status("Установка отменена")
    except Exception as exc:
        message = f"Ошибка: {exc}"
        set_status(message)

    state.installing_game = False
    state.cancel_requested = False
    state.game_process = None
    state.root.after(0, lambda: set_home_locked(False))
    state.root.after(0, lambda: state.stop_button.configure(state="disabled"))
    state.root.after(0, lambda: state.play_button.configure(state="normal", text="Играть", command=on_play))


def on_play():
    if state.installing_game:
        return
    if not state.selected_version:
        state.status_label.configure(text="Сначала выберите версию")
        return
    if state.game_process and state.game_process.poll() is None:
        show_logs_page()
        return
    threading.Thread(target=launch_game, daemon=True).start()
