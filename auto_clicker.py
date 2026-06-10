# auto_clicker_gui.py
"""Windows Auto‑Clicker with a simple Tkinter GUI.

The tool lets you define a sequence of mouse actions (click location,
button, type, and delay) and then runs them repeatedly.

* Click "Add Action" to record a new step.
* Click "Start" to begin the loop. Press Ctrl+C in the console to stop.
"""

import json
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pyautogui
import json
import logging
import logging.handlers
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model for a single click action
# ---------------------------------------------------------------------------
class ClickAction:
    def __init__(self, x=0, y=0, button="left", click_type="click", interval=1.0):
        self.x = x
        self.y = y
        self.button = button
        self.click_type = click_type
        self.interval = interval

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "button": self.button,
            "type": self.click_type,
            "interval": self.interval,
        }

# ---------------------------------------------------------------------------
# Core auto‑clicker logic (runs in a background thread)
# ---------------------------------------------------------------------------
def perform_action(action: ClickAction):
    if action.click_type == "click":
        pyautogui.click(action.x, action.y, button=action.button)
    elif action.click_type == "double":
        pyautogui.doubleClick(action.x, action.y, button=action.button)
    elif action.click_type == "right":
        pyautogui.rightClick(action.x, action.y)
    else:
        pyautogui.click(action.x, action.y, button=action.button)
    time.sleep(action.interval)


def run_actions(actions, stop_event: threading.Event):
    try:
        while not stop_event.is_set():
            for act in actions:
                if stop_event.is_set():
                    break
                perform_action(act)
    except Exception as e:
        print(f"Auto‑clicker stopped: {e}")

# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------
class AutoClickerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto‑Clicker Builder")
        self.geometry("600x400")
        self.configure(bg="#121212")
        self.actions: list[ClickAction] = []
        self.stop_event: threading.Event | None = None
        self.hotkeys = {}
        # Initialise logger first
        self._init_logger()
        # Load configuration (colours, hotkeys)
        self._load_config()
        # Load optional click path
        self._load_click_path()
        # Apply ttk styling
        self._apply_style()
        # Build UI components
        self._build_ui()
        # Status variable & label
        self.status_var = tk.StringVar(value="Ready")
        self._create_status_label()
        # Register hotkeys
        self._register_hotkeys()
        self._center_window()
