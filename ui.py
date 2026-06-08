import os
import shutil
import threading
import io
import requests
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

# Set appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue") # cyan accents will be set manually

# Load theme configuration from config.json
from api import load_config
_theme = "cyan"
try:
    _theme = load_config().get("theme", "cyan").strip().lower()
except Exception:
    pass

# Theme Colors
BG_COLOR = "#0B0B0F"            # Deep movie theater black
PANEL_COLOR = "#15151C"         # Dark gray for cards and overlays
ACCENT_COLOR = "#00F0FF"        # Glowing cyan
ACCENT_HOVER = "#00B3C2"        # Darker cyan
TEXT_PRIMARY = "#FFFFFF"        # Pure white
TEXT_SECONDARY = "#A0A0AA"      # Muted gray
CARD_BORDER = "#1E1E26"         # Subtle card border
APP_VERSION = "1.0.0"


if _theme == "red":
    ACCENT_COLOR = "#EF4444"
    ACCENT_HOVER = "#DC2626"
elif _theme == "blue":
    ACCENT_COLOR = "#3B82F6"
    ACCENT_HOVER = "#2563EB"
elif _theme == "purple":
    ACCENT_COLOR = "#A855F7"
    ACCENT_HOVER = "#9333EA"
elif _theme == "black":
    BG_COLOR = "#050505"
    PANEL_COLOR = "#0D0D10"
    ACCENT_COLOR = "#E0E0E0"
    ACCENT_HOVER = "#A0A0A0"
    CARD_BORDER = "#1A1A22"

