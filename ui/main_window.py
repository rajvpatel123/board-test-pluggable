import os, json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk
import pandas as pd
#Simport fitz  # PyMuPDF

from core.pdf_renderer import render_background
from core import db
from ui.layout_picker import LayoutPicker
from ui.canvas_dialog import CanvasDialog
from ui.history_compare import HistoryCompareWindow

APP_TITLE = "Board Tester"

MODE_ENTRY = "entry"
MODE_LAYOUT = "layout"



from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QScrollArea, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Layout Viewer")
        self.layout = QVBoxLayout(self)

        # Load button
        self.load_button = QPushButton("Load PDF Layout")
        self.load_button.clicked.connect(self.load_pdf)
        self.layout.addWidget(self.load_button)

        # Scroll area and image label
        self.scroll_area = QScrollArea()
        self.image_label = QLabel("No PDF loaded.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)

            # Convert to QImage
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)

            # Set image
            self.image_label.setPixmap(pixmap)
            self.image_label.adjustSize()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF:\n{e}")


class BoardTesterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x900")
        self.minsize(900, 650)

        self.mode = MODE_ENTRY
        self.layout = {}
        self.layout_path = None
        self.bg_image = None
        self.bg_tk = None
        self.canvas = None

        self.field_vars = {}     # id -> variable/widget state
        self.field_entries = {}  # id -> widget(s). For number: dict(entry, unit)
        self.shape_items = {}    # id -> {"rect_id": int, "label_id": int}
        self.selected_field_id = None
        self.dragging = False
        self.drag_offset = (0, 0)
        self.adding_field = False
        self.new_field_start = None
        self.temp_rect_id = None

        db.init_db()
        self._build_toolbar()
        self._build_canvas()

        self.after(200, self._ask_layout_on_launch)

        self.bind("<Delete>", self._delete_selected_field)
        
    def _ask_layout_on_launch(self):
        base_dir = os.path.dirname(os.path.abspath(_file_))
        layouts_dir = os.path.join(base_dir, "data", "layouts")
        
        path = filedialog.askopenfilename(
            title="Open Layout JSON", 
            initialdir = layouts_dir if os.path.isdr(layouts_dir) else base_dir, 
            filetypes=[("JSON Files", "*.json")]
        )

        if not path:
            return 
            
        try:
            self.load_layout(path)
            
        except Exception as e:
            messagebox.showerror("Open Layout", f"Failed to load layout:\n{e}")
    

    def _build_toolbar(self):
        tb = ttk.Frame(self); tb.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)
        ttk.Button(tb, text="Layouts", command=self.pick_layout).pack(side=tk.LEFT, padx=4)
        ttk.Button(tb, text="Open Layout (File…)", command=self.open_layout_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(tb, text="Save Layout As…", command=self.save_layout_as_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(tb, text="Canvas…", command=self.edit_canvas).pack(side=tk.LEFT, padx=4)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.mode_var = tk.StringVar(value=self.mode)
        ttk.Radiobutton(tb, text="Entry Mode", variable=self.mode_var, value=MODE_ENTRY, command=self.set_entry_mode).pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(tb, text="Layout Mode", variable=self.mode_var, value=MODE_LAYOUT, command=self.set_layout_mode).pack(side=tk.LEFT, padx=4)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        self.add_field_btn = ttk.Button(tb, text="Add Field", command=self.begin_add_field, state=tk.DISABLED); self.add_field_btn.pack(side=tk.LEFT, padx=4)
        self.edit_field_btn = ttk.Button(tb, text="Edit Field", command=self.edit_selected_field, state=tk.DISABLED); self.edit_field_btn.pack(side=tk.LEFT, padx=4)
        self.delete_field_btn = ttk.Button(tb, text="Delete Field", command=self.delete_selected_field, state=tk.DISABLED); self.delete_field_btn.pack(side=tk.LEFT, padx=4)

        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self.log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tb, text="Log to SQLite", variable=self.log_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(tb, text="Export to Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=4)
        ttk.Button(tb, text="History/Compare", command=self.open_history_compare).pack(side=tk.LEFT, padx=4)

    def _build_canvas(self):
        frm = ttk.Frame(self); frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(frm, bg="#2a2a2a", cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)

    # ----- Layout ops -----
    def pick_layout(self):
        dlg = LayoutPicker(self, layouts_dir=os.path.join("data","layouts"))
        self.wait_window(dlg)
        if dlg.result: self.load_layout(dlg.result)

    def open_layout_dialog(self):
        path = filedialog.askopenfilename(title="Open Layout JSON", filetypes=[("JSON Files","*.json")], initialdir=os.path.join("data","layouts"))
        if path: self.load_layout(path)

    def save_layout_as_dialog(self):
        if not self.layout:
            messagebox.showinfo("Save Layout", "Nothing to save — load or create a layout first."); return
        if "canvas" not in self.layout:
            self.layout["canvas"] = {"type":"blank","size":[1200,800],"grid":{"enabled":True,"size":20}}
        path = filedialog.asksaveasfilename(title="Save Layout JSON", defaultextension=".json", initialdir=os.path.join("data","layouts"), filetypes=[("JSON Files","*.json")])
        if not path: return
        try:
            with open(path,"w") as f: json.dump(self.layout, f, indent=2)
            self.layout_path = path
            messagebox.showinfo("Save Layout", f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save Layout", f"Failed to save layout:\n{e}")

    def edit_canvas(self):
        current = self.layout.get("canvas") or {"type":"blank","size":[1200,800],"grid":{"enabled":True,"size":20}}
        dlg = CanvasDialog(self, current); self.wait_window(dlg.win)
        if dlg.result:
            self.layout["canvas"] = dlg.result
            self._rebuild_canvas_for_mode()

    def load_layout(self, layout_path: str):
        try:
            with open(layout_path,"r") as f: layout = json.load(f)
        except Exception as e:
            messagebox.showerror("Layout", f"Failed to load layout JSON:\n{e}"); return

        canvas_cfg = layout.get("canvas") or {"type":"pdf", **(layout.get("pdf") or {})}
        if canvas_cfg.get("type") in ("pdf","image"):
            p = canvas_cfg.get("path")
            if not p or not os.path.exists(p):
                messagebox.showerror("Layout", f"File not found:\n{p}"); return

        img = render_background(canvas_cfg)
        if img is None:
            messagebox.showerror("Canvas", "Failed to render background (check Poppler for PDF)."); return

        self.layout = layout; self.layout_path = layout_path
        self.bg_image = img; self.bg_tk = ImageTk.PhotoImage(self.bg_image)
        self._rebuild_canvas_for_mode()
        self.title(f"{APP_TITLE} — {os.path.basename(layout_path)}")

    # ----- Mode switching -----
    def set_entry_mode(self):
        self.mode = MODE_ENTRY; self.mode_var.set(self.mode)
        self.add_field_btn.configure(state=tk.DISABLED)
        self.edit_field_btn.configure(state=tk.DISABLED)
        self.delete_field_btn.configure(state=tk.DISABLED)
        self.adding_field = False
        self._rebuild_canvas_for_mode()

    def set_layout_mode(self):
        self.mode = MODE_LAYOUT; self.mode_var.set(self.mode)
        self.add_field_btn.configure(state=tk.NORMAL)
        self.edit_field_btn.configure(state=tk.NORMAL if self.selected_field_id else tk.DISABLED)
        self.delete_field_btn.configure(state=tk.NORMAL if self.selected_field_id else tk.DISABLED)
        self._rebuild_canvas_for_mode()

    def _rebuild_canvas_for_mode(self):
        self.canvas.delete("all")
        self._clear_entry_widgets()
        self.shape_items.clear()
        self.selected_field_id = None
        if self.bg_tk:
            self.canvas.create_image(0, 0, image=self.bg_tk, anchor="nw")
            self.canvas.config(scrollregion=(0,0,self.bg_image.width, self.bg_image.height))
        if self.mode == MODE_LAYOUT:
            self._build_layout_mode_shapes()
        else:
            self._build_entry_mode_widgets()

    # ----- Entry mode widgets -----
    def _build_entry_mode_widgets(self):
        self.field_vars.clear(); self.field_entries.clear()
        for field in self.layout.get("fields", []):
            fid = field.get("id")
            x,y,w,h = self._field_rect(field)
            
            inp = field.get("input")
            if not inp:
                legacy_units = field.get("units")
                legacy_unit = field.get("default_unit", field.get("unit",""))
                if isinstance(legacy_units, str):
                    legacy_units = [legacy_units] if legacy_units else []
                inp = {
                    "type": "number", 
                    "units": legacy_units or ([legacy_unit] if legacy_unit else []), 
                    "default_unit": legacy_unit
                    }
            itype = (inp.get("type") or "number").lower()

            if itype == "toggle":
                var = tk.BooleanVar(value=False)
                cb = ttk.Checkbutton(self.canvas, variable=var)
                self.canvas.create_window(x, y, window=cb, anchor="nw", width=w, height=h)
                self.field_vars[fid] = var
                self.field_entries[fid] = cb

            elif itype == "enum":
                var = tk.StringVar(value=(inp.get("default") or (inp.get("options") or [""])[0]))
                combo = ttk.Combobox(self.canvas, textvariable=var, values=inp.get("options") or [], state="readonly", width=max(6, min(30, w//8)))
                self.canvas.create_window(x, y, window=combo, anchor="nw", width=w, height=h)
                self.field_vars[fid] = var; self.field_entries[fid] = combo

            elif itype == "text":
                var = tk.StringVar()
                ent = ttk.Entry(self.canvas, textvariable=var, width=max(6, min(30, w//8)))
                self.canvas.create_window(x, y, window=ent, anchor="nw", width=w, height=h)
                self.field_vars[fid] = var; self.field_entries[fid] = ent

            else: # number
                wrapper = ttk.Frame(self.canvas)
                var = tk.StringVar()
                ent = ttk.Entry(wrapper, textvariable=var, width=max(6, min(24, w//10)))
                ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
                units = inp.get("units") or []
                unit_var = tk.StringVar(value=inp.get("default_unit") or (units[0] if units else ""))
                if units:
                    cmb = ttk.Combobox(wrapper, textvariable=unit_var, values=units, state="readonly", width=6)
                    cmb.pack(side=tk.LEFT, padx=4)
                else:
                    cmb = None
                self.canvas.create_window(x, y, window=wrapper, anchor="nw", width=w, height=h)
                self.field_vars[fid] = {"value": var, "unit": unit_var}
                self.field_entries[fid] = {"entry": ent, "unit": cmb}
                # validation hook
                def make_cb(fid=fid, field=field):
                    return lambda *args: self._apply_validation(fid, field)
                var.trace_add("write", make_cb())

    def _apply_validation(self, fid, field):
        inp = field.get("input") or {}
        itype = (inp.get("type") or "number").lower()
        if itype != "number": return
        wdict = self.field_entries.get(fid) or {}
        ent = wdict.get("entry")
        if not ent: return
        vdef = (inp.get("validation") or {})
        s = (self.field_vars[fid]["value"]).get().strip()
        try:
            val = float(s) if s not in ("","-",".") else None
        except:
            ent.configure(background="#FFCDD2"); return  # invalid format
        if val is None:
            ent.configure(background="white"); return
        target = vdef.get("target")
        lpct = vdef.get("lower_pct"); upct = vdef.get("upper_pct")
        labs = vdef.get("lower_abs"); uabs = vdef.get("upper_abs")
        lo = hi = None
        if target is not None and (lpct is not None or upct is not None):
            lo = target * (1 + (lpct or 0)/100.0)
            hi = target * (1 + (upct or 0)/100.0)
        if labs is not None or uabs is not None:
            lo = (lo if lo is not None else (target if target is not None else val)) + (labs or 0)
            hi = (hi if hi is not None else (target if target is not None else val)) + (uabs or 0)
        if lo is None and hi is None:
            ent.configure(background="white"); return
        if lo <= val <= hi:
            ent.configure(background="#C8E6C9")  # green pass
        else:
            ent.configure(background="#FFECB3")  # yellow warn/fail

    def _clear_entry_widgets(self):
        for wid in self.field_entries.values():
            try:
                if isinstance(wid, dict):
                    if "entry" in wid and hasattr(wid["entry"], "destroy"): wid["entry"].destroy()
                    if "unit" in wid and wid["unit"] and hasattr(wid["unit"], "destroy"): wid["unit"].destroy()
                else:
                    wid.destroy()
            except Exception: pass
        self.field_entries.clear(); self.field_vars.clear()

    # ----- Export / Log -----
    def export_to_excel(self):
        if self.mode != MODE_ENTRY:
            messagebox.showinfo("Export", "Switch to Entry Mode to export values."); return
        if not self.layout: messagebox.showinfo("Export", "Load a layout first."); return

        operator = simple_prompt(self, "Operator")  
        if operator is None: 
            return
        lot = simple_prompt(self, "Lot")           
        if lot is None: 
            return
        dut = simple_prompt(self, "DUT ID")        
        if dut is None: 
            return
        notes = simple_prompt(self, "Notes (optional)") or ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S"); run_id = f"{ts}_{self.layout.get('board_name','Board')}"

        suggested = f"run_{run_id}.xlsx"
        out_path = filedialog.asksaveasfilename(title="Save Excel", defaultextension=".xlsx", initialfile=suggested, filetypes=[("Excel","*.xlsx")])
        if not out_path: return

        rows = []
        for field in self.layout.get("fields", []):
            fid = field.get("id"); label = field.get("label", fid); ctype = field.get("component_type","")
            
            inp = field.get("input")
            if not inp:
                legacy_units = field.get("units")
                legacy_unit = field.get("default_unit", field.get("unit",""))
                if isinstance(legacy_units, str):
                    legacy_units = [legacy_units] if legacy_units else []
                inp = {
                    "type": "number", 
                    "units": legacy_units or ([legacy_unit] if legacy_unit else []), 
                    "default_unit": legacy_unit
                    }
            itype = (inp.get("type") or "number").lower()
            
            
            unit = ""; value = ""
            fv = self.field_vars.get(fid)
            if itype == "toggle":
                true_label = (inp.get("labels") or {}).get("true","True")
                false_label = (inp.get("labels") or {}).get("false","False")
                value = true_label if bool(fv.get()) else false_label
            elif itype == "enum":
                value = fv.get().strip()
            elif itype == "text":
                value = fv.get().strip()
            else: # number
                value = (fv["value"]).get().strip()
                unit = (fv["unit"]).get().strip() if fv.get("unit") else (inp.get("default_unit") or "")
            rows.append({"timestamp": ts, "operator": operator, "lot": lot, "dut_id": dut,
                         "field_id": fid, "label": label, "component_type": ctype,
                         "value": value, "unit": unit})

        try:
            pd.DataFrame(rows).to_excel(out_path, index=False)
        except Exception as e:
            messagebox.showerror("Export", f"Failed to save Excel:\n{e}"); return

        if self.log_var.get():
            try:
                meta = {"run_id": run_id, "timestamp": ts, "operator": operator, "lot": lot, "dut_id": dut,
                        "board_name": self.layout.get("board_name",""), "layout_file": self.layout_path or "", "notes": notes}
                db.insert_run(meta, rows)
            except Exception as e:
                messagebox.showwarning("SQLite", f"Saved Excel but failed to log to SQLite:\n{e}")
        messagebox.showinfo("Export", f"Saved: {out_path}\nRun ID: {run_id}")

    # ----- Layout mode -----
    def _build_layout_mode_shapes(self):
        for field in self.layout.get("fields", []):
            fid = field.get("id"); x,y,w,h = self._field_rect(field)
            rect_id = self.canvas.create_rectangle(x, y, x+w, y+h, outline="#00BCD4", width=2)
            label = field.get("label", fid)
            label_id = self.canvas.create_text(x+4, y-8, text=label, anchor="nw", fill="#00BCD4", font=("Arial", 10, "bold"))
            self.shape_items[fid] = {"rect_id": rect_id, "label_id": label_id}

    def begin_add_field(self):
        if self.mode != MODE_LAYOUT: return
        self.adding_field = True; self.selected_field_id = None; self._update_selection_visuals()

    def _on_canvas_click(self, event):
        if self.mode != MODE_LAYOUT: return
        x,y = event.x, event.y
        if self.adding_field:
            self.new_field_start = (x,y)
            self.temp_rect_id = self.canvas.create_rectangle(x,y,x,y, outline="#4CAF50", width=2, dash=(4,2))
            return
        clicked = self._find_field_at(x,y)
        if clicked:
            self.selected_field_id = clicked; self.dragging = True
            f = self._get_field_by_id(clicked); fx,fy,fw,fh = self._field_rect(f)
            self.drag_offset = (x-fx, y-fy)
            self._update_selection_visuals()
        else:
            self.selected_field_id = None; self._update_selection_visuals()

    def _on_canvas_drag(self, event):
        if self.mode != MODE_LAYOUT: return
        x,y = event.x, event.y
        if self.adding_field and self.temp_rect_id and self.new_field_start:
            x0,y0 = self.new_field_start; self.canvas.coords(self.temp_rect_id, x0,y0,x,y); return
        if self.dragging and self.selected_field_id:
            f = self._get_field_by_id(self.selected_field_id); fx,fy,fw,fh = self._field_rect(f)
            nx,ny = max(0,x-self.drag_offset[0]), max(0,y-self.drag_offset[1])
            it = self.shape_items[self.selected_field_id]
            self.canvas.coords(it["rect_id"], nx,ny,nx+fw,ny+fh)
            self.canvas.coords(it["label_id"], nx+4, ny-8)
            self._set_field_rect(f, nx,ny,fw,fh)

    def _on_canvas_release(self, event):
        if self.mode != MODE_LAYOUT: return
        if self.adding_field and self.temp_rect_id and self.new_field_start:
            x0,y0 = self.new_field_start; x1,y1 = event.x, event.y
            x,y = min(x0,x1), min(y0,y1); w,h = abs(x1-x0), abs(y1-y0)
            self.canvas.delete(self.temp_rect_id); self.temp_rect_id=None; self.new_field_start=None; self.adding_field=False
            if w<10 or h<10: return
            fid = simple_prompt(self, "Field ID (e.g., R1)"); 
            if not fid: return
            label = simple_prompt(self, "Label (optional)") or fid
            if any(f.get("id")==fid for f in self.layout.get("fields", [])):
                messagebox.showerror("Add Field", f"Field ID '{fid}' already exists."); return
            new_field = {"id": fid, "label": label, "position": {"x": float(x), "y": float(y), "w": float(w), "h": float(h)}, "input": {"type":"number","units":[""],"default_unit":""}}
            self.layout.setdefault("fields", []).append(new_field)
            rect_id = self.canvas.create_rectangle(x,y,x+w,y+h, outline="#00BCD4", width=2)
            label_id = self.canvas.create_text(x+4, y-8, text=label, anchor="nw", fill="#00BCD4", font=("Arial", 10, "bold"))
            self.shape_items[fid] = {"rect_id": rect_id, "label_id": label_id}
            self.selected_field_id = fid; self._update_selection_visuals(); return
        self.dragging = False

    def _on_canvas_double_click(self, event):
        if self.mode != MODE_LAYOUT: return
        fid = self._find_field_at(event.x, event.y)
        if not fid: return
        self.selected_field_id = fid; self._update_selection_visuals(); self.edit_selected_field()

    def edit_selected_field(self):
        if self.mode != MODE_LAYOUT or not self.selected_field_id: return
        f = self._get_field_by_id(self.selected_field_id)  
        if not f:
            return
        dlg = FieldDialog(self, f, existing_ids=[fld["id"] for fld in self.layout.get("fields", [])]); self.wait_window(dlg.win)
        if dlg.result is None: 
            return
        new_def = dlg.result; old_id = f.get("id"); new_id = new_def.get("id")
        if new_id != old_id and any(ff["id"]==new_id for ff in self.layout["fields"]):
            messagebox.showerror("Edit Field", f"Field ID '{new_id}' already exists."); return
        f.update(new_def)
        if new_id != old_id:
            self.shape_items[new_id] = self.shape_items.pop(old_id)
            if self.selected_field_id == old_id: self.selected_field_id = new_id
        x,y,w,h = self._field_rect(f); it = self.shape_items[self.selected_field_id]
        self.canvas.coords(it["rect_id"], x,y,x+w,y+h)
        self.canvas.itemconfigure(it["label_id"], text=f.get("label", new_id))
        self.canvas.coords(it["label_id"], x+4, y-8)
        self._update_selection_visuals()

    def delete_selected_field(self):
        if self.mode != MODE_LAYOUT or not self.selected_field_id: return
        self.delete_field_by_id(self.selected_field_id)

    def _delete_selected_field(self, event=None):
        if self.mode == MODE_LAYOUT and self.selected_field_id: self.delete_field_by_id(self.selected_field_id)

    def delete_field_by_id(self, fid: str):
        self.layout["fields"] = [f for f in self.layout.get("fields", []) if f.get("id") != fid]
        it = self.shape_items.pop(fid, None)
        if it:
            try: self.canvas.delete(it["rect_id"]); self.canvas.delete(it["label_id"])
            except Exception: pass
        self.selected_field_id=None; self._update_selection_visuals()

    def _update_selection_visuals(self):
        for fid, it in self.shape_items.items():
            color = "#FF9800" if fid == self.selected_field_id else "#00BCD4"
            self.canvas.itemconfigure(it["rect_id"], outline=color, width=3 if fid == self.selected_field_id else 2)
        en = tk.NORMAL if self.selected_field_id else tk.DISABLED
        self.edit_field_btn.configure(state=en); self.delete_field_btn.configure(state=en)

    # ----- helpers -----
    def _find_field_at(self, x,y):
        for f in reversed(self.layout.get("fields", [])):
            fx,fy,fw,fh = self._field_rect(f)
            if fx<=x<=fx+fw and fy<=y<=fy+fh: return f.get("id")
        return None

    def _get_field_by_id(self, fid):
        for f in self.layout.get("fields", []):
            if f.get("id")==fid: return f
        return None

    def _field_rect(self, f):
        pos = f.get("position", {})
        x=float(pos.get("x", f.get("x", 0))); y=float(pos.get("y", f.get("y", 0)))
        w=float(pos.get("w", f.get("w", 100))); h=float(pos.get("h", f.get("h", 24)))
        return x,y,w,h

    def _set_field_rect(self, f, x,y,w,h):
        f["position"] = {"x": float(x), "y": float(y), "w": float(w), "h": float(h)}

    def open_history_compare(self):
        try: HistoryCompareWindow(self)
        except Exception as e: messagebox.showerror("History/Compare", f"Failed to open window:\n{e}")

# ----- Simple dialogs -----
def simple_prompt(root, label):
    win = tk.Toplevel(root); win.title(label); win.transient(root); win.grab_set()
    frm = ttk.Frame(win, padding=12); frm.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frm, text=label + ":").pack(anchor="w")
    var = tk.StringVar(); ent = ttk.Entry(frm, textvariable=var); ent.pack(fill=tk.X, pady=6); ent.focus_set()
    out = {"value": None}
    def ok(): out["value"] = var.get().strip(); win.destroy()
    def cancel(): out["value"] = None; win.destroy()
    btns = ttk.Frame(frm); btns.pack(anchor="e"); ttk.Button(btns, text="Cancel", command=cancel).pack(side=tk.RIGHT, padx=4); ttk.Button(btns, text="OK", command=ok).pack(side=tk.RIGHT)
    root.wait_window(win); return out["value"]

class FieldDialog:
    def __init__(self, root, field_def, existing_ids):
        self.root = root; self.field = dict(field_def); self.existing_ids = set(existing_ids); self.result=None
        self.win = tk.Toplevel(root); self.win.title("Field Properties"); self.win.transient(root); self.win.grab_set()
        frm = ttk.Frame(self.win, padding=12); frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="ID").grid(row=0, column=0, sticky="w")
        self.var_id = tk.StringVar(value=self.field.get("id","")); ttk.Entry(frm, textvariable=self.var_id).grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Label").grid(row=1, column=0, sticky="w")
        self.var_label = tk.StringVar(value=self.field.get("label","")); ttk.Entry(frm, textvariable=self.var_label).grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Component type").grid(row=2, column=0, sticky="w")
        self.var_type = tk.StringVar(value=self.field.get("component_type","")); ttk.Entry(frm, textvariable=self.var_type).grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Input Type").grid(row=3, column=0, sticky="w")
        self.var_input_type = tk.StringVar(value=(self.field.get("input") or {}).get("type","number"))
        ttk.Combobox(frm, textvariable=self.var_input_type, values=["number","text","toggle","enum"], state="readonly").grid(row=3, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Units (comma) [number]").grid(row=4, column=0, sticky="w")
        units = ",".join((self.field.get("input") or {}).get("units", [])); self.var_units = tk.StringVar(value=units)
        ttk.Entry(frm, textvariable=self.var_units).grid(row=4, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Default unit [number]").grid(row=5, column=0, sticky="w")
        self.var_default_unit = tk.StringVar(value=(self.field.get("input") or {}).get("default_unit",""))
        ttk.Entry(frm, textvariable=self.var_default_unit).grid(row=5, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Validation (target,lower_pct,upper_pct,lower_abs,upper_abs) [number]").grid(row=6, column=0, columnspan=1, sticky="w")
        self.var_valid = tk.StringVar(value=self._valid_str())
        ttk.Entry(frm, textvariable=self.var_valid).grid(row=6, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(frm, text="Enum options (comma) / Toggle labels true|false").grid(row=7, column=0, sticky="w")
        self.var_extras = tk.StringVar(value=self._extras_str())
        ttk.Entry(frm, textvariable=self.var_extras).grid(row=7, column=1, sticky="ew", padx=6, pady=4)

        x,y,w,h = root._field_rect(self.field)
        ttk.Label(frm, text="Position (x,y,w,h)").grid(row=8, column=0, sticky="w")
        self.var_pos = tk.StringVar(value=f"{int(x)},{int(y)},{int(w)},{int(h)}"); ttk.Entry(frm, textvariable=self.var_pos, state="disabled").grid(row=8, column=1, sticky="ew", padx=6, pady=4)

        btns = ttk.Frame(frm); btns.grid(row=9, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=4); ttk.Button(btns, text="OK", command=self._ok).pack(side=tk.RIGHT)
        frm.columnconfigure(1, weight=1)

    def _valid_str(self):
        v = (self.field.get("input") or {}).get("validation") or {}
        parts = []
        for k in ["target","lower_pct","upper_pct","lower_abs","upper_abs"]:
            if k in v and v[k] is not None: parts.append(str(v[k]))
            else: parts.append("")
        return ",".join(parts)

    def _extras_str(self):
        it = (self.field.get("input") or {}).get("type","number")
        if it == "enum":
            return ",".join((self.field.get("input") or {}).get("options", []))
        if it == "toggle":
            labels = (self.field.get("input") or {}).get("labels") or {}
            return f"{labels.get('true','True')}|{labels.get('false','False')}"
        return ""

    def _ok(self):
        fid = self.var_id.get().strip()
        if not fid:
            messagebox.showerror("Field", "ID is required."); return
        label = self.var_label.get().strip() or fid
        ctype = self.var_type.get().strip()

        out = dict(self.field)
        out["id"] = fid; out["label"] = label; out["component_type"] = ctype
        input_def = dict(out.get("input") or {})
        itype = self.var_input_type.get()
        input_def["type"] = itype

        if itype == "number":
            units = [u.strip() for u in self.var_units.get().split(",") if u.strip()]
            input_def["units"] = units; input_def["default_unit"] = self.var_default_unit.get().strip()
            parts = [p.strip() for p in self.var_valid.get().split(",")]
            keys = ["target","lower_pct","upper_pct","lower_abs","upper_abs"]
            vd = {}
            for k,p in zip(keys, parts):
                if p != "":
                    try: vd[k] = float(p)
                    except: pass
            input_def["validation"] = vd
        else:
            input_def.pop("units", None); input_def.pop("default_unit", None); input_def.pop("validation", None)

        if itype == "enum":
            opts = [o.strip() for o in self.var_extras.get().split(",") if o.strip()]
            input_def["options"] = opts
        elif itype == "toggle":
            t = self.var_extras.get()
            if "|" in t:
                tlabel,flabel = t.split("|",1)
            else:
                tlabel,flabel = "True","False"
            input_def["labels"] = {"true": tlabel.strip(), "false": flabel.strip()}

        out["input"] = input_def
        self.result = out; self.win.destroy()

    def _cancel(self):
        self.result = None; self.win.destroy()
