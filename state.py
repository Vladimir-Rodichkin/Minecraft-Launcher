import os

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
LOADER_KEYWORDS = ("fabric", "quilt", "forge", "neoforge")

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

root = None
home_frame = None
version_frame = None
nickname_frame = None
settings_frame = None
logs_frame = None
mods_frame = None

username_entry = None
nicknames_button = None
version_button = None
settings_button = None
status_label = None
play_button = None
activity_total_label = None
bars_row = None
day_labels_row = None
stat_versions_label = None
stat_time_label = None
stat_accounts_label = None

search_var = None
search_entry = None
install_progress_label = None
list_frame = None
page_label = None
first_button = None
prev_button = None
next_button = None
last_button = None
cancel_loader_button = None
loader_tabs_buttons = None

nickname_list_frame = None

java_path_entry = None
min_ram_entry = None
max_ram_entry = None
jvm_args_entry = None

log_textbox = None
stop_button = None

mods_list_frame = None
