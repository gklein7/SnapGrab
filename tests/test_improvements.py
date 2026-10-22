import tempfile
import threading
import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from clipboard_watcher import ClipboardWatcher
import config
from core.download_manager import DownloadManager
from core.downloader import MediaDownloader
from core.history import DownloadHistory
import ui.tray as tray_module
from ui.toast import ToastManager, VideoToast


class ClipboardWatcherTests(unittest.TestCase):
    def test_domain_validation_rejects_lookalike_hosts(self):
        watcher = ClipboardWatcher(lambda _url: None)
        self.assertTrue(watcher.is_supported_url("https://m.youtube.com/watch?v=1"))
        self.assertTrue(watcher.is_supported_url("https://youtu.be/abc"))
        self.assertFalse(watcher.is_supported_url("https://youtube.com.evil.test/watch?v=1"))
        self.assertFalse(watcher.is_supported_url("https://notyoutube.com/watch?v=1"))

    def test_same_url_is_detected_after_other_clipboard_text(self):
        detected = []
        both_detected = threading.Event()

        def on_detected(url):
            detected.append(url)
            if len(detected) == 2:
                both_detected.set()

        watcher = ClipboardWatcher(on_detected)
        first = "https://youtube.com/watch?v=video"

        self.assertTrue(watcher.process_clipboard_text(first))
        self.assertFalse(watcher.process_clipboard_text("copied text"))
        self.assertTrue(watcher.process_clipboard_text(first))
        self.assertFalse(watcher.process_clipboard_text(first))

        # The callback intentionally runs on a background thread.
        self.assertTrue(both_detected.wait(timeout=1))
        self.assertEqual(detected, [first, first])