class CTkToolTip:
    """
    A beautiful modern hover tooltip for CustomTkinter widgets.
    """
    def __init__(self, widget, text, delay=350):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        
    def enter(self, event=None):
        self.schedule()
        
    def leave(self, event=None):
        self.unschedule()
        self.hide()
        
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)
        
    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
            
    def show(self):
        if not self.text:
            return
        
        try:
            x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2) - 80
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            
            self.tooltip_window = tk.Toplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True)
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            
            frame = ctk.CTkFrame(self.tooltip_window, fg_color="#1E1E26", border_width=1, border_color=ACCENT_COLOR, corner_radius=6)
            frame.pack()
            
            lbl = ctk.CTkLabel(frame, text=self.text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_PRIMARY, justify="left", padx=8, pady=4)
            lbl.pack()
        except Exception:
            pass
        
    def hide(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            self.tooltip_window = None

def get_fsk_colors(fsk_value: str):
    """
    Maps German FSK ratings to their official colors and text representation.
    Returns: (bg_color, text_color, label_text)
    """
    val = fsk_value.strip().lower()
    if val in ["0", "fsk 0", "fsk0"]:
        return ("#FFFFFF", "#15803d", "FSK 0") # White bg, green text
    elif val in ["6", "fsk 6", "fsk6"]:
        return ("#eab308", "#000000", "FSK 6") # Yellow bg, black text
    elif val in ["12", "fsk 12", "fsk12"]:
        return ("#15803d", "#FFFFFF", "FSK 12") # Green bg, white text
    elif val in ["16", "fsk 16", "fsk16"]:
        return ("#1d4ed8", "#FFFFFF", "FSK 16") # Blue bg, white text
    elif val in ["18", "fsk 18", "fsk18"]:
        return ("#b91c1c", "#FFFFFF", "FSK 18") # Red bg, white text
    else:
        return ("#4b5563", "#FFFFFF", f"FSK {fsk_value}" if fsk_value else "FSK k.A.")

def get_fsk_image(fsk_value: str, size: tuple = (35, 35)) -> Optional[ctk.CTkImage]:
    """
    Returns the CTkImage for the official FSK badge, or None if not available locally.
    """
    if not fsk_value:
        return None
    val = fsk_value.strip().lower().replace("fsk", "").replace("ab", "").strip()
    if val in ["0", "6", "12", "16", "18"]:
        path = f"assets/fsk/fsk{val}.png"
        if os.path.exists(path):
            try:
                pil_img = Image.open(path)
                return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            except Exception as e:
                print(f"Error loading FSK image from {path}: {e}")
    return None

def create_placeholder_image(size: tuple, title: str, img_type: str) -> Image.Image:
    """
    Generates a beautiful modern dark placeholder image dynamically using PIL.
    Ensures 100% offline robustness and error-free display.
    """
    width, height = size
    if img_type == "poster":
        # Create dark card background
        img = Image.new("RGB", size, color=PANEL_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Draw glowing accent border
        draw.rectangle([2, 2, width - 3, height - 3], outline=ACCENT_COLOR, width=2)
        
        # Draw stylized cinema reel
        cx, cy, r = width // 2, 70, 25
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT_COLOR, width=2)
        # Inner reel details
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=ACCENT_COLOR)
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            import math
            rad = math.radians(angle)
            px = cx + int((r - 6) * math.cos(rad))
            py = cy + int((r - 6) * math.sin(rad))
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill="#000000")
            
        # Draw Title text wrapped nicely
        try:
            font = ImageFont.truetype("arial.ttf", 13)
        except IOError:
            font = ImageFont.load_default()
            
        words = title.split()
        lines = []
        current_line = []
        for word in words:
            # Estimate text width
            test_line = " ".join(current_line + [word])
            if len(test_line) * 7.5 < (width - 20):
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        y_offset = 120
        for line in lines[:6]: # Limit lines to avoid overflow
            draw.text((width // 2, y_offset), line, fill=TEXT_PRIMARY, anchor="mm", font=font)
            y_offset += 18
            
        return img
    else:
        # Banner placeholder (widescreen)
        img = Image.new("RGB", size, color="#0E0E12")
        draw = ImageDraw.Draw(img)
        # Gradient effect or border
        draw.rectangle([2, 2, width - 3, height - 3], outline=ACCENT_COLOR, width=1)
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
            
        draw.text((width // 2, height // 2), title, fill=ACCENT_COLOR, anchor="mm", font=font)
        return img

IMAGE_CACHE = {}

def get_ctk_image(path: Optional[str], size: tuple, title: str, img_type: str) -> ctk.CTkImage:
    """
    Loads an image from the disk or falls back to a generated placeholder, caching results.
    Wraps it in a CTkImage for high-DPI scaling.
    """
    cache_key = (path, size)
    if path and cache_key in IMAGE_CACHE:
        return IMAGE_CACHE[cache_key]
        
    if path and os.path.exists(path):
        try:
            pil_img = Image.open(path)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")
            img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            IMAGE_CACHE[cache_key] = img
            return img
        except Exception as e:
            print(f"Error loading image from {path}: {e}")
            
    # Fallback if image path is empty or loading fails
    fallback_key = (None, size, title, img_type)
    if fallback_key in IMAGE_CACHE:
        return IMAGE_CACHE[fallback_key]
        
    fallback_pil = create_placeholder_image(size, title, img_type)
    img = ctk.CTkImage(light_image=fallback_pil, dark_image=fallback_pil, size=size)
    IMAGE_CACHE[fallback_key] = img
    return img


def bind_mouse_wheel_recursive(widget, scroll_frame):
    """
    Recursively binds mouse wheel events on a widget and all its children
    to trigger scrolling on the specified scroll_frame.
    """
    def on_mouse_wheel(event):
        try:
            if hasattr(scroll_frame, "_canvas"):
                scroll_frame._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    widget.bind("<MouseWheel>", on_mouse_wheel, add="+")
    for child in widget.winfo_children():
        bind_mouse_wheel_recursive(child, scroll_frame)


class MovieCard(ctk.CTkFrame):
    """
    A single movie card widget displayed inside the media gallery.
    Features a poster, title, year, FSK badge, and glowing cyan hover effect.
    """
    def __init__(self, parent, movie: dict, on_click_callback):
        super().__init__(parent, fg_color=PANEL_COLOR, border_width=2, border_color=CARD_BORDER, corner_radius=10)
        self.movie = movie
        self.on_click_callback = on_click_callback
        
        # Configure layout (fixed dimensions)
        self.configure(width=160, height=290)
        self.grid_propagate(False)
        
        # 1. Poster Image
        self.poster_img = get_ctk_image(self.movie.get("poster_pfad"), (150, 215), self.movie.get("titel"), "poster")
        self.image_label = ctk.CTkLabel(self, image=self.poster_img, text="")
        self.image_label.pack(pady=(5, 0), padx=5, fill="both", expand=True)
        
        # 2. Movie Title
        title_str = self.movie.get("titel", "Unbekannt")
        # Truncate title if extremely long
        if len(title_str) > 22:
            title_str = title_str[:19] + "..."
            
        self.title_label = ctk.CTkLabel(self, text=title_str, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_PRIMARY)
        self.title_label.pack(pady=(3, 0), padx=5, anchor="w")
        
        # 3. Footer Row (Year & FSK)
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", pady=(0, 6), padx=8)
        
        year_val = self.movie.get("jahr")
        year_str = str(year_val) if year_val else "k.A."
        self.year_label = ctk.CTkLabel(self.footer, text=year_str, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY)
        self.year_label.pack(side="left", anchor="w")
        
        fsk_val = self.movie.get("fsk", "k.A.")
        fsk_img = get_fsk_image(fsk_val, size=(22, 22))
        if fsk_img:
            self.fsk_badge = ctk.CTkLabel(self.footer, image=fsk_img, text="")
        else:
            fsk_bg, fsk_fg, fsk_lbl = get_fsk_colors(fsk_val)
            self.fsk_badge = ctk.CTkLabel(self.footer, text=fsk_lbl, font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                                          fg_color=fsk_bg, text_color=fsk_fg, corner_radius=4, width=42, height=18)
        self.fsk_badge.pack(side="right", anchor="e")
        
        # Bind clicks and hover events to all child widgets to absorb parent-child hover transitions
        for widget in [self, self.image_label, self.title_label, self.footer, self.year_label, self.fsk_badge]:
            widget.bind("<Button-1>", self._on_card_click)
            widget.bind("<Enter>", self._on_hover_enter)
            widget.bind("<Leave>", self._on_hover_leave)
        
    def _on_card_click(self, event):
        self.on_click_callback(self.movie["id"])
        
    def _on_hover_enter(self, event):
        if hasattr(self, "_hover_timer") and self._hover_timer:
            self.after_cancel(self._hover_timer)
            self._hover_timer = None
        self.configure(border_color=ACCENT_COLOR)
        
    def _on_hover_leave(self, event):
        if hasattr(self, "_hover_timer") and self._hover_timer:
            self.after_cancel(self._hover_timer)
        self._hover_timer = self.after(50, self._perform_hover_leave)

    def _perform_hover_leave(self):
        self.configure(border_color=CARD_BORDER)
        self._hover_timer = None


class OnlineMovieCard(ctk.CTkFrame):
    """
    A card widget for online TMDB suggestions.
    Displays poster (downloaded from URL), title, year, and a "+ Hinzufügen" overlay/button.
    """
    def __init__(self, parent, movie: dict, on_click_callback):
        super().__init__(parent, fg_color="#181822", border_width=2, border_color="#3A3A4A", corner_radius=10)
        self.movie = movie
        self.on_click_callback = on_click_callback
        
        self.configure(width=160, height=290)
        self.grid_propagate(False)
        
        # 1. Poster Image (Fetch online in thread or use placeholder, wrap in CTkImage)
        self.image_label = ctk.CTkLabel(self, text="Lade Poster...", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY)
        self.image_label.pack(pady=(5, 0), padx=5, fill="both", expand=True)
        
        # 2. Movie Title
        title_str = self.movie.get("titel", "Unbekannt")
        if len(title_str) > 22:
            title_str = title_str[:19] + "..."
            
        self.title_label = ctk.CTkLabel(self, text=title_str, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_PRIMARY)
        self.title_label.pack(pady=(3, 0), padx=5, anchor="w")
        
        # 3. Footer Row (Year & "+ Hinzufügen" button)
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", pady=(0, 6), padx=8)
        
        year_str = str(self.movie.get("jahr", "k.A."))
        self.year_label = ctk.CTkLabel(self.footer, text=year_str, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY)
        self.year_label.pack(side="left", anchor="w")
        
        self.btn_add = ctk.CTkLabel(self.footer, text="+ Import", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                                    fg_color="#A855F7", text_color="#FFFFFF", corner_radius=4, width=50, height=18)
        self.btn_add.pack(side="right", anchor="e")
        
        # Bind clicks and hover events to all child widgets to absorb parent-child hover transitions
        for widget in [self, self.image_label, self.title_label, self.footer, self.year_label, self.btn_add]:
            widget.bind("<Button-1>", self._on_card_click)
            widget.bind("<Enter>", self._on_hover_enter)
            widget.bind("<Leave>", self._on_hover_leave)
            
        # Start background poster download
        self._load_poster_async()
        
    def _load_poster_async(self):
        def load_thread():
            poster_path = self.movie.get("poster_path")
            if poster_path:
                try:
                    url = f"https://image.tmdb.org/t/p/w154{poster_path}"
                    import requests
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        pil_img = Image.open(io.BytesIO(resp.content))
                        self.after(0, lambda: self._apply_poster(pil_img))
                        return
                except Exception:
                    pass
            
            # Fallback placeholder
            self.after(0, self._apply_placeholder)
            
        import threading
        threading.Thread(target=load_thread, daemon=True).start()
        
    def _apply_poster(self, pil_img):
        try:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 215))
            self.image_label.configure(image=ctk_img, text="")
        except Exception:
            self._apply_placeholder()
            
    def _apply_placeholder(self):
        fallback_pil = create_placeholder_image((150, 215), self.movie.get("titel", ""), "poster")
        ctk_img = ctk.CTkImage(light_image=fallback_pil, dark_image=fallback_pil, size=(150, 215))
        self.image_label.configure(image=ctk_img, text="")
        
    def _on_card_click(self, event):
        self.on_click_callback(self.movie)
        
    def _on_hover_enter(self, event):
        if hasattr(self, "_hover_timer") and self._hover_timer:
            self.after_cancel(self._hover_timer)
            self._hover_timer = None
        self.configure(border_color="#A855F7")
        
    def _on_hover_leave(self, event):
        if hasattr(self, "_hover_timer") and self._hover_timer:
            self.after_cancel(self._hover_timer)
        self._hover_timer = self.after(50, self._perform_hover_leave)

    def _perform_hover_leave(self):
        self.configure(border_color="#3A3A4A")
        self._hover_timer = None


class LoadingOverlay(ctk.CTkFrame):
    """
    An overlay that prevents interaction and shows a loading spinner state.
    """
    def __init__(self, parent, message: str = "Lade Daten... Bitte warten."):
        super().__init__(parent, fg_color=BG_COLOR)
        
        self.container = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=12)
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.4, relheight=0.25)
        
        # Title/Loading label
        self.loading_label = ctk.CTkLabel(self.container, text=message, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.loading_label.pack(expand=True, pady=(20, 10))
        
        # Animated text simulator (typing dots)
        self.dots_count = 0
        self.original_message = message
        self.animate_dots()
        
    def animate_dots(self):
        if not self.winfo_exists():
            return
        self.dots_count = (self.dots_count + 1) % 4
        self.loading_label.configure(text=self.original_message + "." * self.dots_count)
        self.after(500, self.animate_dots)


class DetailOverlay(ctk.CTkFrame):
    """
    Detail Screen Overlay covering the main window view.
    Displays rich media detail hierarchy: banner, poster, core fields, cast, description, actions.
    """
    def __init__(self, parent, movie: dict, on_close_callback, on_delete_callback, on_edit_callback):
        super().__init__(parent, fg_color=BG_COLOR)
        self.movie = movie
        self.on_close_callback = on_close_callback
        self.on_delete_callback = on_delete_callback
        self.on_edit_callback = on_edit_callback
        
        # Main Modal Content Box
        self.content_card = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=16)
        self.content_card.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9)
        
        # Scrollable layout container inside the card
        self.scroll_container = ctk.CTkScrollableFrame(self.content_card, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        # 1. Back button (Semi-transparent floating button on the upper left)
        self.btn_back = ctk.CTkButton(self.content_card, text="← Zurück", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                      fg_color="#0F2D37", text_color=ACCENT_COLOR, border_color=ACCENT_COLOR, border_width=1,
                                      hover_color="#1B4B59", width=100, height=32, command=self.on_close_callback)
        self.btn_back.place(x=15, y=15)
        
        # 2. Movie Wallpaper/Banner
        self.banner_img = get_ctk_image(self.movie.get("banner_pfad"), (900, 280), self.movie.get("titel"), "banner")
        self.banner_label = ctk.CTkLabel(self.scroll_container, image=self.banner_img, text="")
        self.banner_label.pack(fill="x", pady=(0, 15))
        
        # 3. Content layout (Two columns: Left = Poster and Meta, Right = Core text and description)
        self.grid_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=10)
        self.grid_frame.columnconfigure(0, weight=1, minsize=260) # Left col
        self.grid_frame.columnconfigure(1, weight=2) # Right col
        
        # --- LEFT COLUMN ---
        self.left_col = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.left_col.grid(row=0, column=0, sticky="n", padx=(0, 20))
        
        # Poster (Overlaps view or sits high)
        self.detail_poster = get_ctk_image(self.movie.get("poster_pfad"), (200, 290), self.movie.get("titel"), "poster")
        self.poster_label = ctk.CTkLabel(self.left_col, image=self.detail_poster, text="")
        self.poster_label.pack(pady=(0, 15))
        
        # Action buttons frame under poster
        self.poster_actions = ctk.CTkFrame(self.left_col, fg_color="transparent")
        self.poster_actions.pack(fill="x", pady=(0, 15))
        
        self.btn_download_poster = ctk.CTkButton(self.poster_actions, text="↓ Poster-Download", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                                 fg_color="transparent", text_color=TEXT_PRIMARY, border_color=CARD_BORDER, border_width=1,
                                                 hover_color="#2A2A35", height=32, command=self._download_poster_clicked)
        self.btn_download_poster.pack(fill="x", pady=(0, 5), padx=5)
        
        self.btn_download_banner = ctk.CTkButton(self.poster_actions, text="↓ Banner-Download", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                                 fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, height=32,
                                                 command=self._download_banner_clicked)
        self.btn_download_banner.pack(fill="x", pady=(5, 0), padx=5)
        
        # Quick info panel under poster
        self.quick_info = ctk.CTkFrame(self.left_col, fg_color="#181822", border_width=1, border_color="#2E2E3A", corner_radius=8)
        self.quick_info.pack(fill="x", pady=5, padx=5)
        
        self.add_quick_info_row("Laufzeit:", f"{self.movie.get('laufzeit_min', 0)} Min.")
        self.add_quick_info_row("Produktionsland:", self.movie.get("produktionsland", "k.A."))
        self.add_quick_info_row("Filmreihe:", self.movie.get("filmreihe", "-") or "-")
        self.add_quick_info_row("Studio/Firma:", self.movie.get("produktionsfirma_studio", "k.A."))
        
        # --- RIGHT COLUMN ---
        self.right_col = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        self.right_col.grid(row=0, column=1, sticky="nsew")
        
        # Title and Year
        self.title_row = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.title_row.pack(fill="x", anchor="w")
        
        self.lbl_title = ctk.CTkLabel(self.title_row, text=self.movie.get("titel"), font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_title.pack(side="left")
        
        year_val = self.movie.get("jahr")
        year_text = f" ({year_val})" if year_val else ""
        self.lbl_year = ctk.CTkLabel(self.title_row, text=year_text, font=ctk.CTkFont(family="Segoe UI", size=22), text_color=TEXT_SECONDARY)
        self.lbl_year.pack(side="left", padx=5)
        
        # FSK and Genre Row
        self.meta_row = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.meta_row.pack(fill="x", anchor="w", pady=(5, 15))
        
        fsk_val = self.movie.get("fsk", "k.A.")
        fsk_img = get_fsk_image(fsk_val, size=(30, 30))
        if fsk_img:
            self.fsk_badge = ctk.CTkLabel(self.meta_row, image=fsk_img, text="")
        else:
            fsk_bg, fsk_fg, fsk_lbl = get_fsk_colors(fsk_val)
            self.fsk_badge = ctk.CTkLabel(self.meta_row, text=fsk_lbl, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                          fg_color=fsk_bg, text_color=fsk_fg, corner_radius=4, width=55, height=22)
        self.fsk_badge.pack(side="left")
        
        genre_str = self.movie.get("genre_richtung", "k.A.")
        self.lbl_genres = ctk.CTkLabel(self.meta_row, text=f"  |  {genre_str}", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_SECONDARY)
        self.lbl_genres.pack(side="left")
        
        # Regisseur
        self.lbl_director = ctk.CTkLabel(self.right_col, text=f"Regisseur: {self.movie.get('regisseur', 'k.A.')}",
                                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_director.pack(anchor="w", pady=(0, 10))
        
        # Description
        self.lbl_desc_title = ctk.CTkLabel(self.right_col, text="Handlung & Beschreibung", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_desc_title.pack(anchor="w", pady=(5, 2))
        
        desc_text = self.movie.get("handlung_beschreibung", "Keine Beschreibung.")
        self.txt_desc = ctk.CTkLabel(self.right_col, text=desc_text, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_PRIMARY, justify="left", wraplength=550)
        self.txt_desc.pack(anchor="w", pady=(0, 15))
        
        # Cast
        self.lbl_cast_title = ctk.CTkLabel(self.right_col, text="Schauspieler / Besetzung", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_cast_title.pack(anchor="w", pady=(5, 2))
        
        cast_text = self.movie.get("schauspieler_cast", "Keine Angaben.")
        self.txt_cast = ctk.CTkLabel(self.right_col, text=cast_text, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_PRIMARY, justify="left", wraplength=550)
        self.txt_cast.pack(anchor="w", pady=(0, 15))
        
        # Synchronsprecher
        self.lbl_sync_title = ctk.CTkLabel(self.right_col, text="Deutsche Synchronsprecher", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_sync_title.pack(anchor="w", pady=(5, 2))
        
        sync_text = self.movie.get("deutsche_synchronsprecher", "").strip()
        if not sync_text:
            sync_text = "Keine Angaben vorhanden. Klicken Sie unten auf 'Bearbeiten', um Synchronsprecher einzutragen."
            
        self.txt_sync = ctk.CTkLabel(self.right_col, text=sync_text, font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic" if not self.movie.get("deutsche_synchronsprecher") else "roman"),
                                     text_color=TEXT_PRIMARY, justify="left", wraplength=550)
        self.txt_sync.pack(anchor="w", pady=(0, 20))
        
        # Discord Embed Share Section
        self.lbl_discord_title = ctk.CTkLabel(self.right_col, text="Discord Share-Beschreibung", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#5865F2") # Discord Blue
        self.lbl_discord_title.pack(anchor="w", pady=(10, 2))
        
        # Discord container box
        self.discord_box = ctk.CTkFrame(self.right_col, fg_color="#2F3136", border_width=1, border_color="#202225", corner_radius=8)
        self.discord_box.pack(fill="x", pady=(5, 15))
        
        # Discord content layout: Left vertical colored strip, right info
        self.discord_strip = ctk.CTkFrame(self.discord_box, fg_color="#5865F2", width=4, corner_radius=0)
        self.discord_strip.pack(side="left", fill="y", padx=(0, 10))
        
        self.discord_content_frame = ctk.CTkFrame(self.discord_box, fg_color="transparent")
        self.discord_content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Generate Discord Text
        self.discord_text = self._generate_discord_text()
        
        self.lbl_discord_preview = ctk.CTkLabel(self.discord_content_frame, text=self.discord_text, font=ctk.CTkFont(family="Consolas", size=11), text_color="#DCDDDE", justify="left", wraplength=480)
        self.lbl_discord_preview.pack(anchor="w")
        
        # Copy Button
        self.btn_copy_discord = ctk.CTkButton(self.discord_content_frame, text="📋 Discord-Text kopieren", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                             fg_color="#5865F2", text_color="#FFFFFF", hover_color="#4752C4", height=28, command=self._copy_discord_clicked)
        self.btn_copy_discord.pack(anchor="e", pady=(8, 0))
        
        # 4. Action Row at the bottom of the card content
        self.action_row = ctk.CTkFrame(self.right_col, fg_color="transparent")
        self.action_row.pack(fill="x", anchor="w", pady=10)
        
        self.btn_edit = ctk.CTkButton(self.action_row, text="Bearbeiten", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                      fg_color="transparent", text_color=TEXT_PRIMARY, border_color=CARD_BORDER, border_width=1,
                                      hover_color="#2A2A35", width=120, height=35, command=self._edit_clicked)
        self.btn_edit.pack(side="left", padx=(0, 10))
        
        self.btn_delete = ctk.CTkButton(self.action_row, text="Löschen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                        fg_color="#ef4444", text_color="#FFFFFF", hover_color="#dc2626", width=120, height=35, command=self._delete_clicked)
        self.btn_delete.pack(side="left")
        
        # Enable recursive mouse wheel scrolling on all DetailOverlay components
        bind_mouse_wheel_recursive(self.scroll_container, self.scroll_container)
        
    def add_quick_info_row(self, label: str, val: str):
        row = ctk.CTkFrame(self.quick_info, fg_color="transparent")
        row.pack(fill="x", pady=4, padx=8)
        lbl_field = ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, width=110, anchor="w")
        lbl_field.pack(side="left")
        lbl_val = ctk.CTkLabel(row, text=val, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_PRIMARY, wraplength=130, justify="left", anchor="w")
        lbl_val.pack(side="left", fill="x", expand=True)

    def _edit_clicked(self):
        self.on_edit_callback(self.movie)
        
    def _delete_clicked(self):
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie den Film '{self.movie.get('titel')}' wirklich aus der Bibliothek löschen?"):
            self.on_delete_callback(self.movie["id"])

    def _download_banner_clicked(self):
        import shutil
        import re
        import os
        from tkinter import messagebox
        
        banner_pfad = self.movie.get("banner_pfad", "")
        if not banner_pfad:
            messagebox.showwarning("Nicht verfügbar", "Für diesen Film ist kein Banner-Bild vorhanden.")
            return
            
        if not os.path.exists(banner_pfad):
            messagebox.showwarning("Nicht verfügbar", f"Das Banner-Bild wurde lokal nicht gefunden.\nPfad: {banner_pfad}")
            return
            
        try:
            # Get Windows Desktop folder path safely
            desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop") if "USERPROFILE" in os.environ else os.path.expanduser("~/Desktop")
            
            # Create a clean filename from the movie title
            clean_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', self.movie.get("titel", "Banner"))
            clean_title = clean_title.replace(" ", "_")
            
            ext = os.path.splitext(banner_pfad)[1]
            if not ext:
                ext = ".jpg"
                
            dest_filename = f"{clean_title}_banner{ext}"
            dest_path = os.path.join(desktop_dir, dest_filename)
            
            # Copy file
            shutil.copy2(banner_pfad, dest_path)
            messagebox.showinfo("Erfolgreich", f"Das Filmbanner wurde auf Ihrem Desktop gespeichert als:\n\n{dest_filename}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern des Banners auf dem Desktop: {e}")

    def _download_poster_clicked(self):
        import shutil
        import re
        import os
        from tkinter import messagebox
        
        poster_pfad = self.movie.get("poster_pfad", "")
        if not poster_pfad:
            messagebox.showwarning("Nicht verfügbar", "Für diesen Film ist kein Poster-Bild vorhanden.")
            return
            
        if not os.path.exists(poster_pfad):
            messagebox.showwarning("Nicht verfügbar", f"Das Poster-Bild wurde lokal nicht gefunden.\nPfad: {poster_pfad}")
            return
            
        try:
            # Get Windows Desktop folder path safely
            desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop") if "USERPROFILE" in os.environ else os.path.expanduser("~/Desktop")
            
            # Create a clean filename from the movie title
            clean_title = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '', self.movie.get("titel", "Poster"))
            clean_title = clean_title.replace(" ", "_")
            
            ext = os.path.splitext(poster_pfad)[1]
            if not ext:
                ext = ".jpg"
                
            dest_filename = f"{clean_title}_poster{ext}"
            dest_path = os.path.join(desktop_dir, dest_filename)
            
            # Copy file
            shutil.copy2(poster_pfad, dest_path)
            messagebox.showinfo("Erfolgreich", f"Das Filmplakat wurde auf Ihrem Desktop gespeichert als:\n\n{dest_filename}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern des Plakats auf dem Desktop: {e}")

    def _generate_discord_text(self) -> str:
        import re
        titel = self.movie.get("titel", "Unbekannt")
        jahr = self.movie.get("jahr")
        jahr_str = f" ({jahr})" if jahr else ""
        genres = self.movie.get("genre_richtung", "k.A.")
        laufzeit = self.movie.get("laufzeit_min", 0)
        fsk = self.movie.get("fsk", "k.A.")
        regisseur = self.movie.get("regisseur", "k.A.")
        cast = self.movie.get("schauspieler_cast", "k.A.")
        if len(cast) > 120:
            cast = cast[:117] + "..."
        beschreibung = self.movie.get("handlung_beschreibung", "")
        if len(beschreibung) > 300:
            beschreibung = beschreibung[:297] + "..."
            
        discord_msg = (
            f"**🎬 CinePalast Film-Tipp: {titel}{jahr_str}**\n"
            f"> **Genre:** {genres} | **Laufzeit:** {laufzeit} Min. | **FSK:** ab {fsk}\n"
            f"> **Regisseur:** {regisseur}\n"
            f"> **Besetzung:** {cast}\n"
            f">\n"
            f"> 📝 **Handlung:**\n"
            f"> {beschreibung}\n"
            f">\n"
            f"> *Gesendet aus dem CinePalast Manager von Mannis Kinopalast*"
        )
        return discord_msg

    def _copy_discord_clicked(self):
        from tkinter import messagebox
        try:
            self.clipboard_clear()
            self.clipboard_append(self.discord_text)
            self.update() # Keep clipboard alive
            messagebox.showinfo("Kopiert", "Die Discord-Beschreibung wurde erfolgreich in Ihre Zwischenablage kopiert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Kopieren in die Zwischenablage: {e}")


class UpdateDownloadOverlay(ctk.CTkFrame):
    """
    Overlay indicating update download progress.
    """
    def __init__(self, parent):

        super().__init__(parent, fg_color="rgba(11, 11, 15, 0.95)")
        self.parent = parent
        
        self.container = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=12)
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.5, relheight=0.3)
        
        self.title_lbl = ctk.CTkLabel(self.container, text="CINEPALAST LIVE-UPDATE", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=ACCENT_COLOR)
        self.title_lbl.pack(pady=(20, 10))
        
        self.status_lbl = ctk.CTkLabel(self.container, text="Lade Update herunter... 0%", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=TEXT_PRIMARY)
        self.status_lbl.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(self.container, progress_color=ACCENT_COLOR, fg_color="#1E1E26", height=12)
        self.progress.pack(fill="x", padx=40, pady=10)
        self.progress.set(0.0)
        
    def update_progress(self, downloaded, total_size):
        percentage = (downloaded / total_size) * 100 if total_size > 0 else 0
        dl_mb = downloaded / (1024 * 1024)
        tot_mb = total_size / (1024 * 1024)
        self.status_lbl.configure(text=f"Lade Update herunter... {int(percentage)}% ({dl_mb:.1f} MB / {tot_mb:.1f} MB)")
        self.progress.set(downloaded / total_size if total_size > 0 else 0)


class SettingsOverlay(ctk.CTkFrame):
    """
    Overlay to enter, test, and save the TMDB API key and GitHub Token.
    """
    def __init__(self, parent, tmdb_client, on_close_callback):
        super().__init__(parent, fg_color=BG_COLOR)
        self.tmdb_client = tmdb_client
        self.on_close_callback = on_close_callback
        self.parent = parent
        
        self.container = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=16)
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.75)
        
        self.lbl_title = ctk.CTkLabel(self.container, text="CINEPALAST EINSTELLUNGEN", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_title.pack(pady=20)
        
        # Info Box
        info_text = ("Geben Sie Ihren TMDB API-Schlüssel für Filminformationen und Ihren\n"
                     "GitHub Personal Access Token für Live-Updates aus dem Repository ein.")
        self.lbl_info = ctk.CTkLabel(self.container, text=info_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY, justify="center")
        self.lbl_info.pack(pady=(0, 15), padx=20)
        
        # TMDB Key Input Row
        self.input_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=40, pady=8)
        
        self.lbl_key = ctk.CTkLabel(self.input_frame, text="TMDB Key:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_key.pack(side="left", padx=(0, 10))
        
        self.entry_key = ctk.CTkEntry(self.input_frame, fg_color="#1E1E26", border_color=CARD_BORDER, text_color=TEXT_PRIMARY, show="*")
        self.entry_key.pack(side="left", fill="x", expand=True)
        self.entry_key.insert(0, self.tmdb_client.get_api_key())
        
        # GitHub Token Input Row
        self.github_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.github_frame.pack(fill="x", padx=40, pady=8)
        
        self.lbl_github = ctk.CTkLabel(self.github_frame, text="GitHub Token:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_github.pack(side="left", padx=(0, 10))
        
        self.entry_github = ctk.CTkEntry(self.github_frame, fg_color="#1E1E26", border_color=CARD_BORDER, text_color=TEXT_PRIMARY, show="*")
        self.entry_github.pack(side="left", fill="x", expand=True)
        from api import load_github_token
        self.entry_github.insert(0, load_github_token())
        
        # Theme Choice Row
        self.theme_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.theme_frame.pack(fill="x", padx=40, pady=6)
        
        self.lbl_theme = ctk.CTkLabel(self.theme_frame, text="Design-Farbe:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_theme.pack(side="left", padx=(0, 10))
        
        self.theme_option = ctk.CTkOptionMenu(self.theme_frame, values=["Cyan", "Rot", "Blau", "Lila", "Schwarz"],
                                              fg_color="#1E1E26", button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                              dropdown_fg_color="#1E1E26", dropdown_text_color=TEXT_PRIMARY,
                                              dropdown_hover_color="#2A2A35", text_color=TEXT_PRIMARY)
        self.theme_option.pack(side="left", fill="x", expand=True)
        
        theme_map = {"cyan": "Cyan", "red": "Rot", "blue": "Blau", "purple": "Lila", "black": "Schwarz"}
        current_theme_display = theme_map.get(_theme, "Cyan")
        self.theme_option.set(current_theme_display)
        
        # Start-Ansicht Row
        self.view_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.view_frame.pack(fill="x", padx=40, pady=6)
        
        self.lbl_view = ctk.CTkLabel(self.view_frame, text="Start-Ansicht:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_view.pack(side="left", padx=(0, 10))
        
        self.view_option = ctk.CTkOptionMenu(self.view_frame, values=["Galerie", "Tabelle"],
                                             fg_color="#1E1E26", button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                             dropdown_fg_color="#1E1E26", dropdown_text_color=TEXT_PRIMARY,
                                             dropdown_hover_color="#2A2A35", text_color=TEXT_PRIMARY)
        self.view_option.pack(side="left", fill="x", expand=True)
        
        from api import load_config
        current_view = load_config().get("default_view", "Galerie")
        self.view_option.set(current_view)
        
        # Database Options Row
        self.db_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.db_frame.pack(fill="x", padx=40, pady=6)
        
        self.lbl_db_opt = ctk.CTkLabel(self.db_frame, text="Datenbank:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_db_opt.pack(side="left", padx=(0, 10))
        
        self.btn_reset_db = ctk.CTkButton(self.db_frame, text="Datenbank leeren / neu starten", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                          fg_color="#ef4444", text_color="#FFFFFF", hover_color="#dc2626", height=28, command=self._reset_database_clicked)
        self.btn_reset_db.pack(side="left", fill="x", expand=True)
        
        # Database Backup & Restore Row
        self.db_action_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.db_action_frame.pack(fill="x", padx=40, pady=6)
        
        self.lbl_db_act = ctk.CTkLabel(self.db_action_frame, text="DB Aktionen:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, width=100, anchor="w")
        self.lbl_db_act.pack(side="left", padx=(0, 10))
        
        self.btn_backup_db = ctk.CTkButton(self.db_action_frame, text="Backup erstellen", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                           fg_color="transparent", text_color=TEXT_PRIMARY, border_color=ACCENT_COLOR, border_width=1,
                                           hover_color="#0A252E", height=28, command=self._backup_database_clicked)
        self.btn_backup_db.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_restore_db = ctk.CTkButton(self.db_action_frame, text="Backup laden", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                                            fg_color="transparent", text_color=TEXT_PRIMARY, border_color=ACCENT_COLOR, border_width=1,
                                            hover_color="#0A252E", height=28, command=self._restore_database_clicked)
        self.btn_restore_db.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(self.container, text="Status: Nicht getestet", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY)
        self.lbl_status.pack(pady=5)
        
        # Actions Row
        self.btn_row = ctk.CTkFrame(self.container, fg_color="transparent")
        self.btn_row.pack(pady=10)
        
        self.btn_test = ctk.CTkButton(self.btn_row, text="Testen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                      fg_color="transparent", text_color=TEXT_PRIMARY, border_color=ACCENT_COLOR, border_width=1,
                                      hover_color="#0A252E", command=self._test_key)
        self.btn_test.pack(side="left", padx=10)
        
        self.btn_save = ctk.CTkButton(self.btn_row, text="Speichern & Schließen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                      fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, command=self._save_key)
        self.btn_save.pack(side="left", padx=10)
        
        self.btn_cancel = ctk.CTkButton(self.btn_row, text="Abbrechen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                        fg_color="transparent", text_color=TEXT_SECONDARY, hover_color="#2A2A35", command=self.on_close_callback)
        self.btn_cancel.pack(side="left", padx=10)
        
    def _test_key(self):
        test_key = self.entry_key.get().strip()
        test_github = self.entry_github.get().strip()
        
        self.lbl_status.configure(text="Status: Teste Verbindungen...", text_color=TEXT_SECONDARY)
        self.update()
        
        tmdb_ok = False
        github_ok = False
        tmdb_msg = ""
        github_msg = ""
        
        # Test TMDB Key
        if test_key:
            try:
                url = "https://api.themoviedb.org/3/configuration"
                import requests as req
                if len(test_key) > 50 or test_key.startswith("eyJ"):
                    headers = {"Authorization": f"Bearer {test_key}"}
                    params = {}
                else:
                    headers = {}
                    params = {"api_key": test_key}
                
                resp = req.get(url, headers=headers, params=params, timeout=5)
                if resp.status_code == 200:
                    tmdb_ok = True
                    tmdb_msg = "TMDB Key OK"
                else:
                    tmdb_msg = f"TMDB Fehler ({resp.status_code})"
            except Exception as e:
                tmdb_msg = f"TMDB Fehler ({str(e)})"
        else:
            tmdb_msg = "Kein TMDB Key"

        # Test GitHub Token
        if test_github:
            try:
                url = "https://api.github.com/repos/TentixTV/CinepalastManager"
                headers = {"Authorization": f"token {test_github}"}
                import requests as req
                resp = req.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    github_ok = True
                    github_msg = "GitHub Token OK"
                else:
                    github_msg = f"GitHub Fehler ({resp.status_code})"
            except Exception as e:
                github_msg = f"GitHub Fehler ({str(e)})"
        else:
            github_msg = "Kein GitHub Token"

        status_text = f"Status: {tmdb_msg} | {github_msg}"
        status_color = "#22c55e" if (tmdb_ok or not test_key) and (github_ok or not test_github) else "#ef4444"
        if not test_key and not test_github:
            status_color = "#ef4444"
            status_text = "Status: Keine Schlüssel eingegeben"
            
        self.lbl_status.configure(text=status_text, text_color=status_color)
            
    def _save_key(self):
        new_key = self.entry_key.get().strip()
        new_github = self.entry_github.get().strip()
        
        from api import save_api_key, save_github_token, load_config, save_config
        save_api_key(new_key)
        save_github_token(new_github)
        
        # Save theme and default view configuration
        theme_display_map = {"Cyan": "cyan", "Rot": "red", "Blau": "blue", "Lila": "purple", "Schwarz": "black"}
        selected_theme = theme_display_map.get(self.theme_option.get(), "cyan")
        selected_view = self.view_option.get()
        
        cfg = load_config()
        cfg["theme"] = selected_theme
        cfg["default_view"] = selected_view
        save_config(cfg)
        
        # Re-apply theme live
        self.parent.reload_theme()
        messagebox.showinfo("Gespeichert", "Einstellungen wurden erfolgreich gespeichert und live angewendet!")
        self.on_close_callback()
 
    def _reset_database_clicked(self):
        import sqlite3
        if messagebox.askyesno("Datenbank zurücksetzen", "Möchten Sie die gesamte lokale Filmdatenbank wirklich leeren?\n\nAlle importierten Filme werden dauerhaft gelöscht."):
            try:
                conn = sqlite3.connect(self.parent.db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM media;")
                conn.commit()
                conn.close()
                
                self.parent.refresh_gallery()
                messagebox.showinfo("Erfolgreich", "Die lokale Datenbank wurde erfolgreich geleert. Sie ist jetzt komplett leer und bereit für Ihre eigenen Filme!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Leeren der Datenbank: {str(e)}")

    def _backup_database_clicked(self):
        import shutil
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Datenbank", "*.db"), ("Alle Dateien", "*.*")],
            title="Datenbank-Backup speichern",
            initialfile="cinepalast_backup.db"
        )
        if file_path:
            try:
                shutil.copy2(self.parent.db_manager.db_path, file_path)
                messagebox.showinfo("Backup erfolgreich", f"Die Datenbank wurde erfolgreich gesichert unter:\n\n{file_path}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Erstellen des Backups:\n{str(e)}")

    def _restore_database_clicked(self):
        import shutil
        if messagebox.askyesno("Datenbank wiederherstellen", "Möchten Sie wirklich ein Backup einspielen?\n\nDie aktuelle Filmdatenbank wird dabei überschrieben."):
            file_path = filedialog.askopenfilename(
                filetypes=[("SQLite Datenbank", "*.db"), ("Alle Dateien", "*.*")],
                title="Datenbank-Backup laden"
            )
            if file_path:
                try:
                    shutil.copy2(file_path, self.parent.db_manager.db_path)
                    self.parent.refresh_gallery()
                    messagebox.showinfo("Erfolgreich", "Die Datenbank wurde erfolgreich wiederhergestellt!")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Fehler beim Wiederherstellen der Datenbank:\n{str(e)}")



class AddMovieOverlay(ctk.CTkFrame):
    """
    Overlay allowing movie additions:
    1. Online Search (via TMDB) with split-pane detailed preview
    2. Manual creation from scratch with local asset copy options
    """
    def __init__(self, parent, tmdb_client, on_add_callback, on_close_callback):
        super().__init__(parent, fg_color=BG_COLOR)
        self.tmdb_client = tmdb_client
        self.on_add_callback = on_add_callback # callback: function(movie_data)
        self.on_close_callback = on_close_callback
        self.selected_row = None
        
        self.container = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=16)
        self.container.place(relx=0.08, rely=0.08, relwidth=0.84, relheight=0.84)
        
        # Close Button top right
        self.btn_close = ctk.CTkButton(self.container, text="✕", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                       fg_color="transparent", text_color=TEXT_SECONDARY, hover_color="#2E2E3A",
                                       width=30, height=30, command=self.on_close_callback)
        self.btn_close.pack(side="top", anchor="ne", padx=10, pady=10)
        
        self.lbl_title = ctk.CTkLabel(self.container, text="NEUEN FILM HINZUFÜGEN", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_title.pack(pady=(0, 10))
        
        # Tabs
        self.tab_view = ctk.CTkTabview(self.container, fg_color="transparent", text_color=TEXT_PRIMARY, segmented_button_fg_color="#1E1E26",
                                       segmented_button_selected_color=ACCENT_COLOR, segmented_button_selected_hover_color=ACCENT_HOVER,
                                       segmented_button_unselected_color="#1E1E26", segmented_button_unselected_hover_color="#2E2E3A")
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_search = self.tab_view.add("Online TMDB Suche")
        self.tab_manual = self.tab_view.add("Manuell erstellen")
        
        self._setup_search_tab()
        self._setup_manual_tab()
        
    # --- ONLINE SEARCH TAB ---
    def _setup_search_tab(self):
        # Split search tab into a left pane (search results list) and right pane (detailed preview)
        self.split_frame = ctk.CTkFrame(self.tab_search, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.split_frame.columnconfigure(0, weight=4) # Results list width ratio
        self.split_frame.columnconfigure(1, weight=6) # Preview panel width ratio
        self.split_frame.rowconfigure(0, weight=1)
        
        # Left side: search query inputs & results list
        self.left_pane = ctk.CTkFrame(self.split_frame, fg_color="transparent")
        self.left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Search Entry and Search Button inside left pane
        self.search_bar_frame = ctk.CTkFrame(self.left_pane, fg_color="transparent")
        self.search_bar_frame.pack(fill="x", pady=(0, 10))
        
        self.entry_search = ctk.CTkEntry(self.search_bar_frame, placeholder_text="Filmtitel in Deutsch suchen...", fg_color="#1E1E26", border_color=CARD_BORDER)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_search.bind("<Return>", lambda e: self._perform_online_search())
        self.entry_search.bind("<KeyRelease>", self._on_search_key_release)
        
        self.btn_search = ctk.CTkButton(self.search_bar_frame, text="Suchen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                        fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, width=80, command=self._perform_online_search)
        self.btn_search.pack(side="right")
        
        # Search Results List Container
        self.results_scroll = ctk.CTkScrollableFrame(self.left_pane, fg_color="transparent", border_width=1, border_color=CARD_BORDER, corner_radius=8)
        self.results_scroll.pack(fill="both", expand=True)
        
        self.results_empty = ctk.CTkLabel(self.results_scroll, text="Bitte geben Sie einen Filmtitel ein\nund klicken Sie auf Suchen.", font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"), text_color=TEXT_SECONDARY)
        self.results_empty.pack(expand=True, pady=100)
        
        # Right side: preview panel
        self.preview_panel = ctk.CTkFrame(self.split_frame, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=10)
        self.preview_panel.grid(row=0, column=1, sticky="nsew")
        
        self.show_preview_placeholder("Wählen Sie einen Film aus der Liste aus,\num eine Vorschau anzuzeigen.")
        
    def show_preview_placeholder(self, text: str):
        for widget in self.preview_panel.winfo_children():
            widget.destroy()
        lbl = ctk.CTkLabel(self.preview_panel, text=text, font=ctk.CTkFont(family="Segoe UI", size=13, slant="italic"), text_color=TEXT_SECONDARY, justify="center")
        lbl.pack(expand=True, pady=50)

    def _on_search_key_release(self, event):
        if hasattr(self, "_search_timer") and self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(500, self._perform_online_search)

    def _perform_online_search(self):
        query = self.entry_search.get().strip()
        if not query:
            # Clear previous results
            for widget in self.results_scroll.winfo_children():
                widget.destroy()
            self.results_empty = ctk.CTkLabel(self.results_scroll, text="Bitte geben Sie einen Filmtitel ein\nund klicken Sie auf Suchen.", font=ctk.CTkFont(family="Segoe UI", size=12, italic=True), text_color=TEXT_SECONDARY)
            self.results_empty.pack(expand=True, pady=100)
            return

            
        # Clear previous results
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
            

 
        self.btn_search.configure(state="disabled", text="Lade...")
        self.update()
        
        # Run search
        try:
            results = self.tmdb_client.search_movies(query)
            self.btn_search.configure(state="normal", text="Suchen")
            
            if not results:
                no_res = ctk.CTkLabel(self.results_scroll, text="Keine Filme mit diesem Titel gefunden.", font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"), text_color=TEXT_SECONDARY)
                no_res.pack(pady=40)
                return
                
            # Populating search rows
            for m in results:
                row = ctk.CTkFrame(self.results_scroll, fg_color="#181822", border_width=1, border_color=CARD_BORDER, corner_radius=6)
                row.pack(fill="x", pady=4, padx=5)
                
                # Fetch small poster preview
                thumbnail = get_ctk_image(self.tmdb_client.download_and_cache_image(m.get("poster_path"), m["tmdb_id"], "poster") if m.get("poster_path") else "", (40, 58), m["titel"], "poster")
                lbl_thumb = ctk.CTkLabel(row, image=thumbnail, text="")
                lbl_thumb.pack(side="left", padx=10, pady=5)
                
                # Info texts
                lbl_info = ctk.CTkLabel(row, text=f"{m['titel']} ({m['jahr']})\nOriginal: {m['original_titel']}", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_PRIMARY, justify="left", anchor="w")
                lbl_info.pack(side="left", padx=5, fill="both", expand=True)
                
                # Bind clicks to select rows and show preview
                tid = m["tmdb_id"]
                for widget in [row, lbl_thumb, lbl_info]:
                    widget.bind("<Button-1>", lambda e, id=tid, r=row: self.on_search_row_clicked(id, r))
                
        except Exception as e:
            self.btn_search.configure(state="normal", text="Suchen")
            err_lbl = ctk.CTkLabel(self.results_scroll, text=f"Fehler bei der Suche: {str(e)}", text_color="#ef4444")
            err_lbl.pack(pady=40)

    def on_search_row_clicked(self, tmdb_id: int, row_widget: ctk.CTkFrame):
        if hasattr(self, "selected_row") and self.selected_row and self.selected_row.winfo_exists():
            try:
                self.selected_row.configure(border_color=CARD_BORDER)
            except Exception:
                pass
        self.selected_row = row_widget
        try:
            row_widget.configure(border_color=ACCENT_COLOR)
        except Exception:
            pass
            
        self.load_movie_preview(tmdb_id)

    def load_movie_preview(self, tmdb_id: int):
        for widget in self.preview_panel.winfo_children():
            widget.destroy()
            
        loading_label = ctk.CTkLabel(self.preview_panel, text="Lade Film-Vorschau... Bitte warten.", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=ACCENT_COLOR)
        loading_label.pack(expand=True, pady=50)
        self.update()
        
        def fetch_preview_thread():
            try:
                preview_data = self.tmdb_client.fetch_movie_preview(tmdb_id)
                poster_pil = None
                banner_pil = None
                
                if preview_data.get("poster_url"):
                    try:
                        resp = requests.get(preview_data["poster_url"], timeout=5)
                        if resp.status_code == 200:
                            poster_pil = Image.open(io.BytesIO(resp.content))
                    except Exception as e:
                        print(f"Error loading preview poster: {e}")
                        
                if preview_data.get("banner_url"):
                    try:
                        resp = requests.get(preview_data["banner_url"], timeout=5)
                        if resp.status_code == 200:
                            banner_pil = Image.open(io.BytesIO(resp.content))
                    except Exception as e:
                        print(f"Error loading preview banner: {e}")
                        
                self.after(0, lambda: self.display_movie_preview(preview_data, poster_pil, banner_pil))
            except Exception as e:
                self.after(0, lambda err=e: self.show_preview_placeholder(f"Fehler beim Laden der Vorschau:\n{str(err)}"))
                
        threading.Thread(target=fetch_preview_thread, daemon=True).start()

    def display_movie_preview(self, preview_data: dict, poster_pil: Optional[Image.Image], banner_pil: Optional[Image.Image]):
        for widget in self.preview_panel.winfo_children():
            widget.destroy()
            
        preview_scroll = ctk.CTkScrollableFrame(self.preview_panel, fg_color="transparent")
        preview_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Banner image at top
        banner_size = (480, 150)
        if banner_pil:
            banner_img = ctk.CTkImage(light_image=banner_pil, dark_image=banner_pil, size=banner_size)
        else:
            fallback_banner = create_placeholder_image(banner_size, preview_data.get("titel", "Unbekannt"), "banner")
            banner_img = ctk.CTkImage(light_image=fallback_banner, dark_image=fallback_banner, size=banner_size)
            
        banner_label = ctk.CTkLabel(preview_scroll, image=banner_img, text="")
        banner_label.pack(fill="x", pady=(0, 10))
        
        # Title and Year Row
        title_frame = ctk.CTkFrame(preview_scroll, fg_color="transparent")
        title_frame.pack(fill="x", pady=5)
        
        lbl_title = ctk.CTkLabel(title_frame, text=preview_data.get("titel"), font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT_COLOR, wraplength=350, justify="left", anchor="w")
        lbl_title.pack(side="left", anchor="w")
        
        year_val = preview_data.get("jahr")
        year_text = f" ({year_val})" if year_val else ""
        lbl_year = ctk.CTkLabel(title_frame, text=year_text, font=ctk.CTkFont(family="Segoe UI", size=14), text_color=TEXT_SECONDARY)
        lbl_year.pack(side="left", anchor="w", padx=5)
        
        # FSK and basic info row
        meta_frame = ctk.CTkFrame(preview_scroll, fg_color="transparent")
        meta_frame.pack(fill="x", pady=(0, 10))
        
        fsk_val = preview_data.get("fsk", "k.A.")
        fsk_img = get_fsk_image(fsk_val, size=(26, 26))
        if fsk_img:
            fsk_badge = ctk.CTkLabel(meta_frame, image=fsk_img, text="")
        else:
            fsk_bg, fsk_fg, fsk_lbl = get_fsk_colors(fsk_val)
            fsk_badge = ctk.CTkLabel(meta_frame, text=fsk_lbl, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                                     fg_color=fsk_bg, text_color=fsk_fg, corner_radius=4, width=50, height=20)
        fsk_badge.pack(side="left")
        
        runtime = preview_data.get("laufzeit_min", 0)
        runtime_text = f"  |  {runtime} Min." if runtime else ""
        lbl_meta = ctk.CTkLabel(meta_frame, text=f"{runtime_text}  |  {preview_data.get('genre_richtung', 'k.A.')}", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY, wraplength=400, justify="left")
        lbl_meta.pack(side="left", padx=5)
        
        # Info row (poster + facts)
        info_row = ctk.CTkFrame(preview_scroll, fg_color="transparent")
        info_row.pack(fill="x", pady=5)
        
        poster_size = (100, 145)
        if poster_pil:
            poster_img = ctk.CTkImage(light_image=poster_pil, dark_image=poster_pil, size=poster_size)
        else:
            fallback_poster = create_placeholder_image(poster_size, preview_data.get("titel", "Unbekannt"), "poster")
            poster_img = ctk.CTkImage(light_image=fallback_poster, dark_image=fallback_poster, size=poster_size)
            
        poster_label = ctk.CTkLabel(info_row, image=poster_img, text="")
        poster_label.pack(side="left", padx=(0, 10))
        
        # Facts box
        facts_frame = ctk.CTkFrame(info_row, fg_color="#181822", border_width=1, border_color="#2E2E3A", corner_radius=8)
        facts_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        def add_fact(label, val):
            row = ctk.CTkFrame(facts_frame, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=8)
            lbl_field = ctk.CTkLabel(row, text=label, font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color=TEXT_SECONDARY, width=70, anchor="w")
            lbl_field.pack(side="left")
            lbl_val = ctk.CTkLabel(row, text=val, font=ctk.CTkFont(family="Segoe UI", size=9), text_color=TEXT_PRIMARY, wraplength=210, justify="left", anchor="w")
            lbl_val.pack(side="left", fill="x", expand=True)
            
        add_fact("Regisseur:", preview_data.get("regisseur", "k.A."))
        add_fact("Filmreihe:", preview_data.get("filmreihe", "-") or "-")
        add_fact("Land:", preview_data.get("produktionsland", "k.A."))
        add_fact("Studio:", preview_data.get("produktionsfirma_studio", "k.A."))
        
        # Description
        lbl_desc_title = ctk.CTkLabel(preview_scroll, text="Handlung", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=ACCENT_COLOR)
        lbl_desc_title.pack(anchor="w", pady=(10, 2))
        
        desc_text = preview_data.get("handlung_beschreibung", "Keine Beschreibung vorhanden.")
        lbl_desc = ctk.CTkLabel(preview_scroll, text=desc_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_PRIMARY, justify="left", wraplength=450)
        lbl_desc.pack(anchor="w", pady=(0, 10))
        
        # Cast
        lbl_cast_title = ctk.CTkLabel(preview_scroll, text="Besetzung (Cast)", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=ACCENT_COLOR)
        lbl_cast_title.pack(anchor="w", pady=(5, 2))
        
        cast_text = preview_data.get("schauspieler_cast", "Keine Angaben.")
        lbl_cast = ctk.CTkLabel(preview_scroll, text=cast_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_PRIMARY, justify="left", wraplength=450)
        lbl_cast.pack(anchor="w", pady=(0, 15))
        
        # Download & Save Button
        btn_download = ctk.CTkButton(preview_scroll, text="Film importieren & herunterladen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                     fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, height=36,
                                     command=lambda: self._import_movie(preview_data["tmdb_id"]))
        btn_download.pack(fill="x", pady=15, padx=5)

    def _import_movie(self, tmdb_id: int):
        """
        Launches thread-safe downloading/scraping of the full movie metadata
        to avoid locking the UI during HTTP download streams.
        """
        # Show loading spinner overlay
        self.loading = LoadingOverlay(self, message="Film-Metadaten werden heruntergeladen und Bilder gecached")
        self.loading.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.update()
        
        def run_thread():
            try:
                # Scrapes full data and handles image download streams inside api.py
                movie_data = self.tmdb_client.fetch_movie_details(tmdb_id)
                # Success callback on main GUI thread
                self.after(0, lambda: self._import_success(movie_data))
            except Exception as e:
                # Error callback on main GUI thread
                self.after(0, lambda err=e: self._import_failed(err))

        threading.Thread(target=run_thread, daemon=True).start()

    def _import_success(self, movie_data: dict):
        if hasattr(self, 'loading') and self.loading.winfo_exists():
            self.loading.destroy()
        self.on_add_callback(movie_data)
        messagebox.showinfo("Erfolgreich", f"Der Film '{movie_data.get('titel')}' wurde erfolgreich hinzugefügt.")
        self.on_close_callback()

    def _import_failed(self, error: Exception):
        if hasattr(self, 'loading') and self.loading.winfo_exists():
            self.loading.destroy()
        messagebox.showerror("Fehler beim Importieren", f"Es gab ein Problem beim Abrufen der TMDB-Daten:\n{str(error)}")

    # --- MANUAL CREATE TAB ---
    def _setup_manual_tab(self):
        # Create a scrollable container for manual input fields
        self.manual_scroll = ctk.CTkScrollableFrame(self.tab_manual, fg_color="transparent")
        self.manual_scroll.pack(fill="both", expand=True)
        
        self.inputs = {}
        
        # Grid layout for fields
        form_frame = ctk.CTkFrame(self.manual_scroll, fg_color="transparent")
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=3)
        
        fields = [
            ("titel", "Titel / Name*", "entry", ""),
            ("jahr", "Jahr (4-stellig)*", "entry", ""),
            ("genre_richtung", "Genre / Richtung", "entry", "z.B. Action, Sci-Fi, Drama"),
            ("schauspieler_cast", "Schauspieler / Cast", "entry", "Kommagetrennte Liste der Schauspieler"),
            ("regisseur", "Regisseur", "entry", ""),
            ("laufzeit_min", "Laufzeit (Min.)", "entry", "Nur Zahlen"),
            ("handlung_beschreibung", "Handlung / Beschreibung", "textbox", ""),
            ("fsk", "FSK Einstufung*", "optionmenu", ["0", "6", "12", "16", "18", "k.A."]),
            ("produktionsfirma_studio", "Studio / Produktionsfirma", "entry", ""),
            ("filmreihe", "Filmreihe / Franchise", "entry", ""),
            ("produktionsland", "Produktionsland", "entry", ""),
            ("deutsche_synchronsprecher", "Deutsche Synchronsprecher", "entry", "Manuelle Eingabe"),
            ("poster_pfad", "Poster Bilddatei", "filedialog", "Pfad zur lokalen Poster-Bilddatei (wird kopiert)"),
            ("banner_pfad", "Banner / Wallpaper Bild", "filedialog", "Pfad zur lokalen Banner-Bilddatei (wird kopiert)")
        ]
        
        for idx, (key, label_text, widget_type, placeholder) in enumerate(fields):
            lbl = ctk.CTkLabel(form_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, anchor="w")
            lbl.grid(row=idx, column=0, padx=(10, 20), pady=8, sticky="w")
            
            if widget_type == "entry":
                entry = ctk.CTkEntry(form_frame, placeholder_text=placeholder, fg_color="#1E1E26", border_color=CARD_BORDER)
                entry.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = entry
                
            elif widget_type == "textbox":
                textbox = ctk.CTkTextbox(form_frame, height=80, fg_color="#1E1E26", border_color=CARD_BORDER, border_width=1)
                textbox.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = textbox
                
            elif widget_type == "optionmenu":
                option_menu = ctk.CTkOptionMenu(form_frame, values=placeholder, fg_color="#1E1E26", button_color="#1E1E26", button_hover_color=ACCENT_COLOR, dropdown_fg_color=PANEL_COLOR)
                option_menu.set(placeholder[-1]) # Default to last (k.A.)
                option_menu.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = option_menu
                
            elif widget_type == "filedialog":
                file_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
                file_frame.grid(row=idx, column=1, fill="x", pady=5)
                
                entry_path = ctk.CTkEntry(file_frame, placeholder_text=placeholder, fg_color="#1E1E26", border_color=CARD_BORDER)
                entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
                
                # File picker button
                btn_browse = ctk.CTkButton(file_frame, text="Suchen...", font=ctk.CTkFont(family="Segoe UI", size=11),
                                           fg_color="transparent", text_color=TEXT_PRIMARY, border_color=CARD_BORDER, border_width=1,
                                           hover_color="#2E2E3A", width=80, command=lambda e=entry_path: self._select_local_file(e))
                btn_browse.pack(side="right")
                self.inputs[key] = entry_path

        # Manual Save Button
        self.btn_save_manual = ctk.CTkButton(self.manual_scroll, text="Film manuell speichern", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                             fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, height=40, command=self._save_manual_movie)
        self.btn_save_manual.pack(pady=25, padx=20, fill="x")
        
    def _select_local_file(self, target_entry):
        file_path = filedialog.askopenfilename(title="Bilddatei auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if file_path:
            target_entry.delete(0, tk.END)
            target_entry.insert(0, file_path)
            
    def _save_manual_movie(self):
        # 1. Retrieve & Validate Fields
        titel = self.inputs["titel"].get().strip()
        jahr_raw = self.inputs["jahr"].get().strip()
        fsk = self.inputs["fsk"].get()
        
        if not titel:
            messagebox.showerror("Eingabehler", "Der Filmtitel ist ein Pflichtfeld!")
            return
            
        jahr = None
        if jahr_raw:
            try:
                jahr = int(jahr_raw)
                if jahr < 1880 or jahr > 2100:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Eingabefehler", "Das Jahr muss eine 4-stellige Zahl sein (z.B. 2023)!")
                return
                
        laufzeit_raw = self.inputs["laufzeit_min"].get().strip()
        laufzeit = 0
        if laufzeit_raw:
            try:
                laufzeit = int(laufzeit_raw)
            except ValueError:
                messagebox.showerror("Eingabefehler", "Laufzeit muss eine Ganzzahl in Minuten sein!")
                return

        # Handlung Description (Textbox helper)
        handlung = self.inputs["handlung_beschreibung"].get("1.0", tk.END).strip()

        # Handle local image copies
        import uuid
        poster_src = self.inputs["poster_pfad"].get().strip()
        banner_src = self.inputs["banner_pfad"].get().strip()
        
        poster_dest = ""
        banner_dest = ""
        
        # Safe copy to assets/posters/
        if poster_src and os.path.exists(poster_src):
            ext = os.path.splitext(poster_src)[1] or ".jpg"
            unique_name = f"manual_{uuid.uuid4().hex[:12]}{ext}"
            os.makedirs("assets/posters", exist_ok=True)
            poster_dest = f"assets/posters/{unique_name}"
            try:
                shutil.copy2(poster_src, poster_dest)
            except Exception as e:
                print(f"Error copying poster: {e}")
                poster_dest = ""
                
        # Safe copy to assets/banners/
        if banner_src and os.path.exists(banner_src):
            ext = os.path.splitext(banner_src)[1] or ".jpg"
            unique_name = f"manual_{uuid.uuid4().hex[:12]}{ext}"
            os.makedirs("assets/banners", exist_ok=True)
            banner_dest = f"assets/banners/{unique_name}"
            try:
                shutil.copy2(banner_src, banner_dest)
            except Exception as e:
                print(f"Error copying banner: {e}")
                banner_dest = ""

        # Construct payload
        movie_data = {
            "titel": titel,
            "jahr": jahr,
            "schauspieler_cast": self.inputs["schauspieler_cast"].get().strip() or "k.A.",
            "genre_richtung": self.inputs["genre_richtung"].get().strip() or "k.A.",
            "laufzeit_min": laufzeit,
            "handlung_beschreibung": handlung or "Keine Beschreibung vorhanden.",
            "fsk": fsk,
            "produktionsfirma_studio": self.inputs["produktionsfirma_studio"].get().strip() or "k.A.",
            "regisseur": self.inputs["regisseur"].get().strip() or "k.A.",
            "filmreihe": self.inputs["filmreihe"].get().strip() or "",
            "produktionsland": self.inputs["produktionsland"].get().strip() or "k.A.",
            "deutsche_synchronsprecher": self.inputs["deutsche_synchronsprecher"].get().strip() or "",
            "poster_pfad": poster_dest,
            "banner_pfad": banner_dest
        }
        
        self.on_add_callback(movie_data)
        messagebox.showinfo("Erfolgreich", f"Der Film '{titel}' wurde manuell zur Bibliothek hinzugefügt.")
        self.on_close_callback()


class EditMovieOverlay(ctk.CTkFrame):
    """
    Overlay to edit metadata of an existing movie.
    Pre-populates fields with database records.
    """
    def __init__(self, parent, movie: dict, on_save_callback, on_close_callback):
        super().__init__(parent, fg_color=BG_COLOR)
        self.movie = movie
        self.on_save_callback = on_save_callback
        self.on_close_callback = on_close_callback
        
        self.container = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=1, border_color=CARD_BORDER, corner_radius=16)
        self.container.place(relx=0.08, rely=0.08, relwidth=0.84, relheight=0.84)
        
        # Close Button top right
        self.btn_close = ctk.CTkButton(self.container, text="✕", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                       fg_color="transparent", text_color=TEXT_SECONDARY, hover_color="#2E2E3A",
                                       width=30, height=30, command=self.on_close_callback)
        self.btn_close.pack(side="top", anchor="ne", padx=10, pady=10)
        
        self.lbl_title = ctk.CTkLabel(self.container, text=f"FILM BEARBEITEN: {self.movie.get('titel')}", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_title.pack(pady=(0, 10))
        
        # Scrollable Form
        self.form_scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.form_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.inputs = {}
        
        # Form grid
        form_frame = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        form_frame.pack(fill="x", padx=10, pady=10)
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=3)
        
        # Map out fields with prepopulated values
        fields = [
            ("titel", "Titel / Name*", "entry", self.movie.get("titel", "")),
            ("jahr", "Jahr (4-stellig)", "entry", str(self.movie.get("jahr") or "")),
            ("genre_richtung", "Genre / Richtung", "entry", self.movie.get("genre_richtung", "")),
            ("schauspieler_cast", "Schauspieler / Cast", "entry", self.movie.get("schauspieler_cast", "")),
            ("regisseur", "Regisseur", "entry", self.movie.get("regisseur", "")),
            ("laufzeit_min", "Laufzeit (Min.)", "entry", str(self.movie.get("laufzeit_min") or "")),
            ("handlung_beschreibung", "Handlung / Beschreibung", "textbox", self.movie.get("handlung_beschreibung", "")),
            ("fsk", "FSK Einstufung*", "optionmenu", ["0", "6", "12", "16", "18", "k.A."]),
            ("produktionsfirma_studio", "Studio / Produktionsfirma", "entry", self.movie.get("produktionsfirma_studio", "")),
            ("filmreihe", "Filmreihe / Franchise", "entry", self.movie.get("filmreihe", "")),
            ("produktionsland", "Produktionsland", "entry", self.movie.get("produktionsland", "")),
            ("deutsche_synchronsprecher", "Deutsche Synchronsprecher", "entry", self.movie.get("deutsche_synchronsprecher", "")),
            ("poster_pfad", "Poster Bilddatei (Pfad ändern)", "filedialog", self.movie.get("poster_pfad", "")),
            ("banner_pfad", "Banner Bilddatei (Pfad ändern)", "filedialog", self.movie.get("banner_pfad", ""))
        ]
        
        for idx, (key, label_text, widget_type, current_val) in enumerate(fields):
            lbl = ctk.CTkLabel(form_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, anchor="w")
            lbl.grid(row=idx, column=0, padx=(10, 20), pady=8, sticky="w")
            
            if widget_type == "entry":
                entry = ctk.CTkEntry(form_frame, fg_color="#1E1E26", border_color=CARD_BORDER)
                entry.insert(0, current_val)
                entry.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = entry
                
            elif widget_type == "textbox":
                textbox = ctk.CTkTextbox(form_frame, height=80, fg_color="#1E1E26", border_color=CARD_BORDER, border_width=1)
                textbox.insert("1.0", current_val)
                textbox.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = textbox
                
            elif widget_type == "optionmenu":
                option_menu = ctk.CTkOptionMenu(form_frame, values=current_val, fg_color="#1E1E26", button_color="#1E1E26", button_hover_color=ACCENT_COLOR, dropdown_fg_color=PANEL_COLOR)
                option_menu.set(self.movie.get("fsk", "k.A."))
                option_menu.grid(row=idx, column=1, fill="x", pady=5)
                self.inputs[key] = option_menu
                
            elif widget_type == "filedialog":
                file_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
                file_frame.grid(row=idx, column=1, fill="x", pady=5)
                
                entry_path = ctk.CTkEntry(file_frame, fg_color="#1E1E26", border_color=CARD_BORDER)
                entry_path.insert(0, current_val)
                entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
                
                btn_browse = ctk.CTkButton(file_frame, text="Suchen...", font=ctk.CTkFont(family="Segoe UI", size=11),
                                           fg_color="transparent", text_color=TEXT_PRIMARY, border_color=CARD_BORDER, border_width=1,
                                           hover_color="#2E2E3A", width=80, command=lambda e=entry_path: self._select_local_file(e))
                btn_browse.pack(side="right")
                self.inputs[key] = entry_path

        # Save Button
        self.btn_save = ctk.CTkButton(self.form_scroll, text="Änderungen speichern", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                      fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, height=40, command=self._update_movie)
        self.btn_save.pack(pady=25, padx=20, fill="x")
        
    def _select_local_file(self, target_entry):
        file_path = filedialog.askopenfilename(title="Bilddatei auswählen", filetypes=[("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if file_path:
            target_entry.delete(0, tk.END)
            target_entry.insert(0, file_path)
            
    def _update_movie(self):
        titel = self.inputs["titel"].get().strip()
        jahr_raw = self.inputs["jahr"].get().strip()
        fsk = self.inputs["fsk"].get()
        
        if not titel:
            messagebox.showerror("Eingabefehler", "Der Filmtitel ist ein Pflichtfeld!")
            return
            
        jahr = None
        if jahr_raw:
            try:
                jahr = int(jahr_raw)
                if jahr < 1880 or jahr > 2100:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Eingabefehler", "Das Jahr muss eine 4-stellige Zahl sein (z.B. 2023)!")
                return
                
        laufzeit_raw = self.inputs["laufzeit_min"].get().strip()
        laufzeit = 0
        if laufzeit_raw:
            try:
                laufzeit = int(laufzeit_raw)
            except ValueError:
                messagebox.showerror("Eingabefehler", "Laufzeit muss eine Ganzzahl in Minuten sein!")
                return

        handlung = self.inputs["handlung_beschreibung"].get("1.0", tk.END).strip()

        # Handle local image changes (copy only if changed from original)
        import uuid
        poster_src = self.inputs["poster_pfad"].get().strip()
        banner_src = self.inputs["banner_pfad"].get().strip()
        
        poster_dest = self.movie.get("poster_pfad", "")
        banner_dest = self.movie.get("banner_pfad", "")
        
        # Copy poster if path changed and is a valid new file
        if poster_src != self.movie.get("poster_pfad", "") and poster_src and os.path.exists(poster_src):
            ext = os.path.splitext(poster_src)[1] or ".jpg"
            unique_name = f"manual_{uuid.uuid4().hex[:12]}{ext}"
            os.makedirs("assets/posters", exist_ok=True)
            poster_dest = f"assets/posters/{unique_name}"
            try:
                shutil.copy2(poster_src, poster_dest)
            except Exception as e:
                print(f"Error copying poster: {e}")
                poster_dest = self.movie.get("poster_pfad", "")
                
        # Copy banner if path changed
        if banner_src != self.movie.get("banner_pfad", "") and banner_src and os.path.exists(banner_src):
            ext = os.path.splitext(banner_src)[1] or ".jpg"
            unique_name = f"manual_{uuid.uuid4().hex[:12]}{ext}"
            os.makedirs("assets/banners", exist_ok=True)
            banner_dest = f"assets/banners/{unique_name}"
            try:
                shutil.copy2(banner_src, banner_dest)
            except Exception as e:
                print(f"Error copying banner: {e}")
                banner_dest = self.movie.get("banner_pfad", "")

        movie_data = {
            "titel": titel,
            "jahr": jahr,
            "schauspieler_cast": self.inputs["schauspieler_cast"].get().strip() or "k.A.",
            "genre_richtung": self.inputs["genre_richtung"].get().strip() or "k.A.",
            "laufzeit_min": laufzeit,
            "handlung_beschreibung": handlung or "Keine Beschreibung vorhanden.",
            "fsk": fsk,
            "produktionsfirma_studio": self.inputs["produktionsfirma_studio"].get().strip() or "k.A.",
            "regisseur": self.inputs["regisseur"].get().strip() or "k.A.",
            "filmreihe": self.inputs["filmreihe"].get().strip() or "",
            "produktionsland": self.inputs["produktionsland"].get().strip() or "k.A.",
            "deutsche_synchronsprecher": self.inputs["deutsche_synchronsprecher"].get().strip() or "",
            "poster_pfad": poster_dest,
            "banner_pfad": banner_dest
        }
        
        self.on_save_callback(self.movie["id"], movie_data)
        messagebox.showinfo("Erfolgreich", f"Der Film '{titel}' wurde aktualisiert.")
        self.on_close_callback()


class CinePalastApp(ctk.CTk):
    """
    Main application frame and core coordinator.
    Inherits from customtkinter.CTk. Handles windows lifecycle,
    dynamically resizing column calculations, search bindings, settings and DB operations.
    """
    def __init__(self, db_manager, tmdb_client):
        super().__init__()
        self.db_manager = db_manager
        self.tmdb_client = tmdb_client
        
        # 1. Main Window Config
        self.title("CinePalast Manager - Mannis Kinopalast")
        self.geometry("1100x750")
        self.minimum_size = (900, 600)
        self.configure(fg_color=BG_COLOR)
        
        # Load app icon if available
        self._load_app_icon()
        
        # Resize grid calculations helpers
        self.current_cols = 1
        self.last_width = 0
        self.movies_list = [] # Cached list of current movies displayed
        self.online_movies_list = [] # Online recommendations from TMDB
        from api import load_config
        self.view_mode = load_config().get("default_view", "Galerie") # Default view mode loaded from settings
        
        # 2. Setup Top Panel Layout
        self._setup_top_panel()
        
        # 3. Setup Scrollable Media Grid Layout
        self.gallery_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        
        # Bind resize configuration to enable responsive reflow columns
        self.gallery_scroll.bind("<Configure>", self._on_gallery_resize)
        
        # Placeholder for overlays
        self.active_overlay = None
        
        # 4. First load
        self._on_view_changed(self.view_mode)
        self.after(1000, self.check_for_updates_background)
        self.bind_all("<Button-1>", self._on_window_click, add="+")

    def reload_theme(self):
        """Reloads the theme configuration from config.json and updates the GUI live without restarting."""
        global BG_COLOR, PANEL_COLOR, ACCENT_COLOR, ACCENT_HOVER, CARD_BORDER, IMAGE_CACHE
        
        # 1. Reload the theme string from config
        from api import load_config
        theme_str = "cyan"
        try:
            theme_str = load_config().get("theme", "cyan").strip().lower()
        except Exception:
            pass
            
        # 2. Reset the global colors
        if theme_str == "cyan":
            BG_COLOR = "#0B0B0F"
            PANEL_COLOR = "#15151C"
            ACCENT_COLOR = "#00F0FF"
            ACCENT_HOVER = "#00B3C2"
            CARD_BORDER = "#1E1E26"
        elif theme_str == "red":
            BG_COLOR = "#0B0B0F"
            PANEL_COLOR = "#15151C"
            ACCENT_COLOR = "#EF4444"
            ACCENT_HOVER = "#DC2626"
            CARD_BORDER = "#1E1E26"
        elif theme_str == "blue":
            BG_COLOR = "#0B0B0F"
            PANEL_COLOR = "#15151C"
            ACCENT_COLOR = "#3B82F6"
            ACCENT_HOVER = "#2563EB"
            CARD_BORDER = "#1E1E26"
        elif theme_str == "purple":
            BG_COLOR = "#0B0B0F"
            PANEL_COLOR = "#15151C"
            ACCENT_COLOR = "#A855F7"
            ACCENT_HOVER = "#9333EA"
            CARD_BORDER = "#1E1E26"
        elif theme_str == "black":
            BG_COLOR = "#050505"
            PANEL_COLOR = "#0D0D10"
            ACCENT_COLOR = "#E0E0E0"
            ACCENT_HOVER = "#A0A0A0"
            CARD_BORDER = "#1A1A22"
            
        # Update window background
        self.configure(fg_color=BG_COLOR)
        
        # Clear image cache to redraw placeholders in new color
        IMAGE_CACHE.clear()
        
        # Rebuild layout elements
        if hasattr(self, "top_panel") and self.top_panel.winfo_exists():
            self.top_panel.destroy()
        if hasattr(self, "gallery_scroll") and self.gallery_scroll.winfo_exists():
            self.gallery_scroll.destroy()
        if hasattr(self, "table_container") and self.table_container.winfo_exists():
            self.table_container.destroy()
            
        self._setup_top_panel()
        self.gallery_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.gallery_scroll.bind("<Configure>", self._on_gallery_resize)
        
        # Reset grid col count to force reflow on next configure
        self.last_width = 0
        
        # Re-initialize view mode
        self._on_view_changed(self.view_mode)

    def _load_app_icon(self):
        """Checks the project root for icon.ico or assets/DTB.png and applies it natively."""
        icon_ico = "icon.ico"
        icon_dtb = "assets/DTB.png"
        icon_png = "icon.png"
        
        if os.path.exists(icon_ico):
            try:
                self.iconbitmap(icon_ico)
            except Exception as e:
                print(f"Failed to load icon.ico: {e}")
        elif os.path.exists(icon_dtb):
            try:
                from PIL import ImageTk
                img = Image.open(icon_dtb)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.iconphoto(False, self.tk_icon)
            except Exception as e:
                print(f"Failed to load assets/DTB.png: {e}")
        elif os.path.exists(icon_png):
            try:
                from PIL import ImageTk
                img = Image.open(icon_png)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.iconphoto(False, self.tk_icon)
            except Exception as e:
                print(f"Failed to load icon.png: {e}")

    def _setup_top_panel(self):
        self.top_panel = ctk.CTkFrame(self, fg_color=PANEL_COLOR, height=80, corner_radius=0, border_width=0)
        self.top_panel.pack(fill="x", side="top")
        
        # 1. Title and Subtitle Block (Left)
        self.title_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.title_frame.pack(side="left", padx=20, pady=10)
        
        self.lbl_app_title = ctk.CTkLabel(self.title_frame, text="CINEPALAST MANAGER", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT_COLOR)
        self.lbl_app_title.pack(anchor="w")
        self.lbl_app_sub = ctk.CTkLabel(self.title_frame, text=f"Mannis Kinopalast v{APP_VERSION}", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY)
        self.lbl_app_sub.pack(anchor="w")

        
        # 2. Top Buttons Block (Right - packed first so it claims its space)
        self.btn_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=20, pady=15)
        
        # View Switcher (Segmented Button for Galerie/Tabelle)
        self.view_switch = ctk.CTkSegmentedButton(self.btn_frame, values=["Galerie", "Tabelle"],
                                                  command=self._on_view_changed,
                                                  selected_color=ACCENT_COLOR,
                                                  selected_hover_color=ACCENT_HOVER,
                                                  unselected_color="#1E1E26",
                                                  text_color=TEXT_PRIMARY)
        self.view_switch.pack(side="left", padx=(0, 10))
        self.view_switch.set(self.view_mode)
        
        self.btn_add = ctk.CTkButton(self.btn_frame, text="+ Film hinzufügen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                     fg_color=ACCENT_COLOR, text_color="#000000", hover_color=ACCENT_HOVER, command=self._show_add_overlay)
        self.btn_add.pack(side="left", padx=(0, 10))
        
        self.btn_settings = ctk.CTkButton(self.btn_frame, text="Einstellungen", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                          fg_color="transparent", text_color=TEXT_PRIMARY, border_color=CARD_BORDER, border_width=1,
                                          hover_color="#2A2A35", command=self._show_settings_overlay)
        self.btn_settings.pack(side="left")
        
        # 3. Real-time Search (Center - packed last with expand=True)
        self.search_frame = ctk.CTkFrame(self.top_panel, fg_color="transparent")
        self.search_frame.pack(side="left", fill="x", expand=True, padx=40, pady=15)
        
        self.entry_main_search = ctk.CTkEntry(self.search_frame, placeholder_text="Bibliothek sekundenschnell durchsuchen...", fg_color="#1E1E26", border_color=CARD_BORDER)
        self.entry_main_search.pack(fill="x", expand=True)
        self.entry_main_search.bind("<KeyRelease>", self._on_search_key)
        
        # Bind Tooltips
        CTkToolTip(self.entry_main_search, "Durchsuche deine lokale Film-Bibliothek nach Titel, Genre, Cast oder Regisseur.")
        CTkToolTip(self.btn_add, "Füge neue Filme online via TMDB oder manuell hinzu.")
        CTkToolTip(self.btn_settings, "Öffne die Einstellungen für den TMDB API-Key und das Design.")

    # --- GALLERY RENDERING & REFLOW ---
    def refresh_gallery(self):
        """Loads films from DB matching search query, and schedules a grid or table refresh."""
        query = self.entry_main_search.get().strip()
        self.movies_list = self.db_manager.search_movies(query)
        if self.view_mode == "Galerie":
            self._regrid_movies()
        else:
            self._refresh_table_data()

    def _regrid_movies(self):
        """Clears the grid inside scrollable container and repopulates based on column fit."""
        # 1. Clear grid widgets
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()
            
        # 2. Check if both local and online lists are empty
        if not self.movies_list and not self.online_movies_list:
            search_query = self.entry_main_search.get().strip()
            # Show empty placeholder message
            empty_msg = ("Es befinden sich keine Filme in der Auswahl.\n"
                         "Klicken Sie oben auf '+ Film hinzufügen', "
                         "um Ihre Sammlung aufzubauen.")
            if search_query:
                empty_msg = f"Keine lokalen oder Online-Ergebnisse für die Suche nach '{search_query}' gefunden."
                
            self.lbl_empty = ctk.CTkLabel(self.gallery_scroll, text=empty_msg, font=ctk.CTkFont(family="Segoe UI", size=13, slant="italic"), text_color=TEXT_SECONDARY)
            self.lbl_empty.pack(expand=True, pady=(80, 10))
            
            if search_query:
                self.btn_online_search_fallback = ctk.CTkButton(
                    self.gallery_scroll,
                    text=f'Online nach "{search_query}" suchen',
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    fg_color=ACCENT_COLOR,
                    text_color="#000000",
                    hover_color=ACCENT_HOVER,
                    command=lambda: self._trigger_online_search_from_main(search_query)
                )
                self.btn_online_search_fallback.pack(pady=10)
            return

        # 3. Calculate grids
        col_width = 175 # Card width + padding
        available_width = self.gallery_scroll.winfo_width() - 30 # minus scrollbars
        
        if available_width <= 100:
            available_width = self.winfo_width() - 80 # fallback prior to layout configs
            
        cols = max(1, available_width // col_width)
        self.current_cols = cols
        
        # Reconfigure grid columns weights
        for c in range(cols):
            self.gallery_scroll.grid_columnconfigure(c, weight=1)
            
        current_row = 0
        
        # 4. Place Local Movies
        if self.movies_list:
            lbl_local_header = ctk.CTkLabel(self.gallery_scroll, text="Meine Bibliothek", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=ACCENT_COLOR)
            lbl_local_header.grid(row=current_row, column=0, columnspan=cols, padx=8, pady=(10, 5), sticky="w")
            current_row += 1
            
            for idx, m in enumerate(self.movies_list):
                r = current_row + (idx // cols)
                c = idx % cols
                card = MovieCard(self.gallery_scroll, m, self._show_movie_details)
                card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
                bind_mouse_wheel_recursive(card, self.gallery_scroll)
                
            current_row += (len(self.movies_list) - 1) // cols + 1

        # 5. Place Online Suggestions (TMDB)
        if self.online_movies_list:
            lbl_online_header = ctk.CTkLabel(self.gallery_scroll, text="Online-Vorschläge (Klicken zum Importieren)", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#A855F7")
            lbl_online_header.grid(row=current_row, column=0, columnspan=cols, padx=8, pady=(20, 5), sticky="w")
            current_row += 1
            
            for idx, m in enumerate(self.online_movies_list):
                r = current_row + (idx // cols)
                c = idx % cols
                card = OnlineMovieCard(self.gallery_scroll, m, self._import_online_movie_directly)
                card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
                bind_mouse_wheel_recursive(card, self.gallery_scroll)

    def _on_gallery_resize(self, event):
        """Triggers dynamic reflow of grid columns when window scales."""
        width = event.width
        if abs(width - self.last_width) > 20: # Debounce/threshold
            self.last_width = width
            self._regrid_movies()

    def _on_search_key(self, event):
        """Debounces the entire search process (local and online) to prevent lag."""
        query = self.entry_main_search.get().strip()
        
        if not query:
            if hasattr(self, "_main_search_timer") and self._main_search_timer:
                self.after_cancel(self._main_search_timer)
            self._hide_suggestions()
            self.online_movies_list = []
            self.refresh_gallery()
            return
            
        # Debounce local refresh, suggestion display, and TMDB search by 250ms
        if hasattr(self, "_main_search_timer") and self._main_search_timer:
            self.after_cancel(self._main_search_timer)
            
        def execute_search():
            self.refresh_gallery()
            local_matches = self.db_manager.search_movies(query)
            self._show_suggestions(local_matches)
            if len(query) >= 2:
                self._perform_main_online_search(query)
            else:
                self.online_movies_list = []
                self._regrid_movies()
                
        self._main_search_timer = self.after(250, execute_search)


    def _perform_main_online_search(self, query):
        def thread_func():
            try:
                results = self.tmdb_client.search_movies(query)
                # Filter out movies already in local database (by title)
                local_titles = {m["titel"].lower() for m in self.db_manager.get_all_movies()}
                filtered_results = []
                for m in results:
                    title_with_year = f"{m['titel']} ({m['jahr']})"
                    if title_with_year.lower() not in local_titles and m['titel'].lower() not in local_titles:
                        filtered_results.append(m)
                
                self.online_movies_list = filtered_results[:6] # Top 6 recommendations
                self.after(0, self._regrid_movies)
            except Exception as e:
                print(f"Error in main online search: {e}")
                self.online_movies_list = []
                self.after(0, self._regrid_movies)
                
        import threading
        threading.Thread(target=thread_func, daemon=True).start()

    def _import_online_movie_directly(self, movie):
        # Clear main window contents and show fullscreen loading state
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()
            
        loading = ctk.CTkLabel(self.gallery_scroll, text=f'Füge "{movie["titel"]}" hinzu und lade Plakate herunter... Bitte warten.',
                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=ACCENT_COLOR)
        loading.pack(expand=True, pady=100)
        self.update()
        
        def import_thread():
            try:
                tmdb_id = movie["tmdb_id"]
                full_details = self.tmdb_client.fetch_movie_details(tmdb_id)
                self.db_manager.add_movie(full_details)
                self.after(0, self._import_success)
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Fehler", f"Import fehlgeschlagen: {str(err)}"))
                self.after(0, self.refresh_gallery)
                
        import threading
        threading.Thread(target=import_thread, daemon=True).start()
        
    def _import_success(self):
        # Clear search input
        self.entry_main_search.delete(0, "end")
        self.online_movies_list = []
        self.refresh_gallery()
        messagebox.showinfo("Erfolg", "Film wurde erfolgreich zu deiner Bibliothek hinzugefügt!")

    # --- OVERLAY HANDLING ---
    def _close_active_overlay(self):
        if self.active_overlay and self.active_overlay.winfo_exists():
            self.active_overlay.destroy()
        self.active_overlay = None

    def _show_movie_details(self, movie_id: int):
        self._close_active_overlay()
        movie_data = self.db_manager.get_movie(movie_id)
        if not movie_data:
            return
            
        self.active_overlay = DetailOverlay(self, movie_data,
                                            on_close_callback=self._close_active_overlay,
                                            on_delete_callback=self._delete_movie,
                                            on_edit_callback=self._show_edit_overlay)
        self.active_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.active_overlay.lift()

    def _show_add_overlay(self):
        self._close_active_overlay()
        self.active_overlay = AddMovieOverlay(self, self.tmdb_client,
                                              on_add_callback=self._add_movie,
                                              on_close_callback=self._close_active_overlay)
        self.active_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.active_overlay.lift()
        
    def _show_edit_overlay(self, movie: dict):
        self._close_active_overlay()
        self.active_overlay = EditMovieOverlay(self, movie,
                                               on_save_callback=self._update_movie,
                                               on_close_callback=self._close_active_overlay)
        self.active_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.active_overlay.lift()

    def _show_settings_overlay(self):
        self._close_active_overlay()
        self.active_overlay = SettingsOverlay(self, self.tmdb_client,
                                              on_close_callback=self._close_active_overlay)
        self.active_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.active_overlay.lift()

    # --- DATABASE CALLBACKS ---
    def _add_movie(self, movie_data: dict):
        self.db_manager.add_movie(movie_data)
        self.refresh_gallery()
        
    def _update_movie(self, movie_id: int, movie_data: dict):
        self.db_manager.update_movie(movie_id, movie_data)
        self.refresh_gallery()
        # Re-open details after edit
        self._show_movie_details(movie_id)
        
    def _delete_movie(self, movie_id: int):
        self.db_manager.delete_movie(movie_id)
        self._close_active_overlay()
        self.refresh_gallery()

    def _trigger_online_search_from_main(self, query):
        self._show_add_overlay()
        if hasattr(self.active_overlay, "entry_search"):
            self.active_overlay.entry_search.delete(0, "end")
            self.active_overlay.entry_search.insert(0, query)
            self.active_overlay._perform_online_search()

    def _on_view_changed(self, view_mode):
        self.view_mode = view_mode
        if view_mode == "Galerie":
            if hasattr(self, "table_container") and self.table_container.winfo_exists():
                self.table_container.pack_forget()
            self.gallery_scroll.pack(fill="both", expand=True, padx=20, pady=(10, 20))
            self.refresh_gallery()
        else:
            self.gallery_scroll.pack_forget()
            self._show_table_view()

    def _show_table_view(self):
        if hasattr(self, "table_container") and self.table_container.winfo_exists():
            try:
                self.table_container.destroy()
            except Exception:
                pass
                
        self.table_container = ctk.CTkFrame(self, fg_color="transparent")
        self.table_container.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        import tkinter.ttk as ttk
        
        style = ttk.Style()
        style.theme_use("default")
        
        style.configure("Treeview",
                        background=PANEL_COLOR,
                        foreground=TEXT_PRIMARY,
                        rowheight=30,
                        fieldbackground=PANEL_COLOR,
                        bordercolor=CARD_BORDER,
                        borderwidth=0)
        style.map('Treeview',
                  background=[('selected', ACCENT_COLOR)],
                  foreground=[('selected', '#000000')])
                  
        style.configure("Treeview.Heading",
                        background="#1E1E26",
                        foreground=TEXT_PRIMARY,
                        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', ACCENT_COLOR)],
                  foreground=[('active', '#000000')])
                  
        scrollbar = ctk.CTkScrollbar(self.table_container, orientation="vertical")
        scrollbar.pack(side="right", fill="y")
        
        columns = ("id", "titel", "jahr", "genre", "laufzeit", "fsk", "regisseur", "filmreihe", "land")
        self.tree = ttk.Treeview(self.table_container, columns=columns, show="headings", yscrollcommand=scrollbar.set, selectmode="browse")
        
        scrollbar.configure(command=self.tree.yview)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("titel", text="Titel / Name")
        self.tree.heading("jahr", text="Jahr")
        self.tree.heading("genre", text="Genre")
        self.tree.heading("laufzeit", text="Laufzeit (Min.)")
        self.tree.heading("fsk", text="FSK")
        self.tree.heading("regisseur", text="Regisseur")
        self.tree.heading("filmreihe", text="Filmreihe")
        self.tree.heading("land", text="Land")
        
        self.tree.column("id", width=40, minwidth=40, anchor="center")
        self.tree.column("titel", width=220, minwidth=150, anchor="w")
        self.tree.column("jahr", width=60, minwidth=60, anchor="center")
        self.tree.column("genre", width=140, minwidth=100, anchor="w")
        self.tree.column("laufzeit", width=95, minwidth=80, anchor="center")
        self.tree.column("fsk", width=60, minwidth=60, anchor="center")
        self.tree.column("regisseur", width=120, minwidth=100, anchor="w")
        self.tree.column("filmreihe", width=110, minwidth=80, anchor="w")
        self.tree.column("land", width=90, minwidth=70, anchor="center")
        
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind("<Double-1>", self._on_table_double_click)
        self._refresh_table_data()

    def _on_table_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        if values:
            movie_id = int(values[0])
            self._show_movie_details(movie_id)

    def _refresh_table_data(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
            
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for m in self.movies_list:
            self.tree.insert("", "end", values=(
                m.get("id", ""),
                m.get("titel", "Unbekannt"),
                m.get("jahr") or "k.A.",
                m.get("genre_richtung", "k.A."),
                f"{m.get('laufzeit_min', 0)} Min." if m.get('laufzeit_min') else "k.A.",
                m.get("fsk", "k.A."),
                m.get("regisseur", "k.A."),
                m.get("filmreihe", "-") or "-",
                m.get("produktionsland", "k.A.")
            ))

    def check_for_updates_background(self):
        """Spawns a background thread to check for updates from GitHub."""
        def run_check():
            from api import check_for_update, load_github_token
            token = load_github_token()
            if not token:
                print("GitHub Token nicht konfiguriert - Live-Update deaktiviert.")
                return
            
            try:
                remote_version = check_for_update(APP_VERSION)
                if remote_version:
                    # Found update! Trigger prompt on main thread
                    self.after(0, lambda: self.prompt_update(remote_version))
            except Exception as e:
                print(f"Fehler bei automatischem Update-Check: {e}")
                
        threading.Thread(target=run_check, daemon=True).start()

    def prompt_update(self, remote_version: str):
        """Prompts the user if they want to install the update."""
        msg = f"Ein neues Update (Version {remote_version}) ist auf GitHub verfügbar!\n\n" \
              f"Möchten Sie CinePalast Setup jetzt herunterladen, installieren und die App neu starten?"
        if messagebox.askyesno("Update Verfügbar", msg):
            self.start_update_download()

    def start_update_download(self):
        """Shows download overlay and starts background update thread."""
        self.update_overlay = UpdateDownloadOverlay(self)
        self.update_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.update()
        
        def run_download():
            import os
            import sys
            from api import load_github_token, download_update_installer
            token = load_github_token()
            dest_exe = "CinePalastSetup_Update.exe"
            
            # Progress callback to update UI thread
            def progress_cb(downloaded, total_size):
                self.after(0, lambda: self.update_overlay.update_progress(downloaded, total_size))
                
            try:
                download_update_installer(token, dest_exe, progress_cb)
                
                # Check if file exists and has size
                if os.path.exists(dest_exe) and os.path.getsize(dest_exe) > 1024 * 1024:
                    self.after(0, lambda: self.finalize_update(dest_exe))
                else:
                    raise Exception("Heruntergeladene Datei ist ungültig oder zu klein.")
            except Exception as e:
                self.after(0, lambda err=e: self.handle_update_error(err))
                
        threading.Thread(target=run_download, daemon=True).start()

    def finalize_update(self, exe_path: str):
        """Launches the downloaded installer and shuts down the app."""
        if hasattr(self, 'update_overlay') and self.update_overlay.winfo_exists():
            self.update_overlay.destroy()
        
        # Confirm and start installer
        messagebox.showinfo("Update bereit", "Das Update wurde erfolgreich heruntergeladen. "
                                             "Der Installer wird jetzt gestartet und CinePalast wird geschlossen.")
        try:
            import os
            import sys
            os.startfile(exe_path)
            sys.exit(0)
        except Exception as e:
            messagebox.showerror("Fehler beim Start", f"Der Installer konnte nicht gestartet werden: {e}")

    def handle_update_error(self, error: Exception):
        """Cleans up overlay and notifies the user of download error."""
        if hasattr(self, 'update_overlay') and self.update_overlay.winfo_exists():
            self.update_overlay.destroy()
        messagebox.showerror("Update-Fehler", f"Fehler beim Herunterladen des Updates:\n{str(error)}")

    def _show_suggestions(self, matches):
        """Displays a floating suggestions list overlay directly below the search bar."""
        if not matches:
            self._hide_suggestions()
            return
            
        # Limit to top 5 results
        matches = matches[:5]
        
        # Get coordinates of the entry_main_search relative to the main window
        entry = self.entry_main_search
        x = entry.winfo_x()
        y = entry.winfo_y()
        w = entry.winfo_width()
        h = entry.winfo_height()
        
        # Walk up the widget parent tree to find the position relative to self
        parent = entry.master
        while parent and parent != self:
            x += parent.winfo_x()
            y += parent.winfo_y()
            parent = parent.master
            
        if not hasattr(self, "suggestions_frame") or not self.suggestions_frame or not self.suggestions_frame.winfo_exists():
            self.suggestions_frame = ctk.CTkFrame(self, fg_color=PANEL_COLOR, border_width=2, border_color=ACCENT_COLOR, corner_radius=10)
            
        # Position Suggestions Frame exactly under the search bar dynamically
        if w < 10:
            self.suggestions_frame.place(relx=0.25, y=70, relwidth=0.5, height=len(matches) * 55 + 10)
        else:
            self.suggestions_frame.place(x=x, y=y + h + 5, width=w, height=len(matches) * 55 + 10)
            
        self.suggestions_frame.lift() # Bring to front
        
        # Clear old suggestion rows
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
            
        for m in matches:
            row = ctk.CTkFrame(self.suggestions_frame, fg_color="transparent", height=50, corner_radius=6)
            row.pack(fill="x", padx=5, pady=2)
            row.pack_propagate(False)
            
            movie_id = m["id"]
            def make_click_handler(mid):
                return lambda e: (self._show_movie_details(mid), self._hide_suggestions())
            handler = make_click_handler(movie_id)
            
            # Left: Poster Thumbnail
            thumb_path = m.get("poster_pfad")
            thumbnail = get_ctk_image(thumb_path, (30, 45), m.get("titel"), "poster")
            lbl_thumb = ctk.CTkLabel(row, image=thumbnail, text="")
            lbl_thumb.pack(side="left", padx=10, pady=2)
            
            # Center: Title
            title_text = m.get("titel", "Unbekannt")
            year_val = m.get("jahr")
            if year_val and f"({year_val})" not in title_text:
                title_text = f"{title_text} ({year_val})"
            
            lbl_title = ctk.CTkLabel(row, text=title_text, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY, anchor="w")
            lbl_title.pack(side="left", fill="both", expand=True, padx=5)
            
            # Right: FSK Badge
            fsk_val = m.get("fsk", "k.A.")
            fsk_img = get_fsk_image(fsk_val, size=(22, 22))
            if fsk_img:
                fsk_badge = ctk.CTkLabel(row, image=fsk_img, text="")
            else:
                fsk_bg, fsk_fg, fsk_lbl = get_fsk_colors(fsk_val)
                fsk_badge = ctk.CTkLabel(row, text=fsk_lbl, font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                                              fg_color=fsk_bg, text_color=fsk_fg, corner_radius=4, width=42, height=18)
            fsk_badge.pack(side="right", padx=15, pady=15)
            
            # Hover animations
            def on_enter(e, r=row):
                r.configure(fg_color="#1E1E26")
            def on_leave(e, r=row):
                r.configure(fg_color="transparent")
                
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
            
            for widget in [row, lbl_thumb, lbl_title, fsk_badge]:
                widget.bind("<Button-1>", handler)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)

    def _hide_suggestions(self):
        """Hides the floating suggestions list overlay."""
        if hasattr(self, "suggestions_frame") and self.suggestions_frame and self.suggestions_frame.winfo_exists():
            self.suggestions_frame.place_forget()

    def _on_window_click(self, event):
        """Dismiss suggestions frame if clicking outside of it."""
        if hasattr(self, "suggestions_frame") and self.suggestions_frame and self.suggestions_frame.winfo_exists():
            try:
                # Get the widget that was clicked
                widget = event.widget
                # If widget is not suggestions_frame and suggestions_frame is not a parent of it, hide suggestions
                if widget != self.entry_main_search:
                    is_inside = False
                    parent = widget
                    while parent:
                        if parent == self.suggestions_frame:
                            is_inside = True
                            break
                        parent = parent.master
                    if not is_inside:
                        self._hide_suggestions()
            except Exception:
                pass


