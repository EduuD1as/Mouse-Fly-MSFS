import os
import sys
import tkinter as tk

import customtkinter as ctk

from . import __version__
from .config import Settings
from .engine import HOTKEYS, Engine

BG = "#0e1117"
CARD = "#161b22"
CARD_2 = "#1f2630"
BORDER = "#2a313c"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
GREEN = "#22c55e"
GREEN_HOVER = "#16a34a"
AMBER = "#f59e0b"
RED = "#ef4444"

CHIPS = [("left", "L", 1), ("right", "R", 2), ("middle", "M", 3), ("x1", "M4", 4),
         ("x2", "M5", 5), ("wup", "▲", 6), ("wdn", "▼", 7)]


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=BG)
        self.settings = Settings.load()
        self.engine = Engine(self.settings)

        self.title("Mouse-Fly MSFS")
        self.geometry("860x540")
        self.minsize(820, 520)
        try:
            self.iconbitmap(resource_path(os.path.join("assets", "icon.ico")))
        except tk.TclError:
            pass
        self.attributes("-topmost", self.settings.always_on_top)

        self.font_title = ctk.CTkFont("Segoe UI Semibold", 22)
        self.font_h = ctk.CTkFont("Segoe UI Semibold", 14)
        self.font = ctk.CTkFont("Segoe UI", 13)
        self.font_small = ctk.CTkFont("Segoe UI", 11)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_live_panel()
        self._build_settings_panel()
        self._build_footer()

        self.engine.start()
        if self.settings.start_active:
            self.engine.set_active(True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._save_job = None
        self.after(33, self._refresh)

    # -- layout ------------------------------------------------------------
    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER, **kw)

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 8))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text="✈  Mouse-Fly MSFS", font=self.font_title, text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(bar, text=f"v{__version__}  ·  mouse → joystick vJoy", font=self.font_small,
                     text_color=MUTED).grid(row=0, column=1, sticky="w", padx=12, pady=(6, 0))
        self.toggle_btn = ctk.CTkButton(bar, text="", width=190, height=40, corner_radius=20,
                                        font=self.font_h, command=self.engine.toggle)
        self.toggle_btn.grid(row=0, column=2, sticky="e")

    def _build_live_panel(self):
        card = self._card(self)
        card.grid(row=1, column=0, sticky="nsw", padx=(20, 10), pady=8)
        ctk.CTkLabel(card, text="Visualização ao vivo", font=self.font_h, text_color=TEXT).pack(anchor="w", padx=18, pady=(14, 6))

        self.size = 250
        self.canvas = tk.Canvas(card, width=self.size, height=self.size, bg=CARD_2, highlightthickness=0, bd=0)
        self.canvas.pack(padx=18)
        s = self.size
        for i in range(1, 4):
            p = s * i / 4
            self.canvas.create_line(p, 0, p, s, fill=BORDER)
            self.canvas.create_line(0, p, s, p, fill=BORDER)
        self.canvas.create_line(s / 2, 0, s / 2, s, fill="#3a4350", width=2)
        self.canvas.create_line(0, s / 2, s, s / 2, fill="#3a4350", width=2)
        self.dz_rect = self.canvas.create_rectangle(0, 0, 0, 0, outline="#4b5563", dash=(3, 3))
        self.trail = self.canvas.create_line(s / 2, s / 2, s / 2, s / 2, fill=ACCENT, width=2)
        self.dot = self.canvas.create_oval(0, 0, 0, 0, fill=ACCENT, outline="white", width=2)

        self.axis_lbl = ctk.CTkLabel(card, text="X 0.00   Y 0.00", font=ctk.CTkFont("Consolas", 12), text_color=MUTED)
        self.axis_lbl.pack(pady=(6, 2))

        zrow = ctk.CTkFrame(card, fg_color="transparent")
        zrow.pack(fill="x", padx=18, pady=(4, 2))
        ctk.CTkLabel(zrow, text="Z", font=self.font_small, text_color=MUTED, width=14).pack(side="left")
        self.zbar = ctk.CTkProgressBar(zrow, height=8, progress_color=ACCENT, fg_color=CARD_2)
        self.zbar.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.zbar.set(0)

        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.pack(padx=14, pady=(10, 16))
        self.chips = {}
        for i, (key, label, num) in enumerate(CHIPS):
            box = ctk.CTkFrame(chips, fg_color=CARD_2, corner_radius=8, width=32, height=40)
            box.grid(row=0, column=i, padx=2)
            box.grid_propagate(False)
            ctk.CTkLabel(box, text=label, font=ctk.CTkFont("Segoe UI Semibold", 11), text_color=TEXT,
                         height=16).place(relx=0.5, rely=0.36, anchor="center")
            ctk.CTkLabel(box, text=str(num), font=ctk.CTkFont("Segoe UI", 9), text_color=MUTED,
                         height=12).place(relx=0.5, rely=0.76, anchor="center")
            self.chips[key] = box

    def _build_settings_panel(self):
        card = self._card(self)
        card.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=8)
        tabs = ctk.CTkTabview(card, fg_color=CARD, segmented_button_fg_color=CARD_2,
                              segmented_button_selected_color=ACCENT,
                              segmented_button_selected_hover_color=ACCENT_HOVER,
                              segmented_button_unselected_color=CARD_2)
        tabs.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self._build_axes_tab(tabs.add("Eixos"))
        self._build_buttons_tab(tabs.add("Botões"))
        self._build_general_tab(tabs.add("Geral"))

    def _row(self, parent, label, hint=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=5)
        row.grid_columnconfigure(1, weight=1)
        lbl = ctk.CTkFrame(row, fg_color="transparent")
        lbl.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(lbl, text=label, font=self.font, text_color=TEXT, height=18).pack(anchor="w")
        if hint:
            ctk.CTkLabel(lbl, text=hint, font=self.font_small, text_color=MUTED, height=14).pack(anchor="w")
        return row

    def _slider(self, parent, label, attr, lo, hi, fmt, hint=None, on_change=None):
        row = self._row(parent, label, hint)
        val = ctk.CTkLabel(row, text=fmt(getattr(self.settings, attr)), font=self.font, text_color=MUTED, width=52)
        val.grid(row=0, column=2, sticky="e")

        def changed(v):
            setattr(self.settings, attr, round(float(v), 3))
            val.configure(text=fmt(float(v)))
            if on_change:
                on_change()
            self._schedule_save()

        sl = ctk.CTkSlider(row, from_=lo, to=hi, width=200, command=changed, button_color=ACCENT,
                           button_hover_color=ACCENT_HOVER, progress_color=ACCENT)
        sl.set(getattr(self.settings, attr))
        sl.grid(row=0, column=1, sticky="e", padx=10)
        return sl

    def _switch(self, parent, label, attr, hint=None, on_change=None):
        row = self._row(parent, label, hint)
        var = tk.BooleanVar(value=getattr(self.settings, attr))

        def changed():
            setattr(self.settings, attr, bool(var.get()))
            if on_change:
                on_change()
            self._schedule_save()

        ctk.CTkSwitch(row, text="", variable=var, command=changed, progress_color=ACCENT,
                      width=46).grid(row=0, column=2, sticky="e")
        return var

    def _build_axes_tab(self, tab):
        row = self._row(tab, "Modo", "Cursor: posição na tela  ·  Relativo: movimento bruto")
        self.mode_btn = ctk.CTkSegmentedButton(row, values=["Cursor", "Relativo"], command=self._set_mode,
                                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                                               unselected_color=CARD_2, font=self.font)
        self.mode_btn.set("Cursor" if self.settings.mode == "cursor" else "Relativo")
        self.mode_btn.grid(row=0, column=2, sticky="e")
        self._slider(tab, "Sensibilidade", "sensitivity", 0.3, 3.0, lambda v: f"{v:.2f}x")
        self._slider(tab, "Zona morta", "deadzone", 0.0, 0.3, lambda v: f"{v * 100:.0f}%")
        self._slider(tab, "Curva", "curve", 1.0, 3.0, lambda v: f"{v:.2f}", "1 = linear, maior = mais fino no centro")
        self._slider(tab, "Auto-centrar", "auto_center", 0.0, 3.0,
                     lambda v: "off" if v < 0.01 else f"{v:.1f}", "Só no modo Relativo")
        self._switch(tab, "Inverter X", "invert_x")
        self._switch(tab, "Inverter Y", "invert_y", "Padrão: mouse para trás = puxar o manche")
        ctk.CTkButton(tab, text="Centralizar eixos", fg_color=CARD_2, hover_color=BORDER, font=self.font,
                      command=self.engine.recenter).pack(anchor="e", padx=8, pady=(6, 0))

    def _build_buttons_tab(self, tab):
        grid = ctk.CTkFrame(tab, fg_color=CARD_2, corner_radius=10)
        grid.pack(fill="x", padx=8, pady=(4, 8))
        names = [("Clique esquerdo", 1), ("Clique direito", 2), ("Clique do scroll", 3), ("Mouse 4 (lateral)", 4),
                 ("Mouse 5 (lateral)", 5), ("Scroll para cima", 6), ("Scroll para baixo", 7)]
        for i, (name, num) in enumerate(names):
            r, c = divmod(i, 2)
            ctk.CTkLabel(grid, text=f"{name}", font=self.font, text_color=TEXT, anchor="w").grid(
                row=r, column=c * 2, sticky="w", padx=(14, 4), pady=3)
            ctk.CTkLabel(grid, text=f"Botão {num}", font=self.font_small, text_color=ACCENT, anchor="e").grid(
                row=r, column=c * 2 + 1, sticky="e", padx=(4, 18), pady=3)
        self._switch(tab, "Scroll → botões 6/7", "wheel_buttons", "Cada 'clique' do scroll = um pressionamento")
        self._switch(tab, "Scroll → eixo Z", "wheel_axis", "Use como throttle (precisa eixo Z no vJoy)",
                     on_change=self.engine.change_device)
        self._slider(tab, "Passo do eixo Z", "wheel_axis_step", 0.01, 0.2, lambda v: f"{v * 100:.0f}%")
        self._switch(tab, "Bloquear cliques no Windows", "block_clicks",
                     "Enquanto ativo, botões/scroll só vão para o joystick")

    def _build_general_tab(self, tab):
        row = self._row(tab, "Dispositivo vJoy", "Número do joystick virtual")
        self.dev_menu = ctk.CTkOptionMenu(row, values=[str(i) for i in range(1, 17)], width=80, font=self.font,
                                          fg_color=CARD_2, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                                          command=self._set_device)
        self.dev_menu.set(str(self.settings.device_id))
        self.dev_menu.grid(row=0, column=2, sticky="e")

        row = self._row(tab, "Tecla liga/desliga", "Funciona mesmo com o simulador em foco")
        hk = ctk.CTkOptionMenu(row, values=list(HOTKEYS), width=120, font=self.font, fg_color=CARD_2,
                               button_color=ACCENT, button_hover_color=ACCENT_HOVER, command=self._set_hotkey)
        hk.set(self.settings.hotkey)
        hk.grid(row=0, column=2, sticky="e")

        self._switch(tab, "Ativar ao abrir", "start_active")
        self._switch(tab, "Sempre no topo", "always_on_top",
                     on_change=lambda: self.attributes("-topmost", self.settings.always_on_top))

        info = ("Dica: no MSFS, vá em Controles → vJoy Device e associe X/Y a\n"
                "Aileron/Elevator e os botões 1–7 às funções desejadas.")
        ctk.CTkLabel(tab, text=info, font=self.font_small, text_color=MUTED, justify="left").pack(
            anchor="w", padx=8, pady=(14, 0))

    def _build_footer(self):
        self.status_lbl = ctk.CTkLabel(self, text="", font=self.font_small, text_color=MUTED, anchor="w")
        self.status_lbl.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 12))

    # -- actions -----------------------------------------------------------
    def _set_mode(self, value):
        self.settings.mode = "cursor" if value == "Cursor" else "relative"
        self.engine.recenter()
        self._schedule_save()

    def _set_device(self, value):
        self.settings.device_id = int(value)
        self.engine.change_device()
        self._schedule_save()

    def _set_hotkey(self, value):
        self.settings.hotkey = value
        self._schedule_save()

    def _schedule_save(self):
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(600, self.settings.save)

    def _on_close(self):
        self.settings.save()
        self.engine.stop()
        self.destroy()

    # -- refresh -----------------------------------------------------------
    def _refresh(self):
        e = self.engine
        s = self.size
        half = s / 2
        px, py = half + e.x * (half - 8), half + e.y * (half - 8)
        r = 8
        color = GREEN if e.active else MUTED
        self.canvas.coords(self.dot, px - r, py - r, px + r, py + r)
        self.canvas.itemconfigure(self.dot, fill=color)
        self.canvas.coords(self.trail, half, half, px, py)
        self.canvas.itemconfigure(self.trail, fill=color)
        dz = self.settings.deadzone * half
        self.canvas.coords(self.dz_rect, half - dz, half - dz, half + dz, half + dz)
        self.axis_lbl.configure(text=f"X {e.x:+.2f}   Y {e.y:+.2f}   Z {e.z:.2f}")
        self.zbar.set(e.z)

        states = dict(e.buttons)
        states["wup"] = e.wheel_up.pressed
        states["wdn"] = e.wheel_down.pressed
        for key, box in self.chips.items():
            box.configure(fg_color=ACCENT if states.get(key) else CARD_2)

        hk = self.settings.hotkey
        if e.active:
            self.toggle_btn.configure(text=f"● ATIVO  ({hk})", fg_color=GREEN, hover_color=GREEN_HOVER)
        else:
            self.toggle_btn.configure(text=f"○ DESATIVADO  ({hk})", fg_color=CARD_2, hover_color=BORDER)

        if e.error:
            self.status_lbl.configure(text="⚠ " + e.status, text_color=RED)
        elif "atenção" in e.status:
            self.status_lbl.configure(text="⚠ " + e.status, text_color=AMBER)
        else:
            self.status_lbl.configure(text="● " + e.status, text_color=MUTED)
        self.after(33, self._refresh)


def run():
    App().mainloop()
