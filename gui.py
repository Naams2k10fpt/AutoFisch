"""
Modern Dark UI for Fisch Multi-Rod Auto Fishing Bot.
Built with Python Tkinter.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import keyboard
import mss
import numpy as np

from config import load_config, save_config
from vision_utils import LANE_CONFIG, get_roblox_client_rect
from macro_engine import MacroEngine

ROD_DEFINITIONS = [
    {
        "id": "default",
        "name": "Default Rod",
        "calib_text": "TEST BAR (F7)",
        "desc": "Thanh bar trắng trượt ngang & spam giữ tâm"
    },
    {
        "id": "tranquility",
        "name": "Tranquility Rod",
        "calib_text": "QUÉT LÀN (F7)",
        "desc": "Minigame 4 phím D / F / J / K"
    }
]

class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Fisch")
        self.root.geometry("540x670")
        self.root.resizable(False, False)
        self.root.configure(bg="#12131C")
        
        self.config = load_config()
        self.engine = MacroEngine(
            config=self.config,
            on_lane_hit_fn=self._on_lane_hit,
            on_default_bar_fn=self._on_default_bar_update,
            on_log_fn=self._append_log,
            on_state_fn=self._on_state_change
        )
        
        self.lane_labels = {}
        self.lane_reset_timers = {}
        
        self._build_ui()
        self._register_hotkeys()
        self._start_stats_updater()
        self._switch_mode_view(self.config.get('rod_mode', 'default'))

    def _build_ui(self):
        # Header banner
        header_frame = tk.Frame(self.root, bg="#1A1C29", height=65)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        title = tk.Label(header_frame, text="AUTO FISCH", font=("Segoe UI", 16, "bold"), fg="#38BDF8", bg="#1A1C29")
        title.pack(anchor=tk.W, padx=20, pady=(8, 0))
        
        subtitle = tk.Label(header_frame, text="Naams", font=("Segoe UI", 9), fg="#94A3B8", bg="#1A1C29")
        subtitle.pack(anchor=tk.W, padx=20, pady=(0, 8))

        # Configure dark styling for ttk Combobox
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Rod.TCombobox',
            fieldbackground='#0F172A',
            background='#1E293B',
            foreground='#38BDF8',
            darkcolor='#334155',
            lightcolor='#334155',
            selectbackground='#0F172A',
            selectforeground='#38BDF8',
            arrowcolor='#38BDF8',
            bordercolor='#334155',
            padding=4
        )
        style.map(
            'Rod.TCombobox',
            fieldbackground=[('readonly', '#0F172A')],
            selectbackground=[('readonly', '#0F172A')],
            selectforeground=[('readonly', '#38BDF8')],
            foreground=[('readonly', '#38BDF8')],
            background=[('readonly', '#1E293B')]
        )
        self.root.option_add('*TCombobox*Listbox.background', '#0F172A')
        self.root.option_add('*TCombobox*Listbox.foreground', '#F8FAFC')
        self.root.option_add('*TCombobox*Listbox.selectBackground', '#1E293B')
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#38BDF8')
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 9, 'bold'))

        # Rod Selector Frame (Dropdown)
        rod_select_frame = tk.Frame(self.root, bg="#161824", pady=8, padx=12)
        rod_select_frame.pack(fill=tk.X, padx=15, pady=(8, 4))
        
        tk.Label(
            rod_select_frame, text="CHỌN CẦN CÂU (ROD):",
            font=("Segoe UI", 9, "bold"), fg="#F8FAFC", bg="#161824"
        ).pack(side=tk.LEFT, padx=(4, 10))
        
        self.rod_id_to_def = {r['id']: r for r in ROD_DEFINITIONS}
        self.rod_name_to_id = {r['name']: r['id'] for r in ROD_DEFINITIONS}
        
        current_id = self.config.get('rod_mode', 'default')
        if current_id not in self.rod_id_to_def:
            current_id = 'default'
            
        current_name = self.rod_id_to_def[current_id]['name']
        
        self.rod_combo = ttk.Combobox(
            rod_select_frame,
            values=[r['name'] for r in ROD_DEFINITIONS],
            state="readonly",
            style="Rod.TCombobox",
            font=("Segoe UI", 9, "bold"),
            width=28
        )
        self.rod_combo.set(current_name)
        self.rod_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.rod_combo.bind("<<ComboboxSelected>>", self._on_rod_combo_select)

        # Mode Dynamic Container
        self.container_frame = tk.Frame(self.root, bg="#12131C")
        self.container_frame.pack(fill=tk.X, padx=15, pady=(2, 4))

        # --- Sub-panel 1: Default Rod Panel ---
        self.default_panel = tk.Frame(self.container_frame, bg="#161824", pady=8, padx=10)
        
        self.bar_canvas = tk.Canvas(self.default_panel, width=490, height=36, bg="#0F172A", highlightthickness=1, highlightbackground="#334155")
        self.bar_canvas.pack(pady=4)
        
        self.canvas_track_bg = self.bar_canvas.create_rectangle(5, 6, 485, 30, fill="#1E293B", outline="#475569")
        self.canvas_bar = self.bar_canvas.create_rectangle(140, 6, 340, 30, fill="#F8FAFC", outline="")
        self.canvas_center_line = self.bar_canvas.create_line(240, 6, 240, 30, fill="#38BDF8", width=2)
        self.canvas_fish = self.bar_canvas.create_oval(234, 9, 246, 27, fill="#EF4444", outline="#FBBF24", width=2)
        
        info_row = tk.Frame(self.default_panel, bg="#161824")
        info_row.pack(fill=tk.X, pady=4)
        info_row.columnconfigure(0, weight=1)
        info_row.columnconfigure(1, weight=1)
        info_row.columnconfigure(2, weight=1)
        
        self.lbl_bar_w = tk.Label(info_row, text="Độ dài Bar: --- px", font=("Segoe UI", 9, "bold"), fg="#F8FAFC", bg="#161824")
        self.lbl_bar_w.grid(row=0, column=0, sticky=tk.W, padx=4)
        
        self.lbl_err = tk.Label(info_row, text="Lệch: 0px", font=("Segoe UI", 9), fg="#94A3B8", bg="#161824")
        self.lbl_err.grid(row=0, column=1, sticky=tk.N+tk.S)

        # Action indicator boxes (aligned to the right as requested by user)
        self.action_box_frame = tk.Frame(info_row, bg="#161824")
        self.action_box_frame.grid(row=0, column=2, sticky=tk.E, padx=4)
        
        self.action_icons = {
            "RELEASE": {
                "icon": "⏪",
                "label": "GIẢM TỐC",
                "tip": "⏪ Giảm tốc / Trôi trái (Thả chuột)",
                "active_bg": "#451A03",
                "active_fg": "#FBBF24",
                "active_border": "#F59E0B"
            },
            "SPAM_HOVER": {
                "icon": "⚡",
                "label": "PHANH",
                "tip": "⚡ Phanh chống trôi lố (Spam click giữ tâm)",
                "active_bg": "#3B0764",
                "active_fg": "#E879F9",
                "active_border": "#A855F7"
            },
            "CENTER": {
                "icon": "🎯",
                "label": "TÂM",
                "tip": "🎯 Đang ổn định trong tâm",
                "active_bg": "#064E3B",
                "active_fg": "#34D399",
                "active_border": "#10B981"
            },
            "HOLD": {
                "icon": "⏩",
                "label": "TĂNG TỐC",
                "tip": "⏩ Tăng tốc / Kéo phải (Nhấn giữ chuột)",
                "active_bg": "#082F49",
                "active_fg": "#38BDF8",
                "active_border": "#0284C7"
            }
        }
        
        self.action_boxes = {}
        for key in ["RELEASE", "SPAM_HOVER", "CENTER", "HOLD"]:
            meta = self.action_icons[key]
            box = tk.Label(
                self.action_box_frame,
                text=meta["icon"],
                font=("Segoe UI Emoji", 11),
                bg="#1E2235",
                fg="#64748B",
                width=3,
                pady=1,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground="#334155"
            )
            box.pack(side=tk.LEFT, padx=2)
            self.action_boxes[key] = box
        
        # Deadband & Inertia Lead parameters (hidden from UI per user request, maintained via config)
        self.deadband_var = tk.IntVar(value=self.config.get('bar_deadband_px', 10))
        self.inertia_var = tk.DoubleVar(value=self.config.get('inertia_lead_sec', 0.12))
        self.fish_lead_var = tk.DoubleVar(value=self.config.get('fish_lead_sec', 0.08))

        # Spam Click Hover Settings
        spam_row = tk.Frame(self.default_panel, bg="#161824")
        spam_row.pack(fill=tk.X, pady=(4, 0))

        self.spam_var = tk.BooleanVar(value=self.config.get('spam_enabled', True))
        self.spam_cb = tk.Checkbutton(
            spam_row, text="Tốc độ spam:", variable=self.spam_var,
            font=("Segoe UI", 9), fg="#F1F5F9", bg="#161824", activebackground="#161824",
            activeforeground="#38BDF8", selectcolor="#0F172A", command=self._on_spam_toggle
        )
        self.spam_cb.pack(side=tk.LEFT, padx=(4, 8), pady=(12, 0))
        
        current_pulse = max(30, min(100, self.config.get('spam_pulse_ms', 50)))
        self.spam_pulse_var = tk.IntVar(value=current_pulse)
        self.spam_slider = tk.Scale(
            spam_row, from_=30, to=100, orient=tk.HORIZONTAL,
            variable=self.spam_pulse_var, bg="#161824", fg="#38BDF8",
            highlightthickness=0, command=self._on_spam_pulse_change
        )
        self.spam_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=4)

        # --- Sub-panel 2: Tranquility Rod Panel ---
        self.tranquility_panel = tk.Frame(self.container_frame, bg="#161824", pady=8, padx=10)
        
        lane_grid = tk.Frame(self.tranquility_panel, bg="#161824")
        lane_grid.pack()
        
        for idx, lane in enumerate(['D', 'F', 'J', 'K']):
            col_frame = tk.Frame(lane_grid, bg="#1E2235", width=95, height=72, relief=tk.RIDGE, bd=2)
            col_frame.pack_propagate(False)
            col_frame.grid(row=0, column=idx, padx=8)
            
            key_label = tk.Label(col_frame, text=lane, font=("Segoe UI", 20, "bold"), fg="#64748B", bg="#1E2235")
            key_label.pack(expand=True)
            
            color_label = tk.Label(col_frame, text=LANE_CONFIG[lane]['color_name'], font=("Segoe UI", 8), fg="#64748B", bg="#1E2235")
            color_label.pack(pady=(0, 4))
            
            self.lane_labels[lane] = (col_frame, key_label, color_label)
            
        rhythm_tune_row = tk.Frame(self.tranquility_panel, bg="#161824")
        rhythm_tune_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(rhythm_tune_row, text="Độ lệch thời điểm bấm (-px = Sớm, +px = Trễ):", font=("Segoe UI", 8), fg="#CBD5E1", bg="#161824").pack(side=tk.LEFT, padx=8)
        self.offset_var = tk.IntVar(value=self.config.get('timing_offset_px', 0))
        self.offset_slider = tk.Scale(rhythm_tune_row, from_=-15, to=15, orient=tk.HORIZONTAL, variable=self.offset_var, bg="#161824", fg="#A855F7", highlightthickness=0, command=self._on_offset_change)
        self.offset_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=8)

        # Control Panel (Buttons)
        ctrl_frame = tk.Frame(self.root, bg="#161824", pady=8)
        ctrl_frame.pack(fill=tk.X, padx=15, pady=(2, 6))
        
        btn_grid = tk.Frame(ctrl_frame, bg="#161824")
        btn_grid.pack()
        
        self.toggle_btn = tk.Button(
            btn_grid, text="BẬT BOT (F6)", font=("Segoe UI", 12, "bold"),
            bg="#059669", fg="white", activebackground="#10B981", activeforeground="white",
            relief=tk.FLAT, width=18, height=2, command=self.engine.toggle, cursor="hand2"
        )
        self.toggle_btn.grid(row=0, column=0, padx=8)
        
        self.calib_btn = tk.Button(
            btn_grid, text="KIỂM TRA (F7)", font=("Segoe UI", 11, "bold"),
            bg="#3B82F6", fg="white", activebackground="#60A5FA", activeforeground="white",
            relief=tk.FLAT, width=14, height=2, command=self._manual_calibrate, cursor="hand2"
        )
        self.calib_btn.grid(row=0, column=1, padx=8)

        # Auto-Cast Settings
        cast_frame = tk.LabelFrame(self.root, text=" Cài Đặt Auto Cast ", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#161824", padx=12, pady=4)
        cast_frame.pack(fill=tk.X, padx=15, pady=(0, 6))
        
        self.auto_cast_var = tk.BooleanVar(value=self.config.get('auto_cast', True))
        cast_cb = tk.Checkbutton(
            cast_frame, text="Tiếp tục câu cá",
            variable=self.auto_cast_var, font=("Segoe UI", 9), fg="#F1F5F9", bg="#161824",
            activebackground="#161824", activeforeground="#38BDF8", selectcolor="#0F172A",
            command=self._on_autocast_toggle
        )
        cast_cb.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        
        tk.Label(cast_frame, text="Thời gian giữ chuột (giây):", font=("Segoe UI", 8), fg="#CBD5E1", bg="#161824").grid(row=1, column=0, sticky=tk.W, pady=1)
        self.cast_dur_var = tk.DoubleVar(value=self.config.get('cast_duration_sec', 0.5))
        self.cast_dur_slider = tk.Scale(cast_frame, from_=0.1, to=2.0, resolution=0.05, orient=tk.HORIZONTAL, variable=self.cast_dur_var, bg="#161824", fg="#38BDF8", highlightthickness=0, command=self._on_cast_dur_change)
        self.cast_dur_slider.grid(row=1, column=1, sticky=tk.EW, padx=8)
        
        tk.Label(cast_frame, text="Thời gian delay (giây):", font=("Segoe UI", 8), fg="#CBD5E1", bg="#161824").grid(row=2, column=0, sticky=tk.W, pady=1)
        self.cast_delay_var = tk.DoubleVar(value=self.config.get('cast_delay_sec', 1.2))
        self.cast_delay_slider = tk.Scale(cast_frame, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.cast_delay_var, bg="#161824", fg="#38BDF8", highlightthickness=0, command=self._on_cast_delay_change)
        self.cast_delay_slider.grid(row=2, column=1, sticky=tk.EW, padx=8)

        # Status Bar
        status_bar = tk.Frame(self.root, bg="#1E2235", height=28)
        status_bar.pack(fill=tk.X, padx=15, pady=(0, 4))
        
        self.status_lbl = tk.Label(status_bar, text="Status: ĐÃ TẮT (Bấm F6)", font=("Segoe UI", 9, "bold"), fg="#EF4444", bg="#1E2235")
        self.status_lbl.pack(side=tk.LEFT, padx=10, pady=4)
        
        self.fps_lbl = tk.Label(status_bar, text="FPS: 0.0", font=("Segoe UI", 9), fg="#94A3B8", bg="#1E2235")
        self.fps_lbl.pack(side=tk.RIGHT, padx=10, pady=4)
        
        self.stats_lbl = tk.Label(status_bar, text="Cá: 0", font=("Segoe UI", 9), fg="#94A3B8", bg="#1E2235")
        self.stats_lbl.pack(side=tk.RIGHT, padx=15, pady=4)

        # Mode Instruction Banner
        self.info_lbl = tk.Label(
            self.root,
            text="Bấm F6 một lần để bật bot. Hãy quăng cần lần đầu để bắt đầu treo!",
            font=("Segoe UI", 8, "italic"), fg="#94A3B8", bg="#12131C"
        )
        self.info_lbl.pack(anchor=tk.W, padx=18, pady=(0, 3))

        # Log Console
        log_frame = tk.Frame(self.root, bg="#0D0E15")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, bg="#0D0E15", fg="#A7F3D0", font=("Consolas", 8), relief=tk.FLAT, height=5)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log_text.insert(tk.END, "Ready. Chọn Cần và Bấm F6 để bắt đầu tự động câu cá.\n")

    def _switch_mode_view(self, mode):
        rod_def = self.rod_id_to_def.get(mode)
        calib_text = rod_def['calib_text'] if rod_def else "HIỆU CHUẨN (F7)"
        self.calib_btn.configure(text=calib_text)

        if mode == 'default':
            self.tranquility_panel.pack_forget()
            self.default_panel.pack(fill=tk.X)
        elif mode == 'tranquility':
            self.default_panel.pack_forget()
            self.tranquility_panel.pack(fill=tk.X)
        else:
            self.default_panel.pack_forget()
            self.tranquility_panel.pack_forget()

    def _on_rod_combo_select(self, event=None):
        selected_name = self.rod_combo.get()
        new_mode = self.rod_name_to_id.get(selected_name, 'default')
        if new_mode == self.config.get('rod_mode'):
            return
            
        self.config['rod_mode'] = new_mode
        save_config(self.config)
        self._switch_mode_view(new_mode)
        self._append_log(f"Đã chuyển sang chế độ: {selected_name}")
        if self.engine.is_running:
            self._append_log("Đang khởi động lại macro theo chế độ mới...")
            self.engine.stop()
            self.root.after(300, self.engine.start)

    def _register_hotkeys(self):
        try:
            keyboard.add_hotkey(self.config['hotkey_toggle'], lambda: self.root.after(0, self.engine.toggle))
            keyboard.add_hotkey(self.config['hotkey_calibrate'], lambda: self.root.after(0, self._manual_calibrate))
            keyboard.add_hotkey(self.config['hotkey_exit'], lambda: self.root.after(0, self._exit_app))
        except Exception as e:
            self._append_log(f"Warning: Could not register global hotkeys: {e}")

    def _manual_calibrate(self):
        mode = self.config.get('rod_mode', 'default')
        if mode == 'default':
            self._append_log("Đang kiểm tra nhận diện thanh bar và cá trên màn hình...")
            with mss.MSS() as sct:
                roblox_info = get_roblox_client_rect()
                if roblox_info:
                    _, rx, ry, rw, rh, title = roblox_info
                else:
                    mon = [m for m in sct.monitors if m.get('is_primary')][0]
                    rx, ry, rw, rh = mon['left'], mon['top'], mon['width'], mon['height']
                
                track_left = rx + int(rw * (570.0 / 1920.0))
                track_width = int(rw * ((1350.0 - 570.0) / 1920.0))
                track_top = ry + int(rh * (908.0 / 1080.0))
                track_height = max(18, int(rh * (30.0 / 1080.0)))
                
                roi = {'left': track_left, 'top': track_top, 'width': track_width, 'height': track_height}
                raw = sct.grab(roi)
                frame = np.array(raw)[:, :, :3]
                
                col_bright = np.mean(np.mean(frame, axis=0), axis=1)
                edge = max(6, int(track_width * 0.015))
                valid_white = np.where(col_bright[edge:-edge] > 180)[0] + edge
                if len(valid_white) >= 60:
                    bar_w = valid_white[-1] - valid_white[0]
                    messagebox.showinfo("Nhận Diện Thành Công", f"Đã tìm thấy thanh bar minigame!\nĐộ dài: {bar_w}px (Tự động nhận diện)\nBấm F6 để bắt đầu tự động câu.")
                else:
                    messagebox.showwarning("Thông Báo", "Chưa phát hiện thanh bar minigame.\nHãy chắc chắn minigame đang hiển thị trên màn hình rồi bấm lại.")
        else:
            self._append_log("Đang quét màn hình để hiệu chỉnh tọa độ 4 làn phím...")
            with mss.MSS() as sct:
                ok = self.engine.tranquility_engine.calibrate(sct)
            if ok:
                messagebox.showinfo("Hiệu Chỉnh Thành Công", "Đã định vị thành công 4 làn phím Tranquility!\nBấm F6 để bắt đầu tự động câu.")
            else:
                messagebox.showwarning("Thông Báo", "Chưa tìm thấy đủ 4 làn phím.\nHãy chắc chắn minigame đang hiển thị trên màn hình rồi bấm lại.")

    def _reset_action_boxes(self):
        for widget in self.action_boxes.values():
            widget.configure(
                bg="#1E2235",
                fg="#64748B",
                highlightbackground="#334155"
            )

    def _on_state_change(self, state):
        def update():
            if state == "PLAYING":
                self.toggle_btn.configure(text="TẮT BOT (F6)", bg="#DC2626", activebackground="#EF4444")
                self.status_lbl.configure(text="Status: ⚡ ĐANG TỰ ĐỘNG CHƠI!", fg="#10B981")
                self.info_lbl.configure(text="Bot đang tự động điều khiển giữ cá trong tâm bar...", fg="#34D399")
            elif state == "CASTING":
                self._reset_action_boxes()
                self.toggle_btn.configure(text="TẮT BOT (F6)", bg="#DC2626", activebackground="#EF4444")
                self.status_lbl.configure(text="Status: 🎣 ĐANG QUĂNG CẦN...", fg="#38BDF8")
                self.info_lbl.configure(text="Đang chờ hoạt ảnh nhận cá và tự quăng cần cho lượt tiếp...", fg="#38BDF8")
            elif state == "STANDBY":
                self._reset_action_boxes()
                self.toggle_btn.configure(text="TẮT BOT (F6)", bg="#DC2626", activebackground="#EF4444")
                self.status_lbl.configure(text="Status: 🐟 ĐANG CHỜ CÁ CẮN...", fg="#F59E0B")
                self.info_lbl.configure(text="Hãy quăng cần câu xuống nước. Khi cá cắn câu, bot sẽ tự động chơi và lặp lại!", fg="#FBBF24")
            else:
                self._reset_action_boxes()
                self.toggle_btn.configure(text="BẬT BOT (F6)", bg="#059669", activebackground="#10B981")
                self.status_lbl.configure(text="Status: ĐÃ TẮT (Bấm F6)", fg="#EF4444")
                self.info_lbl.configure(text="Bấm F6 một lần để bật bot. Hãy tự do quăng cần lần đầu để bắt đầu chuỗi tự động!", fg="#94A3B8")
        self.root.after(0, update)

    def _on_default_bar_update(self, bar_l, bar_r, bar_w, bar_c, fish_x, raw_err, pred_err, v_bar, action, track_w):
        def draw():
            cw = 480.0
            scale = cw / max(1, track_w)
            
            c_bar_l = 5 + bar_l * scale
            c_bar_r = 5 + bar_r * scale
            c_bar_c = 5 + bar_c * scale
            c_fish_x = 5 + fish_x * scale
            
            self.bar_canvas.coords(self.canvas_bar, c_bar_l, 6, c_bar_r, 30)
            self.bar_canvas.coords(self.canvas_center_line, c_bar_c, 6, c_bar_c, 30)
            self.bar_canvas.coords(self.canvas_fish, c_fish_x - 6, 9, c_fish_x + 6, 27)
            
            self.lbl_bar_w.configure(text=f"Độ dài Bar: {int(bar_w)}px")
            self.lbl_err.configure(text=f"Lệch: {raw_err:+.0f}px")
            
            # Update action indicator boxes (bright for active action, dimmed gray for others)
            curr_action = action if action in self.action_boxes else "CENTER"
            for act_key, widget in self.action_boxes.items():
                if act_key == curr_action:
                    meta = self.action_icons[act_key]
                    widget.configure(
                        bg=meta['active_bg'],
                        fg=meta['active_fg'],
                        highlightbackground=meta['active_border']
                    )
                else:
                    widget.configure(
                        bg="#1E2235",
                        fg="#64748B",
                        highlightbackground="#334155"
                    )
        self.root.after(0, draw)

    def _on_lane_hit(self, lane, is_red=False):
        def highlight():
            if lane not in self.lane_labels:
                return
            frame, klbl, clbl = self.lane_labels[lane]
            active_hex = "#EF4444" if is_red else LANE_CONFIG[lane]['hex']
            frame.configure(bg=active_hex, relief=tk.SOLID)
            klbl.configure(bg=active_hex, fg="#FFFFFF" if is_red else "#000000")
            clbl.configure(bg=active_hex, fg="#FFFFFF" if is_red else "#000000")
            
            if lane in self.lane_reset_timers and self.lane_reset_timers[lane]:
                self.root.after_cancel(self.lane_reset_timers[lane])
            self.lane_reset_timers[lane] = self.root.after(120, lambda l=lane: self._reset_lane_ui(l))
            
        self.root.after(0, highlight)

    def _reset_lane_ui(self, lane):
        if lane in self.lane_labels:
            frame, klbl, clbl = self.lane_labels[lane]
            frame.configure(bg="#1E2235", relief=tk.RIDGE)
            klbl.configure(bg="#1E2235", fg="#64748B")
            clbl.configure(bg="#1E2235", fg="#64748B")

    def _on_autocast_toggle(self):
        self.config['auto_cast'] = self.auto_cast_var.get()
        save_config(self.config)

    def _on_cast_dur_change(self, val):
        self.config['cast_duration_sec'] = float(val)
        save_config(self.config)

    def _on_cast_delay_change(self, val):
        self.config['cast_delay_sec'] = float(val)
        save_config(self.config)

    def _on_offset_change(self, val):
        self.config['timing_offset_px'] = int(val)
        save_config(self.config)

    def _on_deadband_change(self, val):
        self.config['bar_deadband_px'] = int(val)
        save_config(self.config)

    def _on_inertia_change(self, val):
        self.config['inertia_lead_sec'] = float(val)
        save_config(self.config)

    def _on_fish_lead_change(self, val):
        self.config['fish_lead_sec'] = float(val)
        save_config(self.config)

    def _on_spam_toggle(self):
        self.config['spam_enabled'] = self.spam_var.get()
        save_config(self.config)

    def _on_spam_pulse_change(self, val):
        self.config['spam_pulse_ms'] = int(val)
        save_config(self.config)

    def _append_log(self, text):
        def append():
            self.log_text.insert(tk.END, f"{text}\n")
            self.log_text.see(tk.END)
        self.root.after(0, append)

    def _start_stats_updater(self):
        def loop():
            self.fps_lbl.configure(text=f"FPS: {self.engine.fps:.1f}")
            if self.config.get('rod_mode') == 'tranquility':
                self.stats_lbl.configure(text=f"Hits: {self.engine.tranquility_engine.total_hits}")
            else:
                self.stats_lbl.configure(text=f"Cá: {self.engine.total_catches}")
            self.root.after(500, loop)
        self.root.after(500, loop)

    def _exit_app(self):
        self.engine.stop()
        self.root.destroy()
