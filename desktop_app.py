from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk


def _configure_tk_paths() -> None:
    base_dir = os.path.dirname(sys.executable)
    tcl_dir = os.path.join(base_dir, "tcl")
    tcl_library = os.path.join(tcl_dir, "tcl8.6")
    tk_library = os.path.join(tcl_dir, "tk8.6")
    if os.path.isdir(tcl_library):
        os.environ.setdefault("TCL_LIBRARY", tcl_library)
    if os.path.isdir(tk_library):
        os.environ.setdefault("TK_LIBRARY", tk_library)


_configure_tk_paths()

from app_core import (
    PROVIDER_SPECS,
    dispatch_command,
    load_store,
    provider_snapshot,
    rollback_snapshot,
    set_provider,
    store_snapshot,
    set_uid,
)


class DesktopControlApp:
    LANGUAGES = {
        "中文": "zh",
        "English": "en",
    }

    TEXTS = {
        "zh": {
            "app_title": "Bigtree First 桌面端",
            "brand": "Bigtree First",
            "brand_subtitle": "Desktop Control",
            "user_info": "用户信息",
            "nav_home": "首页",
            "nav_settings": "设置",
            "version": "版本号: v1.0.10",
            "page_home": "首页",
            "page_home_status": "{provider} | UID {uid} | 刷新={refresh} | 置顶={pinned}",
            "home_card_title": "沟通",
            "home_card_subtitle": "在这里直接发送指令，查看机器人回复",
            "send": "发送",
            "page_settings": "设置",
            "page_settings_subtitle": "API、模型、刷新速度和日志都放在这里",
            "settings_api_title": "接口设置",
            "settings_api_subtitle": "切换 GitHub / DeepSeek，并配置对应参数",
            "provider": "Provider",
            "github_token": "GitHub Token",
            "deepseek_key": "DeepSeek API Key",
            "deepseek_base_url": "DeepSeek Base URL",
            "model_name": "Model Name",
            "uid": "UID",
            "uid_hint": "绑定当前玩家 UID，和命令 uid <value> 一致",
            "bind_uid": "绑定 UID",
            "save": "保存",
            "settings_refresh_title": "刷新速度",
            "settings_refresh_subtitle": "控制主页和状态自动更新频率",
            "settings_pin_title": "窗口钉住",
            "settings_pin_subtitle": "点一下让窗口保持最上层",
            "pin_window": "钉住窗口",
            "pin_window_on": "已钉住",
            "floating_toggle": "浮窗化",
            "floating_restore": "还原",
            "settings_log_title": "日志",
            "settings_log_subtitle": "最近的状态和命令输出",
            "language": "语言",
            "language_zh": "中文",
            "language_en": "English",
            "language_changed": "语言已切换。",
            "on_state": "开",
            "off_state": "关",
            "yes_state": "是",
            "no_state": "否",
            "home_hint": "主页：沟通",
            "settings_hint": "设置：接口与日志",
            "desktop_ready": "Desktop control window ready.",
            "switched_page": "Switched to {page} page.",
            "refresh_mode_set": "Refresh mode set to {mode}.",
            "pinned_on": "Window pinned to top.",
            "pinned_off": "Window unpinned from top.",
            "auto_refresh": "Auto refresh triggered ({mode}).",
            "rollback_complete": "Rollback complete.",
            "provider_label": "{provider_label} ({provider}) | Model: {model_name}",
            "store_label": "UID {uid} | messages={message_count} | pending_task={pending_task}",
            "rollback_label": "committed={committed_count} | pending={pending_count}",
            "status_hint": "pin={pinned} | refresh={refresh}",
            "connected": "已连接",
        },
        "en": {
            "app_title": "Bigtree First Desktop",
            "brand": "Bigtree First",
            "brand_subtitle": "Desktop Control",
            "user_info": "User Info",
            "nav_home": "Home",
            "nav_settings": "Settings",
            "version": "Version: v1.0.10",
            "page_home": "Home",
            "page_home_status": "{provider} | UID {uid} | refresh={refresh} | pinned={pinned}",
            "home_card_title": "Chat",
            "home_card_subtitle": "Send commands here and view bot replies",
            "send": "Send",
            "page_settings": "Settings",
            "page_settings_subtitle": "API, model, refresh speed, and logs live here",
            "settings_api_title": "API Settings",
            "settings_api_subtitle": "Switch GitHub / DeepSeek and set their parameters",
            "provider": "Provider",
            "github_token": "GitHub Token",
            "deepseek_key": "DeepSeek API Key",
            "deepseek_base_url": "DeepSeek Base URL",
            "model_name": "Model Name",
            "uid": "UID",
            "uid_hint": "Bind the current player UID; same as uid <value>",
            "bind_uid": "Bind UID",
            "save": "Save",
            "settings_refresh_title": "Refresh Speed",
            "settings_refresh_subtitle": "Control auto refresh frequency",
            "settings_pin_title": "Pin Window",
            "settings_pin_subtitle": "Keep the window always on top",
            "pin_window": "Pin Window",
            "pin_window_on": "Pinned",
            "floating_toggle": "Float Window",
            "floating_restore": "Restore",
            "settings_log_title": "Logs",
            "settings_log_subtitle": "Recent status and command output",
            "language": "Language",
            "language_zh": "Chinese",
            "language_en": "English",
            "language_changed": "Language switched.",
            "on_state": "on",
            "off_state": "off",
            "yes_state": "yes",
            "no_state": "no",
            "home_hint": "Home: Chat",
            "settings_hint": "Settings: API & Logs",
            "desktop_ready": "Desktop control window ready.",
            "switched_page": "Switched to {page} page.",
            "refresh_mode_set": "Refresh mode set to {mode}.",
            "pinned_on": "Window pinned to top.",
            "pinned_off": "Window unpinned from top.",
            "auto_refresh": "Auto refresh triggered ({mode}).",
            "rollback_complete": "Rollback complete.",
            "provider_label": "{provider_label} ({provider}) | Model: {model_name}",
            "store_label": "UID {uid} | messages={message_count} | pending_task={pending_task}",
            "rollback_label": "committed={committed_count} | pending={pending_count}",
            "status_hint": "pin={pinned} | refresh={refresh}",
            "connected": "Connected",
        },
    }

    REFRESH_MODES = {
        "实时": 1000,
        "高": 3000,
        "中": 8000,
        "低": 20000,
    }

    THEME = {
        "app_bg": "#eef3f9",
        "sidebar_bg": "#f6f8fc",
        "sidebar_border": "#d9e2ef",
        "surface_bg": "#ffffff",
        "surface_border": "#dce5f1",
        "surface_soft": "#f7faff",
        "surface_tint": "#edf4ff",
        "title": "#20314d",
        "text": "#2b3e56",
        "muted": "#6f8097",
        "muted_2": "#8b99ad",
        "accent": "#4f84e8",
        "accent_soft": "#dfeaff",
        "accent_text": "#24486e",
        "input_bg": "#f5f8fd",
        "input_border": "#cfd9e8",
        "input_border_focus": "#5d8bea",
        "button_bg": "#4f84e8",
        "button_bg_soft": "#eef4ff",
        "button_text": "#ffffff",
        "button_text_soft": "#355c8a",
        "pin_bg_on": "#c2d6f6",
        "pin_fg_on": "#143b84",
        "pin_bg_off": "#eef4ff",
        "pin_fg_off": "#355c8a",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.pinned = False
        self.compact = False
        self.active_page = "home"
        self.drag_origin: tuple[int, int] | None = None
        self.drag_window_origin: tuple[int, int] | None = None
        self.drag_target: tuple[int, int] | None = None
        self.drag_pending = False
        self.refresh_after_id: str | None = None
        self.activity_entries: list[str] = []

        self.language_var = tk.StringVar(value="中文")
        self.root.title(self.tr("app_title"))
        self.root.geometry("1080x760")
        self.root.minsize(380, 260)
        self.root.configure(bg=self.THEME["app_bg"])
        self.root.attributes("-topmost", False)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.bind("<Map>", self._on_map)

        current_provider = provider_snapshot()
        current_store = load_store()
        self.provider_var = tk.StringVar(value=current_provider["provider"])
        self.github_token_var = tk.StringVar()
        self.deepseek_token_var = tk.StringVar()
        self.deepseek_base_url_var = tk.StringVar(value=current_provider["deepseek_base_url"])
        self.model_name_var = tk.StringVar(value=current_provider["model_name"])
        self.uid_var = tk.StringVar(value=str(current_store.get("uid", "")))
        self.command_var = tk.StringVar()

        self.status_provider = tk.StringVar()
        self.status_store = tk.StringVar()
        self.status_rollback = tk.StringVar()
        self.status_hint = tk.StringVar()
        self._floating_restore_geometry: str | None = None
        self._floating_restore_page = "home"

        self.pin_btn = None
        self.floating_pin_btn = None
        self.refresh_mode_var = tk.StringVar(value="实时")
        self.refresh_button = None
        self.floating_mode = False
        self.page_buttons: dict[str, tk.Button] = {}
        self.page_frames: dict[str, tk.Frame] = {}
        self.sidebar: tk.Frame | None = None
        self.content: tk.Frame | None = None
        self.full_app: tk.Frame | None = None
        self.floating_shell: tk.Frame | None = None
        self.command_listbox = None
        self.floating_log = None
        self.command_entry = None
        self.floating_command_entry = None
        self.home_status_var = tk.StringVar(value=self.tr("connected"))
        self.sidebar_hint_var = tk.StringVar(value=self.tr("home_hint"))
        self.floating_status_var = tk.StringVar(value=self.tr("connected"))
        self.window_btn = None
        self.window_buttons: list[tk.Button] = []

        self._build_layout()
        self.refresh_status()
        self.show_page("home")
        self._log(self.tr("desktop_ready"))

    def _build_layout(self) -> None:
        self.root.title(self.tr("app_title"))
        self.root.configure(bg=self.THEME["app_bg"])
        self.root.minsize(980, 680)

        self.full_app = tk.Frame(self.root, bg=self.THEME["app_bg"])
        self.full_app.pack(fill="both", expand=True)

        sidebar = tk.Frame(self.full_app, bg=self.THEME["sidebar_bg"], width=280, highlightthickness=1, highlightbackground=self.THEME["sidebar_border"])
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        brand = tk.Frame(sidebar, bg=self.THEME["sidebar_bg"])
        brand.pack(fill="x", padx=18, pady=(18, 14))
        tk.Label(brand, text=self.tr("brand"), bg=self.THEME["sidebar_bg"], fg=self.THEME["title"], font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(brand, text=self.tr("brand_subtitle"), bg=self.THEME["sidebar_bg"], fg=self.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))
        tk.Label(brand, text=self.tr("user_info"), bg=self.THEME["sidebar_bg"], fg=self.THEME["text"], font=("Segoe UI", 11)).pack(anchor="w", pady=(12, 0))

        nav = tk.Frame(sidebar, bg=self.THEME["sidebar_bg"])
        nav.pack(fill="x", padx=12, pady=(8, 0))
        self.page_buttons["home"] = self._nav_button(nav, self.tr("nav_home"), lambda: self.show_page("home"))
        self.page_buttons["home"].pack(fill="x", pady=6)
        self.page_buttons["settings"] = self._nav_button(nav, self.tr("nav_settings"), lambda: self.show_page("settings"))
        self.page_buttons["settings"].pack(fill="x", pady=6)

        sidebar_footer = tk.Frame(sidebar, bg=self.THEME["sidebar_bg"])
        sidebar_footer.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Label(sidebar_footer, text=self.tr("version"), bg=self.THEME["sidebar_bg"], fg=self.THEME["muted_2"], font=("Segoe UI", 9)).pack(anchor="w")
        self.sidebar_hint_label = tk.Label(sidebar_footer, textvariable=self.sidebar_hint_var, bg=self.THEME["sidebar_bg"], fg=self.THEME["muted_2"], font=("Segoe UI", 9))
        self.sidebar_hint_label.pack(anchor="w", pady=(4, 0))

        self.content = tk.Frame(self.full_app, bg=self.THEME["app_bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self.page_frames["home"] = self._build_home_page(self.content)
        self.page_frames["settings"] = self._build_settings_page(self.content)
        self._sync_activity_views()
        self._build_floating_layout()

    def _build_floating_layout(self) -> None:
        floating = tk.Frame(self.root, bg=self.THEME["app_bg"])
        self.floating_shell = floating

        header = tk.Frame(floating, bg=self.THEME["surface_bg"], highlightthickness=1, highlightbackground=self.THEME["surface_border"])
        header.pack(fill="x", padx=12, pady=(12, 8))
        self._bind_drag(header)

        header_left = tk.Frame(header, bg=self.THEME["surface_bg"])
        header_left.pack(side="left", padx=14, pady=12)
        tk.Label(header_left, text=self.tr("brand"), bg=self.THEME["surface_bg"], fg=self.THEME["title"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(header_left, text=self.tr("home_card_subtitle"), bg=self.THEME["surface_bg"], fg=self.THEME["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))
        tk.Label(header_left, textvariable=self.floating_status_var, bg=self.THEME["surface_bg"], fg=self.THEME["muted_2"], font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        header_right = tk.Frame(header, bg=self.THEME["surface_bg"])
        header_right.pack(side="right", padx=12, pady=10)
        self.floating_pin_btn = self._button(header_right, self._pin_button_text(), self.toggle_pin, accent=False)
        self.floating_pin_btn.pack(side="left", padx=(0, 8))
        self._make_window_button(header_right).pack(side="left")

        body = tk.Frame(floating, bg=self.THEME["app_bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        chat_card = tk.Frame(body, bg=self.THEME["surface_bg"], highlightthickness=1, highlightbackground=self.THEME["surface_border"])
        chat_card.pack(fill="both", expand=True)
        chat_head = tk.Frame(chat_card, bg=self.THEME["surface_bg"])
        chat_head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(chat_head, text=self.tr("home_card_title"), bg=self.THEME["surface_bg"], fg=self.THEME["title"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(chat_head, text=self.tr("settings_hint"), bg=self.THEME["surface_bg"], fg=self.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        chat_body = tk.Frame(chat_card, bg=self.THEME["surface_bg"])
        chat_body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.floating_log = tk.Text(
            chat_body,
            bg=self.THEME["surface_soft"],
            fg=self.THEME["text"],
            relief="flat",
            wrap="word",
            font=("Segoe UI", 11),
            height=12,
            insertbackground=self.THEME["text"],
        )
        self.floating_log.pack(fill="both", expand=True)
        self.floating_log.configure(state="disabled")

        floating_input = tk.Frame(chat_body, bg=self.THEME["surface_bg"])
        floating_input.pack(fill="x", pady=(14, 0))
        self.floating_command_entry = tk.Entry(
            floating_input,
            textvariable=self.command_var,
            bg=self.THEME["input_bg"],
            fg=self.THEME["title"],
            insertbackground=self.THEME["title"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.THEME["input_border"],
            highlightcolor=self.THEME["input_border_focus"],
        )
        self.floating_command_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.floating_command_entry.bind("<Return>", lambda _event: self.submit_command())
        self._button(floating_input, self.tr("send"), self.submit_command, accent=True).pack(side="left", padx=(10, 0))

    def _rebuild_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.page_buttons = {}
        self.page_frames = {}
        self.command_listbox = None
        self.floating_log = None
        self.refresh_button = None
        self.pin_btn = None
        self.floating_pin_btn = None
        self.command_entry = None
        self.floating_command_entry = None
        self.full_app = None
        self.floating_shell = None
        self.window_buttons = []
        self._build_layout()
        if self.floating_mode:
            self._apply_mode_layout()
        self.refresh_status()
        self.show_page(self.active_page)

    def _apply_mode_layout(self) -> None:
        if self.full_app is None or self.floating_shell is None:
            return
        if self.floating_mode:
            if self.full_app.winfo_ismapped():
                self.full_app.pack_forget()
            if not self.floating_shell.winfo_ismapped():
                self.floating_shell.pack(fill="both", expand=True)
            self.root.geometry("480x640")
            self.root.minsize(360, 460)
            self.root.attributes("-topmost", True)
        else:
            if self.floating_shell.winfo_ismapped():
                self.floating_shell.pack_forget()
            if not self.full_app.winfo_ismapped():
                self.full_app.pack(fill="both", expand=True)
            if self._floating_restore_geometry:
                self.root.geometry(self._floating_restore_geometry)
            else:
                self.root.geometry("1080x760")
            self.root.minsize(980, 680)
            self.root.attributes("-topmost", self.pinned)
            self.show_page(self._floating_restore_page)
        self._sync_activity_views()

    def set_language(self, value: str | None = None) -> None:
        if value in self.LANGUAGES:
            self.language_var.set(value)
        self._rebuild_ui()
        self._log(self.tr("language_changed"))

    def tr(self, key: str, **kwargs) -> str:
        lang = self.LANGUAGES.get(self.language_var.get(), "zh")
        template = self.TEXTS[lang].get(key, key)
        return template.format(**kwargs) if kwargs else template

    def _refresh_mode_label(self, mode_key: str) -> str:
        lang = self.LANGUAGES.get(self.language_var.get(), "zh")
        labels = {
            "zh": {"实时": "实时", "高": "高", "中": "中", "低": "低"},
            "en": {"实时": "Live", "高": "High", "中": "Medium", "低": "Low"},
        }
        return labels[lang].get(mode_key, mode_key)

    def _all_refresh_mode_items(self) -> list[tuple[str, str]]:
        return [(key, self._refresh_mode_label(key)) for key in self.REFRESH_MODES]

    def _nav_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.THEME["button_bg_soft"],
            fg=self.THEME["button_text_soft"],
            activebackground=self.THEME["accent_soft"],
            activeforeground=self.THEME["accent_text"],
            relief="flat",
            bd=0,
            padx=16,
            pady=14,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
        )

    def _page_card(self, parent: tk.Widget, title: str, subtitle: str | None = None) -> tk.Frame:
        card = tk.Frame(parent, bg=self.THEME["surface_bg"], bd=0, highlightthickness=1, highlightbackground=self.THEME["surface_border"])
        head = tk.Frame(card, bg=self.THEME["surface_bg"])
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(head, text=title, bg=self.THEME["surface_bg"], fg=self.THEME["title"], font=("Segoe UI", 14, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, bg=self.THEME["surface_bg"], fg=self.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        return card

    def _window_button_text(self) -> str:
        return self.tr("floating_restore") if self.floating_mode else self.tr("floating_toggle")

    def _make_window_button(self, parent: tk.Widget) -> tk.Button:
        button = self._button(parent, self._window_button_text(), self.toggle_floating_mode, accent=False)
        button.configure(padx=12, pady=6)
        self.window_buttons.append(button)
        return button

    def _build_home_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=self.THEME["app_bg"])
        page.place(relx=0, rely=0, relwidth=1, relheight=1)

        top = tk.Frame(page, bg=self.THEME["app_bg"])
        top.pack(fill="x", padx=18, pady=(18, 10))
        left = tk.Frame(top, bg=self.THEME["app_bg"])
        left.pack(side="left", anchor="w")
        tk.Label(left, text=self.tr("page_home"), bg=self.THEME["app_bg"], fg=self.THEME["title"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(left, textvariable=self.home_status_var, bg=self.THEME["app_bg"], fg=self.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        right = tk.Frame(top, bg=self.THEME["app_bg"])
        right.pack(side="right", anchor="e")
        self._make_window_button(right).pack(anchor="e")

        card = self._page_card(page, self.tr("home_card_title"), self.tr("home_card_subtitle"))
        card.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        body = tk.Frame(card, bg=self.THEME["surface_bg"])
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.command_listbox = tk.Text(
            body,
            bg=self.THEME["surface_soft"],
            fg=self.THEME["text"],
            relief="flat",
            wrap="word",
            font=("Segoe UI", 11),
            height=12,
            insertbackground=self.THEME["text"],
        )
        self.command_listbox.pack(fill="both", expand=True)
        self.command_listbox.configure(state="disabled")

        input_row = tk.Frame(body, bg=self.THEME["surface_bg"])
        input_row.pack(fill="x", pady=(14, 0))
        self.command_entry = tk.Entry(
            input_row,
            textvariable=self.command_var,
            bg=self.THEME["input_bg"],
            fg=self.THEME["title"],
            insertbackground=self.THEME["title"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.THEME["input_border"],
            highlightcolor=self.THEME["input_border_focus"],
        )
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.command_entry.bind("<Return>", lambda _event: self.submit_command())
        self._button(input_row, self.tr("send"), self.submit_command, accent=True).pack(side="left", padx=(10, 0))
        return page

    def _build_settings_page(self, parent: tk.Widget) -> tk.Frame:
        page = tk.Frame(parent, bg=self.THEME["app_bg"])
        page.place(relx=0, rely=0, relwidth=1, relheight=1)

        top = tk.Frame(page, bg=self.THEME["app_bg"])
        top.pack(fill="x", padx=18, pady=(18, 10))
        left = tk.Frame(top, bg=self.THEME["app_bg"])
        left.pack(side="left", anchor="w")
        tk.Label(left, text=self.tr("page_settings"), bg=self.THEME["app_bg"], fg=self.THEME["title"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(left, text=self.tr("page_settings_subtitle"), bg=self.THEME["app_bg"], fg=self.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        right = tk.Frame(top, bg=self.THEME["app_bg"])
        right.pack(side="right", anchor="e")
        self._make_window_button(right).pack(anchor="e")

        settings = tk.Frame(page, bg=self.THEME["app_bg"])
        settings.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        provider_card = self._page_card(settings, self.tr("settings_api_title"), self.tr("settings_api_subtitle"))
        provider_card.pack(fill="x", pady=(0, 12))
        provider_body = tk.Frame(provider_card, bg=self.THEME["surface_bg"])
        provider_body.pack(fill="x", padx=18, pady=(0, 18))
        self._labeled_field(provider_body, self.tr("provider"), self.provider_var, widget="optionmenu", row=0, values=list(PROVIDER_SPECS.keys()))
        self._labeled_field(provider_body, self.tr("github_token"), self.github_token_var, widget="entry", row=1, show="*")
        self._labeled_field(provider_body, self.tr("deepseek_key"), self.deepseek_token_var, widget="entry", row=2, show="*")
        self._labeled_field(provider_body, self.tr("deepseek_base_url"), self.deepseek_base_url_var, widget="entry", row=3)
        self._labeled_field(provider_body, self.tr("model_name"), self.model_name_var, widget="entry", row=4)
        self._labeled_field(provider_body, self.tr("uid"), self.uid_var, widget="entry", row=5)
        tk.Label(provider_body, text=self.tr("uid_hint"), bg=self.THEME["surface_bg"], fg=self.THEME["muted_2"], font=("Segoe UI", 9)).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 4))

        action_row = tk.Frame(provider_body, bg=self.THEME["surface_bg"])
        action_row.grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self._button(action_row, self.tr("save"), self.save_provider, accent=True).pack(side="left")
        self._button(action_row, "GitHub", lambda: self.provider_var.set("github"), accent=False).pack(side="left", padx=8)
        self._button(action_row, "DeepSeek", lambda: self.provider_var.set("deepseek"), accent=False).pack(side="left")
        self._button(action_row, self.tr("bind_uid"), self.save_uid, accent=False).pack(side="left", padx=8)

        options_row = tk.Frame(settings, bg=self.THEME["app_bg"])
        options_row.pack(fill="x", pady=(0, 12))
        refresh_card = self._page_card(options_row, self.tr("settings_refresh_title"), self.tr("settings_refresh_subtitle"))
        refresh_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        refresh_body = tk.Frame(refresh_card, bg=self.THEME["surface_bg"])
        refresh_body.pack(fill="x", padx=18, pady=(0, 18))
        refresh_button = tk.Menubutton(
            refresh_body,
            text=self._refresh_button_text(),
            bg=self.THEME["surface_soft"],
            fg=self.THEME["title"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.THEME["input_border"],
            activebackground=self.THEME["accent_soft"],
            activeforeground=self.THEME["accent_text"],
            cursor="hand2",
            padx=12,
            pady=8,
        )
        refresh_button.pack(anchor="w")
        refresh_menu = tk.Menu(
            refresh_button,
            tearoff=0,
            bg=self.THEME["surface_bg"],
            fg=self.THEME["text"],
            activebackground=self.THEME["accent_soft"],
            activeforeground=self.THEME["accent_text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        for mode_key, label in self._all_refresh_mode_items():
            refresh_menu.add_command(label=label, command=lambda value=mode_key: self.set_refresh_mode(value))
        refresh_button.configure(menu=refresh_menu)
        self.refresh_button = refresh_button

        pin_card = self._page_card(options_row, self.tr("settings_pin_title"), self.tr("settings_pin_subtitle"))
        pin_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        pin_body = tk.Frame(pin_card, bg=self.THEME["surface_bg"])
        pin_body.pack(fill="x", padx=18, pady=(0, 18))
        self.pin_btn = self._button(pin_body, self._pin_button_text(), self.toggle_pin, accent=False)
        self.pin_btn.pack(anchor="w")

        language_card = self._page_card(settings, self.tr("language"), f"{self.tr('language_zh')} / {self.tr('language_en')}")
        language_card.pack(fill="x", pady=(0, 12))
        language_body = tk.Frame(language_card, bg=self.THEME["surface_bg"])
        language_body.pack(fill="x", padx=18, pady=(0, 18))
        language_menu = tk.OptionMenu(language_body, self.language_var, *self.LANGUAGES.keys(), command=self.set_language)
        language_menu.configure(bg=self.THEME["surface_soft"], fg=self.THEME["title"], relief="flat", highlightthickness=1, highlightbackground=self.THEME["input_border"], activebackground=self.THEME["accent_soft"], activeforeground=self.THEME["accent_text"])
        language_menu.pack(anchor="w")

        log_card = self._page_card(settings, self.tr("settings_log_title"), self.tr("settings_log_subtitle"))
        log_card.pack(fill="both", expand=True)
        log_body = tk.Frame(log_card, bg=self.THEME["surface_bg"])
        log_body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.log = tk.Text(
            log_body,
            bg=self.THEME["surface_soft"],
            fg=self.THEME["text"],
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
            height=12,
            insertbackground=self.THEME["text"],
        )
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_body, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)
        return page

    def show_page(self, page_name: str) -> None:
        if self.floating_mode:
            if page_name in self.page_frames:
                self._floating_restore_page = page_name
            return
        self.active_page = page_name
        for name, frame in self.page_frames.items():
            if name == page_name:
                frame.lift()
            else:
                frame.lower()
        for name, button in self.page_buttons.items():
            if name == page_name:
                button.configure(bg=self.THEME["accent_soft"], fg=self.THEME["accent_text"])
            else:
                button.configure(bg=self.THEME["button_bg_soft"], fg=self.THEME["button_text_soft"])
        self.sidebar_hint_var.set(self.tr("home_hint") if page_name == "home" else self.tr("settings_hint"))
        self._log(self.tr("switched_page", page=self.tr("page_home") if page_name == "home" else self.tr("page_settings")))

    def _labeled_field(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        widget: str,
        row: int,
        show: str | None = None,
        values: list[str] | None = None,
    ) -> None:
        tk.Label(parent, text=label, bg=self.THEME["surface_bg"], fg=self.THEME["text"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=6)
        if widget == "optionmenu":
            option = tk.OptionMenu(parent, variable, *(values or []))
            option.configure(bg=self.THEME["button_bg"], fg=self.THEME["button_text"], relief="flat", highlightthickness=0, activebackground="#5f93ef", activeforeground=self.THEME["button_text"])
            option.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        else:
            entry = tk.Entry(
                parent,
                textvariable=variable,
                show=show or "",
                bg=self.THEME["input_bg"],
                fg=self.THEME["title"],
                insertbackground=self.THEME["title"],
                relief="flat",
                highlightthickness=1,
                highlightbackground=self.THEME["input_border"],
                highlightcolor=self.THEME["input_border_focus"],
            )
            entry.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _button(self, parent: tk.Widget, text: str, command, accent: bool) -> tk.Button:
        bg = self.THEME["button_bg"] if accent else self.THEME["button_bg_soft"]
        active = "#5f93ef" if accent else self.THEME["accent_soft"]
        fg = self.THEME["button_text"] if accent else self.THEME["button_text_soft"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
        )

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._do_drag)
        widget.bind("<ButtonRelease-1>", self._end_drag)

    def _start_drag(self, event) -> None:
        self.drag_origin = (event.x_root, event.y_root)
        self.drag_window_origin = (self.root.winfo_x(), self.root.winfo_y())
        self.drag_target = self.drag_window_origin

    def _do_drag(self, event) -> None:
        if not self.drag_origin or not self.drag_window_origin:
            return
        dx = event.x_root - self.drag_origin[0]
        dy = event.y_root - self.drag_origin[1]
        self.drag_target = (self.drag_window_origin[0] + dx, self.drag_window_origin[1] + dy)
        if self.drag_pending:
            return
        self.drag_pending = True
        self.root.after_idle(self._flush_drag)

    def _flush_drag(self) -> None:
        self.drag_pending = False
        if not self.drag_target:
            return
        x, y = self.drag_target
        self.root.geometry(f"+{x}+{y}")

    def _end_drag(self, _event) -> None:
        self.drag_origin = None
        self.drag_window_origin = None
        self.drag_target = None
        self.drag_pending = False

    def _log(self, text: str) -> None:
        self.activity_entries.append(text)
        if self.log is not None:
            self.log.configure(state="normal")
            self.log.insert("end", text + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        if self.command_listbox is not None:
            self.command_listbox.configure(state="normal")
            self.command_listbox.insert("end", text + "\n")
            self.command_listbox.see("end")
            self.command_listbox.configure(state="disabled")
        if self.floating_log is not None:
            self.floating_log.configure(state="normal")
            self.floating_log.insert("end", text + "\n")
            self.floating_log.see("end")
            self.floating_log.configure(state="disabled")

    def _sync_activity_views(self) -> None:
        if self.log is not None:
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            for entry in self.activity_entries:
                self.log.insert("end", entry + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        if self.command_listbox is not None:
            self.command_listbox.configure(state="normal")
            self.command_listbox.delete("1.0", "end")
            for entry in self.activity_entries:
                self.command_listbox.insert("end", entry + "\n")
            self.command_listbox.see("end")
            self.command_listbox.configure(state="disabled")
        if self.floating_log is not None:
            self.floating_log.configure(state="normal")
            self.floating_log.delete("1.0", "end")
            for entry in self.activity_entries:
                self.floating_log.insert("end", entry + "\n")
            self.floating_log.see("end")
            self.floating_log.configure(state="disabled")

    def refresh_status(self) -> None:
        provider = provider_snapshot()
        store = store_snapshot()
        rollback = rollback_snapshot()
        self.status_provider.set(self.tr("provider_label", provider_label=provider["provider_label"], provider=provider["provider"], model_name=provider["model_name"]))
        self.status_store.set(self.tr("store_label", uid=store["uid"], message_count=store["message_count"], pending_task=self.tr("yes_state") if store["has_pending_task"] else self.tr("no_state")))
        self.status_rollback.set(self.tr("rollback_label", committed_count=rollback["committed_count"], pending_count=rollback["pending_count"]))
        self.status_hint.set(self.tr("status_hint", pinned=self.tr("on_state") if self.pinned else self.tr("off_state"), refresh=self._refresh_mode_label(self.refresh_mode_var.get())))
        self.home_status_var.set(self.tr("page_home_status", provider=provider["provider_label"], uid=store["uid"], refresh=self._refresh_mode_label(self.refresh_mode_var.get()), pinned=self.tr("on_state") if self.pinned else self.tr("off_state")))
        self.floating_status_var.set(self.tr("page_home_status", provider=provider["provider_label"], uid=store["uid"], refresh=self._refresh_mode_label(self.refresh_mode_var.get()), pinned=self.tr("on_state") if (self.pinned or self.floating_mode) else self.tr("off_state")))
        self.sidebar_hint_var.set(self.tr("home_hint") if self.active_page == "home" else self.tr("settings_hint"))
        if self.refresh_button is not None:
            self.refresh_button.configure(text=self._refresh_button_text())
        if self.pin_btn is not None:
            self.pin_btn.configure(
                text=self._pin_button_text(),
                bg=self.THEME["pin_bg_on"] if (self.pinned or self.floating_mode) else self.THEME["pin_bg_off"],
                fg=self.THEME["pin_fg_on"] if (self.pinned or self.floating_mode) else self.THEME["pin_fg_off"],
                activebackground="#b0c9ef" if (self.pinned or self.floating_mode) else self.THEME["accent_soft"],
            )
        if self.floating_pin_btn is not None:
            self.floating_pin_btn.configure(
                text=self._pin_button_text(),
                bg=self.THEME["pin_bg_on"] if (self.pinned or self.floating_mode) else self.THEME["pin_bg_off"],
                fg=self.THEME["pin_fg_on"] if (self.pinned or self.floating_mode) else self.THEME["pin_fg_off"],
                activebackground="#b0c9ef" if (self.pinned or self.floating_mode) else self.THEME["accent_soft"],
            )
        for button in self.window_buttons:
            button.configure(text=self._window_button_text())
        self._schedule_auto_refresh()

    def _refresh_button_text(self) -> str:
        return f"{self.tr('settings_refresh_title')}: {self._refresh_mode_label(self.refresh_mode_var.get())}"

    def _pin_button_text(self) -> str:
        return f"📌 {self.tr('pin_window_on')}" if self.pinned else f"📌 {self.tr('pin_window')}"

    def set_refresh_mode(self, mode: str) -> None:
        if mode not in self.REFRESH_MODES:
            return
        self.refresh_mode_var.set(mode)
        if self.refresh_button is not None:
            self.refresh_button.configure(text=self._refresh_button_text())
        self._schedule_auto_refresh()
        self.refresh_status()

    def toggle_pin(self) -> None:
        self.pinned = not self.pinned
        self.root.attributes("-topmost", self.pinned or self.floating_mode)
        self.refresh_status()
        self._log(self.tr("pinned_on") if self.pinned else self.tr("pinned_off"))

    def toggle_floating_mode(self) -> None:
        if not self.floating_mode:
            self._floating_restore_geometry = self.root.geometry()
            self._floating_restore_page = self.active_page
        self.floating_mode = not self.floating_mode
        self._apply_mode_layout()
        self.refresh_status()
        if self.floating_mode:
            self._log(self.tr("floating_toggle"))
        else:
            self._log(self.tr("floating_restore"))

    def _schedule_auto_refresh(self) -> None:
        if self.refresh_after_id is not None:
            try:
                self.root.after_cancel(self.refresh_after_id)
            except Exception:
                pass
            self.refresh_after_id = None

        interval = self.REFRESH_MODES.get(self.refresh_mode_var.get())
        if not interval:
            return
        self.refresh_after_id = self.root.after(interval, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self.refresh_after_id = None
        self.refresh_status()

    def close_window(self) -> None:
        if self.refresh_after_id is not None:
            try:
                self.root.after_cancel(self.refresh_after_id)
            except Exception:
                pass
        self.root.destroy()

    def _on_map(self, _event) -> None:
        self.root.attributes("-topmost", self.pinned or self.floating_mode)

    def submit_command(self) -> None:
        text = self.command_var.get().strip()
        if not text:
            return
        self.command_var.set("")
        self.run_command(text)

    def run_command(self, text: str) -> None:
        self._log(f"> {text}")

        def worker() -> None:
            result = dispatch_command(text)
            self.root.after(0, lambda: self._handle_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_result(self, result) -> None:
        prefix = "OK" if result.ok else "ERR"
        self._log(f"[{prefix}] {result.title}: {result.message}")
        self.refresh_status()
        if result.ok and result.title == "rollback":
            self._log("Rollback complete.")

    def save_provider(self) -> None:
        provider = self.provider_var.get().strip().lower()

        def worker() -> None:
            result = set_provider(
                provider,
                github_token=self.github_token_var.get(),
                deepseek_api_key=self.deepseek_token_var.get(),
                deepseek_base_url=self.deepseek_base_url_var.get(),
                model_name=self.model_name_var.get(),
            )
            self.root.after(0, lambda: self._handle_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def save_uid(self) -> None:
        uid = self.uid_var.get().strip()

        def worker() -> None:
            result = set_uid(uid)
            self.root.after(0, lambda: self._handle_result(result))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    DesktopControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
