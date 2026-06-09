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


def run_actions(actions):
    try:
        while True:
            for act in actions:
                perform_action(act)
    except KeyboardInterrupt:
        # Graceful stop when user hits Ctrl+C in console
        print("Auto‑clicker stopped by user.")

# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------
class AutoClickerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auto‑Clicker Builder")
        self.geometry("600x400")
        self.actions: list[ClickAction] = []
        self._build_ui()
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
        ttk.Button(btn_frame, text="Test Click", command=self.test_click).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side=tk.RIGHT, padx=5)
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

    def start_clicker(self):
        if not self.actions:
            messagebox.showwarning("No actions", "Add at least one action before starting.")
            return
        # Run in background thread so UI stays responsive
        t = threading.Thread(target=run_actions, args=(self.actions,), daemon=True)
        t.start()
        messagebox.showinfo("Started", "Auto‑clicker is running in the background.\nPress Ctrl+C in the console to stop.")

    def save_config(self):
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












