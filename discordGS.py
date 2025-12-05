import tkinter as tk
from tkinter import messagebox
import os
import sys
import shutil
import subprocess
import time
import tempfile
import math
import ctypes 
import webbrowser
import json

# --- KONFIGURASI TEMA MODERN (Deep Dark / Cyberpunk Minimalist) ---
THEME = {
    "bg_main": "#121212",       # Hampir hitam
    "bg_surface": "#1E1E1E",    # Abu gelap untuk card/input
    "bg_popup": "#252525",      # Abu sedikit terang untuk dropdown
    "primary": "#BB86FC",       # Ungu pastel (aksen modern)
    "primary_dark": "#3700B3",  # Ungu gelap untuk hover
    "secondary": "#00E676",     # Hijau terang (Online Status)
    "secondary_dim": "#004D40", # Hijau gelap
    "danger": "#CF6679",        # Merah soft
    "danger_hover": "#B00020",  # Merah gelap
    "blue": "#2979FF",          # Biru modern (Tombol Source)
    "blue_hover": "#0055FF",    # Biru gelap hover
    "text_main": "#E1E1E1",     # Putih tulang
    "text_dim": "#B0B0B0",      # Abu muda
    "font_family": "Segoe UI"
}

HISTORY_FILE = "game_history.json"

# --- FUNGSI DUMMY MODE (CHILD PROCESS) ---
def run_dummy_mode():
    """
    Fungsi ini akan dijalankan oleh proses 'palsu' (file yang dicopy menjadi nama game).
    Ini menggantikan logika '-c' script string yang lama agar kompatibel dengan PyInstaller.
    """
    try:
        # Kita buat window tkinter minimalis
        root = tk.Tk()
        # Set judul sesuai nama file executable saat ini (misal: Valorant.exe)
        current_exe_name = os.path.basename(sys.executable)
        root.title(current_exe_name)
        root.geometry("300x100")
        root.configure(bg="#121212")
        
        # Pesan status
        lbl = tk.Label(root, text=f"Game Simulator Running...\n({current_exe_name})", 
                       fg="#03DAC6", bg="#121212", font=("Segoe UI", 10))
        lbl.pack(expand=True)
        
        # Minimize window agar tidak mengganggu, tapi tetap ada di taskbar
        # Gunakan after agar event loop jalan dulu baru minimize
        root.after(100, root.iconify)
        
        # Bind close event agar proses benar-benar mati saat ditutup manual
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        
        root.mainloop()
    except Exception as e:
        # Jika terjadi error di background process, kita bisa log atau abaikan
        pass

def hex_to_rgb(hex_val):
    hex_val = hex_val.lstrip('#')
    return tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_tuple):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb_tuple[0]), int(rgb_tuple[1]), int(rgb_tuple[2]))

def interpolate_color(start_hex, end_hex, t):
    """Interpolasi linear antara dua warna untuk animasi smooth"""
    s_rgb = hex_to_rgb(start_hex)
    e_rgb = hex_to_rgb(end_hex)
    cur_rgb = (
        s_rgb[0] + (e_rgb[0] - s_rgb[0]) * t,
        s_rgb[1] + (e_rgb[1] - s_rgb[1]) * t,
        s_rgb[2] + (e_rgb[2] - s_rgb[2]) * t
    )
    return rgb_to_hex(cur_rgb)

