import tkinter as tk
from tkinter import ttk, filedialog

class CanvasDialog:
    def __init__(self, root, canvas_cfg):
        self.root = root
        self.result = None
        self.cfg = dict(canvas_cfg or {})
        if "type" not in self.cfg: self.cfg["type"] = "pdf"
        self.win = tk.Toplevel(root); self.win.title("Canvas Settings"); self.win.transient(root); self.win.grab_set()

        frm = ttk.Frame(self.win, padding=12); frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Canvas Type").grid(row=0, column=0, sticky="w")
        self.var_type = tk.StringVar(value=self.cfg.get("type","pdf"))
        cmb = ttk.Combobox(frm, textvariable=self.var_type, values=["pdf","image","blank"], state="readonly"); cmb.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        cmb.bind("<<ComboboxSelected>>", lambda e: self._on_type())

        ttk.Label(frm, text="Path (pdf/image)").grid(row=1, column=0, sticky="w")
        self.var_path = tk.StringVar(value=self.cfg.get("path",""))
        row1 = ttk.Frame(frm); row1.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        self.ent_path = ttk.Entry(row1, textvariable=self.var_path); self.ent_path.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row1, text="Browse…", command=self._browse).pack(side=tk.LEFT, padx=4)

        ttk.Label(frm, text="PDF page index").grid(row=2, column=0, sticky="w")
        self.var_page = tk.IntVar(value=int(self.cfg.get("page",0)))
        ttk.Entry(frm, textvariable=self.var_page).grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="DPI (pdf/image)").grid(row=3, column=0, sticky="w")
        self.var_dpi = tk.IntVar(value=int(self.cfg.get("dpi",144)))
        ttk.Entry(frm, textvariable=self.var_dpi).grid(row=3, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Blank size WxH").grid(row=4, column=0, sticky="w")
        self.var_size = tk.StringVar(value="1200,800")
        if "size" in self.cfg: self.var_size.set(f"{self.cfg['size'][0]},{self.cfg['size'][1]}")
        ttk.Entry(frm, textvariable=self.var_size).grid(row=4, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Grid size (blank)").grid(row=5, column=0, sticky="w")
        self.var_grid = tk.IntVar(value=int(((self.cfg.get("grid") or {}).get("size", 16))))
        ttk.Entry(frm, textvariable=self.var_grid).grid(row=5, column=1, sticky="ew", padx=6, pady=4)

        btns = ttk.Frame(frm); btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="OK", command=self._ok).pack(side=tk.RIGHT)

        frm.columnconfigure(1, weight=1); self._on_type()

    def _on_type(self):
        t = self.var_type.get()
        en = ("normal" if t in ("pdf","image") else "disabled")
        for w in self.ent_path.master.winfo_children():
            try: w.configure(state=en)
            except: pass

    def _browse(self):
        from tkinter import filedialog
        t = self.var_type.get()
        if t == "pdf":
            p = filedialog.askopenfilename(title="Choose PDF", filetypes=[("PDF","*.pdf")])
        elif t == "image":
            p = filedialog.askopenfilename(title="Choose Image", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp")])
        else:
            p = ""
        if p: self.var_path.set(p)

    def _ok(self):
        t = self.var_type.get()
        out = {"type": t}
        if t in ("pdf","image"):
            out["path"] = self.var_path.get().strip()
            out["dpi"] = int(self.var_dpi.get())
        if t == "pdf":
            out["page"] = int(self.var_page.get())
        if t == "blank":
            try:
                w,h = [int(v.strip()) for v in self.var_size.get().split(",")]
            except:
                w,h = 1200,800
            out["size"] = [w,h]
            out["grid"] = {"enabled": True, "size": int(self.var_grid.get())}
        self.result = out; self.win.destroy()

    def _cancel(self):
        self.result = None; self.win.destroy()
