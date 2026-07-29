from datetime import date, timedelta

import customtkinter as ctk

import state
import storage


def render_activity_card():
    config = storage.load_config()
    activity = config.get("activity", {})
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    values = [activity.get(d.isoformat(), 0) for d in days]
    max_value = max(values) or 1

    state.activity_total_label.configure(text=storage.format_duration(sum(values)))

    for widget in state.bars_row.winfo_children():
        widget.destroy()
    for widget in state.day_labels_row.winfo_children():
        widget.destroy()

    n = len(days)
    for i, (d, value) in enumerate(zip(days, values)):
        is_today = d == today
        bar_h = max(3, int(state.BAR_HEIGHT * value / max_value)) if value else 3
        bar = ctk.CTkFrame(state.bars_row, fg_color=state.ACCENT if is_today else state.BAR_MUTED, corner_radius=4, width=state.BAR_WIDTH, height=bar_h)
        bar.place(relx=(i + 0.5) / n, rely=1.0, anchor="s")
        bar.bind("<Enter>", lambda _e, dd=d, vv=value: state.status_label.configure(text=f"{state.WEEKDAY_RU[dd.weekday()]}: {storage.format_duration(vv)}"))

        label = ctk.CTkLabel(
            state.day_labels_row, text=state.WEEKDAY_RU[d.weekday()], font=ctk.CTkFont(size=9, weight="bold" if is_today else "normal"),
            text_color=state.ACCENT if is_today else "#9a9a9a",
        )
        label.place(relx=(i + 0.5) / n, rely=0.5, anchor="c")

    state.stat_versions_label.configure(text=f"🧩 {len(config.get('versions_used', []))}")
    state.stat_time_label.configure(text=f"⏱ {storage.format_duration(sum(activity.values()))}")
    state.stat_accounts_label.configure(text=f"👤 {len(config.get('nicknames', []))}")