class DownloaderPathTests(unittest.TestCase):
    def test_uses_actual_output_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            final_file = Path(temp_dir) / "video.mp4"
            source_file = Path(temp_dir) / "video.webm"
            final_file.touch()
            source_file.touch()

            class FakeYdl:
                def prepare_filename(self, _info):
                    return str(source_file)

            downloader = MediaDownloader(output_dir=temp_dir)
            path = downloader._resolve_output_path(
                FakeYdl(), {"requested_downloads": [{"filepath": str(source_file)}]}, "video"
            )
            self.assertEqual(path, str(final_file))

    def test_cancelled_event_stops_before_network_access(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = MediaDownloader(output_dir=temp_dir)
            cancel_event = threading.Event()
            cancel_event.set()
            statuses = []
            with patch("core.downloader.yt_dlp.YoutubeDL") as youtube_dl:
                result = downloader.download(
                    "https://youtube.com/watch?v=test",
                    cancel_event=cancel_event,
                    progress_callback=lambda data: statuses.append(data["status"]),
                )
            youtube_dl.assert_not_called()
            self.assertTrue(result["cancelled"])
            self.assertIn("cancelled", statuses)


class PreviewMetadataTests(unittest.TestCase):
    def test_get_info_returns_preview_metadata_from_ytdlp(self):
        fake_ydl = MagicMock()
        fake_ydl.__enter__.return_value.extract_info.return_value = {
            "title": "Sample video",
            "uploader": "Sample channel",
            "duration": 120,
            "thumbnail": "https://images.example.test/thumbnail.jpg",
            "formats": [
                {"height": 720, "vcodec": "avc1", "acodec": "mp4a", "filesize": 8_000_000},
                {"height": 480, "vcodec": "avc1", "acodec": "mp4a", "filesize": 4_000_000},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = MediaDownloader(output_dir=temp_dir)
            with patch("core.downloader.yt_dlp.YoutubeDL", return_value=fake_ydl):
                info = downloader.get_info("https://youtube.com/watch?v=sample")

        self.assertEqual(info["title"], "Sample video")
        self.assertEqual(info["uploader"], "Sample channel")
        self.assertEqual(info["available_resolutions"], [720, 480])
        self.assertEqual(info["size_estimates"]["best"], 8_000_000)

    def test_lists_real_resolutions_and_estimates_video_and_audio_sizes(self):
        preview = MediaDownloader._build_preview_details(
            {
                "duration": 1000,
                "formats": [
                    {"height": 1080, "vcodec": "avc1", "acodec": "none", "filesize": 90_000_000},
                    {"height": 720, "vcodec": "avc1", "acodec": "none", "filesize": 45_000_000},
                    {"height": 480, "vcodec": "avc1", "acodec": "none", "filesize": 25_000_000},
                    {"vcodec": "none", "acodec": "mp4a", "filesize": 10_000_000},
                ],
            }
        )

        self.assertEqual(preview["available_resolutions"], [1080, 720, 480])
        self.assertEqual(
            [option["value"] for option in preview["quality_options"]],
            ["best", "720p", "480p"],
        )
        self.assertEqual(preview["size_estimates"]["best"], 100_000_000)
        self.assertEqual(preview["size_estimates"]["720p"], 55_000_000)
        self.assertEqual(preview["size_estimates"]["480p"], 35_000_000)
        self.assertEqual(preview["audio_size_estimate"], 40_000_000)

    def test_bitrate_can_estimate_missing_format_size_and_duration(self):
        estimate = MediaDownloader._format_size_estimate(
            {"tbr": 1500}, duration=60
        )
        self.assertEqual(estimate, 11_250_000)

    def test_preview_duration_and_size_labels_are_readable(self):
        self.assertEqual(VideoToast._format_duration(3723), "1:02:03")
        self.assertEqual(VideoToast._format_duration(125), "2:05")
        self.assertEqual(VideoToast._format_size(1_572_864), "~1.5 MB")
        self.assertEqual(VideoToast._format_size(0), "indisponível")


class DownloadManagerTests(unittest.TestCase):
    def test_limits_concurrency_and_cancels_queued_job(self):
        started = threading.Event()
        release = threading.Event()
        completion_lock = threading.Lock()
        completed = []

        class FakeDownloader:
            def download(self, url, **kwargs):
                started.set()
                release.wait(timeout=2)
                if kwargs["cancel_event"].is_set():
                    return {"success": False, "cancelled": True}
                return {"success": True, "filename": url, "title": url}

        def on_complete(job, result):
            with completion_lock:
                completed.append((job["url"], result))

        manager = DownloadManager(FakeDownloader(), on_complete, max_workers=1)
        callback = lambda _data: None
        try:
            first = manager.submit("first", "video", "best", callback)
            self.assertTrue(started.wait(timeout=1))
            second = manager.submit("second", "audio", "best", callback)
            self.assertTrue(manager.cancel(second))
            release.set()

            deadline = threading.Event()
            for _ in range(100):
                with completion_lock:
                    if len(completed) == 2:
                        break
                deadline.wait(0.02)

            self.assertEqual(len(completed), 2)
            results = {url: result for url, result in completed}
            self.assertTrue(results["first"]["success"])
            self.assertTrue(results["second"]["cancelled"])
        finally:
            release.set()
            manager.shutdown(wait=True)

    def test_cancels_an_active_cooperative_download(self):
        started = threading.Event()
        finished = threading.Event()
        callback_statuses = []

        class CooperativeDownloader:
            def download(self, url, **kwargs):
                started.set()
                self_cancel = kwargs["cancel_event"]
                self_cancel.wait(timeout=2)
                return {"success": False, "cancelled": self_cancel.is_set()}

        manager = DownloadManager(
            CooperativeDownloader(),
            on_complete=lambda _job, _result: finished.set(),
            max_workers=1,
        )
        try:
            task_id = manager.submit(
                "url", "video", "best", lambda data: callback_statuses.append(data["status"])
            )
            self.assertTrue(started.wait(timeout=1))
            self.assertTrue(manager.cancel(task_id))
            self.assertTrue(finished.wait(timeout=1))
            self.assertIn("cancelling", callback_statuses)
            self.assertIn("cancelled", callback_statuses)
        finally:
            manager.shutdown(wait=True)


class DownloadHistoryTests(unittest.TestCase):
    def test_persists_and_limits_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history = DownloadHistory(Path(temp_dir) / "history.sqlite3", limit=2)
            for index in range(3):
                history.add(
                    {
                        "url": f"https://example.test/{index}",
                        "title": f"Video {index}",
                        "media_type": "video",
                        "quality": "1080p",
                    },
                    {"success": index != 1, "filename": f"{index}.mp4", "error": "failure"},
                )
            rows = history.recent()
            self.assertEqual([row["title"] for row in rows], ["Video 2", "Video 1"])
            self.assertEqual(rows[1]["status"], "failed")


class SettingsTests(unittest.TestCase):
    def test_saved_folder_and_concurrency_setting_are_used(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings_file = root / "settings.json"
            custom_downloads = root / "my-downloads"
            settings_file.write_text(
                json.dumps(
                    {
                        "download_dir": str(custom_downloads),
                        "max_concurrent_downloads": 20,
                        "video_quality": "invalid",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(config, "SETTINGS_FILE", settings_file),
                patch.object(config, "LEGACY_SETTINGS_FILE", root / "legacy.json"),
            ):
                self.assertEqual(config.get_download_dir(), custom_downloads)
                self.assertTrue(custom_downloads.is_dir())
                self.assertEqual(config.get_max_concurrent_downloads(), 5)
                self.assertEqual(config.get_current_quality(), config.DEFAULT_VIDEO_QUALITY)


class SystemTrayTests(unittest.TestCase):
    def test_about_action_calls_ui_callback(self):
        on_show_about = MagicMock()
        tray = tray_module.SystemTrayApp(
            on_toggle_pause=lambda _active: None,
            on_download_clipboard=lambda: None,
            on_change_quality=lambda _quality: None,
            on_quit=lambda: None,
            on_show_about=on_show_about,
        )

        tray._show_about(None, None)

        on_show_about.assert_called_once_with()

    def test_about_request_is_queued_for_tkinter_main_thread(self):
        manager = ToastManager(lambda *_args: None)

        manager.show_about()

        self.assertEqual(manager.task_queue.get_nowait(), {"action": "about"})

    def test_start_loads_pystray_before_creating_icon(self):
        fake_icon = MagicMock()
        fake_pystray = MagicMock()
        fake_pystray.Icon.return_value = fake_icon
        tray = tray_module.SystemTrayApp(
            on_toggle_pause=lambda: None,
            on_download_clipboard=lambda: None,
            on_change_quality=lambda _quality: None,
            on_quit=lambda: None,
        )

        def load_pystray():
            tray_module.pystray = fake_pystray

        with (
            patch.object(tray_module, "pystray", None),
            patch.object(tray_module, "_load_pystray", side_effect=load_pystray) as load,
            patch.object(tray, "_get_menu", return_value=None),
        ):
            tray.start()

        load.assert_called_once()
        fake_pystray.Icon.assert_called_once()
        fake_icon.run_detached.assert_called_once()


if __name__ == "__main__":
    unittest.main()
