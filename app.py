#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    stream_with_context,
    url_for,
)

try:
    import instaloader
    from instaloader.exceptions import ConnectionException, LoginException
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: instaloader. Install with 'pip install -r requirements.txt'."
    ) from exc

try:
    import pymysql
except ModuleNotFoundError:  # pragma: no cover
    pymysql = None


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ADS_TXT = ""  # Paste your AdSense line here later.
CONTACT_TO = "pv50017@gmail.com"
DEFAULT_LANG = "en"
CACHE_TTL_SECONDS = 300
POST_CACHE: Dict[str, Dict[str, object]] = {}
RATE_LIMIT_WINDOW_SECONDS = 10
RATE_LIMIT_MAX_REQUESTS = 6
RATE_LIMITS: Dict[str, deque] = {}
STATS_KEY = os.environ.get("STATS_KEY", "5988")
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = int(os.environ.get("DB_PORT", "3306") or 3306)
DB_NAME = os.environ.get("DB_NAME", "")
DB_USER = os.environ.get("DB_USER", "")
DB_PASS = os.environ.get("DB_PASS", "")
STATS: Dict[str, int] = {
    "total_requests": 0,
    "cache_hits": 0,
    "rate_limited": 0,
    "metadata_blocked": 0,
    "invalid_links": 0,
    "success": 0,
}

LANG_ORDER = [
    "en",
    "hi",
    "es",
    "ar",
    "bn",
    "pt",
    "ru",
    "fr",
    "de",
    "zh",
]

