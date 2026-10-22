import json

from core.downloader import MediaDownloader


class _CancelEvent:
    def __init__(self, callbacks):
        self.callbacks = callbacks

    def is_set(self):
        return self.callbacks.isCancelled()


def get_info_json(url, output_dir, ffmpeg_path):
    downloader = MediaDownloader(output_dir=output_dir, ffmpeg_path=ffmpeg_path)
    return json.dumps(downloader.get_info(url), ensure_ascii=False)


def download_json(url, output_dir, ffmpeg_path, media_type, quality, callbacks):
    downloader = MediaDownloader(output_dir=output_dir, ffmpeg_path=ffmpeg_path)

    def report_progress(data):
        callbacks.onProgress(
            int(float(data.get("percent") or 0)),
            str(data.get("status") or ""),
            str(data.get("speed_str") or ""),
            str(data.get("eta_str") or ""),
        )

    result = downloader.download(
        url,
        media_type=media_type,
        quality=quality,
        progress_callback=report_progress,
        use_cookies=False,
        browser_name="",
        cancel_event=_CancelEvent(callbacks),
        allow_cookie_retry=False,
    )
    return json.dumps(result, ensure_ascii=False)
