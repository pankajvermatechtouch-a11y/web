#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from flask import Flask, render_template, request, send_file

try:
    import instaloader
    from instaloader.exceptions import ConnectionException, LoginException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: instaloader. Install with 'pip install -r requirements.txt'.") from exc


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


def safe_segment(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ._@-]+", "_", name).strip()
    return cleaned or "untitled"


def make_loader(output_dir: Path, *, download_pictures: bool, download_videos: bool) -> "instaloader.Instaloader":
    loader = instaloader.Instaloader(
        dirname_pattern=str(output_dir / "{target}"),
        filename_pattern="{date_utc}_UTC_{shortcode}",
        download_pictures=download_pictures,
        download_videos=download_videos,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=True,
        quiet=True,
    )
    loader.context.max_connection_attempts = 3
    return loader


MEDIA_URL_RE = re.compile(r"(?:https?://)?(?:www\\.)?instagram\\.com/(p|reel|reels|tv)/([^/?#]+)/?")


def parse_media_url(raw: str) -> Optional[Tuple[str, str]]:
    value = raw.strip()
    if not value:
        return None
    match = MEDIA_URL_RE.search(value)
    if not match:
        return None
    kind = match.group(1)
    if kind == "reels":
        kind = "reel"
    shortcode = match.group(2)
    return kind, shortcode


def is_reel(post: "instaloader.Post") -> bool:
    product_type = getattr(post, "product_type", None)
    if product_type:
        return product_type == "clips"
    return False


def zip_dir(source_dir: Path) -> Path:
    zip_path = source_dir / "download.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for name in files:
                if name == zip_path.name:
                    continue
                file_path = Path(root) / name
                rel_path = file_path.relative_to(source_dir)
                zf.write(file_path, rel_path.as_posix())
    return zip_path


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    media_url = (request.form.get("media_url") or "").strip()
    media_type = (request.form.get("media_type") or "video").strip()

    parsed = parse_media_url(media_url)
    if not parsed:
        return render_template("index.html", error="Please paste a valid Instagram post or reel link.")

    url_kind, shortcode = parsed

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "downloads"
        output_dir.mkdir(parents=True, exist_ok=True)

        download_pictures = media_type == "photo"
        download_videos = media_type in {"video", "reels"}
        loader = make_loader(output_dir, download_pictures=download_pictures, download_videos=download_videos)

        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            owner = getattr(post, "owner_username", "instagram")
            safe_owner = safe_segment(owner)
            owner_profile = getattr(post, "owner_profile", None)
            if owner_profile and getattr(owner_profile, "is_private", False):
                return render_template(
                    "index.html",
                    private_error=True,
                    error="This account is private. Media cannot be downloaded.",
                )

            is_video = getattr(post, "is_video", False)
            if media_type == "photo" and is_video:
                return render_template("index.html", error="This link is a video. Select Video or Reels.")
            if media_type == "video" and not is_video:
                return render_template("index.html", error="This link is a photo. Select Photo.")
            if media_type == "reels":
                if not is_video:
                    return render_template("index.html", error="This link is not a reel.")
                if not (url_kind == "reel" or is_reel(post)):
                    return render_template("index.html", error="This link is not a reel.")

            target = f"{safe_owner}/{media_type}"
            loader.download_post(post, target=target)

            zip_path = zip_dir(output_dir)
            download_name = f"{safe_owner}_{media_type}.zip"
            return send_file(zip_path, as_attachment=True, download_name=download_name)

        except LoginException:
            return render_template(
                "index.html",
                private_error=True,
                error="This account is private. Media cannot be downloaded.",
            )
        except ConnectionException as exc:
            return render_template("index.html", error=f"Connection error: {exc}")
        except Exception as exc:  # pragma: no cover
            return render_template("index.html", error=f"Unexpected error: {exc}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