LANGS = {
    "en": {"label": "English", "dir": "ltr"},
    "hi": {"label": "हिन्दी", "dir": "ltr"},
    "es": {"label": "Español", "dir": "ltr"},
    "ar": {"label": "العربية", "dir": "rtl"},
    "bn": {"label": "বাংলা", "dir": "ltr"},
    "pt": {"label": "Português", "dir": "ltr"},
    "ru": {"label": "Русский", "dir": "ltr"},
    "fr": {"label": "Français", "dir": "ltr"},
    "de": {"label": "Deutsch", "dir": "ltr"},
    "zh": {"label": "中文", "dir": "ltr"},
}

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "Instagram Media Downloader",
        "home_title": "Instagram Downloader: Download Reels, Videos & Photos Easily",
        "home_description": "You can use our tool FastDl App to download instagram reels, videos and photos in 4k free and without any signup.",
        "title_video": "Instagram Video Downloader - Free & Easy",
        "title_reels": "Instagram Reels Downloader - Free & Easy",
        "title_photo": "Instagram Photos Downloader - Free & Easy",
        "meta_description": "Download Instagram videos, reels, and photos from public posts. Paste a link and get previews with direct downloads.",
        "meta_description_video": "Instagram video downloader that lets you download videos in 4k free and without any signup.",
        "meta_description_reels": "Instagram reels downloader that lets you download reels in 4k free and without any signup.",
        "meta_description_photo": "Instagram photo downloader that lets you download photos in 4k free and without any signup.",
        "meta_keywords": "instagram downloader, instagram video downloader, instagram reels downloader, instagram photo downloader, download instagram media",
        "brand": "FastDl App",
        "home": "Home",
        "status": "Public posts only",
        "language_label": "Language",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Photo",
        "kicker": "Download all Instagram stuff here",
        "headline_video": "Instagram Video Downloader",
        "headline_reels": "Instagram Reels Downloader",
        "headline_photo": "Instagram Photo Downloader",
        "sub": "Paste a public post or reel link. Private accounts will show a privacy alert.",
        "placeholder": "Paste Instagram post or reel link",
        "paste": "Paste",
        "clear": "Clear",
        "search": "Search",
        "results": "Results",
        "download": "Download",
        "error_invalid_link": "Please paste a valid Instagram post or reel link.",
        "modal_private_title": "Private Account",
        "modal_private_body": "This Instagram account is private. Media cannot be downloaded.",
        "modal_mismatch_title": "Wrong Media Type",
        "modal_mismatch_video": "This link is an image. Please select the Photo tab.",
        "modal_mismatch_photo": "This link is a video. Please select Video or Reels.",
        "modal_mismatch_reel": "This link is not a reel. Please select the Photo tab.",
        "modal_temp_title": "Please try again",
        "modal_temp_body": "Instagram temporarily blocked this request. Please wait a minute and try again.",
        "modal_rate_title": "Please wait",
        "modal_rate_body": "Too many requests. Please wait a few seconds and try again.",
        "seo_title": "Fast Instagram Media Downloader for Public Posts",
        "seo_video_title": "Instagram Video Downloader for Public Posts",
        "seo_reels_title": "Instagram Reels Downloader for Public Profiles",
        "seo_photo_title": "Instagram Photo Downloader for Public Posts",
        "seo_list_title": "Features",
        "seo_list_1": "Supports public Instagram posts, reels, and photos",
        "seo_list_2": "Clean previews and one-click downloads",
        "seo_list_3": "Handles carousels with multiple items",
        "seo_list_4": "Privacy-aware: private accounts show a warning",
        "footer_contact": "Contact us",
        "footer_about": "About us",
        "footer_privacy": "Privacy policy",
        "footer_disclaimer": "This website is intended for educational and personal use only. All videos, photos, and media remain the property of their respective owners. We do not claim any rights over the content downloaded through this tool. All copyrights and trademarks belong to their rightful owners. Instagram and the Instagram logo are trademarks of Meta Platforms, Inc.",
        "footer_copy": "Copyright © 2026 FastDl App. All rights reserved.",
        "page_about_title": "About us",
        "page_about_body": "{brand} provides a simple way to preview and download public Instagram media for personal use.",
        "page_about_html": (
            "<p>Welcome to {brand} — a fast, free, and easy tool designed to help you download Instagram photos, videos, reels, and stories in just a few clicks.</p>"
            "<p>Our goal is to make saving your favorite Instagram content simple, secure, and hassle-free. No sign-ups, no complicated steps — just paste the link and download instantly.</p>"
            "<p>We’re constantly improving our tool to give you the best experience with speed, reliability, and privacy at the core.</p>"
        ),
        "page_contact_title": "Contact us",
        "page_contact_body": "For support or inquiries, email: pv50017@gmail.com",
        "page_contact_html": (
            "<p>Have a question, suggestion, or facing an issue while downloading Instagram media? We’re here to help!</p>"
            "<p>Feel free to reach out to us anytime, and our team will get back to you as soon as possible.</p>"
            "<h2>Support Hours</h2>"
            "<p><strong>🕒 24/7</strong></p>"
            "<p>Your feedback helps us improve and serve you better.</p>"
            "<h2>Email</h2>"
            "<p><a href=\"mailto:pv50017@gmail.com\">pv50017@gmail.com</a></p>"
        ),
        "page_privacy_title": "Privacy policy",
        "page_privacy_body": "We do not store the media you download. Requests are processed in real time.",
        "page_privacy_html": (
            "<p>Your privacy matters to us. This Privacy Policy explains how our Instagram Media Downloader website collects, uses, and protects your information when you use our service.</p>"
            "<h2>1. Information We Do Not Collect</h2>"
            "<p>We do not require you to sign up or create an account. We do not ask for personal information such as your name, email address, or Instagram login details to use our tool.</p>"
            "<h2>2. Log Data</h2>"
            "<p>Like most websites, we may collect basic log data such as:</p>"
            "<ul><li>IP address</li><li>Browser type</li><li>Device information</li><li>Pages visited</li><li>Time and date of visit</li></ul>"
            "<p>This data is used only to improve website performance and user experience.</p>"
            "<h2>3. Cookies</h2>"
            "<p>We may use cookies to enhance your browsing experience. Cookies help us understand user behavior and improve our services. You can disable cookies in your browser settings at any time.</p>"
            "<h2>4. Third-Party Services</h2>"
            "<p>We may use third-party services such as analytics tools or advertising networks that may collect information in accordance with their own privacy policies.</p>"
            "<h2>5. How We Use Information</h2>"
            "<p>Any data collected is used only for:</p>"
            "<ul><li>Improving website performance</li><li>Monitoring usage and traffic patterns</li><li>Fixing technical issues</li></ul>"
            "<p>We do not sell, trade, or share your information with third parties.</p>"
            "<h2>6. Data Security</h2>"
            "<p>We implement standard security measures to protect our website and users. However, no method of transmission over the internet is 100% secure.</p>"
            "<h2>7. Links to Other Websites</h2>"
            "<p>Our website may contain links to other websites. We are not responsible for the privacy practices of those sites.</p>"
            "<h2>8. Children’s Privacy</h2>"
            "<p>Our service is not intended for children under the age of 13. We do not knowingly collect information from children.</p>"
            "<h2>9. Changes to This Policy</h2>"
            "<p>We may update this Privacy Policy from time to time. Any changes will be posted on this page.</p>"
            "<h2>10. Contact Us</h2>"
            "<p>If you have any questions about this Privacy Policy, feel free to contact us at: <a href=\"{contact_url}\">{contact_url}</a></p>"
        ),
        "preview_alt": "Instagram media preview",
    },
    "ar": {
        "title": "أداة تنزيل وسائط إنستغرام",
        "home_title": "مُحمّل إنستغرام: حمّل الريلز والفيديوهات والصور بسهولة",
        "home_description": "يمكنك استخدام أداتنا FastDl App لتنزيل ريلز وفيديوهات وصور إنستغرام بدقة 4K مجانًا وبدون تسجيل.",
        "title_video": "مُحمّل فيديو إنستغرام - Free & Easy",
        "title_reels": "مُحمّل ريلز إنستغرام - Free & Easy",
        "title_photo": "مُحمّل صور إنستغرام - Free & Easy",
        "meta_description": "حمّل فيديوهات وصور وريـلز إنستغرام من المنشورات العامة. الصق الرابط وشاهد المعاينة.",
        "meta_description_video": "مُحمّل فيديو إنستغرام. الصق الرابط، شاهد المعاينة واحفظ بالجودة الأصلية. Instagram video downloader.",
        "meta_description_reels": "مُحمّل ريلز إنستغرام. الصق الرابط وحمّل فورًا. Instagram reels downloader.",
        "meta_description_photo": "مُحمّل صور إنستغرام. الصق الرابط، شاهد المعاينة واحفظ بجودة عالية. Instagram photo downloader.",
        "meta_keywords": "تحميل انستغرام, تنزيل ريلز, تحميل فيديو انستغram, تنزيل صور انستغram",
        "status": "المنشورات العامة فقط",
        "language_label": "اللغة",
        "tab_video": "فيديو",
        "tab_reels": "ريلز",
        "tab_photo": "صور",
        "kicker": "حمّل كل محتوى إنستغرام هنا",
        "headline_video": "أداة تنزيل فيديو إنستغرام",
        "headline_reels": "أداة تنزيل ريلز إنستغرام",
        "headline_photo": "أداة تنزيل صور إنستغرام",
        "sub": "الصق رابط منشور عام أو ريلز. الحسابات الخاصة ستعرض تنبيهًا.",
        "placeholder": "الصق رابط منشور أو ريلز إنستغram",
        "paste": "لصق",
        "clear": "مسح",
        "search": "بحث",
        "results": "النتائج",
        "download": "تنزيل",
        "modal_private_title": "حساب خاص",
        "modal_private_body": "هذا الحساب خاص. لا يمكن تنزيل الوسائط.",
        "modal_mismatch_title": "نوع غير صحيح",
        "modal_mismatch_video": "هذا الرابط لصورة. اختر تبويب الصور.",
        "modal_mismatch_photo": "هذا الرابط لفيديو. اختر الفيديو أو الريلز.",
        "modal_mismatch_reel": "هذا الرابط ليس ريلز. اختر الفيديو.",
        "seo_title": "أداة سريعة لتنزيل وسائط إنستغرام من المنشورات العامة",
        "footer_contact": "اتصل بنا",
        "footer_about": "من نحن",
        "footer_privacy": "سياسة الخصوصية",
    },
    "bn": {
        "title": "ইনস্টাগ্রাম মিডিয়া ডাউনলোডার",
        "home_title": "ইনস্টাগ্রাম ডাউনলোডার: রিলস, ভিডিও ও ছবি সহজে ডাউনলোড করুন",
        "home_description": "আমাদের FastDl App টুল দিয়ে আপনি Instagram রিলস, ভিডিও ও ছবি 4K-তে ফ্রি এবং সাইন-আপ ছাড়াই ডাউনলোড করতে পারবেন।",
        "title_video": "ইনস্টাগ্রাম ভিডিও ডাউনলোডার - Free & Easy",
        "title_reels": "ইনস্টাগ্রাম রিলস ডাউনলোডার - Free & Easy",
        "title_photo": "ইনস্টাগ্রাম ফটো ডাউনলোডার - Free & Easy",
        "meta_description": "পাবলিক পোস্ট থেকে ইনস্টাগ্রাম ভিডিও, রিল এবং ছবি ডাউনলোড করুন। লিংক পেস্ট করে প্রিভিউ দেখুন।",
        "meta_description_video": "ইনস্টাগ্রাম ভিডিও ডাউনলোডার। লিংক পেস্ট করুন, প্রিভিউ দেখুন এবং অরিজিনাল কোয়ালিটিতে সেভ করুন। Instagram video downloader.",
        "meta_description_reels": "ইনস্টাগ্রাম রিলস ডাউনলোডার। লিংক পেস্ট করে সাথে সাথে ডাউনলোড করুন। Instagram reels downloader.",
        "meta_description_photo": "ইনস্টাগ্রাম ফটো ডাউনলোডার। লিংক পেস্ট করে প্রিভিউ দেখুন এবং উচ্চমানের ছবি সেভ করুন। Instagram photo downloader.",
        "meta_keywords": "instagram downloader, ইনস্টাগ্রাম ডাউনলোডার, রিল ডাউনলোড, ভিডিও ডাউনলোড",
        "status": "শুধু পাবলিক পোস্ট",
        "language_label": "ভাষা",
        "tab_video": "ভিডিও",
        "tab_reels": "রিলস",
        "tab_photo": "ফটো",
        "kicker": "সব ইনস্টাগ্রাম কনটেন্ট এখানে ডাউনলোড করুন",
        "headline_video": "ইনস্টাগ্রাম ভিডিও ডাউনলোডার",
        "headline_reels": "ইনস্টাগ্রাম রিলস ডাউনলোডার",
        "headline_photo": "ইনস্টাগ্রাম ফটো ডাউনলোডার",
        "sub": "পাবলিক পোস্ট বা রিল লিংক পেস্ট করুন। প্রাইভেট অ্যাকাউন্টে সতর্কতা দেখাবে।",
        "placeholder": "ইনস্টাগ্রাম পোস্ট বা রিল লিংক পেস্ট করুন",
        "paste": "পেস্ট",
        "clear": "মুছুন",
        "search": "সার্চ",
        "results": "ফলাফল",
        "download": "ডাউনলোড",
        "modal_private_title": "প্রাইভেট অ্যাকাউন্ট",
        "modal_private_body": "এই অ্যাকাউন্টটি প্রাইভেট। মিডিয়া ডাউনলোড করা যাবে না।",
        "modal_mismatch_title": "ভুল মিডিয়া টাইপ",
        "modal_mismatch_video": "এই লিংকটি ছবি। ফটো ট্যাব নির্বাচন করুন।",
        "modal_mismatch_photo": "এই লিংকটি ভিডিও। ভিডিও বা রিলস ট্যাব নির্বাচন করুন।",
        "modal_mismatch_reel": "এই লিংকটি রিল নয়। ভিডিও নির্বাচন করুন।",
        "seo_title": "পাবলিক পোস্টের জন্য দ্রুত ইনস্টাগ্রাম ডাউনলোডার",
        "footer_contact": "যোগাযোগ",
        "footer_about": "আমাদের সম্পর্কে",
        "footer_privacy": "প্রাইভেসি পলিসি",
    },
    "zh": {
        "title": "Instagram 媒体下载器",
        "home_title": "Instagram 下载器：轻松下载 Reels、视频和照片",
        "home_description": "使用我们的 FastDl App，可免费、无需注册下载 Instagram Reels、视频和照片，最高 4K。",
        "title_video": "Instagram 视频下载器 - Free & Easy",
        "title_reels": "Instagram Reels 下载器 - Free & Easy",
        "title_photo": "Instagram 照片下载器 - Free & Easy",
        "meta_description": "从公开帖子下载 Instagram 视频、Reels 和照片。粘贴链接即可预览并下载。",
        "meta_description_video": "Instagram 视频下载器。粘贴链接、预览并保存原画质。 Instagram video downloader.",
        "meta_description_reels": "Instagram Reels 下载器。粘贴链接即可立即下载。 Instagram reels downloader.",
        "meta_description_photo": "Instagram 照片下载器。粘贴链接、预览并保存高质量图片。 Instagram photo downloader.",
        "meta_keywords": "instagram 下载, reels 下载, instagram 视频下载, instagram 图片下载",
        "status": "仅限公开帖子",
        "language_label": "语言",
        "tab_video": "视频",
        "tab_reels": "Reels",
        "tab_photo": "照片",
        "kicker": "在这里下载所有 Instagram 内容",
        "headline_video": "Instagram 视频下载器",
        "headline_reels": "Instagram Reels 下载器",
        "headline_photo": "Instagram 照片下载器",
        "sub": "粘贴公开帖子或 Reels 链接。私密账号会显示提示。",
        "placeholder": "粘贴 Instagram 帖子或 Reels 链接",
        "paste": "粘贴",
        "clear": "清除",
        "search": "搜索",
        "results": "结果",
        "download": "下载",
        "modal_private_title": "私密账号",
        "modal_private_body": "该账号为私密账号，无法下载媒体。",
        "modal_mismatch_title": "类型不匹配",
        "modal_mismatch_video": "该链接是图片，请选择照片标签。",
        "modal_mismatch_photo": "该链接是视频，请选择视频或 Reels 标签。",
        "modal_mismatch_reel": "该链接不是 Reels，请选择视频。",
        "seo_title": "快速 Instagram 公开帖下载器",
        "footer_contact": "联系我们",
        "footer_about": "关于我们",
        "footer_privacy": "隐私政策",
    },
    "fr": {
        "title": "Téléchargeur de médias Instagram",
        "home_title": "Téléchargeur Instagram: téléchargez Reels, vidéos et photos facilement",
        "home_description": "Avec notre outil FastDl App, vous pouvez télécharger des Reels, vidéos et photos Instagram en 4K gratuitement et sans inscription.",
        "title_video": "Téléchargeur vidéo Instagram - Free & Easy",
        "title_reels": "Téléchargeur Reels Instagram - Free & Easy",
        "title_photo": "Téléchargeur photo Instagram - Free & Easy",
        "meta_description": "Téléchargez vidéos, reels et photos Instagram depuis des posts publics. Collez le lien pour prévisualiser.",
        "meta_description_video": "Téléchargeur vidéo Instagram. Collez le lien, prévisualisez et enregistrez en qualité d'origine. Instagram video downloader.",
        "meta_description_reels": "Téléchargeur Reels Instagram. Collez le lien et téléchargez instantanément. Instagram reels downloader.",
        "meta_description_photo": "Téléchargeur photo Instagram. Collez le lien, prévisualisez et enregistrez en haute qualité. Instagram photo downloader.",
        "meta_keywords": "instagram downloader, telecharger instagram, reels instagram, video instagram",
        "status": "Publications publiques uniquement",
        "language_label": "Langue",
        "tab_video": "Vidéo",
        "tab_reels": "Reels",
        "tab_photo": "Photo",
        "kicker": "Téléchargez tout le contenu Instagram ici",
        "headline_video": "Téléchargeur vidéo Instagram",
        "headline_reels": "Téléchargeur Reels Instagram",
        "headline_photo": "Téléchargeur photo Instagram",
        "sub": "Collez un lien de post ou reel public. Les comptes privés afficheront une alerte.",
        "placeholder": "Collez un lien de post ou reel Instagram",
        "paste": "Coller",
        "clear": "Effacer",
        "search": "Rechercher",
        "results": "Résultats",
        "download": "Télécharger",
        "modal_private_title": "Compte privé",
        "modal_private_body": "Ce compte est privé. Impossible de télécharger.",
        "modal_mismatch_title": "Type incorrect",
        "modal_mismatch_video": "Ce lien est une image. Sélectionnez l’onglet Photo.",
        "modal_mismatch_photo": "Ce lien est une vidéo. Sélectionnez Vidéo ou Reels.",
        "modal_mismatch_reel": "Ce lien n’est pas un reel. Sélectionnez Vidéo.",
        "seo_title": "Téléchargeur Instagram rapide pour posts publics",
        "footer_contact": "Contact",
        "footer_about": "À propos",
        "footer_privacy": "Politique de confidentialité",
    },
    "de": {
        "title": "Instagram Medien-Downloader",
        "home_title": "Instagram Downloader: Reels, Videos & Fotos einfach herunterladen",
        "home_description": "Mit unserem Tool FastDl App kannst du Instagram Reels, Videos und Fotos in 4K kostenlos und ohne Anmeldung herunterladen.",
        "title_video": "Instagram Video-Downloader - Free & Easy",
        "title_reels": "Instagram Reels Downloader - Free & Easy",
        "title_photo": "Instagram Foto-Downloader - Free & Easy",
        "meta_description": "Lade Instagram Videos, Reels und Fotos aus öffentlichen Posts. Link einfügen und Vorschau sehen.",
        "meta_description_video": "Instagram Video-Downloader. Link einfügen, Vorschau ansehen und in Originalqualität speichern. Instagram video downloader.",
        "meta_description_reels": "Instagram Reels Downloader. Link einfügen und sofort herunterladen. Instagram reels downloader.",
        "meta_description_photo": "Instagram Foto-Downloader. Link einfügen, Vorschau ansehen und in hoher Qualität speichern. Instagram photo downloader.",
        "meta_keywords": "instagram downloader, instagram video downloader, reels downloader, instagram foto",
        "status": "Nur öffentliche Beiträge",
        "language_label": "Sprache",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Alle Instagram-Inhalte hier herunterladen",
        "headline_video": "Instagram Video Downloader",
        "headline_reels": "Instagram Reels Downloader",
        "headline_photo": "Instagram Foto Downloader",
        "sub": "Füge einen öffentlichen Post- oder Reel-Link ein. Private Konten zeigen eine Warnung.",
        "placeholder": "Instagram Post- oder Reel-Link einfügen",
        "paste": "Einfügen",
        "clear": "Löschen",
        "search": "Suchen",
        "results": "Ergebnisse",
        "download": "Download",
        "modal_private_title": "Privates Konto",
        "modal_private_body": "Dieses Konto ist privat. Medien können nicht heruntergeladen werden.",
        "modal_mismatch_title": "Falscher Medientyp",
        "modal_mismatch_video": "Dieser Link ist ein Bild. Bitte Foto-Tab wählen.",
        "modal_mismatch_photo": "Dieser Link ist ein Video. Bitte Video oder Reels wählen.",
        "modal_mismatch_reel": "Dieser Link ist kein Reel. Bitte Video wählen.",
        "seo_title": "Schneller Instagram Downloader für öffentliche Posts",
        "footer_contact": "Kontakt",
        "footer_about": "Über uns",
        "footer_privacy": "Datenschutz",
    },
    "hi": {
        "title": "इंस्टाग्राम मीडिया डाउनलोडर",
        "home_title": "इंस्टाग्राम डाउनलोडर: रील्स, वीडियो और फोटो आसानी से डाउनलोड करें",
        "home_description": "हमारे टूल FastDl App से आप Instagram रील्स, वीडियो और फोटो 4K में मुफ्त और बिना साइन-अप डाउनलोड कर सकते हैं।",
        "title_video": "Instagram वीडियो डाउनलोडर - Free & Easy",
        "title_reels": "Instagram रील्स डाउनलोडर - Free & Easy",
        "title_photo": "Instagram फोटो डाउनलोडर - Free & Easy",
        "meta_description": "पब्लिक पोस्ट से Instagram वीडियो, रील और फोटो डाउनलोड करें। लिंक पेस्ट करें और प्रिव्यू देखें।",
        "meta_description_video": "Instagram वीडियो डाउनलोडर। लिंक पेस्ट करें, प्रिव्यू देखें और ओरिजिनल क्वालिटी में सेव करें। Instagram video downloader.",
        "meta_description_reels": "Instagram रील्स डाउनलोडर। लिंक पेस्ट करें और तुरंत डाउनलोड करें। Instagram reels downloader.",
        "meta_description_photo": "Instagram फोटो डाउनलोडर। लिंक पेस्ट करें, प्रिव्यू देखें और हाई क्वालिटी में सेव करें। Instagram photo downloader.",
        "meta_keywords": "instagram downloader, instagram video downloader, reels downloader, फोटो डाउनलोड",
        "status": "केवल सार्वजनिक पोस्ट",
        "language_label": "भाषा",
        "tab_video": "वीडियो",
        "tab_reels": "रील्स",
        "tab_photo": "फोटो",
        "kicker": "यहाँ सभी Instagram कंटेंट डाउनलोड करें",
        "headline_video": "Instagram वीडियो डाउनलोडर",
        "headline_reels": "Instagram रील्स डाउनलोडर",
        "headline_photo": "Instagram फोटो डाउनलोडर",
        "sub": "पब्लिक पोस्ट या रील लिंक पेस्ट करें। प्राइवेट अकाउंट पर चेतावनी दिखेगी।",
        "placeholder": "Instagram पोस्ट या रील लिंक पेस्ट करें",
        "paste": "पेस्ट",
        "clear": "क्लियर",
        "search": "सर्च",
        "results": "रिज़ल्ट्स",
        "download": "डाउनलोड",
        "modal_private_title": "प्राइवेट अकाउंट",
        "modal_private_body": "यह अकाउंट प्राइवेट है। मीडिया डाउनलोड नहीं हो सकता।",
        "modal_mismatch_title": "गलत मीडिया प्रकार",
        "modal_mismatch_video": "यह लिंक फोटो का है। फोटो टैब चुनें।",
        "modal_mismatch_photo": "यह लिंक वीडियो का है। वीडियो या रील्स टैब चुनें।",
        "modal_mismatch_reel": "यह लिंक रील नहीं है। वीडियो चुनें।",
        "seo_title": "पब्लिक पोस्ट के लिए तेज़ Instagram डाउनलोडर",
        "footer_contact": "संपर्क करें",
        "footer_about": "हमारे बारे में",
        "footer_privacy": "प्राइवेसी पॉलिसी",
    },
    "pt": {
        "title": "Downloader de mídia do Instagram",
        "home_title": "Instagram Downloader: baixe Reels, vídeos e fotos facilmente",
        "home_description": "Com nossa ferramenta FastDl App, você pode baixar Reels, vídeos e fotos do Instagram em 4K grátis e sem cadastro.",
        "title_video": "Downloader de vídeo do Instagram - Free & Easy",
        "title_reels": "Downloader de Reels do Instagram - Free & Easy",
        "title_photo": "Downloader de fotos do Instagram - Free & Easy",
        "meta_description": "Baixe vídeos, reels e fotos do Instagram de posts públicos. Cole o link e veja a prévia.",
        "meta_description_video": "Downloader de vídeo do Instagram. Cole o link, pré-visualize e salve em qualidade original. Instagram video downloader.",
        "meta_description_reels": "Downloader de Reels do Instagram. Cole o link e faça o download instantâneo. Instagram reels downloader.",
        "meta_description_photo": "Downloader de fotos do Instagram. Cole o link, pré-visualize e salve em alta qualidade. Instagram photo downloader.",
        "meta_keywords": "instagram downloader, baixar video instagram, baixar reels, baixar fotos instagram",
        "status": "Somente posts públicos",
        "language_label": "Idioma",
        "tab_video": "Vídeo",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Baixe todo o conteúdo do Instagram aqui",
        "headline_video": "Downloader de vídeos do Instagram",
        "headline_reels": "Downloader de Reels do Instagram",
        "headline_photo": "Downloader de fotos do Instagram",
        "sub": "Cole um link de post ou reels público. Contas privadas mostrarão um alerta.",
        "placeholder": "Cole o link do post ou reels do Instagram",
        "paste": "Colar",
        "clear": "Limpar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Baixar",
        "modal_private_title": "Conta privada",
        "modal_private_body": "Esta conta é privada. Não é possível baixar.",
        "modal_mismatch_title": "Tipo incorreto",
        "modal_mismatch_video": "Este link é uma imagem. Selecione a aba Foto.",
        "modal_mismatch_photo": "Este link é um vídeo. Selecione Vídeo ou Reels.",
        "modal_mismatch_reel": "Este link não é reels. Selecione Vídeo.",
        "seo_title": "Downloader rápido do Instagram para posts públicos",
        "footer_contact": "Contato",
        "footer_about": "Sobre nós",
        "footer_privacy": "Política de privacidade",
    },
    "ru": {
        "title": "Загрузчик медиа Instagram",
        "home_title": "Instagram Downloader: скачайте Reels, видео и фото легко",
        "home_description": "С помощью нашего инструмента FastDl App вы можете скачать Reels, видео и фото из Instagram в 4K бесплатно и без регистрации.",
        "title_video": "Загрузчик видео Instagram - Free & Easy",
        "title_reels": "Загрузчик Reels Instagram - Free & Easy",
        "title_photo": "Загрузчик фото Instagram - Free & Easy",
        "meta_description": "Скачивайте видео, reels и фото Instagram из публичных постов. Вставьте ссылку для просмотра.",
        "meta_description_video": "Загрузчик видео Instagram. Вставьте ссылку, посмотрите предпросмотр и сохраните в оригинальном качестве. Instagram video downloader.",
        "meta_description_reels": "Загрузчик Reels Instagram. Вставьте ссылку и скачайте сразу. Instagram reels downloader.",
        "meta_description_photo": "Загрузчик фото Instagram. Вставьте ссылку, посмотрите предпросмотр и сохраните в высоком качестве. Instagram photo downloader.",
        "meta_keywords": "instagram downloader, скачать instagram, reels instagram, скачать фото",
        "status": "Только публичные посты",
        "language_label": "Язык",
        "tab_video": "Видео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Скачивайте весь контент Instagram здесь",
        "headline_video": "Загрузчик видео Instagram",
        "headline_reels": "Загрузчик Reels Instagram",
        "headline_photo": "Загрузчик фото Instagram",
        "sub": "Вставьте ссылку на публичный пост или reels. Приватные аккаунты покажут предупреждение.",
        "placeholder": "Вставьте ссылку на пост или reels Instagram",
        "paste": "Вставить",
        "clear": "Очистить",
        "search": "Поиск",
        "results": "Результаты",
        "download": "Скачать",
        "modal_private_title": "Приватный аккаунт",
        "modal_private_body": "Этот аккаунт приватный. Скачивание невозможно.",
        "modal_mismatch_title": "Неверный тип",
        "modal_mismatch_video": "Это изображение. Выберите вкладку Фото.",
        "modal_mismatch_photo": "Это видео. Выберите Видео или Reels.",
        "modal_mismatch_reel": "Это не reels. Выберите Видео.",
        "seo_title": "Быстрый загрузчик Instagram для публичных постов",
        "footer_contact": "Контакты",
        "footer_about": "О нас",
        "footer_privacy": "Политика конфиденциальности",
    },
    "es": {
        "title": "Descargador de medios de Instagram",
        "home_title": "Instagram Downloader: descarga Reels, videos y fotos fácilmente",
        "home_description": "Con nuestra herramienta FastDl App puedes descargar Reels, videos y fotos de Instagram en 4K gratis y sin registro.",
        "title_video": "Descargador de videos de Instagram - Free & Easy",
        "title_reels": "Descargador de Reels de Instagram - Free & Easy",
        "title_photo": "Descargador de fotos de Instagram - Free & Easy",
        "meta_description": "Descarga videos, reels y fotos de Instagram desde publicaciones públicas. Pega el enlace y previsualiza.",
        "meta_description_video": "Descargador de videos de Instagram. Pega el enlace, previsualiza y guarda en calidad original. Instagram video downloader.",
        "meta_description_reels": "Descargador de Reels de Instagram. Pega el enlace y descarga al instante. Instagram reels downloader.",
        "meta_description_photo": "Descargador de fotos de Instagram. Pega el enlace, previsualiza y guarda en alta calidad. Instagram photo downloader.",
        "meta_keywords": "instagram downloader, descargar instagram, reels instagram, descargar fotos",
        "status": "Solo publicaciones públicas",
        "language_label": "Idioma",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Descarga todo el contenido de Instagram aquí",
        "headline_video": "Descargador de videos de Instagram",
        "headline_reels": "Descargador de Reels de Instagram",
        "headline_photo": "Descargador de fotos de Instagram",
        "sub": "Pega un enlace de publicación o reel público. Las cuentas privadas mostrarán una alerta.",
        "placeholder": "Pega el enlace de publicación o reel de Instagram",
        "paste": "Pegar",
        "clear": "Borrar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Descargar",
        "modal_private_title": "Cuenta privada",
        "modal_private_body": "Esta cuenta es privada. No se puede descargar.",
        "modal_mismatch_title": "Tipo incorrecto",
        "modal_mismatch_video": "Este enlace es una imagen. Selecciona la pestaña Foto.",
        "modal_mismatch_photo": "Este enlace es un video. Selecciona Video o Reels.",
        "modal_mismatch_reel": "Este enlace no es un reel. Selecciona Video.",
        "seo_title": "Descargador rápido de Instagram para publicaciones públicas",
        "footer_contact": "Contacto",
        "footer_about": "Sobre nosotros",
        "footer_privacy": "Política de privacidad",
    },
}

