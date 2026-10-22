import os
import sys
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk
import urllib.parse
from config import DEFAULT_VIDEO_QUALITY, AVAILABLE_QUALITIES, get_download_dir, get_toast_timeout

def detect_platform(url):
    """Retorna badge e cor da plataforma com base na URL."""
    hostname = (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    if hostname == "youtu.be" or hostname == "youtube.com" or hostname.endswith(".youtube.com"):
        return "▶ YouTube", "#ef4444" # Vermelho
    elif hostname == "instagram.com" or hostname.endswith(".instagram.com"):
        return "📷 Instagram", "#e1306c" # Rosa/Instagram
    elif hostname in {"twitter.com", "x.com"} or hostname.endswith(".twitter.com") or hostname.endswith(".x.com"):
        return "𝕏 X (Twitter)", "#0f1419" # Preto/X
    elif hostname == "tiktok.com" or hostname.endswith(".tiktok.com"):
        return "🎵 TikTok", "#00f2fe" # Ciano
    elif hostname == "reddit.com" or hostname.endswith(".reddit.com"):
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
        self.last_media_type = "video"
        self.cancel_action = None
        self.cancel_btn = None
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
        self.reposition(0)

        self._build_ui()
        self._start_autoclose_timer(get_toast_timeout())

    def reposition(self, index):
        if not self.win.winfo_exists():
            return
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        rows_per_column = max(1, (screen_h - 80) // (self.height + 12))
        column, row = divmod(index, rows_per_column)
        pos_x = max(8, screen_w - self.width - 24 - column * (self.width + 12))
        pos_y = max(8, screen_h - self.height - 60 - row * (self.height + 12))
        self.win.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

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
        self._start_autoclose_timer(get_toast_timeout())
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
        self.last_media_type = media_type

        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        # Label de status
        quality_str = self.selected_quality if media_type == "video" else "mp3"
        status_row = tk.Frame(self.dynamic_frame, bg="#18181b")
        status_row.pack(fill="x", pady=(0, 6))
        self.status_lbl = tk.Label(
            status_row,
            text=f"Adicionando à fila ({quality_str})...",
            bg="#18181b",
            fg="#a1a1aa",
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)
        self.cancel_btn = tk.Button(
            status_row,
            text="Cancelar",
            bg="#3f3f46",
            fg="#f4f4f5",
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            command=self._cancel_download,
        )
        self.cancel_btn.pack(side="right", padx=(6, 0))

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
        self.cancel_action = self.on_download_request(
            self.url, media_type, self.selected_quality, self
        )

    def _cancel_download(self):
        if self.cancel_action:
            self.cancel_action()
            if self.cancel_btn and self.cancel_btn.winfo_exists():
                self.cancel_btn.config(text="Cancelando…", state="disabled")

    def update_progress(self, data):
        """Atualiza a interface com base no hook do yt-dlp."""
        if not self.win.winfo_exists():
            return

        status = data.get("status")
        if status == "queued":
            self.status_lbl.config(text="Na fila de downloads...", fg="#a1a1aa")
        elif status == "started":
            self.status_lbl.config(text="Download iniciado...", fg="#a1a1aa")
        elif status == "cancelling":
            if self.cancel_btn and self.cancel_btn.winfo_exists():
                self.cancel_btn.config(text="Cancelando…", state="disabled")
            self.status_lbl.config(text="Cancelando download...", fg="#fbbf24")
        elif status == "cancelled":
            self.is_downloading = False
            self._show_error_state("Download cancelado.", retry=True)
        elif status == "downloading":
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
            self.is_downloading = False
            self.result_filename = data.get("filename")
            self._show_completed_state()

        elif status == "error":
            self.is_downloading = False
            err = data.get("error", "Erro desconhecido")
            self._show_error_state(err, retry=True)

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

    def _show_error_state(self, error_msg, retry=False):
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

        actions = tk.Frame(self.dynamic_frame, bg="#18181b")
        actions.pack(fill="x")
        if retry:
            btn_retry = tk.Button(
                actions,
                text="Tentar novamente",
                bg="#2563eb",
                fg="#ffffff",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                cursor="hand2",
                command=lambda: self._on_click_download(self.last_media_type),
            )
            btn_retry.pack(side="left")

        btn_close = tk.Button(
            actions,
            text="Fechar",
            bg="#27272a",
            fg="#f4f4f5",
            font=("Segoe UI", 8),
            relief="flat",
            cursor="hand2",
            command=self.close
        )
        btn_close.pack(side="right")
        self._start_autoclose_timer(8)

    def _open_file(self):
        if self.result_filename and os.path.exists(self.result_filename):
            try:
                os.startfile(self.result_filename)
            except Exception:
                pass
        self.close()

    def _open_folder(self):
        download_dir = get_download_dir()
        target = self.result_filename if self.result_filename and os.path.exists(self.result_filename) else download_dir
        try:
            if os.path.isfile(target):
                subprocess.Popen(f'explorer /select,"{os.path.abspath(target)}"')
            else:
                os.startfile(str(download_dir))
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
                    self._position_toasts()
                    auto_download = task.get("auto_download")
                    if auto_download in {"video", "audio"}:
                        self.root.after_idle(
                            lambda target=toast, media=auto_download:
                                target._on_click_download(media)
                        )
                elif action == "update_progress":
                    toast = task["toast"]
                    data = task["data"]
                    toast.update_progress(data)
                elif action == "history":
                    self._show_history_window(task["records"], task["on_retry"])
                elif action == "quit":
                    self.root.quit()
                    return
        except Exception as e:
            print("Erro no processamento da fila UI:", e)

        if self.root:
            self.root.after(100, self._process_queue)

    def show_toast(self, url, info, quality=DEFAULT_VIDEO_QUALITY, auto_download=None):
        self.task_queue.put({
            "action": "show",
            "url": url,
            "info": info,
            "quality": quality,
            "auto_download": auto_download,
        })

    def update_progress(self, toast, data):
        self.task_queue.put({"action": "update_progress", "toast": toast, "data": data})

    def _on_toast_dismiss(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self._position_toasts()

    def _position_toasts(self):
        for index, toast in enumerate(reversed(self.active_toasts)):
            toast.reposition(index)

    def show_history(self, records, on_retry):
        self.task_queue.put(
            {"action": "history", "records": records, "on_retry": on_retry}
        )

    def _show_history_window(self, records, on_retry):
        window = tk.Toplevel(self.root)
        window.title("SnapGrab — Histórico")
        window.geometry("760x360")
        window.minsize(600, 280)

        columns = ("date", "title", "type", "quality", "status")
        table = ttk.Treeview(window, columns=columns, show="headings", height=12)
        table.heading("date", text="Data")
        table.heading("title", text="Título / link")
        table.heading("type", text="Tipo")
        table.heading("quality", text="Qualidade")
        table.heading("status", text="Status")
        table.column("date", width=145, stretch=False)
        table.column("title", width=330)
        table.column("type", width=70, stretch=False)
        table.column("quality", width=85, stretch=False)
        table.column("status", width=90, stretch=False)
        table.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        scrollbar = ttk.Scrollbar(window, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scrollbar.set)
        scrollbar.place(relx=1, rely=0.03, relheight=0.79, anchor="ne")
        record_by_id = {}
        for index, record in enumerate(records):
            item_id = str(index)
            record_by_id[item_id] = record
            table.insert(
                "", "end", iid=item_id,
                values=(
                    record.get("completed_at", "").replace("T", " ")[:16],
                    record.get("title") or record.get("url", ""),
                    "Áudio" if record.get("media_type") == "audio" else "Vídeo",
                    record.get("quality", ""),
                    {"completed": "Concluído", "failed": "Falhou", "cancelled": "Cancelado"}.get(
                        record.get("status"), record.get("status", "")
                    ),
                ),
            )

        actions = tk.Frame(window)
        actions.pack(fill="x", padx=10, pady=(4, 10))

        def selected_record():
            selected = table.selection()
            return record_by_id.get(selected[0]) if selected else None

        def retry_selected():
            record = selected_record()
            if record:
                on_retry(record)
                window.destroy()

        def open_selected():
            record = selected_record()
            filename = record.get("filename") if record else None
            if filename and os.path.isfile(filename):
                try:
                    if hasattr(os, "startfile"):
                        os.startfile(filename)
                    else:
                        subprocess.Popen(["xdg-open", filename])
                except OSError:
                    pass

        ttk.Button(actions, text="Abrir arquivo", command=open_selected).pack(side="left")
        ttk.Button(actions, text="Repetir download", command=retry_selected).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Fechar", command=window.destroy).pack(side="right")

    def stop(self):
        self.task_queue.put({"action": "quit"})
