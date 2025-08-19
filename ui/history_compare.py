import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict
from core import db

class HistoryCompareWindow(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.title("History / Compare")
        self.geometry("1100x700")
        self.resizable(True, True)
        self.root = root

        left = ttk.Frame(self, padding=10); left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="Select runs to compare").pack(anchor="w")
        self.run_list = tk.Listbox(left, selectmode=tk.EXTENDED, height=20, width=40)
        self.run_list.pack(fill=tk.BOTH, expand=False, pady=(4,8))

        btns = ttk.Frame(left); btns.pack(anchor="w", pady=(4,8))
        ttk.Button(btns, text="Refresh", command=self.load_runs).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Compare ▶", command=self.compare_selected).pack(side=tk.LEFT, padx=2)
        self.only_diff_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Show only differences", variable=self.only_diff_var, command=self.compare_selected).pack(anchor="w", pady=(6,0))
        note = "Tip: first selected run is the baseline; differing cells are highlighted."
        ttk.Label(left, text=note).pack(anchor="w", pady=(10,0))

        right = ttk.Frame(self); right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(right, background="#1e1e1e"); self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_y = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview); self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview); self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0,0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.load_runs()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def load_runs(self):
        self.run_list.delete(0, tk.END)
        try:
            with db.get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT run_id, timestamp, board_name, lot, dut_id FROM runs ORDER BY timestamp DESC")
                self._rows = cur.fetchall()
                for run_id, ts, board, lot, dut in self._rows:
                    label = f"{ts} | {board} | lot:{lot} | dut:{dut} | {run_id}"
                    self.run_list.insert(tk.END, label)
        except Exception as e:
            messagebox.showerror("SQLite", f"Failed to load runs:\n{e}")

    def compare_selected(self):
        for child in self.grid_frame.winfo_children(): child.destroy()
        sel = self.run_list.curselection()
        if not sel: return
        labels = [f"{ts} | {board} | lot:{lot} | dut:{dut} | {run_id}" for run_id, ts, board, lot, dut in self._rows]
        run_ids = [labels[i].split("|")[-1].strip() for i in sel]

        try:
            with db.get_conn() as conn:
                cur = conn.cursor()
                q_marks = ",".join("?" for _ in run_ids)
                cur.execute(f"SELECT m.run_id, m.field_id, m.label, m.value, m.unit FROM measurements m WHERE m.run_id IN ({q_marks})", run_ids)
                data = cur.fetchall()
        except Exception as e:
            messagebox.showerror("SQLite", f"Failed to load measurements:\n{e}")
            return

        pivot = {}
        for rid, fid, label, value, unit in data:
            pivot.setdefault(fid, {"label": label or fid})
            display = f"{value}" if not unit else f"{value} {unit}"
            pivot[fid][rid] = display

        baseline = run_ids[0]
        header_font = ("Arial", 10, "bold")
        ttk.Label(self.grid_frame, text="Field ID", font=header_font).grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        ttk.Label(self.grid_frame, text="Label", font=header_font).grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        col_offset = 2
        for j, rid in enumerate(run_ids):
            ttk.Label(self.grid_frame, text=rid, font=header_font).grid(row=0, column=col_offset + j, sticky="nsew", padx=2, pady=2)

        row = 1
        for fid in sorted(pivot.keys(), key=lambda s: s.lower()):
            base_val = pivot[fid].get(baseline, "")
            values = [pivot[fid].get(rid, "") for rid in run_ids]
            if self.only_diff_var.get() and all(v == base_val for v in values):
                continue

            ttk.Label(self.grid_frame, text=fid).grid(row=row, column=0, sticky="nsew", padx=2, pady=1)
            ttk.Label(self.grid_frame, text=pivot[fid]["label"]).grid(row=row, column=1, sticky="nsew", padx=2, pady=1)

            for j, val in enumerate(values):
                cell = tk.Label(self.grid_frame, text=val, anchor="w", padx=6, pady=2)
                cell.grid(row=row, column=col_offset + j, sticky="nsew", padx=2, pady=1)
                if j == 0: cell.configure(bg="#E3F2FD")
                elif val != base_val: cell.configure(bg="#FFF59D")
            row += 1

        for c in range(col_offset + len(run_ids)):
            self.grid_frame.grid_columnconfigure(c, weight=1)