MEDIA_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/(p|reel|reels|tv)/([^/?#]+)/?",
    re.IGNORECASE,
)

ALLOWED_HOST_SUFFIXES = ("cdninstagram.com", "fbcdn.net", "instagram.com")
MEDIA_SLUGS = {
    "video": "video-download",
    "reels": "reels-download",
    "photo": "photo-download",
}
MEDIA_ENDPOINTS = {
    "video": "video_download",
    "reels": "reels_download",
    "photo": "photo_download",
}


def build_strings(lang: str) -> Dict[str, str]:
    base = STRINGS[DEFAULT_LANG].copy()
    base.update(STRINGS.get(lang, {}))
    return base


def get_lang(lang: str) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


def get_languages() -> List[Tuple[str, str]]:
    return [(code, LANGS[code]["label"]) for code in LANG_ORDER]


def base_url() -> str:
    return request.url_root.rstrip("/")


CONTENT_DIR = Path(__file__).resolve().parent / "static" / "content"


def load_long_html(lang: str, media_type: str) -> str:
    media_type = normalize_media_type(media_type)
    candidates = [
        CONTENT_DIR / lang / f"{media_type}.html",
        CONTENT_DIR / DEFAULT_LANG / f"{media_type}.html",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return cleaned or "instagram_media"


def make_loader() -> "instaloader.Instaloader":
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )
    loader.context.max_connection_attempts = 3
    return loader


def fetch_post_with_retry(
    loader: "instaloader.Instaloader", shortcode: str, *, retries: int = 2, delay: float = 1.5
) -> "instaloader.Post":
    for attempt in range(retries + 1):
        try:
            return instaloader.Post.from_shortcode(loader.context, shortcode)
        except Exception as exc:
            if "Fetching Post metadata failed" in str(exc):
                if attempt < retries:
                    time.sleep(delay)
                    continue
            raise


def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    bucket = RATE_LIMITS.setdefault(ip, deque())
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return True
    bucket.append(now)
    return False


def get_cached_post(shortcode: str) -> Optional[Dict[str, object]]:
    entry = POST_CACHE.get(shortcode)
    if not entry:
        return None
    if entry.get("expires", 0) < time.time():
        POST_CACHE.pop(shortcode, None)
        return None
    return entry


def set_cached_post(shortcode: str, entry: Dict[str, object]) -> None:
    entry["expires"] = time.time() + CACHE_TTL_SECONDS
    POST_CACHE[shortcode] = entry


def inc_stat(key: str) -> None:
    STATS[key] = STATS.get(key, 0) + 1
    inc_stat_db(key)


def db_enabled() -> bool:
    return bool(DB_HOST and DB_NAME and DB_USER and DB_PASS and pymysql)


def get_db_connection():
    if not db_enabled():
        return None
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=5,
        charset="utf8mb4",
        autocommit=True,
    )