class SmoothButton(tk.Canvas):
    """Tombol Custom dengan animasi hover yang fluid"""
    def __init__(self, master, text, command, width=200, height=45, bg_color=THEME["primary"], hover_color=THEME["primary_dark"], text_color="black"):
        super().__init__(master, width=width, height=height, bg=THEME["bg_main"], highlightthickness=0)
        self.command = command
        self.text = text
        self.base_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        # State
        self.is_disabled = False
        self.animating = False
        self.anim_start_time = 0
        self.target_hex = bg_color
        self.start_hex = bg_color

        # Draw Elements
        self.rect = self.create_rectangle(2, 2, width-2, height-2, fill=bg_color, outline="", width=0)
        self.label = self.create_text(width/2, height/2, text=text, fill=text_color, font=(THEME["font_family"], 9, "bold"))
        
        # Bindings
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
        # Ubah kursor
        self.config(cursor="hand2")

    def set_state(self, state):
        """Mengatur status aktif/mati tombol secara visual dan fungsional"""
        self.animating = False
        
        if state == "disabled":
            if not self.is_disabled: 
                self.is_disabled = True
                self.itemconfig(self.rect, fill="#333333")
                self.itemconfig(self.label, fill="#555555")
                self.config(cursor="arrow")
        else:
            if self.is_disabled: 
                self.is_disabled = False
                self.itemconfig(self.rect, fill=self.base_color)
                self.itemconfig(self.label, fill=self.text_color)
                self.config(cursor="hand2")

    def on_enter(self, e):
        if self.is_disabled: return
        self.start_color_anim(self.hover_color)

    def on_leave(self, e):
        if self.is_disabled: return
        self.start_color_anim(self.base_color)

    def on_click(self, e):
        if not self.is_disabled and self.command:
            self.command()

    def start_color_anim(self, target_hex):
        if self.is_disabled: return 
        
        self.target_hex = target_hex
        self.start_hex = self.itemcget(self.rect, "fill")
        self.anim_start_time = time.time()
        if not self.animating:
            self.animating = True
            self.animate()

    def animate(self):
        if not self.animating: return
        if self.is_disabled: 
            self.animating = False
            return
        
        # Durasi animasi 200ms
        elapsed = (time.time() - self.anim_start_time) / 0.2
        if elapsed >= 1.0:
            elapsed = 1.0
            self.animating = False
            self.itemconfig(self.rect, fill=self.target_hex)
        else:
            new_col = interpolate_color(self.start_hex, self.target_hex, elapsed)
            self.itemconfig(self.rect, fill=new_col)
            self.after(16, self.animate) # ~60 FPS

class GameSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Presence Simulator")
        self.root.geometry("450x420")
        self.root.configure(bg=THEME["bg_main"])
        
        # Fade In Effect variables
        self.alpha = 0.0
        self.root.attributes("-alpha", self.alpha)
        
        # Frameless Logic
        self.root.overrideredirect(True)
        self.center_window()
        self.force_taskbar_appearance() 

        # Drag Logic
        self.offset_x = 0
        self.offset_y = 0

        # App Logic
        self.running_process = None
        self.temp_exe_name = "" 
        self.anim_job = None
        self.pulse_time = 0
        self.history = self.load_history() # Load History
        
        # Input Variable untuk Real-time Tracking
        self.game_name_var = tk.StringVar()
        self.game_name_var.trace_add("write", self.update_button_states)

        self.setup_ui()
        self.fade_in_window()
        
        # Set initial value based on history or default
        last_game = self.history[0] if self.history else "Valorant.exe"
        self.game_name_var.set(last_game)
        
        # Global click bind to close history
        self.root.bind("<Button-1>", self.on_root_click)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_history(self):
        """Memuat riwayat dari file JSON"""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except:
                return []
        return []

    def save_history(self):
        """Menyimpan riwayat ke file JSON"""
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.history, f)
        except:
            pass

    def add_to_history(self, game_name):
        """Menambahkan game ke riwayat (Unik & FIFO)"""
        if game_name in self.history:
            self.history.remove(game_name)
        self.history.insert(0, game_name)
        
        # Batasi riwayat hanya 5 item terakhir
        if len(self.history) > 5:
            self.history = self.history[:5]
        
        self.save_history()

    def force_taskbar_appearance(self):
        try:
            if os.name == 'nt':
                GWL_EXSTYLE = -20
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                if hwnd == 0: hwnd = self.root.winfo_id()
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = style & ~WS_EX_TOOLWINDOW
                style = style | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                self.root.withdraw()
                self.root.after(10, self.root.deiconify)
        except Exception as e:
            print(f"Taskbar fix error: {e}")

    def center_window(self):
        self.root.update_idletasks()
        w, h = 450, 420
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{int(x)}+{int(y)}')

    def fade_in_window(self):
        if self.alpha < 1.0:
            self.alpha += 0.05
            self.root.attributes("-alpha", self.alpha)
            self.root.after(20, self.fade_in_window)

    def setup_ui(self):
        # --- TITLE BAR ---
        title_bar = tk.Frame(self.root, bg=THEME["bg_main"], height=40)
        title_bar.pack(fill="x", side="top", pady=5)
        title_bar.bind("<ButtonPress-1>", self.start_move)
        title_bar.bind("<B1-Motion>", self.do_move)

        lbl_icon = tk.Label(title_bar, text="🎮", bg=THEME["bg_main"], fg=THEME["primary"], font=("Segoe UI Emoji", 12))
        lbl_icon.pack(side="left", padx=(15, 5))
        
        lbl_title = tk.Label(title_bar, text="DISCORD GAME SPOOFER", bg=THEME["bg_main"], fg=THEME["text_main"], 
                             font=(THEME["font_family"], 10, "bold"))
        lbl_title.pack(side="left")

        # Tombol Close
        btn_close = tk.Label(title_bar, text="✕", bg=THEME["bg_main"], fg=THEME["text_dim"], font=("Arial", 12))
        btn_close.pack(side="right", padx=15)
        btn_close.bind("<Button-1>", lambda e: self.on_close())
        btn_close.bind("<Enter>", lambda e: btn_close.config(fg=THEME["danger"]))
        btn_close.bind("<Leave>", lambda e: btn_close.config(fg=THEME["text_dim"]))

        # --- MAIN CONTENT ---
        main_frame = tk.Frame(self.root, bg=THEME["bg_main"])
        main_frame.pack(fill="both", expand=True, padx=30, pady=5)

        # --- STATUS AREA ---
        self.status_container = tk.Frame(main_frame, bg=THEME["bg_main"])
        self.status_container.pack(pady=(5, 15))

        self.status_canvas = tk.Canvas(self.status_container, width=16, height=16, bg=THEME["bg_main"], highlightthickness=0)
        self.status_canvas.pack(side="left", padx=(0, 8))
        self.status_dot = self.status_canvas.create_oval(3, 3, 13, 13, fill="#444444", outline="")

        self.lbl_status_text = tk.Label(self.status_container, text="OFFLINE / IDLE", bg=THEME["bg_main"], fg=THEME["text_dim"], 
                                   font=(THEME["font_family"], 9, "bold"))
        self.lbl_status_text.pack(side="left")

        # --- INPUT AREA ---
        self.input_container = tk.Frame(main_frame, bg=THEME["bg_main"])
        self.input_container.pack(fill="x", pady=10)

        tk.Label(self.input_container, text="Target Executable Name", bg=THEME["bg_main"], fg=THEME["primary"], 
                 font=(THEME["font_family"], 8)).pack(anchor="w")
        
        self.entry_name = tk.Entry(self.input_container, textvariable=self.game_name_var, 
                                   font=(THEME["font_family"], 14), bg=THEME["bg_surface"], 
                                   fg="white", relief="flat", insertbackground="white")
        self.entry_name.pack(fill="x", ipady=5)
        
        # BINDING UNTUK HISTORY
        self.entry_name.bind("<Button-1>", self.show_history_popup)
        self.entry_name.bind("<FocusIn>", self.show_history_popup)
        
        tk.Frame(self.input_container, bg=THEME["primary"], height=2).pack(fill="x")

        # --- HISTORY LISTBOX (Hidden by default) ---
        self.history_frame = tk.Frame(self.root, bg=THEME["primary"]) # Frame tipis untuk border ungu
        self.history_listbox = tk.Listbox(self.history_frame, font=(THEME["font_family"], 11),
                                          bg=THEME["bg_popup"], fg=THEME["text_main"],
                                          selectbackground=THEME["primary"], selectforeground="white",
                                          highlightthickness=0, bd=0, activestyle="none", height=5)
        self.history_listbox.pack(fill="both", expand=True, padx=1, pady=1)
        self.history_listbox.bind("<<ListboxSelect>>", self.on_history_select)

        # --- ACTIONS AREA ---
        action_frame = tk.Frame(main_frame, bg=THEME["bg_main"])
        action_frame.pack(fill="x", pady=15)

        self.btn_start = SmoothButton(action_frame, text="LAUNCH GAME", command=self.start_simulation, 
                                      width=220, height=45, bg_color=THEME["secondary"], hover_color="#00C853", text_color="black")
        self.btn_start.pack(pady=5)

        self.btn_stop = SmoothButton(action_frame, text="STOP PROCESS", command=self.stop_simulation, 
                                     width=220, height=45, bg_color=THEME["danger"], hover_color=THEME["danger_hover"], text_color="black")
        self.btn_stop.pack(pady=5)
        
        self.update_button_states()

        # --- FOOTER (Source Code Button) ---
        footer_frame = tk.Frame(self.root, bg=THEME["bg_main"])
        footer_frame.pack(side="bottom", pady=25)
        
        self.btn_source = SmoothButton(footer_frame, text="SOURCE CODE", 
                                       command=lambda: webbrowser.open("https://github.com/DEX-1101/discord-game-spoofer"),
                                       width=140, height=32, 
                                       bg_color=THEME["blue"], 
                                       hover_color=THEME["blue_hover"],
                                       text_color="white")
        self.btn_source.pack()

    # --- HISTORY LOGIC ---
    def show_history_popup(self, event=None):
        if not self.history: return # Jangan muncul jika kosong
        
        # Reset listbox
        self.history_listbox.delete(0, tk.END)
        for item in self.history:
            self.history_listbox.insert(tk.END, item)
            
        # Hitung posisi absolute entry
        x = self.entry_name.winfo_rootx() - self.root.winfo_rootx()
        y = self.entry_name.winfo_rooty() - self.root.winfo_rooty() + self.entry_name.winfo_height()
        w = self.entry_name.winfo_width()
        
        # Tampilkan popup di atas UI lain (menggunakan place)
        self.history_frame.place(x=x, y=y, width=w)
        self.history_frame.lift() # Pastikan paling atas

    def hide_history_popup(self):
        self.history_frame.place_forget()

    def on_history_select(self, event):
        selection = self.history_listbox.curselection()
        if selection:
            data = self.history_listbox.get(selection[0])
            self.game_name_var.set(data)
            self.hide_history_popup()
            self.root.focus() # Hilangkan fokus dari entry agar popup tidak muncul lagi seketika

    def on_root_click(self, event):
        """Menutup popup jika klik di luar area entry atau listbox"""
        try:
            widget = event.widget
            # Jika yang diklik bukan entry dan bukan bagian dari listbox
            if widget != self.entry_name and widget != self.history_listbox:
                self.hide_history_popup()
        except:
            pass

    # --- LOGIC UTAMA ---
    def update_button_states(self, *args):
        # FIX: Sembunyikan history popup saat user mulai mengetik (trace triggered)
        self.hide_history_popup()

        input_text = self.game_name_var.get().strip()
        is_running = self.running_process is not None

        if is_running:
            self.btn_start.set_state("disabled")
            self.btn_stop.set_state("normal")
            self.entry_name.config(state="disabled", disabledbackground=THEME["bg_main"], disabledforeground=THEME["secondary"])
            self.hide_history_popup() # Sembunyikan jika game jalan
        else:
            self.btn_stop.set_state("disabled")
            self.entry_name.config(state="normal", bg=THEME["bg_surface"], fg="white")
            if input_text:
                self.btn_start.set_state("normal")
            else:
                self.btn_start.set_state("disabled")

    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y
        self.hide_history_popup() # Tutup popup saat drag

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self.offset_x
        y = self.root.winfo_y() + event.y - self.offset_y
        self.root.geometry(f"+{x}+{y}")

    def animate_status(self):
        if self.running_process:
            self.pulse_time += 0.15
            intensity = (math.sin(self.pulse_time) + 1) / 2 
            col = interpolate_color("#006400", "#00FF00", intensity)
            
            self.status_canvas.itemconfig(self.status_dot, fill=col)
            
            game_name = os.path.basename(self.temp_exe_name)
            self.lbl_status_text.config(text=f"PLAYING: {game_name}", fg=THEME["text_main"])
            
            self.anim_job = self.root.after(50, self.animate_status)
        else:
            self.lbl_status_text.config(text="OFFLINE / IDLE", fg=THEME["text_dim"])
            self.status_canvas.itemconfig(self.status_dot, fill="#444444")

    def start_simulation(self):
        filename_input = self.game_name_var.get().strip()
        if not filename_input: return
        if not filename_input.endswith(".exe"): filename_input += ".exe"

        # Simpan ke history sebelum jalan
        self.add_to_history(filename_input)

        temp_dir = tempfile.gettempdir()
        target_path = os.path.join(temp_dir, filename_input)

        # Hapus file lama jika ada
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except:
                messagebox.showerror("Error", "File is locked. Close it in Task Manager.")
                return

        try:
            # COPY EXECUTABLE SAAT INI (Baik itu python.exe atau Aplikasi.exe)
            shutil.copy(sys.executable, target_path)
            self.temp_exe_name = target_path

            # LOGIKA UNTUK MENJALANKAN DUMMY PROCESS
            # Jika dijalankan sebagai EXE (frozen), kita tidak bisa pakai -c.
            # Kita harus pakai argumen khusus --dummy-mode.
            
            if getattr(sys, 'frozen', False):
                # MODE EXE (Compiled)
                # Jalankan target_path dengan argumen --dummy-mode
                cmd = [self.temp_exe_name, "--dummy-mode"]
            else:
                # MODE SCRIPT (Development)
                # Jika development, sys.executable adalah python.exe
                # Kita harus menyertakan script ini sendiri
                current_script = os.path.abspath(__file__)
                cmd = [self.temp_exe_name, current_script, "--dummy-mode"]
            
            # Jalankan tanpa creationflags khusus agar window behavior normal (biar child handle sendiri)
            # Jika ingin menyembunyikan console di dev mode, bisa pakai flags, tapi untuk PyInstaller --windowed aman.
            creation_flags = 0
            if os.name == 'nt':
                 # Opsional: Jika ingin benar-benar no window untuk process, tapi kita punya GUI di child
                 # jadi biarkan default atau gunakan DETACHED_PROCESS jika perlu.
                 # 0x08000000 = CREATE_NO_WINDOW
                 creation_flags = 0x08000000 
            
            self.running_process = subprocess.Popen(cmd, creationflags=creation_flags)

            self.pulse_time = 0
            self.animate_status()
            self.update_button_states()

        except Exception as e:
            messagebox.showerror("Fail", str(e))
            self.cleanup()

    def stop_simulation(self):
        # UPDATE: Gunakan TASKKILL untuk mematikan tree process secara paksa
        # Ini mengatasi masalah pada PyInstaller one-file dimana child process (Python payload)
        # tidak ikut mati saat terminate() dipanggil pada parent (Bootloader).
        if self.running_process:
            try:
                if os.name == 'nt':
                    # /F = Force, /T = Tree (Kill children), /PID = Process ID
                    # Gunakan creationflags=0x08000000 untuk menyembunyikan console window taskkill
                    subprocess.call(
                        ["taskkill", "/F", "/T", "/PID", str(self.running_process.pid)],
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL,
                        creationflags=0x08000000
                    )
                else:
                    self.running_process.terminate()
            except Exception:
                # Fallback jika taskkill gagal
                try: self.running_process.terminate() 
                except: pass
            
            self.running_process = None
        
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None
        
        self.cleanup()
        
        # Reset Status
        self.lbl_status_text.config(text="OFFLINE / IDLE", fg=THEME["text_dim"])
        self.status_canvas.itemconfig(self.status_dot, fill="#444444")
        
        self.update_button_states()

    def cleanup(self):
        if self.temp_exe_name and os.path.exists(self.temp_exe_name):
            try:
                for _ in range(3):
                    try: os.remove(self.temp_exe_name); break
                    except: time.sleep(0.5)
            except: pass

    def on_close(self):
        self.stop_simulation()
        self.root.destroy()

if __name__ == "__main__":
    # CEK ARGUMEN UNTUK MENENTUKAN MODE (MAIN APP atau DUMMY GAME)
    if "--dummy-mode" in sys.argv:
        run_dummy_mode()
    else:
        root = tk.Tk()
        app = GameSimulatorApp(root)
        root.mainloop()