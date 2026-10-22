"""Fila de downloads com concorrência limitada e cancelamento cooperativo."""

from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

from config import get_max_concurrent_downloads


class DownloadManager:
    def __init__(self, downloader, on_complete=None, max_workers=None):
        self.downloader = downloader
        self.on_complete = on_complete
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers or get_max_concurrent_downloads(),
            thread_name_prefix="snapgrab-download",
        )
        self._jobs = {}
        self._lock = threading.RLock()

    def submit(self, url, media_type, quality, progress_callback, title=None):
        job_id = uuid.uuid4().hex[:10]
        job = {
            "id": job_id,
            "url": url,
            "media_type": media_type,
            "quality": quality,
            "title": title,
            "cancel_event": threading.Event(),
            "callback": progress_callback,
            "future": None,
        }
        with self._lock:
            self._jobs[job_id] = job

        progress_callback({"status": "queued", "task_id": job_id})

        def run():
            if job["cancel_event"].is_set():
                return {"success": False, "cancelled": True, "error": "Download cancelado."}
            progress_callback({"status": "started", "task_id": job_id})
            try:
                return self.downloader.download(
                    url=url,
                    media_type=media_type,
                    quality=quality,
                    cancel_event=job["cancel_event"],
                    progress_callback=lambda data: progress_callback(
                        {**data, "task_id": job_id}
                    ),
                )
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
                progress_callback({"status": "error", "task_id": job_id, "error": str(exc)})
                return result

        future = self.executor.submit(run)
        job["future"] = future
        future.add_done_callback(lambda done: self._finish(job, done))
        return job_id

    def cancel(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            future = job.get("future")
            if future is not None and future.cancel():
                return True
            job["cancel_event"].set()
            job["callback"]({"status": "cancelling", "task_id": job_id})
            return True

    def _finish(self, job, future):
        if future.cancelled():
            result = {"success": False, "cancelled": True, "error": "Download cancelado."}
        else:
            try:
                result = future.result()
            except Exception as exc:
                result = {"success": False, "error": str(exc)}

        if result.get("cancelled"):
            job["callback"](
                {"status": "cancelled", "task_id": job["id"], "error": result.get("error")}
            )

        if self.on_complete:
            try:
                self.on_complete(job, result)
            except Exception as exc:
                print(f"Erro ao registrar download {job['id']}: {exc}")
        with self._lock:
            self._jobs.pop(job["id"], None)

    def shutdown(self, wait=False):
        with self._lock:
            for job in self._jobs.values():
                job["cancel_event"].set()
        self.executor.shutdown(wait=wait, cancel_futures=True)