def ensure_stats_table(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                name VARCHAR(64) PRIMARY KEY,
                value BIGINT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )


def inc_stat_db(key: str) -> None:
    if not db_enabled():
        return
    try:
        conn = get_db_connection()
        if not conn:
            return
        ensure_stats_table(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO stats (name, value)
                VALUES (%s, 1)
                ON DUPLICATE KEY UPDATE value = value + 1
                """,
                (key,),
            )
        conn.close()
    except Exception:
        pass


def load_stats_db() -> Optional[Dict[str, int]]:
    if not db_enabled():
        return None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        ensure_stats_table(conn)
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, value FROM stats")
            rows = cursor.fetchall()
        conn.close()
        return {row[0]: int(row[1]) for row in rows}
    except Exception:
        return None


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


def extract_items(post: "instaloader.Post", media_type: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    if post.typename == "GraphSidecar":
        nodes = list(post.get_sidecar_nodes())
        for idx, node in enumerate(nodes, start=1):
            is_video = node.is_video
            if media_type == "photo" and is_video:
                continue
            if media_type in {"video", "reels"} and not is_video:
                continue
            url = node.video_url if is_video else node.display_url
            if not url:
                continue
            ext = ".mp4" if is_video else ".jpg"
            filename = safe_filename(f"{post.shortcode}_{idx}{ext}")
            items.append({"type": "video" if is_video else "photo", "url": url, "name": filename})
    else:
        is_video = getattr(post, "is_video", False)
        url = post.video_url if is_video else post.url
        if not url:
            return []
        if media_type == "photo" and is_video:
            return []
        if media_type in {"video", "reels"} and not is_video:
            return []
        ext = ".mp4" if is_video else ".jpg"
        filename = safe_filename(f"{post.shortcode}{ext}")
        items.append({"type": "video" if is_video else "photo", "url": url, "name": filename})

    return items


def is_allowed_media_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname or ""
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES)


def normalize_media_type(value: str) -> str:
    return value if value in MEDIA_SLUGS else "video"


def page_meta(
    t: Dict[str, str],
    media_type: str,
    *,
    is_home: bool = False,
    lang: str = DEFAULT_LANG,
) -> Tuple[str, str, str, List[str]]:
    key = normalize_media_type(media_type)
    if is_home:
        if lang != DEFAULT_LANG:
            lang_strings = STRINGS.get(lang, {})
            if "home_title" in lang_strings:
                page_title = lang_strings["home_title"]
            else:
                page_title = t.get(f"title_{key}", t["title"])
            if "home_description" in lang_strings:
                page_description = lang_strings["home_description"]
            else:
                page_description = t.get(f"meta_description_{key}", t["meta_description"])
        else:
            page_title = t.get("home_title", t.get(f"title_{key}", t["title"]))
            page_description = t.get("home_description", t.get(f"meta_description_{key}", t["meta_description"]))
    else:
        page_title = t.get(f"title_{key}", t["title"])
        page_description = t.get(f"meta_description_{key}", t["meta_description"])
    seo_title = t.get(f"seo_{key}_title", t.get("seo_title", ""))
    paragraphs = t.get(f"seo_{key}_paragraphs")
    if not paragraphs:
        paragraphs = [t.get("seo_p1", ""), t.get("seo_p2", "")]
    seo_paragraphs = [p for p in paragraphs if p]
    return page_title, page_description, seo_title, seo_paragraphs


def render_index(
    lang: str,
    *,
    selected_type: str = "video",
    page_slug: str = "",
    items: Optional[List[Dict[str, str]]] = None,
    media_url: str = "",
    error: Optional[str] = None,
    modal_show: bool = False,
    modal_title: Optional[str] = None,
    modal_message: Optional[str] = None,
    modal_retry: bool = False,
):
    t = build_strings(lang)
    selected_type = normalize_media_type(selected_type)
    page_title, page_description, seo_title, seo_paragraphs = page_meta(
        t,
        selected_type,
        is_home=(page_slug == ""),
        lang=lang,
    )
    post_url = url_for(MEDIA_ENDPOINTS[selected_type], lang=lang)
    long_html = load_long_html(lang, selected_type)
    return render_template(
        "index.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        default_lang=DEFAULT_LANG,
        selected_type=selected_type,
        page_slug=page_slug,
        page_title=page_title,
        page_description=page_description,
        seo_title=seo_title,
        seo_paragraphs=seo_paragraphs,
        long_html=long_html,
        post_url=post_url,
        items=items or [],
        media_url=media_url,
        error=error,
        modal_show=modal_show,
        modal_title=modal_title,
        modal_message=modal_message,
        modal_retry=modal_retry,
    )


@app.route("/")
def root():
    requested = request.args.get("lang", "").strip()
    target = requested if requested in LANGS else DEFAULT_LANG
    return redirect(f"/{target}", code=302)


@app.route("/<lang>")
@app.route("/<lang>/")
def index(lang: str):
    lang = get_lang(lang)
    return render_index(lang, selected_type="video", page_slug="")


def process_download(lang: str, media_type: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    media_type = normalize_media_type(media_type)
    page_slug = MEDIA_SLUGS[media_type]

    inc_stat("total_requests")
    media_url = (request.form.get("media_url") or "").strip()
    parsed = parse_media_url(media_url)
    if not parsed:
        inc_stat("invalid_links")
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            error=t["error_invalid_link"],
        )

    url_kind, shortcode = parsed

    cached = get_cached_post(shortcode)
    if cached:
        inc_stat("cache_hits")
        if media_type == "reels" and not (url_kind == "reel" or cached.get("is_reel")):
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=t["modal_mismatch_reel"],
            )

        cached_items = (
            cached.get("photo_items", [])
            if media_type == "photo"
            else cached.get("video_items", [])
        )
        if not cached_items:
            mismatch = t["modal_mismatch_photo"] if media_type == "photo" else t["modal_mismatch_video"]
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=mismatch,
            )

        inc_stat("success")
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            items=cached_items,
        )

    if is_rate_limited(get_client_ip()):
        inc_stat("rate_limited")
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            modal_show=True,
            modal_title=t.get("modal_rate_title", "Please wait"),
            modal_message=t.get(
                "modal_rate_body",
                "Too many requests. Please wait a few seconds and try again.",
            ),
        )

    try:
        loader = make_loader()
        post = fetch_post_with_retry(loader, shortcode)

        owner_profile = getattr(post, "owner_profile", None)
        if owner_profile and getattr(owner_profile, "is_private", False):
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t["modal_private_title"],
                modal_message=t["modal_private_body"],
            )

        is_reel_flag = is_reel(post)
        video_items = extract_items(post, "video")
        photo_items = extract_items(post, "photo")
        set_cached_post(
            shortcode,
            {
                "video_items": video_items,
                "photo_items": photo_items,
                "is_reel": is_reel_flag,
            },
        )

        if media_type == "reels" and not (url_kind == "reel" or is_reel_flag):
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=t["modal_mismatch_reel"],
            )

        items = photo_items if media_type == "photo" else video_items
        if not items:
            mismatch = t["modal_mismatch_photo"] if media_type == "photo" else t["modal_mismatch_video"]
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=mismatch,
            )

        inc_stat("success")
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            items=items,
        )

    except LoginException:
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            modal_show=True,
            modal_title=t["modal_private_title"],
            modal_message=t["modal_private_body"],
        )
    except ConnectionException as exc:
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            error=f"Connection error: {exc}",
        )
    except Exception as exc:  # pragma: no cover
        if "Fetching Post metadata failed" in str(exc):
            inc_stat("metadata_blocked")
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                media_url=media_url,
                modal_show=True,
                modal_title=t.get("modal_temp_title", "Please try again"),
                modal_message=t.get(
                    "modal_temp_body",
                    "Instagram temporarily blocked this request. Please wait a minute and try again.",
                ),
                modal_retry=True,
            )
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            media_url=media_url,
            error=f"Unexpected error: {exc}",
        )


def media_page(lang: str, media_type: str):
    lang = get_lang(lang)
    media_type = normalize_media_type(media_type)
    page_slug = MEDIA_SLUGS[media_type]
    if request.method == "GET":
        return render_index(lang, selected_type=media_type, page_slug=page_slug)
    form_type = normalize_media_type(request.form.get("media_type") or media_type)
    return process_download(lang, form_type)


@app.route("/<lang>/video-download", methods=["GET", "POST"])
def video_download(lang: str):
    return media_page(lang, "video")


@app.route("/<lang>/reels-download", methods=["GET", "POST"])
def reels_download(lang: str):
    return media_page(lang, "reels")


@app.route("/<lang>/photo-download", methods=["GET", "POST"])
def photo_download(lang: str):
    return media_page(lang, "photo")


@app.route("/<lang>/download", methods=["POST"])
def download(lang: str):
    media_type = normalize_media_type(request.form.get("media_type") or "video")
    return process_download(lang, media_type)


@app.route("/media-proxy")
def media_proxy():
    url = request.args.get("url", "")
    if not is_allowed_media_url(url):
        abort(400)

    headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    resp = requests.get(url, stream=True, timeout=20, headers=headers)
    if resp.status_code not in (200, 206):
        abort(404)

    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    forward_headers = {}
    for key in ("Content-Range", "Accept-Ranges", "Content-Length"):
        if key in resp.headers:
            forward_headers[key] = resp.headers[key]

    return Response(
        stream_with_context(resp.iter_content(chunk_size=8192)),
        status=resp.status_code,
        headers=forward_headers,
        content_type=content_type,
    )


@app.route("/download-file")
def download_file():
    url = request.args.get("url", "")
    filename = safe_filename(request.args.get("name", "instagram_media"))
    if not is_allowed_media_url(url):
        abort(400)
    resp = requests.get(url, stream=True, timeout=20)
    if resp.status_code != 200:
        abort(404)
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        stream_with_context(resp.iter_content(chunk_size=8192)),
        headers=headers,
        content_type=content_type,
    )


@app.route("/<lang>/about")
def about(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    page_body = t.get("page_about_html", t["page_about_body"]).format(brand=t["brand"])
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_about_title"],
        page_body=page_body,
        page_slug="about",
        default_lang=DEFAULT_LANG,
    )


@app.route("/<lang>/contact")
def contact(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    contact_url = f"{base_url()}/{lang}/contact"
    page_body = t.get("page_contact_html", t["page_contact_body"]).format(
        brand=t["brand"],
        contact_url=contact_url,
    )
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_contact_title"],
        page_body=page_body,
        page_slug="contact",
        default_lang=DEFAULT_LANG,
    )


@app.route("/<lang>/privacy")
def privacy(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    contact_url = f"{base_url()}/{lang}/contact"
    page_body = t.get("page_privacy_html", t["page_privacy_body"]).format(
        brand=t["brand"],
        contact_url=contact_url,
    )
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_privacy_title"],
        page_body=page_body,
        page_slug="privacy",
        default_lang=DEFAULT_LANG,
    )
@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml", mimetype="application/xml")

@app.route("/ads.txt")
def ads_txt():
    return Response(ADS_TXT + "\n", mimetype="text/plain")


@app.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nAllow: /\nSitemap: https://fastdlapp.cc/sitemap.xml\n"
    return Response(content, mimetype="text/plain")


@app.route("/stats")
def stats():
    key = (request.args.get("key") or "").strip()
    if not key or key != STATS_KEY:
        abort(404)
    data = STATS.copy()
    db_data = load_stats_db()
    if db_data:
        data.update(db_data)
    rows = "".join(
        f"<tr><th style='text-align:left;padding:6px 10px'>{name}</th>"
        f"<td style='padding:6px 10px'>{value}</td></tr>"
        for name, value in data.items()
    )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Stats</title></head><body style='font-family:Arial,sans-serif'>"
        "<h1>Stats</h1>"
        "<table border='1' cellpadding='0' cellspacing='0' style='border-collapse:collapse'>"
        f"{rows}</table></body></html>"
    )
    response = Response(html, mimetype="text/html")
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
