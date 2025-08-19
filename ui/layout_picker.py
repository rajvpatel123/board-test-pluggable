import os
import tkinter as tk
from tkinter import ttk

class LayoutPicker(tk.Toplevel):
    def __init__(self, root, layouts_dir: str):
        super().__init__(root)
        self.title("Select Layout")
        self.transient(root)
        self.grab_set()
        self.result = None
        self.layouts_dir = layouts_dir

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Choose a layout from: " + layouts_dir).pack(anchor="w", pady=(0,6))

        self.listbox = tk.Listbox(frm, selectmode=tk.SINGLE, height=14, width=48)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(frm); btns.pack(anchor="e", pady=(8,0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="Open", command=self._open).pack(side=tk.RIGHT)

        self.listbox.bind("<Double-Button-1>", lambda e: self._open())
        self._load_items()

    def _load_items(self):
        try:
            files = [f for f in os.listdir(self.layouts_dir) if f.lower().endswith(".json")]
            files.sort()
            for f in files:
                self.listbox.insert(tk.END, f)
        except Exception:
            pass

    def _open(self):
        idx = self.listbox.curselection()
        if not idx: return
        name = self.listbox.get(idx[0])
        self.result = os.path.join(self.layouts_dir, name)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
