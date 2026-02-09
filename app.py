#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import Flask, Response, abort, render_template, request, stream_with_context

try:
    import instaloader
    from instaloader.exceptions import ConnectionException, LoginException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: instaloader. Install with 'pip install -r requirements.txt'.") from exc


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

MEDIA_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/(p|reel|reels|tv)/([^/?#]+)/?",
    re.IGNORECASE,
)

ALLOWED_HOST_SUFFIXES = ("cdninstagram.com", "fbcdn.net", "instagram.com")


def safe_segment(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ._@-]+", "_", name).strip()
    return cleaned or "untitled"


def make_loader() -> "instaloader.Instaloader":
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=True,
        quiet=True,
    )
    loader.context.max_connection_attempts = 3
    return loader


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


def is_allowed_media_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    return any(host.endswith(suffix) for suffix in ALLOWED_HOST_SUFFIXES)


def guess_extension(content_type: str) -> str:
    if not content_type:
        return ""
    content_type = content_type.split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
    }
    return mapping.get(content_type, "")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/download-file", methods=["GET"])
def download_file():
    media_url = (request.args.get("url") or "").strip()
    base_name = (request.args.get("name") or "media").strip()

    if not media_url or not is_allowed_media_url(media_url):
        return abort(400, "Invalid media URL")

    try:
        upstream = requests.get(media_url, stream=True, timeout=20, allow_redirects=False)
        upstream.raise_for_status()
    except requests.RequestException:
        return abort(502, "Failed to fetch media")

    content_type = upstream.headers.get("Content-Type", "application/octet-stream")
    extension = guess_extension(content_type)
    filename = safe_segment(base_name) + extension

    headers = {
        "Content-Type": content_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        headers=headers,
    )


@app.route("/download", methods=["POST"])
def download():
    media_url = (request.form.get("media_url") or request.form.get("target_input") or "").strip()
    media_type = (request.form.get("media_type") or "video").strip()

    parsed = parse_media_url(media_url)
    if not parsed:
        return render_template("index.html", error="Please paste a valid Instagram post or reel link.")

    url_kind, shortcode = parsed

    loader = make_loader()

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
        is_carousel = getattr(post, "typename", "") == "GraphSidecar"

        if media_type == "photo" and is_video and not is_carousel:
            return render_template("index.html", error="This link is a video. Select Video or Reels.")
        if media_type == "video" and not is_video and not is_carousel:
            return render_template("index.html", error="This link is a photo. Select Photo.")
        if media_type == "reels":
            if not is_video:
                return render_template("index.html", error="This link is not a reel.")
            if not (url_kind == "reel" or is_reel(post)):
                return render_template("index.html", error="This link is not a reel.")

        items: List[dict] = []

        if is_carousel:
            for idx, node in enumerate(post.get_sidecar_nodes(), start=1):
                node_is_video = getattr(node, "is_video", False)
                if media_type == "photo" and node_is_video:
                    continue
                if media_type in {"video", "reels"} and not node_is_video:
                    continue

                media_link = node.video_url if node_is_video else node.display_url
                if not media_link:
                    continue
                label = "video" if node_is_video else "photo"
                items.append(
                    {
                        "type": label,
                        "url": media_link,
                        "name": f"{safe_owner}_{shortcode}_{idx}",
                    }
                )
        else:
            media_link = post.video_url if is_video else post.url
            if media_link:
                label = "video" if is_video else "photo"
                if media_type == "photo" and label != "photo":
                    items = []
                elif media_type in {"video", "reels"} and label != "video":
                    items = []
                else:
                    items.append(
                        {
                            "type": label,
                            "url": media_link,
                            "name": f"{safe_owner}_{shortcode}",
                        }
                    )

        if not items:
            return render_template("index.html", error="No media found for that selection.")

        return render_template("index.html", items=items)

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
