import os
import sys
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk
import urllib.parse
from config import TOAST_TIMEOUT_SECONDS, DEFAULT_DOWNLOAD_DIR, DEFAULT_VIDEO_QUALITY, AVAILABLE_QUALITIES

def detect_platform(url):
    """Retorna badge e cor da plataforma com base na URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "▶ YouTube", "#ef4444" # Vermelho
    elif "instagram.com" in url_lower:
        return "📷 Instagram", "#e1306c" # Rosa/Instagram
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "𝕏 X (Twitter)", "#0f1419" # Preto/X
    elif "tiktok.com" in url_lower:
        return "🎵 TikTok", "#00f2fe" # Ciano
    elif "reddit.com" in url_lower:
        return "🤖 Reddit", "#ff4500" # Laranja
    else:
        return "🌐 Vídeo Web", "#3b82f6" # Azul

class VideoToast:
    def __init__(self, root, url, info, on_download_request, on_dismiss, default_quality=DEFAULT_VIDEO_QUALITY):
        self.root = root
        self.url = url
        self.info = info or {}
        self.on_download_request = on_download_request
        self.on_dismiss = on_dismiss
        self.selected_quality = default_quality if default_quality in AVAILABLE_QUALITIES else "best"
        self.is_downloading = False
        self.timer_id = None
        self.result_filename = None

        # Cria janela Toplevel
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#18181b") # Zinc dark

        # Dimensões e posicionamento (canto inferior direito)
        self.width = 410
        self.height = 220
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        pos_x = screen_w - self.width - 24
        pos_y = screen_h - self.height - 60
        self.win.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        self._build_ui()
        self._start_autoclose_timer(TOAST_TIMEOUT_SECONDS)

    def _build_ui(self):
        # Container com borda
        border_frame = tk.Frame(self.win, bg="#3f3f46", bd=1)
        border_frame.pack(fill="both", expand=True, padx=1, pady=1)

        container = tk.Frame(border_frame, bg="#18181b", padx=14, pady=12)
        container.pack(fill="both", expand=True)

        # Cabeçalho: Badge da plataforma + Fechar
        header_frame = tk.Frame(container, bg="#18181b")
        header_frame.pack(fill="x", pady=(0, 6))

        badge_text, badge_color = detect_platform(self.url)
        badge_lbl = tk.Label(
            header_frame,
            text=f"  {badge_text}  ",
            bg=badge_color,
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat"
        )
        badge_lbl.pack(side="left")

        close_btn = tk.Label(
            header_frame,
            text="✕",
            bg="#18181b",
            fg="#71717a",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2"
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ffffff"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#71717a"))

        # Título do vídeo
        title_text = self.info.get("title") or self.url
        if len(title_text) > 85:
            title_text = title_text[:82] + "..."

        self.title_lbl = tk.Label(
            container,
            text=title_text,
            bg="#18181b",
            fg="#f4f4f5",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
            wraplength=380
        )
        self.title_lbl.pack(fill="x", pady=(0, 8))

        # Painel dinâmico (Botões ou Progresso)
        self.dynamic_frame = tk.Frame(container, bg="#18181b")
        self.dynamic_frame.pack(fill="x", expand=True)

        self._show_action_buttons()

    def _set_quality(self, q):
        self.selected_quality = q
        self._start_autoclose_timer(TOAST_TIMEOUT_SECONDS)
        self._show_action_buttons()

    def _show_action_buttons(self):
        # Limpa dynamic_frame
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        # Linha de Seleção de Qualidade
        quality_frame = tk.Frame(self.dynamic_frame, bg="#18181b")
        quality_frame.pack(fill="x", pady=(0, 8))

        q_lbl = tk.Label(
            quality_frame,
            text="Resolução:",
            bg="#18181b",
            fg="#a1a1aa",
            font=("Segoe UI", 8)
        )
        q_lbl.pack(side="left", padx=(0, 6))

        quality_options = [
            ("best", "Máx (4K)"),
            ("1080p", "1080p"),
            ("720p", "720p"),
            ("480p", "480p")
        ]

        for q, label in quality_options:
            is_sel = (q == self.selected_quality)
            bg_col = "#2563eb" if is_sel else "#27272a"
            fg_col = "#ffffff" if is_sel else "#a1a1aa"

            btn_q = tk.Button(
                quality_frame,
                text=label,
                bg=bg_col,
                fg=fg_col,
                activebackground="#1d4ed8" if is_sel else "#3f3f46",
                activeforeground="#ffffff",
                font=("Segoe UI", 8, "bold" if is_sel else "normal"),
                relief="flat",
                cursor="hand2",
                padx=6,
                pady=1,
                command=lambda target_q=q: self._set_quality(target_q)
            )
            btn_q.pack(side="left", padx=2)

        # Linha de Ação Principal
        btn_row = tk.Frame(self.dynamic_frame, bg="#18181b")
        btn_row.pack(fill="x")

        # Rótulo do botão com a qualidade atual embutida
        q_tag = "Máx" if self.selected_quality == "best" else self.selected_quality
        video_btn_text = f"🎬 Vídeo ({q_tag})"

        # Botão Vídeo MP4
        btn_video = tk.Button(
            btn_row,
            text=video_btn_text,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            command=lambda: self._on_click_download("video")
        )
        btn_video.pack(side="left", padx=(0, 6), expand=True, fill="x")

        # Botão Áudio MP3
        btn_audio = tk.Button(
            btn_row,
            text="🎵 Áudio (MP3)",
            bg="#7c3aed",
            fg="#ffffff",
            activebackground="#6d28d9",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            command=lambda: self._on_click_download("audio")
        )
        btn_audio.pack(side="left", expand=True, fill="x")

    def _on_click_download(self, media_type):
        self._cancel_autoclose_timer()
        self.is_downloading = True

        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        # Label de status
        quality_str = self.selected_quality if media_type == "video" else "mp3"
        self.status_lbl = tk.Label(
            self.dynamic_frame,
            text=f"Iniciando download ({quality_str})...",
            bg="#18181b",
            fg="#a1a1aa",
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.status_lbl.pack(fill="x", pady=(0, 6))

        # Barra de progresso visual em Canvas
        self.progress_canvas = tk.Canvas(
            self.dynamic_frame,
            bg="#27272a",
            height=8,
            bd=0,
            highlightthickness=0
        )
        self.progress_canvas.pack(fill="x", pady=(0, 6))
        self.progress_rect = self.progress_canvas.create_rectangle(
            0, 0, 0, 8,
            fill="#3b82f6",
            width=0
        )

        # Dispara download passando a qualidade escolhida
        self.on_download_request(self.url, media_type, self.selected_quality, self)

    def update_progress(self, data):
        """Atualiza a interface com base no hook do yt-dlp."""
        if not self.win.winfo_exists():
            return

        status = data.get("status")
        if status == "downloading":
            pct = data.get("percent", 0)
            speed = data.get("speed_str", "")
            eta = data.get("eta_str", "")
            canvas_w = self.progress_canvas.winfo_width()
            bar_w = (pct / 100.0) * canvas_w
            self.progress_canvas.coords(self.progress_rect, 0, 0, bar_w, 8)

            txt = f"Baixando... {pct:.0f}%  •  {speed}"
            if eta and eta != "--":
                txt += f"  •  ETA: {eta}"
            self.status_lbl.config(text=txt, fg="#e4e4e7")

        elif status == "processing":
            self.progress_canvas.coords(self.progress_rect, 0, 0, self.progress_canvas.winfo_width(), 8)
            self.status_lbl.config(text="Processando e mesclando com FFmpeg...", fg="#38bdf8")

        elif status == "completed":
            self.result_filename = data.get("filename")
            self._show_completed_state()

        elif status == "error":
            err = data.get("error", "Erro desconhecido")
            self._show_error_state(err)

    def _show_completed_state(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        success_row = tk.Frame(self.dynamic_frame, bg="#18181b")
        success_row.pack(fill="x", pady=(2, 6))

        lbl = tk.Label(
            success_row,
            text="✅ Concluído com sucesso!",
            bg="#18181b",
            fg="#22c55e",
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        )
        lbl.pack(side="left")

        action_row = tk.Frame(self.dynamic_frame, bg="#18181b")
        action_row.pack(fill="x")

        # Botão abrir arquivo
        btn_open = tk.Button(
            action_row,
            text="▶ Abrir Arquivo",
            bg="#27272a",
            fg="#f4f4f5",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._open_file
        )
        btn_open.pack(side="left", padx=(0, 6))

        # Botão abrir pasta
        btn_folder = tk.Button(
            action_row,
            text="📂 Abrir Pasta",
            bg="#27272a",
            fg="#f4f4f5",
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=4,
            command=self._open_folder
        )
        btn_folder.pack(side="left")

        # Auto-fecha após 6 segundos de concluído
        self._start_autoclose_timer(6)

    def _show_error_state(self, error_msg):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        short_err = error_msg.split("\n")[0]
        if len(short_err) > 60:
            short_err = short_err[:57] + "..."

        lbl = tk.Label(
            self.dynamic_frame,
            text=f"⚠️ {short_err}",
            bg="#18181b",
            fg="#ef4444",
            font=("Segoe UI", 8),
            anchor="w"
        )
        lbl.pack(fill="x", pady=(2, 6))

        btn_close = tk.Button(
            self.dynamic_frame,
            text="Fechar",
            bg="#27272a",
            fg="#f4f4f5",
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            command=self.close
        )
        btn_close.pack(anchor="e")
        self._start_autoclose_timer(8)

    def _open_file(self):
        if self.result_filename and os.path.exists(self.result_filename):
            try:
                os.startfile(self.result_filename)
            except Exception:
                pass
        self.close()

    def _open_folder(self):
        target = self.result_filename if self.result_filename and os.path.exists(self.result_filename) else DEFAULT_DOWNLOAD_DIR
        try:
            if os.path.isfile(target):
                subprocess.Popen(f'explorer /select,"{os.path.abspath(target)}"')
            else:
                os.startfile(str(DEFAULT_DOWNLOAD_DIR))
        except Exception:
            pass
        self.close()

    def _start_autoclose_timer(self, seconds):
        self._cancel_autoclose_timer()
        self.timer_id = self.root.after(int(seconds * 1000), self.close)

    def _cancel_autoclose_timer(self):
        if self.timer_id:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None

    def close(self):
        self._cancel_autoclose_timer()
        try:
            self.win.destroy()
        except Exception:
            pass
        self.on_dismiss(self)

class ToastManager:
    """Gerenciador central de notificações visuais rodando em loop Tkinter."""
    def __init__(self, on_download_handler):
        self.on_download_handler = on_download_handler
        self.root = None
        self.task_queue = queue.Queue()
        self.active_toasts = []
        self.is_ready = threading.Event()

    def run(self):
        self.root = tk.Tk()
        self.root.withdraw() # Oculta janela raiz
        self.is_ready.set()

        # Agenda verificação periódica da fila
        self.root.after(100, self._process_queue)
        self.root.mainloop()

    def _process_queue(self):
        try:
            while not self.task_queue.empty():
                task = self.task_queue.get_nowait()
                action = task.get("action")
                if action == "show":
                    url = task["url"]
                    info = task["info"]
                    quality = task.get("quality", DEFAULT_VIDEO_QUALITY)
                    toast = VideoToast(
                        self.root,
                        url,
                        info,
                        self.on_download_handler,
                        self._on_toast_dismiss,
                        default_quality=quality
                    )
                    self.active_toasts.append(toast)
                elif action == "update_progress":
                    toast = task["toast"]
                    data = task["data"]
                    toast.update_progress(data)
                elif action == "quit":
                    self.root.quit()
                    return
        except Exception as e:
            print("Erro no processamento da fila UI:", e)

        if self.root:
            self.root.after(100, self._process_queue)

    def show_toast(self, url, info, quality=DEFAULT_VIDEO_QUALITY):
        self.task_queue.put({"action": "show", "url": url, "info": info, "quality": quality})

    def update_progress(self, toast, data):
        self.task_queue.put({"action": "update_progress", "toast": toast, "data": data})

    def _on_toast_dismiss(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)

    def stop(self):
        self.task_queue.put({"action": "quit"})