# Duplicate init block removed – UI already set up
    def _build_ui(self):
        # Table / list of actions
        self.tree = ttk.Treeview(self, columns=("X", "Y", "Button", "Type", "Delay"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10)

        ttk.Button(btn_frame, text="Add Action", command=self.add_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Start", command=self.start_clicker).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Stop", command=self.stop_clicker).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Run Once", command=self.run_once).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Test Click", command=self.test_click).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side=tk.RIGHT, padx=5)
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill=tk.X, padx=10, pady=4)
    def test_click(self):
        """Move mouse to (100, 100) and click – used for debugging."""
        try:
            pyautogui.moveTo(100, 100, duration=0.2)
            pyautogui.click()
            messagebox.showinfo("Test", "Clicked at (100,100)")
        except Exception as e:
            messagebox.showerror("Error", str(e))


    def add_action(self):
        # Prompt user for coordinates and parameters
        dlg = ActionDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            act = ClickAction(*dlg.result)
            self.actions.append(act)
            self.tree.insert("", tk.END, values=(act.x, act.y, act.button, act.click_type, act.interval))

    def remove_selected(self):
        sel = self.tree.selection()
        for item in sel:
            idx = self.tree.index(item)
            self.tree.delete(item)
            del self.actions[idx]

    def run_once(self):
        if not self.actions:
            messagebox.showwarning("No actions", "Add at least one action before running.")
            return
        # Run actions once without threading
        for act in self.actions:
            perform_action(act)
        self.status_var.set("Run once completed.")

    def start_clicker(self):
        if not self.actions:
            messagebox.showwarning("No actions", "Add at least one action before starting.")
            return
        # Initialize stop event and run in background thread so UI stays responsive
        self.stop_event = threading.Event()
        t = threading.Thread(target=run_actions, args=(self.actions, self.stop_event), daemon=True)
        t.start()
        self.status_var.set("Auto‑clicker started.")
    
    def stop_clicker(self):
        """Stop the running auto‑clicker thread if active."""
        if self.stop_event:
            self.stop_event.set()
            self._update_status("Auto‑clicker stopped.")
            # Re‑enable start button, disable stop button
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        
    def _apply_style(self):
        """Configure ttk dark theme and widget colours."""
        style = ttk.Style(self)
        style.theme_use('clam')
        # Colours from config if present
        bg = getattr(self, "config_theme_bg", "#1e1e1e")
        fg = getattr(self, "config_theme_fg", "#ffffff")
        accent = getattr(self, "config_theme_accent", "#4a90e2")
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg)
        style.map("Treeview", background=[('selected', accent)])
        style.configure("TButton", background=bg, foreground=fg)
        style.map("TButton", background=[('active', accent)])
    
    def _init_logger(self):
        """Set up rotating file logger under the project folder."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "auto_clicker.log"
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger = logging.getLogger('AutoClicker')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)
        self.logger.info('AutoClicker started')
    
    def _load_config(self):
        """Load UI colours and hotkey mapping from config.json if it exists."""
        cfg_path = Path(__file__).parent / "config.json"
        if cfg_path.is_file():
            try:
                cfg = json.loads(cfg_path.read_text())
                theme = cfg.get('theme', {})
                self.config_theme_bg = theme.get('bg', '#1e1e1e')
                self.config_theme_fg = theme.get('fg', '#ffffff')
                self.config_theme_accent = theme.get('accent', '#4a90e2')
                self.hotkeys = cfg.get('hotkeys', {})
                self.logger.info('Config loaded')
            except Exception as e:
                self.logger.error(f'Failed to load config: {e}')
        else:
            # No config file – use built‑in defaults for theme colours
            self.config_theme_bg = '#1e1e1e'
            self.config_theme_fg = '#ffffff'
            self.config_theme_accent = '#4a90e2'
            self.logger.info('No config.json found, using defaults')
    
    def _load_click_path(self):
        """Read click_path.json and populate self.actions if valid."""
        path_file = Path(__file__).parent / "click_path.json"
        if not path_file.is_file():
            self.logger.info('No click_path.json found')
            return
        try:
            data = json.loads(path_file.read_text())
            for entry in data:
                x = int(entry.get('x', 0))
                y = int(entry.get('y', 0))
                button = entry.get('button', 'left')
                click_type = entry.get('type', 'click')
                interval = float(entry.get('interval', 1.0))
                self.actions.append(ClickAction(x, y, button, click_type, interval))
            self.logger.info(f'Loaded {len(self.actions)} actions from click_path.json')
        except Exception as e:
            self.logger.error(f'Error loading click_path.json: {e}')
    

    
    def _export_path(self):
        """Write current actions to click_path.json for external use."""
        path_file = Path(__file__).parent / "click_path.json"
        try:
            data = [act.to_dict() for act in self.actions]
            path_file.write_text(json.dumps(data, indent=2))
            self.logger.info('Exported click path')
            self._update_status('Exported click path')
        except Exception as e:
            self.logger.error(f'Failed to export click path: {e}')
    
    def _create_status_label(self):
        """Add a status label at the bottom of the window."""
        ttk.Label(self, textvariable=self.status_var, anchor="w", background=self.config_theme_bg, foreground=self.config_theme_fg).pack(fill=tk.X, padx=10, pady=4)
    
    def _update_status(self, message: str):
        """Update the status bar and log the change."""
        self.status_var.set(message)
        if hasattr(self, 'logger'):
            self.logger.info(message)
    
    def _safety_countdown(self):
        """Show a 3‑second countdown before the first click."""
        for i in range(3, 0, -1):
            self._update_status(f"Starting in {i}…")
            self.update()  # force UI refresh
            time.sleep(1)
        self._update_status("Running")
    
    def _register_hotkeys(self):
        """Bind hotkeys for start, stop, run once based on config or defaults."""
        start_key = self.hotkeys.get('start', '<Control-s>')
        stop_key = self.hotkeys.get('stop', '<Control-x>')
        runonce_key = self.hotkeys.get('run_once', '<Control-r>')
        self.bind_all(start_key, lambda e: self.start_clicker())
        self.bind_all(stop_key, lambda e: self.stop_clicker())
        self.bind_all(runonce_key, lambda e: self.run_once())
    
    # Override start_clicker to include safety countdown and button state handling
    def start_clicker(self):
        if not self.actions:
            messagebox.showwarning("No actions", "Add at least one action before starting.")
            return
        # Disable start button, enable stop button
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        # Safety countdown
        self._safety_countdown()
        # Initialise stop event and start background thread
        self.stop_event = threading.Event()
        t = threading.Thread(target=run_actions, args=(self.actions, self.stop_event), daemon=True)
        t.start()
        self._update_status("Auto‑clicker started")
    
    # Add Export Path button in UI build method
    def _build_ui(self):
        # Table / list of actions
        self.tree = ttk.Treeview(self, columns=("X", "Y", "Button", "Type", "Delay"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10)
        ttk.Button(btn_frame, text="Add Action", command=self.add_action).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_clicker)
        self.start_btn.pack(side=tk.RIGHT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_clicker, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Run Once", command=self.run_once).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Export Path", command=self._export_path).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Test Click", command=self.test_click).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side=tk.RIGHT, padx=5)

        """Stop the running auto‑clicker thread if active."""
        if self.stop_event:
            self.stop_event.set()
            self.status_var.set("Auto‑clicker stopped.")

    def save_config(self):
        # Existing save_config logic unchanged
        if not self.actions:
            messagebox.showwarning("Empty", "No actions to save.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save actions as JSON",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in self.actions], f, indent=2)
            messagebox.showinfo("Saved", f"Configuration saved to {file_path}")
        if not self.actions:
            messagebox.showwarning("Empty", "No actions to save.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save actions as JSON",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([a.to_dict() for a in self.actions], f, indent=2)
            messagebox.showinfo("Saved", f"Configuration saved to {file_path}")

    def _center_window(self):
        """Center the Tk window on the screen."""
        # Ensure geometry info is up‑to‑date
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        # End of centering helper
        # ---------------------------------------------------------------------------
# Simple dialog to capture a single action
# ---------------------------------------------------------------------------
class ActionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Action")
        self.resizable(False, False)
        self.result = None
        self._build()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        self.vars = {
            "x": tk.IntVar(value=0),
            "y": tk.IntVar(value=0),
            "button": tk.StringVar(value="left"),
            "type": tk.StringVar(value="click"),
            "interval": tk.DoubleVar(value=1.0),
        }

        ttk.Label(frm, text="X:").grid(row=0, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.vars["x"], width=10).grid(row=0, column=1)
        ttk.Label(frm, text="Y:").grid(row=1, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.vars["y"], width=10).grid(row=1, column=1)

        ttk.Label(frm, text="Button:").grid(row=2, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.vars["button"], values=["left", "right", "middle"], state="readonly").grid(row=2, column=1)
        ttk.Label(frm, text="Type:").grid(row=3, column=0, sticky="e")
        ttk.Combobox(frm, textvariable=self.vars["type"], values=["click", "double", "right"], state="readonly").grid(row=3, column=1)
        ttk.Label(frm, text="Delay (s):").grid(row=4, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.vars["interval"], width=10).grid(row=4, column=1)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)

    def ok(self):
        try:
            vals = (
                self.vars["x"].get(),
                self.vars["y"].get(),
                self.vars["button"].get(),
                self.vars["type"].get(),
                self.vars["interval"].get(),
            )
            self.result = vals
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def cancel(self):
        self.result = None
        self.destroy()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Ensure pyautogui fails fast if required permissions are missing.
    try:
        pyautogui.FAILSAFE = True
    except Exception:
        pass
    app = AutoClickerApp()
    app.mainloop()










