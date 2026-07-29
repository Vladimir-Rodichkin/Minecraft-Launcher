import json
import os
from datetime import date, datetime

import minecraft_launcher_lib as mll

import state


def load_config():
    try:
        with open(state.CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("nicknames", [])
    data.setdefault("settings", dict(state.DEFAULT_SETTINGS))
    return data


def write_config(data):
    os.makedirs(state.APP_DATA_DIR, exist_ok=True)
    with open(state.CONFIG_PATH, "w", encoding="utf-8") as f:
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
    os.makedirs(state.MINECRAFT_DIR, exist_ok=True)
    for filename in ("launcher_profiles.json", "launcher_profiles_microsoft_store.json"):
        path = os.path.join(state.MINECRAFT_DIR, filename)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(stub, f, indent=2)


def load_nicknames():
    return load_config()["nicknames"]


def save_nickname(name):
    config = load_config()
    nicknames = [n for n in config["nicknames"] if n != name]
    nicknames.insert(0, name)
    config["nicknames"] = nicknames[:state.MAX_SAVED_NICKNAMES]
    write_config(config)


def delete_nickname(name):
    config = load_config()
    config["nicknames"] = [n for n in config["nicknames"] if n != name]
    write_config(config)


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
    return f"{dt.day} {state.RU_MONTHS[dt.month]} {dt.year} г."


def is_installed(version):
    return any(v["id"] == version for v in mll.utils.get_installed_versions(state.MINECRAFT_DIR))
