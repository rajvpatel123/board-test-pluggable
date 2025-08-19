from typing import Optional, Dict, Any
from pdf2image import convert_from_path
from PIL import Image, ImageDraw

def render_background(canvas_cfg: Dict[str, Any]) -> Optional[Image.Image]:
    ctype = (canvas_cfg or {}).get("type", "pdf")
    if ctype == "pdf":
        path = canvas_cfg.get("path")
        page = int(canvas_cfg.get("page", 0))
        dpi = int(canvas_cfg.get("dpi", 144))
        try:
            pages = convert_from_path(path, dpi=dpi, first_page=page+1, last_page=page+1, fmt='png')
            if not pages:
                return None
            return pages[0].convert("RGB")
        except Exception as e:
            print(f"[renderer] PDF render failed: {e}")
            return None
    elif ctype == "image":
        path = canvas_cfg.get("path")
        try:
            img = Image.open(path).convert("RGB")
            return img
        except Exception as e:
            print(f"[renderer] Image load failed: {e}")
            return None
    elif ctype == "blank":
        size = canvas_cfg.get("size") or [1200, 800]
        w, h = int(size[0]), int(size[1])
        img = Image.new("RGB", (w, h), "white")
        grid = (canvas_cfg.get("grid") or {})
        if grid.get("enabled", True):
            g = int(grid.get("size", 16))
            draw = ImageDraw.Draw(img)
            for x in range(0, w, g):
                draw.line([(x,0),(x,h)], fill="#eeeeee")
            for y in range(0, h, g):
                draw.line([(0,y),(w,y)], fill="#eeeeee")
        return img
    else:
        return None
