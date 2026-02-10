#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
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


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ADS_TXT = ""  # Paste your AdSense line here later.
CONTACT_TO = "pv50017@gmail.com"
DEFAULT_LANG = "en"
LANG_ORDER = [
    "en",
    "ar",
    "bn",
    "zh",
    "fr",
    "de",
    "hi",
    "hu",
    "id",
    "it",
    "ja",
    "ko",
    "pl",
    "pt",
    "ru",
    "es",
    "sw",
    "te",
    "th",
    "tr",
    "uk",
]

LANGS = {
    "en": {"label": "English", "dir": "ltr"},
    "ar": {"label": "العربية", "dir": "rtl"},
    "bn": {"label": "বাংলা", "dir": "ltr"},
    "zh": {"label": "中文", "dir": "ltr"},
    "fr": {"label": "Français", "dir": "ltr"},
    "de": {"label": "Deutsch", "dir": "ltr"},
    "hi": {"label": "हिन्दी", "dir": "ltr"},
    "hu": {"label": "Magyar", "dir": "ltr"},
    "id": {"label": "Bahasa Indonesia", "dir": "ltr"},
    "it": {"label": "Italiano", "dir": "ltr"},
    "ja": {"label": "日本語", "dir": "ltr"},
    "ko": {"label": "한국어", "dir": "ltr"},
    "pl": {"label": "Polski", "dir": "ltr"},
    "pt": {"label": "Português", "dir": "ltr"},
    "ru": {"label": "Русский", "dir": "ltr"},
    "es": {"label": "Español", "dir": "ltr"},
    "sw": {"label": "Kiswahili", "dir": "ltr"},
    "te": {"label": "తెలుగు", "dir": "ltr"},
    "th": {"label": "ไทย", "dir": "ltr"},
    "tr": {"label": "Türkçe", "dir": "ltr"},
    "uk": {"label": "Українська", "dir": "ltr"},
}

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "Instagram Media Downloader",
        "title_video": "Instagram Video Download",
        "title_reels": "Instagram Reels Download",
        "title_photo": "Instagram Photo Download",
        "meta_description": "Download Instagram videos, reels, and photos from public posts. Paste a link and get previews with direct downloads.",
        "meta_description_video": "Instagram video download for public posts. Paste a link, preview the video, and save it in original quality.",
        "meta_description_reels": "Instagram Reels download for public profiles. Paste a Reel link to preview and download instantly.",
        "meta_description_photo": "Instagram photo download for public posts. Paste a link to preview and save images in high quality.",
        "meta_keywords": "instagram downloader, instagram video downloader, instagram reels downloader, instagram photo downloader, download instagram media",
        "brand": "Media Vault",
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
        "modal_mismatch_reel": "This link is not a reel. Please select Video.",
        "seo_title": "Fast Instagram Media Downloader for Public Posts",
        "seo_p1": "Use this Instagram downloader to save public videos, reels, and photos directly from post links.",
        "seo_p2": "Paste a link, preview the media, and download each item individually.",
        "seo_video_title": "Instagram Video Downloader for Public Posts",
        "seo_video_paragraphs": [
            "Download Instagram videos from public posts with clean previews and direct downloads.",
            "Paste a link, watch the video instantly, and save it without extra steps.",
            "Works for single videos and carousels that include videos, each with its own download button.",
            "Private accounts are not supported. Only download content you own or have permission to use.",
        ],
        "seo_reels_title": "Instagram Reels Downloader for Public Profiles",
        "seo_reels_paragraphs": [
            "Download Instagram Reels from public profiles in seconds with fast previews and direct links.",
            "Paste a Reel link and get the video instantly, ready to save in original quality.",
            "Great for creators, editors, and marketers who need quick access to public Reels for inspiration.",
            "Private accounts are not supported. Respect copyright and only download with permission.",
        ],
        "seo_photo_title": "Instagram Photo Downloader for Public Posts",
        "seo_photo_paragraphs": [
            "Download Instagram photos from public posts in high quality with clean previews.",
            "Supports single-photo posts and multi-photo carousels, each image with its own download button.",
            "Paste a link, preview every image, and save them quickly and easily.",
            "Private accounts are not supported. Only download content you own or have permission to use.",
        ],
        "seo_list_title": "Features",
        "seo_list_1": "Supports public Instagram posts, reels, and photos",
        "seo_list_2": "Clean previews and one-click downloads",
        "seo_list_3": "Handles carousels with multiple items",
        "seo_list_4": "Privacy-aware: private accounts show a warning",
        "footer_contact": "Contact us",
        "footer_about": "About us",
        "footer_privacy": "Privacy policy",
        "footer_disclaimer": "This website is intended for educational and personal use only. All videos, photos, and media remain the property of their respective owners. We do not claim any rights over the content downloaded through this tool. All copyrights and trademarks belong to their rightful owners. Instagram and the Instagram logo are trademarks of Meta Platforms, Inc.",
        "footer_copy": "Copyright © 2026 Media Vault. All rights reserved.",
        "page_about_title": "About us",
        "page_about_body": "Media Vault provides a simple way to preview and download public Instagram media for personal use.",
        "page_about_html": (
            "<p>Welcome to {brand} — a fast, free, and easy tool designed to help you download Instagram photos, videos, reels, and stories in just a few clicks.</p>"
            "<p>Our goal is to make saving your favorite Instagram content simple, secure, and hassle-free. No sign-ups, no complicated steps — just paste the link and download instantly.</p>"
            "<p>We’re constantly improving our tool to give you the best experience with speed, reliability, and privacy at the core.</p>"
        ),
        "page_contact_title": "Contact us",
        "page_contact_body": "For support or inquiries, email: support@example.com",
        "page_contact_html": (
            "<p>Have a question, suggestion, or facing an issue while downloading Instagram media? We’re here to help!</p>"
            "<p>Feel free to reach out to us anytime, and our team will get back to you as soon as possible.</p>"
            "<h2>Support Hours</h2>"
            "<p><strong>🕒 24/7</strong></p>"
            "<p>Your feedback helps us improve and serve you better.</p>"
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
        "meta_description": "حمّل فيديوهات وصور وريـلز إنستغرام من المنشورات العامة. الصق الرابط وشاهد المعاينة.",
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
        "meta_description": "পাবলিক পোস্ট থেকে ইনস্টাগ্রাম ভিডিও, রিল এবং ছবি ডাউনলোড করুন। লিংক পেস্ট করে প্রিভিউ দেখুন।",
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
        "meta_description": "从公开帖子下载 Instagram 视频、Reels 和照片。粘贴链接即可预览并下载。",
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
        "meta_description": "Téléchargez vidéos, reels et photos Instagram depuis des posts publics. Collez le lien pour prévisualiser.",
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
        "meta_description": "Lade Instagram Videos, Reels und Fotos aus öffentlichen Posts. Link einfügen und Vorschau sehen.",
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
        "meta_description": "पब्लिक पोस्ट से Instagram वीडियो, रील और फोटो डाउनलोड करें। लिंक पेस्ट करें और प्रिव्यू देखें।",
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
    "hu": {
        "title": "Instagram média letöltő",
        "meta_description": "Tölts le Instagram videókat, reelseket és fotókat nyilvános posztokból. Illeszd be a linket.",
        "meta_keywords": "instagram letöltő, instagram videó letöltő, reels letöltő, instagram fotó",
        "status": "Csak nyilvános posztok",
        "language_label": "Nyelv",
        "tab_video": "Videó",
        "tab_reels": "Reels",
        "tab_photo": "Fotó",
        "kicker": "Tölts le minden Instagram tartalmat itt",
        "headline_video": "Instagram videó letöltő",
        "headline_reels": "Instagram Reels letöltő",
        "headline_photo": "Instagram fotó letöltő",
        "sub": "Illessz be egy nyilvános poszt vagy reels linket. Privát fióknál figyelmeztetés lesz.",
        "placeholder": "Instagram poszt vagy reels link beillesztése",
        "paste": "Beillesztés",
        "clear": "Törlés",
        "search": "Keresés",
        "results": "Eredmények",
        "download": "Letöltés",
        "modal_private_title": "Privát fiók",
        "modal_private_body": "Ez a fiók privát. Nem tölthető le.",
        "modal_mismatch_title": "Rossz médiatípus",
        "modal_mismatch_video": "Ez a link kép. Válaszd a Fotó fület.",
        "modal_mismatch_photo": "Ez a link videó. Válaszd a Videó vagy Reels fület.",
        "modal_mismatch_reel": "Ez a link nem reels. Válaszd a Videó fület.",
        "seo_title": "Gyors Instagram letöltő nyilvános posztokhoz",
        "footer_contact": "Kapcsolat",
        "footer_about": "Rólunk",
        "footer_privacy": "Adatvédelem",
    },
    "id": {
        "title": "Pengunduh Media Instagram",
        "meta_description": "Unduh video, reels, dan foto Instagram dari posting publik. Tempel tautan untuk pratinjau.",
        "meta_keywords": "instagram downloader, unduh video instagram, unduh reels, unduh foto instagram",
        "status": "Hanya posting publik",
        "language_label": "Bahasa",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Unduh semua konten Instagram di sini",
        "headline_video": "Pengunduh Video Instagram",
        "headline_reels": "Pengunduh Reels Instagram",
        "headline_photo": "Pengunduh Foto Instagram",
        "sub": "Tempel tautan posting atau reels publik. Akun privat akan menampilkan peringatan.",
        "placeholder": "Tempel tautan posting atau reels Instagram",
        "paste": "Tempel",
        "clear": "Hapus",
        "search": "Cari",
        "results": "Hasil",
        "download": "Unduh",
        "modal_private_title": "Akun Privat",
        "modal_private_body": "Akun ini privat. Media tidak dapat diunduh.",
        "modal_mismatch_title": "Jenis Media Salah",
        "modal_mismatch_video": "Tautan ini adalah gambar. Pilih tab Foto.",
        "modal_mismatch_photo": "Tautan ini adalah video. Pilih tab Video atau Reels.",
        "modal_mismatch_reel": "Tautan ini bukan reels. Pilih tab Video.",
        "seo_title": "Pengunduh Instagram cepat untuk posting publik",
        "footer_contact": "Hubungi kami",
        "footer_about": "Tentang kami",
        "footer_privacy": "Kebijakan privasi",
    },
    "it": {
        "title": "Downloader media Instagram",
        "meta_description": "Scarica video, reels e foto Instagram da post pubblici. Incolla il link per l’anteprima.",
        "meta_keywords": "instagram downloader, scarica video instagram, reels instagram, scarica foto instagram",
        "status": "Solo post pubblici",
        "language_label": "Lingua",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Scarica tutti i contenuti Instagram qui",
        "headline_video": "Downloader video Instagram",
        "headline_reels": "Downloader Reels Instagram",
        "headline_photo": "Downloader foto Instagram",
        "sub": "Incolla un link di post o reel pubblico. Gli account privati mostrano un avviso.",
        "placeholder": "Incolla link post o reel Instagram",
        "paste": "Incolla",
        "clear": "Pulisci",
        "search": "Cerca",
        "results": "Risultati",
        "download": "Scarica",
        "modal_private_title": "Account privato",
        "modal_private_body": "Questo account è privato. Impossibile scaricare.",
        "modal_mismatch_title": "Tipo di media errato",
        "modal_mismatch_video": "Questo link è un’immagine. Seleziona Foto.",
        "modal_mismatch_photo": "Questo link è un video. Seleziona Video o Reels.",
        "modal_mismatch_reel": "Questo link non è un reel. Seleziona Video.",
        "seo_title": "Downloader Instagram veloce per post pubblici",
        "footer_contact": "Contatti",
        "footer_about": "Chi siamo",
        "footer_privacy": "Privacy",
    },
    "ja": {
        "title": "Instagram メディアダウンローダー",
        "meta_description": "公開投稿からInstagramの動画・リール・写真をダウンロード。リンクを貼り付けてプレビュー。",
        "meta_keywords": "instagram ダウンロード, reels ダウンロード, instagram 動画, instagram 写真",
        "status": "公開投稿のみ",
        "language_label": "言語",
        "tab_video": "動画",
        "tab_reels": "リール",
        "tab_photo": "写真",
        "kicker": "ここでInstagramのすべてをダウンロード",
        "headline_video": "Instagram 動画ダウンローダー",
        "headline_reels": "Instagram リールダウンローダー",
        "headline_photo": "Instagram 写真ダウンローダー",
        "sub": "公開投稿またはリールのリンクを貼り付けてください。非公開アカウントは警告が表示されます。",
        "placeholder": "Instagram投稿またはリールのリンクを貼り付け",
        "paste": "貼り付け",
        "clear": "クリア",
        "search": "検索",
        "results": "結果",
        "download": "ダウンロード",
        "modal_private_title": "非公開アカウント",
        "modal_private_body": "このアカウントは非公開です。ダウンロードできません。",
        "modal_mismatch_title": "メディアタイプが違います",
        "modal_mismatch_video": "このリンクは画像です。写真タブを選択してください。",
        "modal_mismatch_photo": "このリンクは動画です。動画またはリールを選択してください。",
        "modal_mismatch_reel": "このリンクはリールではありません。動画を選択してください。",
        "seo_title": "公開投稿向けの高速Instagramダウンローダー",
        "footer_contact": "お問い合わせ",
        "footer_about": "私たちについて",
        "footer_privacy": "プライバシーポリシー",
    },
    "ko": {
        "title": "인스타그램 미디어 다운로더",
        "meta_description": "공개 게시물에서 Instagram 비디오, 릴스, 사진을 다운로드하세요. 링크를 붙여넣어 미리보기.",
        "meta_keywords": "instagram downloader, 인스타그램 다운로드, 릴스 다운로드, 사진 다운로드",
        "status": "공개 게시물만",
        "language_label": "언어",
        "tab_video": "동영상",
        "tab_reels": "릴스",
        "tab_photo": "사진",
        "kicker": "여기에서 인스타그램 콘텐츠를 다운로드하세요",
        "headline_video": "인스타그램 동영상 다운로더",
        "headline_reels": "인스타그램 릴스 다운로더",
        "headline_photo": "인스타그램 사진 다운로더",
        "sub": "공개 게시물 또는 릴스 링크를 붙여넣으세요. 비공개 계정은 경고가 표시됩니다.",
        "placeholder": "인스타그램 게시물 또는 릴스 링크 붙여넣기",
        "paste": "붙여넣기",
        "clear": "지우기",
        "search": "검색",
        "results": "결과",
        "download": "다운로드",
        "modal_private_title": "비공개 계정",
        "modal_private_body": "이 계정은 비공개입니다. 다운로드할 수 없습니다.",
        "modal_mismatch_title": "잘못된 미디어 유형",
        "modal_mismatch_video": "이 링크는 이미지입니다. 사진 탭을 선택하세요.",
        "modal_mismatch_photo": "이 링크는 동영상입니다. 동영상 또는 릴스 탭을 선택하세요.",
        "modal_mismatch_reel": "이 링크는 릴스가 아닙니다. 동영상 탭을 선택하세요.",
        "seo_title": "공개 게시물용 빠른 Instagram 다운로더",
        "footer_contact": "문의하기",
        "footer_about": "소개",
        "footer_privacy": "개인정보처리방침",
    },
    "pl": {
        "title": "Pobieranie mediów z Instagram",
        "meta_description": "Pobieraj wideo, reels i zdjęcia z publicznych postów Instagram. Wklej link, aby zobaczyć podgląd.",
        "meta_keywords": "instagram downloader, pobierz instagram, reels instagram, pobierz zdjęcia",
        "status": "Tylko publiczne posty",
        "language_label": "Język",
        "tab_video": "Wideo",
        "tab_reels": "Reels",
        "tab_photo": "Zdjęcie",
        "kicker": "Pobierz cały content z Instagrama tutaj",
        "headline_video": "Pobieranie wideo z Instagram",
        "headline_reels": "Pobieranie Reels z Instagram",
        "headline_photo": "Pobieranie zdjęć z Instagram",
        "sub": "Wklej link do publicznego posta lub reels. Prywatne konta pokażą alert.",
        "placeholder": "Wklej link do posta lub reels Instagram",
        "paste": "Wklej",
        "clear": "Wyczyść",
        "search": "Szukaj",
        "results": "Wyniki",
        "download": "Pobierz",
        "modal_private_title": "Konto prywatne",
        "modal_private_body": "To konto jest prywatne. Nie można pobrać.",
        "modal_mismatch_title": "Błędny typ",
        "modal_mismatch_video": "Ten link to obraz. Wybierz zakładkę Zdjęcie.",
        "modal_mismatch_photo": "Ten link to wideo. Wybierz Wideo lub Reels.",
        "modal_mismatch_reel": "Ten link nie jest reels. Wybierz Wideo.",
        "seo_title": "Szybki downloader Instagrama dla publicznych postów",
        "footer_contact": "Kontakt",
        "footer_about": "O nas",
        "footer_privacy": "Polityka prywatności",
    },
    "pt": {
        "title": "Downloader de mídia do Instagram",
        "meta_description": "Baixe vídeos, reels e fotos do Instagram de posts públicos. Cole o link e veja a prévia.",
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
        "meta_description": "Скачивайте видео, reels и фото Instagram из публичных постов. Вставьте ссылку для просмотра.",
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
        "meta_description": "Descarga videos, reels y fotos de Instagram desde publicaciones públicas. Pega el enlace y previsualiza.",
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
    "sw": {
        "title": "Kipakua Media ya Instagram",
        "meta_description": "Pakua video, reels na picha za Instagram kutoka posti za umma. Bandika kiungo uone mwonekano.",
        "meta_keywords": "instagram downloader, pakua instagram, reels instagram, pakua picha",
        "status": "Posti za umma pekee",
        "language_label": "Lugha",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Picha",
        "kicker": "Pakua maudhui yote ya Instagram hapa",
        "headline_video": "Kipakua Video cha Instagram",
        "headline_reels": "Kipakua Reels cha Instagram",
        "headline_photo": "Kipakua Picha cha Instagram",
        "sub": "Bandika kiungo cha post au reels ya umma. Akaunti binafsi zitaonyesha arifa.",
        "placeholder": "Bandika kiungo cha post au reels ya Instagram",
        "paste": "Bandika",
        "clear": "Futa",
        "search": "Tafuta",
        "results": "Matokeo",
        "download": "Pakua",
        "modal_private_title": "Akaunti Binafsi",
        "modal_private_body": "Akaunti hii ni binafsi. Haiwezi kupakuliwa.",
        "modal_mismatch_title": "Aina isiyo sahihi",
        "modal_mismatch_video": "Kiungo hiki ni picha. Chagua kichupo cha Picha.",
        "modal_mismatch_photo": "Kiungo hiki ni video. Chagua Video au Reels.",
        "modal_mismatch_reel": "Kiungo hiki si reels. Chagua Video.",
        "seo_title": "Kipakua cha haraka cha Instagram kwa posti za umma",
        "footer_contact": "Wasiliana nasi",
        "footer_about": "Kuhusu sisi",
        "footer_privacy": "Sera ya faragha",
    },
    "te": {
        "title": "ఇన్‍స్టాగ్రామ్ మీడియా డౌన్‌లోడర్",
        "meta_description": "పబ్లిక్ పోస్టుల నుండి Instagram వీడియోలు, రీల్స్ మరియు ఫోటోలు డౌన్‌లోడ్ చేయండి.",
        "meta_keywords": "instagram downloader, instagram video downloader, reels downloader, ఫోటో డౌన్‌లోడ్",
        "status": "పబ్లిక్ పోస్టులు మాత్రమే",
        "language_label": "భాష",
        "tab_video": "వీడియో",
        "tab_reels": "రీల్స్",
        "tab_photo": "ఫోటో",
        "kicker": "ఇక్కడ అన్ని Instagram కంటెంట్ డౌన్‌లోడ్ చేయండి",
        "headline_video": "Instagram వీడియో డౌన్‌లోడర్",
        "headline_reels": "Instagram రీల్స్ డౌన్‌లోడర్",
        "headline_photo": "Instagram ఫోటో డౌన్‌లోడర్",
        "sub": "పబ్లిక్ పోస్టు లేదా రీల్ లింక్ పేస్ట్ చేయండి. ప్రైవేట్ అకౌంట్లకు అలర్ట్ వస్తుంది.",
        "placeholder": "Instagram పోస్టు లేదా రీల్ లింక్ పేస్ట్ చేయండి",
        "paste": "పేస్ట్",
        "clear": "క్లియర్",
        "search": "సెర్చ్",
        "results": "ఫలితాలు",
        "download": "డౌన్‌లోడ్",
        "modal_private_title": "ప్రైవేట్ అకౌంట్",
        "modal_private_body": "ఈ అకౌంట్ ప్రైవేట్. మీడియా డౌన్‌లోడ్ కాదు.",
        "modal_mismatch_title": "తప్పు మీడియా టైప్",
        "modal_mismatch_video": "ఈ లింక్ ఫోటో. ఫోటో ట్యాబ్ ఎంచుకోండి.",
        "modal_mismatch_photo": "ఈ లింక్ వీడియో. వీడియో లేదా రీల్స్ ట్యాబ్ ఎంచుకోండి.",
        "modal_mismatch_reel": "ఈ లింక్ రీల్ కాదు. వీడియో ఎంచుకోండి.",
        "seo_title": "పబ్లిక్ పోస్టుల కోసం వేగమైన Instagram డౌన్‌లోడర్",
        "footer_contact": "మమ్మల్ని సంప్రదించండి",
        "footer_about": "మా గురించి",
        "footer_privacy": "ప్రైవసీ పాలసీ",
    },
    "th": {
        "title": "ตัวดาวน์โหลดสื่อ Instagram",
        "meta_description": "ดาวน์โหลดวิดีโอ Reels และรูปภาพ Instagram จากโพสต์สาธารณะ วางลิงก์แล้วพรีวิวได้ทันที",
        "meta_keywords": "instagram downloader, ดาวน์โหลด instagram, reels instagram, ดาวน์โหลดรูป",
        "status": "เฉพาะโพสต์สาธารณะ",
        "language_label": "ภาษา",
        "tab_video": "วิดีโอ",
        "tab_reels": "Reels",
        "tab_photo": "รูปภาพ",
        "kicker": "ดาวน์โหลดคอนเทนต์ Instagram ทั้งหมดได้ที่นี่",
        "headline_video": "ตัวดาวน์โหลดวิดีโอ Instagram",
        "headline_reels": "ตัวดาวน์โหลด Reels Instagram",
        "headline_photo": "ตัวดาวน์โหลดรูปภาพ Instagram",
        "sub": "วางลิงก์โพสต์หรือรีลสาธารณะ บัญชีส่วนตัวจะแสดงการแจ้งเตือน",
        "placeholder": "วางลิงก์โพสต์หรือรีลของ Instagram",
        "paste": "วาง",
        "clear": "ล้าง",
        "search": "ค้นหา",
        "results": "ผลลัพธ์",
        "download": "ดาวน์โหลด",
        "modal_private_title": "บัญชีส่วนตัว",
        "modal_private_body": "บัญชีนี้เป็นส่วนตัว ดาวน์โหลดไม่ได้",
        "modal_mismatch_title": "ประเภทไม่ถูกต้อง",
        "modal_mismatch_video": "ลิงก์นี้เป็นรูปภาพ กรุณาเลือกแท็บรูปภาพ",
        "modal_mismatch_photo": "ลิงก์นี้เป็นวิดีโอ กรุณาเลือกวิดีโอหรือ Reels",
        "modal_mismatch_reel": "ลิงก์นี้ไม่ใช่ Reels กรุณาเลือกวิดีโอ",
        "seo_title": "ดาวน์โหลด Instagram สำหรับโพสต์สาธารณะอย่างรวดเร็ว",
        "footer_contact": "ติดต่อเรา",
        "footer_about": "เกี่ยวกับเรา",
        "footer_privacy": "นโยบายความเป็นส่วนตัว",
    },
    "tr": {
        "title": "Instagram Medya İndirici",
        "meta_description": "Herkese açık gönderilerden Instagram video, reels ve fotoğraf indirin. Bağlantıyı yapıştırın ve önizleyin.",
        "meta_keywords": "instagram indirici, instagram video indir, reels indir, fotoğraf indir",
        "status": "Yalnızca herkese açık gönderiler",
        "language_label": "Dil",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Fotoğraf",
        "kicker": "Tüm Instagram içeriklerini buradan indir",
        "headline_video": "Instagram Video İndirici",
        "headline_reels": "Instagram Reels İndirici",
        "headline_photo": "Instagram Fotoğraf İndirici",
        "sub": "Herkese açık post veya reels bağlantısı yapıştırın. Özel hesaplar uyarı gösterir.",
        "placeholder": "Instagram post veya reels bağlantısı yapıştırın",
        "paste": "Yapıştır",
        "clear": "Temizle",
        "search": "Ara",
        "results": "Sonuçlar",
        "download": "İndir",
        "modal_private_title": "Özel Hesap",
        "modal_private_body": "Bu hesap özel. Medya indirilemez.",
        "modal_mismatch_title": "Yanlış Medya Türü",
        "modal_mismatch_video": "Bu bağlantı bir görsel. Fotoğraf sekmesini seçin.",
        "modal_mismatch_photo": "Bu bağlantı bir video. Video veya Reels seçin.",
        "modal_mismatch_reel": "Bu bağlantı reels değil. Video seçin.",
        "seo_title": "Herkese açık gönderiler için hızlı Instagram indirici",
        "footer_contact": "Bize ulaşın",
        "footer_about": "Hakkımızda",
        "footer_privacy": "Gizlilik politikası",
    },
    "uk": {
        "title": "Завантажувач медіа Instagram",
        "meta_description": "Завантажуйте відео, reels і фото Instagram з публічних постів. Вставте посилання для перегляду.",
        "meta_keywords": "instagram downloader, скачати інстаграм, reels instagram, скачати фото",
        "status": "Лише публічні пости",
        "language_label": "Мова",
        "tab_video": "Відео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Завантажуйте весь контент Instagram тут",
        "headline_video": "Завантажувач відео Instagram",
        "headline_reels": "Завантажувач Reels Instagram",
        "headline_photo": "Завантажувач фото Instagram",
        "sub": "Вставте посилання на публічний пост або reels. Приватні акаунти покажуть попередження.",
        "placeholder": "Вставте посилання на пост або reels Instagram",
        "paste": "Вставити",
        "clear": "Очистити",
        "search": "Пошук",
        "results": "Результати",
        "download": "Завантажити",
        "modal_private_title": "Приватний акаунт",
        "modal_private_body": "Цей акаунт приватний. Завантаження неможливе.",
        "modal_mismatch_title": "Неправильний тип",
        "modal_mismatch_video": "Це зображення. Оберіть вкладку Фото.",
        "modal_mismatch_photo": "Це відео. Оберіть Відео або Reels.",
        "modal_mismatch_reel": "Це не reels. Оберіть Відео.",
        "seo_title": "Швидкий Instagram завантажувач для публічних постів",
        "footer_contact": "Контакти",
        "footer_about": "Про нас",
        "footer_privacy": "Політика конфіденційності",
    },
}

SEO_I18N: Dict[str, Dict[str, object]] = {
    "ar": {
        "seo_video_title": "أداة تنزيل فيديو إنستغرام للمنشورات العامة",
        "seo_video_paragraphs": [
            "نزّل فيديوهات إنستغرام من المنشورات العامة مع معاينة واضحة وتنزيل مباشر.",
            "الصق الرابط وشغّل الفيديو فوراً ثم احفظه بالجودة الأصلية.",
            "يدعم الفيديوهات الفردية ومنشورات الكاروسيل التي تحتوي على فيديو، ولكل عنصر زر تنزيل.",
            "الحسابات الخاصة غير مدعومة. نزّل فقط المحتوى الذي تملكه أو لديك إذن به.",
        ],
        "seo_reels_title": "أداة تنزيل ريلز إنستغram للحسابات العامة",
        "seo_reels_paragraphs": [
            "نزّل ريلز إنستغram من الحسابات العامة خلال ثوانٍ مع معاينة سريعة وروابط مباشرة.",
            "الصق رابط الريلز واحصل على الفيديو فوراً وجاهز للحفظ بالجودة الأصلية.",
            "مفيد للمبدعين والمحررين والمسوقين للوصول السريع إلى ريلز عامة للإلهام.",
            "الحسابات الخاصة غير مدعومة. احترم حقوق النشر ولا تنزّل إلا بإذن.",
        ],
        "seo_photo_title": "أداة تنزيل صور إنستغram للمنشورات العامة",
        "seo_photo_paragraphs": [
            "نزّل صور إنستغram من المنشورات العامة بجودة عالية ومعاينة واضحة.",
            "يدعم المنشورات ذات صورة واحدة والكاروسيل متعدد الصور، ولكل صورة زر تنزيل.",
            "الصق الرابط، شاهد كل الصور، ثم احفظها بسرعة وسهولة.",
            "الحسابات الخاصة غير مدعومة. نزّل فقط المحتوى الذي تملكه أو لديك إذن به.",
        ],
    },
    "bn": {
        "seo_video_title": "পাবলিক পোস্টের জন্য ইনস্টাগ্রাম ভিডিও ডাউনলোডার",
        "seo_video_paragraphs": [
            "পাবলিক পোস্ট থেকে ইনস্টাগ্রাম ভিডিও পরিষ্কার প্রিভিউসহ সরাসরি ডাউনলোড করুন।",
            "লিংক পেস্ট করুন, সাথে সাথে ভিডিও দেখুন এবং মূল মানে সেভ করুন।",
            "একক ভিডিও এবং ভিডিওসহ ক্যারোসেল পোস্ট, প্রতিটির জন্য আলাদা ডাউনলোড বোতাম।",
            "প্রাইভেট অ্যাকাউন্ট সমর্থিত নয়। অনুমতি থাকলে তবেই ডাউনলোড করুন।",
        ],
        "seo_reels_title": "পাবলিক প্রোফাইলের জন্য ইনস্টাগ্রাম রিলস ডাউনলোডার",
        "seo_reels_paragraphs": [
            "পাবলিক প্রোফাইল থেকে রিলস দ্রুত ডাউনলোড করুন, দ্রুত প্রিভিউ ও সরাসরি লিঙ্কসহ।",
            "রিল লিংক পেস্ট করুন এবং সঙ্গে সঙ্গে ভিডিওটি পান।",
            "ক্রিয়েটর ও মার্কেটারদের জন্য পাবলিক রিলস দেখার ও সংরক্ষণের সহজ উপায়।",
            "প্রাইভেট অ্যাকাউন্ট সমর্থিত নয়। কপিরাইট মেনে চলুন।",
        ],
        "seo_photo_title": "পাবলিক পোস্টের জন্য ইনস্টাগ্রাম ছবি ডাউনলোডার",
        "seo_photo_paragraphs": [
            "পাবলিক পোস্টের ছবি উচ্চ মানে ডাউনলোড করুন।",
            "সিঙ্গেল ও মাল্টি-ফটো ক্যারোসেল, প্রতিটি ছবির জন্য আলাদা ডাউনলোড বোতাম।",
            "লিংক পেস্ট করুন, সব ছবি প্রিভিউ করুন, দ্রুত সেভ করুন।",
            "প্রাইভেট অ্যাকাউন্ট সমর্থিত নয়। অনুমতি থাকলে তবেই ডাউনলোড করুন।",
        ],
    },
    "zh": {
        "seo_video_title": "公开帖子 Instagram 视频下载器",
        "seo_video_paragraphs": [
            "从公开帖子下载 Instagram 视频，提供清晰预览与直接下载。",
            "粘贴链接即可立即播放并保存原画质视频。",
            "支持单个视频和含视频的轮播，每个项目都有下载按钮。",
            "不支持私密账号。仅下载你拥有或获授权的内容。",
        ],
        "seo_reels_title": "公开账号 Instagram Reels 下载器",
        "seo_reels_paragraphs": [
            "从公开账号快速下载 Reels，预览快，链接直达。",
            "粘贴 Reel 链接即可立即获取视频并保存原画质。",
            "适合创作者和营销人员快速获取公开 Reels 灵感。",
            "不支持私密账号，请尊重版权并获得许可。",
        ],
        "seo_photo_title": "公开帖子 Instagram 图片下载器",
        "seo_photo_paragraphs": [
            "从公开帖子高质量下载 Instagram 图片，并提供清晰预览。",
            "支持单图与多图轮播，每张图片都有独立下载按钮。",
            "粘贴链接，预览全部图片，快速保存。",
            "不支持私密账号。仅下载你拥有或获授权的内容。",
        ],
    },
    "fr": {
        "seo_video_title": "Téléchargeur de vidéos Instagram pour posts publics",
        "seo_video_paragraphs": [
            "Téléchargez des vidéos Instagram depuis des posts publics avec aperçu clair et lien direct.",
            "Collez un lien, regardez la vidéo instantanément et enregistrez-la en qualité d'origine.",
            "Fonctionne pour les vidéos seules et les carrousels contenant des vidéos, avec un bouton par élément.",
            "Les comptes privés ne sont pas pris en charge. Téléchargez uniquement avec autorisation.",
        ],
        "seo_reels_title": "Téléchargeur de Reels Instagram pour profils publics",
        "seo_reels_paragraphs": [
            "Téléchargez des Reels Instagram depuis des profils publics en quelques secondes.",
            "Collez le lien d'un Reel et obtenez la vidéo immédiatement en qualité d'origine.",
            "Idéal pour les créateurs et marketeurs qui veulent accéder rapidement aux Reels publics.",
            "Comptes privés non pris en charge. Respectez les droits d'auteur.",
        ],
        "seo_photo_title": "Téléchargeur de photos Instagram pour posts publics",
        "seo_photo_paragraphs": [
            "Téléchargez des photos Instagram de posts publics en haute qualité avec aperçu propre.",
            "Prend en charge les posts à photo unique et les carrousels multi-photos, chaque image a son bouton.",
            "Collez un lien, prévisualisez toutes les images, puis enregistrez-les rapidement.",
            "Comptes privés non pris en charge. Téléchargez seulement avec permission.",
        ],
    },
    "de": {
        "seo_video_title": "Instagram Video-Downloader für öffentliche Beiträge",
        "seo_video_paragraphs": [
            "Lade Instagram-Videos aus öffentlichen Beiträgen mit klarer Vorschau und Direktdownload.",
            "Link einfügen, Video sofort ansehen und in Originalqualität speichern.",
            "Funktioniert für einzelne Videos und Karussells mit Videos, jedes mit eigenem Download-Button.",
            "Private Konten werden nicht unterstützt. Nur mit Erlaubnis herunterladen.",
        ],
        "seo_reels_title": "Instagram Reels Downloader für öffentliche Profile",
        "seo_reels_paragraphs": [
            "Lade Instagram Reels von öffentlichen Profilen in Sekunden mit schneller Vorschau.",
            "Reel-Link einfügen und das Video sofort in Originalqualität erhalten.",
            "Ideal für Creator und Marketer, die schnell auf öffentliche Reels zugreifen wollen.",
            "Private Konten werden nicht unterstützt. Urheberrecht beachten.",
        ],
        "seo_photo_title": "Instagram Foto-Downloader für öffentliche Beiträge",
        "seo_photo_paragraphs": [
            "Lade Instagram-Fotos aus öffentlichen Beiträgen in hoher Qualität mit Vorschau.",
            "Unterstützt Einzelbilder und Mehrfach-Karussells, jede Bilddatei mit eigenem Button.",
            "Link einfügen, alle Bilder ansehen und schnell speichern.",
            "Private Konten werden nicht unterstützt. Nur mit Erlaubnis herunterladen.",
        ],
    },
    "hi": {
        "seo_video_title": "पब्लिक पोस्ट के लिए Instagram वीडियो डाउनलोडर",
        "seo_video_paragraphs": [
            "पब्लिक पोस्ट से Instagram वीडियो साफ़ प्रिव्यू और डायरेक्ट डाउनलोड के साथ डाउनलोड करें।",
            "लिंक पेस्ट करें, तुरंत वीडियो देखें और ओरिजिनल क्वालिटी में सेव करें।",
            "सिंगल वीडियो और वीडियो वाले कैरॉसेल दोनों सपोर्ट करता है, हर आइटम का अलग डाउनलोड बटन।",
            "प्राइवेट अकाउंट सपोर्टेड नहीं हैं। अनुमति होने पर ही डाउनलोड करें।",
        ],
        "seo_reels_title": "पब्लिक प्रोफाइल के लिए Instagram रील्स डाउनलोडर",
        "seo_reels_paragraphs": [
            "पब्लिक प्रोफाइल से रील्स तेज़ी से डाउनलोड करें, जल्दी प्रिव्यू के साथ।",
            "रील लिंक पेस्ट करें और वीडियो तुरंत ऑरिजिनल क्वालिटी में पाएं।",
            "क्रिएटर्स और मार्केटर्स के लिए पब्लिक रील्स तक तेज़ पहुंच।",
            "प्राइवेट अकाउंट सपोर्टेड नहीं हैं। कॉपीराइट का सम्मान करें।",
        ],
        "seo_photo_title": "पब्लिक पोस्ट के लिए Instagram फोटो डाउनलोडर",
        "seo_photo_paragraphs": [
            "पब्लिक पोस्ट की फोटो हाई क्वालिटी में डाउनलोड करें और साफ़ प्रिव्यू देखें।",
            "सिंगल और मल्टी-फोटो कैरॉसेल सपोर्ट, हर फोटो के लिए अलग डाउनलोड बटन।",
            "लिंक पेस्ट करें, सभी फोटो देखें और जल्दी सेव करें।",
            "प्राइवेट अकाउंट सपोर्टेड नहीं हैं। अनुमति होने पर ही डाउनलोड करें।",
        ],
    },
    "hu": {
        "seo_video_title": "Instagram videó letöltő nyilvános posztokhoz",
        "seo_video_paragraphs": [
            "Instagram videók letöltése nyilvános posztokból tiszta előnézettel és közvetlen letöltéssel.",
            "Link beillesztése, azonnali lejátszás és mentés eredeti minőségben.",
            "Működik egyedi videókra és videós karusellekre, minden elemhez külön letöltés.",
            "Privát fiókok nem támogatottak. Csak engedéllyel tölts le.",
        ],
        "seo_reels_title": "Instagram Reels letöltő nyilvános profilokhoz",
        "seo_reels_paragraphs": [
            "Instagram Reels letöltése nyilvános profilokról másodpercek alatt.",
            "Reel link beillesztése, és a videó azonnal elérhető eredeti minőségben.",
            "Hasznos kreatoroknak és marketingeseknek gyors inspirációhoz.",
            "Privát fiókok nem támogatottak. Tartsd tiszteletben a szerzői jogokat.",
        ],
        "seo_photo_title": "Instagram fotó letöltő nyilvános posztokhoz",
        "seo_photo_paragraphs": [
            "Instagram fotók letöltése nyilvános posztokból magas minőségben.",
            "Egyedi fotók és többképes karusellek támogatása, minden képhez külön gomb.",
            "Link beillesztése, előnézet, gyors mentés.",
            "Privát fiókok nem támogatottak. Csak engedéllyel tölts le.",
        ],
    },
    "id": {
        "seo_video_title": "Pengunduh Video Instagram untuk Post Publik",
        "seo_video_paragraphs": [
            "Unduh video Instagram dari post publik dengan pratinjau bersih dan tautan langsung.",
            "Tempel tautan, tonton video segera, dan simpan dalam kualitas asli.",
            "Mendukung video tunggal dan carousel berisi video, setiap item punya tombol unduh.",
            "Akun privat tidak didukung. Unduh hanya dengan izin.",
        ],
        "seo_reels_title": "Pengunduh Reels Instagram untuk Profil Publik",
        "seo_reels_paragraphs": [
            "Unduh Reels Instagram dari profil publik dalam hitungan detik.",
            "Tempel tautan Reel dan dapatkan video segera dalam kualitas asli.",
            "Cocok untuk kreator dan marketer yang butuh akses cepat ke Reels publik.",
            "Akun privat tidak didukung. Hormati hak cipta.",
        ],
        "seo_photo_title": "Pengunduh Foto Instagram untuk Post Publik",
        "seo_photo_paragraphs": [
            "Unduh foto Instagram dari post publik dengan kualitas tinggi.",
            "Mendukung post foto tunggal dan carousel multi-foto, setiap foto punya tombol unduh.",
            "Tempel tautan, pratinjau semua foto, simpan dengan cepat.",
            "Akun privat tidak didukung. Unduh hanya dengan izin.",
        ],
    },
    "it": {
        "seo_video_title": "Downloader video Instagram per post pubblici",
        "seo_video_paragraphs": [
            "Scarica video Instagram da post pubblici con anteprima chiara e download diretto.",
            "Incolla il link, guarda subito il video e salvalo in qualità originale.",
            "Supporta video singoli e caroselli con video, ogni elemento ha il suo download.",
            "Account privati non supportati. Scarica solo con permesso.",
        ],
        "seo_reels_title": "Downloader Reels Instagram per profili pubblici",
        "seo_reels_paragraphs": [
            "Scarica Reels Instagram da profili pubblici in pochi secondi.",
            "Incolla il link di un Reel e ottieni il video subito in qualità originale.",
            "Ideale per creator e marketer che vogliono accesso rapido ai Reels pubblici.",
            "Account privati non supportati. Rispetta il copyright.",
        ],
        "seo_photo_title": "Downloader foto Instagram per post pubblici",
        "seo_photo_paragraphs": [
            "Scarica foto Instagram da post pubblici in alta qualità con anteprima.",
            "Supporta post singoli e caroselli multipli, ogni immagine ha il suo download.",
            "Incolla il link, visualizza tutte le foto e salva rapidamente.",
            "Account privati non supportati. Scarica solo con permesso.",
        ],
    },
    "ja": {
        "seo_video_title": "公開投稿向けInstagram動画ダウンローダー",
        "seo_video_paragraphs": [
            "公開投稿のInstagram動画を、きれいなプレビューと直接ダウンロードで取得できます。",
            "リンクを貼り付けるとすぐ再生でき、オリジナル品質で保存できます。",
            "単体動画と動画入りカルーセルに対応し、各項目にダウンロードボタン付き。",
            "非公開アカウントは非対応。権利を尊重し、許可のある内容のみ保存してください。",
        ],
        "seo_reels_title": "公開プロフィール向けInstagram Reelsダウンローダー",
        "seo_reels_paragraphs": [
            "公開プロフィールのReelsを数秒でダウンロードできます。",
            "Reelリンクを貼り付ければ、すぐにオリジナル品質で取得可能です。",
            "クリエイターやマーケターが公開Reelsに素早くアクセスするのに最適。",
            "非公開アカウントは非対応。著作権を尊重してください。",
        ],
        "seo_photo_title": "公開投稿向けInstagram写真ダウンローダー",
        "seo_photo_paragraphs": [
            "公開投稿のInstagram写真を高画質でダウンロードできます。",
            "単一写真と複数写真カルーセルに対応し、各写真にダウンロードボタン付き。",
            "リンクを貼り付け、すべての写真をプレビューして素早く保存。",
            "非公開アカウントは非対応。許可のある内容のみ保存してください。",
        ],
    },
    "ko": {
        "seo_video_title": "공개 게시물용 Instagram 동영상 다운로더",
        "seo_video_paragraphs": [
            "공개 게시물의 Instagram 동영상을 깔끔한 미리보기와 직접 다운로드로 저장하세요.",
            "링크를 붙여넣으면 즉시 재생되고 원본 품질로 저장할 수 있습니다.",
            "단일 동영상과 동영상 포함 캐러셀을 지원하며 각 항목에 다운로드 버튼이 있습니다.",
            "비공개 계정은 지원되지 않습니다. 허가된 콘텐츠만 다운로드하세요.",
        ],
        "seo_reels_title": "공개 프로필용 Instagram Reels 다운로더",
        "seo_reels_paragraphs": [
            "공개 프로필의 Reels를 몇 초 만에 다운로드하세요.",
            "Reel 링크를 붙여넣으면 원본 품질의 영상을 바로 받을 수 있습니다.",
            "크리에이터와 마케터에게 공개 Reels에 빠르게 접근할 수 있는 도구입니다.",
            "비공개 계정은 지원되지 않습니다. 저작권을 존중하세요.",
        ],
        "seo_photo_title": "공개 게시물용 Instagram 사진 다운로더",
        "seo_photo_paragraphs": [
            "공개 게시물의 Instagram 사진을 고화질로 다운로드하세요.",
            "단일 사진과 다중 사진 캐러셀을 지원하며 각 사진에 다운로드 버튼이 있습니다.",
            "링크를 붙여넣고 모든 사진을 미리 본 후 빠르게 저장하세요.",
            "비공개 계정은 지원되지 않습니다. 허가된 콘텐츠만 다운로드하세요.",
        ],
    },
    "pl": {
        "seo_video_title": "Pobieranie wideo z Instagram dla publicznych postów",
        "seo_video_paragraphs": [
            "Pobieraj wideo z publicznych postów Instagram z czystym podglądem i bezpośrednim pobraniem.",
            "Wklej link, obejrzyj wideo od razu i zapisz w oryginalnej jakości.",
            "Obsługuje pojedyncze wideo i karuzele z wideo, każdy element ma własny przycisk pobierania.",
            "Konta prywatne nie są obsługiwane. Pobieraj tylko za zgodą.",
        ],
        "seo_reels_title": "Pobieranie Instagram Reels dla publicznych profili",
        "seo_reels_paragraphs": [
            "Pobieraj Reels z publicznych profili w kilka sekund.",
            "Wklej link do Reels i pobierz wideo natychmiast w oryginalnej jakości.",
            "Idealne dla twórców i marketerów do szybkiego dostępu do publicznych Reels.",
            "Konta prywatne nie są obsługiwane. Szanuj prawa autorskie.",
        ],
        "seo_photo_title": "Pobieranie zdjęć z Instagram dla publicznych postów",
        "seo_photo_paragraphs": [
            "Pobieraj zdjęcia z publicznych postów Instagram w wysokiej jakości.",
            "Obsługuje pojedyncze zdjęcia i karuzele, każda fotografia ma własny przycisk.",
            "Wklej link, obejrzyj wszystkie zdjęcia i szybko je zapisz.",
            "Konta prywatne nie są obsługiwane. Pobieraj tylko za zgodą.",
        ],
    },
    "pt": {
        "seo_video_title": "Downloader de vídeos do Instagram para posts públicos",
        "seo_video_paragraphs": [
            "Baixe vídeos do Instagram de posts públicos com prévia limpa e download direto.",
            "Cole o link, assista imediatamente e salve em qualidade original.",
            "Funciona com vídeos únicos e carrosséis com vídeos, cada item com seu botão.",
            "Contas privadas não são suportadas. Baixe apenas com permissão.",
        ],
        "seo_reels_title": "Downloader de Reels do Instagram para perfis públicos",
        "seo_reels_paragraphs": [
            "Baixe Reels de perfis públicos em segundos com prévia rápida.",
            "Cole o link do Reel e obtenha o vídeo na hora em qualidade original.",
            "Ótimo para criadores e marketers que precisam de acesso rápido a Reels públicos.",
            "Contas privadas não são suportadas. Respeite direitos autorais.",
        ],
        "seo_photo_title": "Downloader de fotos do Instagram para posts públicos",
        "seo_photo_paragraphs": [
            "Baixe fotos do Instagram de posts públicos em alta qualidade.",
            "Suporta post único e carrosséis com várias fotos, cada foto com botão próprio.",
            "Cole o link, visualize todas as fotos e salve rapidamente.",
            "Contas privadas não são suportadas. Baixe apenas com permissão.",
        ],
    },
    "ru": {
        "seo_video_title": "Загрузчик видео Instagram для публичных постов",
        "seo_video_paragraphs": [
            "Скачивайте видео из публичных постов Instagram с чистым предпросмотром и прямой загрузкой.",
            "Вставьте ссылку, сразу смотрите видео и сохраняйте в оригинальном качестве.",
            "Поддерживает одиночные видео и карусели с видео, у каждого элемента свой файл.",
            "Приватные аккаунты не поддерживаются. Скачивайте только с разрешения.",
        ],
        "seo_reels_title": "Загрузчик Instagram Reels для публичных профилей",
        "seo_reels_paragraphs": [
            "Скачивайте Reels с публичных профилей за секунды.",
            "Вставьте ссылку на Reel и получите видео сразу в оригинальном качестве.",
            "Подходит для создателей и маркетологов, которым нужен быстрый доступ к публичным Reels.",
            "Приватные аккаунты не поддерживаются. Уважайте авторские права.",
        ],
        "seo_photo_title": "Загрузчик фото Instagram для публичных постов",
        "seo_photo_paragraphs": [
            "Скачивайте фотографии Instagram из публичных постов в высоком качестве.",
            "Поддерживает одиночные фото и карусели, каждая картинка с отдельной кнопкой.",
            "Вставьте ссылку, просмотрите все фото и быстро сохраните.",
            "Приватные аккаунты не поддерживаются. Скачивайте только с разрешения.",
        ],
    },
    "es": {
        "seo_video_title": "Descargador de videos de Instagram para publicaciones públicas",
        "seo_video_paragraphs": [
            "Descarga videos de Instagram de publicaciones públicas con vista previa limpia y descarga directa.",
            "Pega un enlace, reproduce el video al instante y guárdalo en su calidad original.",
            "Funciona con videos individuales y carruseles con videos, cada uno con su botón de descarga.",
            "Las cuentas privadas no son compatibles. Descarga solo con permiso.",
        ],
        "seo_reels_title": "Descargador de Reels de Instagram para perfiles públicos",
        "seo_reels_paragraphs": [
            "Descarga Reels de perfiles públicos en segundos con vista previa rápida.",
            "Pega el enlace del Reel y obtén el video de inmediato en calidad original.",
            "Ideal para creadores y marketers que necesitan acceso rápido a Reels públicos.",
            "Las cuentas privadas no son compatibles. Respeta los derechos de autor.",
        ],
        "seo_photo_title": "Descargador de fotos de Instagram para publicaciones públicas",
        "seo_photo_paragraphs": [
            "Descarga fotos de Instagram de publicaciones públicas en alta calidad.",
            "Compatible con fotos únicas y carruseles, cada imagen con su botón de descarga.",
            "Pega el enlace, previsualiza todas las fotos y guárdalas rápidamente.",
            "Las cuentas privadas no son compatibles. Descarga solo con permiso.",
        ],
    },
    "sw": {
        "seo_video_title": "Kipakua Video za Instagram kwa Posti za Umma",
        "seo_video_paragraphs": [
            "Pakua video za Instagram kutoka posti za umma na mwonekano safi pamoja na upakuaji wa moja kwa moja.",
            "Bandika kiungo, tazama video mara moja na uihifadhi kwa ubora wa asili.",
            "Hufanya kazi kwa video moja na carousels zenye video, kila kipengele kina kitufe chake.",
            "Akaunti binafsi hazisaidiwi. Pakua tu kwa ruhusa.",
        ],
        "seo_reels_title": "Kipakua Reels za Instagram kwa Profaili za Umma",
        "seo_reels_paragraphs": [
            "Pakua Reels kutoka profaili za umma kwa sekunde chache.",
            "Bandika kiungo cha Reel na upate video mara moja kwa ubora wa asili.",
            "Bora kwa watayarishi na wauzaji wanaohitaji ufikiaji wa haraka wa Reels za umma.",
            "Akaunti binafsi hazisaidiwi. Heshimu hakimiliki.",
        ],
        "seo_photo_title": "Kipakua Picha za Instagram kwa Posti za Umma",
        "seo_photo_paragraphs": [
            "Pakua picha za Instagram kutoka posti za umma kwa ubora wa juu.",
            "Inasaidia picha moja na carousels nyingi, kila picha ina kitufe chake.",
            "Bandika kiungo, tazama picha zote, na zihifadhi haraka.",
            "Akaunti binafsi hazisaidiwi. Pakua tu kwa ruhusa.",
        ],
    },
    "te": {
        "seo_video_title": "పబ్లిక్ పోస్టుల కోసం Instagram వీడియో డౌన్‌లోడర్",
        "seo_video_paragraphs": [
            "పబ్లిక్ పోస్టుల నుండి Instagram వీడియోలను క్లియర్ ప్రివ్యూ మరియు డైరెక్ట్ డౌన్‌లోడ్‌తో పొందండి.",
            "లింక్ పేస్ట్ చేస్తే వెంటనే వీడియో చూడొచ్చు, ఒరిజినల్ క్వాలిటీలో సేవ్ చేయొచ్చు.",
            "సింగిల్ వీడియోలు మరియు వీడియో ఉన్న కారౌజెల్స్‌కు మద్దతు, ప్రతి ఐటెమ్‌కు డౌన్‌లోడ్ బటన్.",
            "ప్రైవేట్ అకౌంట్లు సపోర్ట్ చేయబడవు. అనుమతి ఉన్నప్పుడు మాత్రమే డౌన్‌లోడ్ చేయండి.",
        ],
        "seo_reels_title": "పబ్లిక్ ప్రొఫైళ్ల కోసం Instagram రీల్స్ డౌన్‌లోడర్",
        "seo_reels_paragraphs": [
            "పబ్లిక్ ప్రొఫైళ్ల నుండి రీల్స్‌ను కొన్ని సెకన్లలో డౌన్‌లోడ్ చేయండి.",
            "రీల్ లింక్ పేస్ట్ చేయగానే వీడియో ఒరిజినల్ క్వాలిటీలో వెంటనే లభిస్తుంది.",
            "క్రియేటర్లు, మార్కెటర్లకు పబ్లిక్ రీల్స్‌కు త్వరిత యాక్సెస్.",
            "ప్రైవేట్ అకౌంట్లు సపోర్ట్ చేయబడవు. కాపీరైట్‌ను గౌరవించండి.",
        ],
        "seo_photo_title": "పబ్లిక్ పోస్టుల కోసం Instagram ఫోటో డౌన్‌లోడర్",
        "seo_photo_paragraphs": [
            "పబ్లిక్ పోస్టుల నుండి Instagram ఫోటోలను హై క్వాలిటీలో డౌన్‌లోడ్ చేయండి.",
            "సింగిల్ ఫోటో మరియు మల్టీ-ఫోటో కారౌజెల్స్‌కు మద్దతు, ప్రతి ఫోటోకు డౌన్‌లోడ్ బటన్.",
            "లింక్ పేస్ట్ చేయండి, అన్ని ఫోటోలు ప్రివ్యూ చేసి వేగంగా సేవ్ చేయండి.",
            "ప్రైవేట్ అకౌంట్లు సపోర్ట్ చేయబడవు. అనుమతి ఉన్నప్పుడు మాత్రమే డౌన్‌లోడ్ చేయండి.",
        ],
    },
    "th": {
        "seo_video_title": "ตัวดาวน์โหลดวิดีโอ Instagram สำหรับโพสต์สาธารณะ",
        "seo_video_paragraphs": [
            "ดาวน์โหลดวิดีโอ Instagram จากโพสต์สาธารณะพร้อมพรีวิวที่ชัดเจนและลิงก์ดาวน์โหลดตรง",
            "วางลิงก์แล้วดูวิดีโอได้ทันทีและบันทึกคุณภาพต้นฉบับ",
            "รองรับวิดีโอเดี่ยวและโพสต์แบบคารูเซลที่มีวิดีโอ ทุกชิ้นมีปุ่มดาวน์โหลด",
            "ไม่รองรับบัญชีส่วนตัว ดาวน์โหลดเฉพาะเมื่อได้รับอนุญาต",
        ],
        "seo_reels_title": "ตัวดาวน์โหลด Instagram Reels สำหรับโปรไฟล์สาธารณะ",
        "seo_reels_paragraphs": [
            "ดาวน์โหลด Reels จากโปรไฟล์สาธารณะได้ภายในไม่กี่วินาที",
            "วางลิงก์ Reel แล้วรับวิดีโอทันทีในคุณภาพต้นฉบับ",
            "เหมาะสำหรับครีเอเตอร์และนักการตลาดที่ต้องการเข้าถึง Reels สาธารณะอย่างรวดเร็ว",
            "ไม่รองรับบัญชีส่วนตัว โปรดเคารพลิขสิทธิ์",
        ],
        "seo_photo_title": "ตัวดาวน์โหลดรูปภาพ Instagram สำหรับโพสต์สาธารณะ",
        "seo_photo_paragraphs": [
            "ดาวน์โหลดรูปภาพ Instagram จากโพสต์สาธารณะในคุณภาพสูงพร้อมพรีวิว",
            "รองรับรูปเดี่ยวและคารูเซลหลายรูป ทุกภาพมีปุ่มดาวน์โหลด",
            "วางลิงก์ ดูรูปทั้งหมด แล้วบันทึกได้รวดเร็ว",
            "ไม่รองรับบัญชีส่วนตัว ดาวน์โหลดเฉพาะเมื่อได้รับอนุญาต",
        ],
    },
    "tr": {
        "seo_video_title": "Herkese Açık Gönderiler için Instagram Video İndirici",
        "seo_video_paragraphs": [
            "Herkese açık Instagram videolarını temiz önizleme ve doğrudan indirme ile kaydedin.",
            "Bağlantıyı yapıştırın, videoyu anında izleyin ve orijinal kalitede kaydedin.",
            "Tek videolar ve video içeren karuseller desteklenir, her öğe için ayrı indirme düğmesi.",
            "Özel hesaplar desteklenmez. Yalnızca izinli içerik indirin.",
        ],
        "seo_reels_title": "Herkese Açık Profiller için Instagram Reels İndirici",
        "seo_reels_paragraphs": [
            "Herkese açık profillerden Reels videolarını saniyeler içinde indirin.",
            "Reel bağlantısını yapıştırın ve videoyu orijinal kalitede anında alın.",
            "Creator ve pazarlamacılar için public Reels'e hızlı erişim sağlar.",
            "Özel hesaplar desteklenmez. Telif haklarına saygı gösterin.",
        ],
        "seo_photo_title": "Herkese Açık Gönderiler için Instagram Fotoğraf İndirici",
        "seo_photo_paragraphs": [
            "Herkese açık gönderilerden Instagram fotoğraflarını yüksek kalitede indirin.",
            "Tek fotoğraf ve çoklu fotoğraf karuselleri desteklenir, her fotoğraf için düğme vardır.",
            "Bağlantıyı yapıştırın, tüm fotoğrafları önizleyin ve hızlıca kaydedin.",
            "Özel hesaplar desteklenmez. Yalnızca izinli içerik indirin.",
        ],
    },
    "uk": {
        "seo_video_title": "Завантажувач відео Instagram для публічних постів",
        "seo_video_paragraphs": [
            "Завантажуйте відео з публічних постів Instagram з чистим переглядом і прямим завантаженням.",
            "Вставте посилання, дивіться відео одразу та зберігайте в оригінальній якості.",
            "Підтримуються одиночні відео та каруселі з відео, кожен елемент має кнопку завантаження.",
            "Приватні акаунти не підтримуються. Завантажуйте лише за наявності дозволу.",
        ],
        "seo_reels_title": "Завантажувач Instagram Reels для публічних профілів",
        "seo_reels_paragraphs": [
            "Завантажуйте Reels з публічних профілів за кілька секунд.",
            "Вставьте посилання на Reel і отримайте відео одразу в оригінальній якості.",
            "Зручно для творців і маркетологів, яким потрібен швидкий доступ до публічних Reels.",
            "Приватні акаунти не підтримуються. Поважайте авторські права.",
        ],
        "seo_photo_title": "Завантажувач фото Instagram для публічних постів",
        "seo_photo_paragraphs": [
            "Завантажуйте фото Instagram з публічних постів у високій якості.",
            "Підтримуються одиночні фото і багатофoto-каруселі, кожне фото має власну кнопку.",
            "Вставьте посилання, перегляньте всі фото та швидко збережіть.",
            "Приватні акаунти не підтримуються. Завантажуйте лише за наявності дозволу.",
        ],
    },
}

for code, seo in SEO_I18N.items():
    STRINGS.setdefault(code, {}).update(seo)

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


def send_contact_email(name: str, email: str, message: str) -> Tuple[bool, str]:
    host = os.getenv("SMTP_HOST")
    if not host:
        return False, "Email is not configured yet."
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM") or user
    if not from_addr:
        return False, "Email is not configured yet."

    msg = EmailMessage()
    msg["Subject"] = f"New message from {STRINGS['en']['brand']}"
    msg["From"] = from_addr
    msg["To"] = CONTACT_TO
    if email:
        msg["Reply-To"] = email
    msg.set_content(
        f"Name: {name or '-'}\n"
        f"Email: {email or '-'}\n\n"
        f"Message:\n{message}"
    )

    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True, ""
    except Exception:
        return False, "Unable to send message right now."


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


def page_meta(t: Dict[str, str], media_type: str) -> Tuple[str, str, str, List[str]]:
    key = normalize_media_type(media_type)
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
    error: Optional[str] = None,
    modal_show: bool = False,
    modal_title: Optional[str] = None,
    modal_message: Optional[str] = None,
):
    t = build_strings(lang)
    selected_type = normalize_media_type(selected_type)
    page_title, page_description, seo_title, seo_paragraphs = page_meta(t, selected_type)
    post_url = url_for(MEDIA_ENDPOINTS[selected_type], lang=lang)
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
        post_url=post_url,
        items=items or [],
        error=error,
        modal_show=modal_show,
        modal_title=modal_title,
        modal_message=modal_message,
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

    media_url = (request.form.get("media_url") or "").strip()
    parsed = parse_media_url(media_url)
    if not parsed:
        return render_index(lang, selected_type=media_type, page_slug=page_slug, error=t["error_invalid_link"])

    url_kind, shortcode = parsed

    try:
        loader = make_loader()
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        owner_profile = getattr(post, "owner_profile", None)
        if owner_profile and getattr(owner_profile, "is_private", False):
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                modal_show=True,
                modal_title=t["modal_private_title"],
                modal_message=t["modal_private_body"],
            )

        if media_type == "reels" and not (url_kind == "reel" or is_reel(post)):
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=t["modal_mismatch_reel"],
            )

        items = extract_items(post, media_type)
        if not items:
            mismatch = t["modal_mismatch_photo"] if media_type == "photo" else t["modal_mismatch_video"]
            return render_index(
                lang,
                selected_type=media_type,
                page_slug=page_slug,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=mismatch,
            )

        return render_index(lang, selected_type=media_type, page_slug=page_slug, items=items)

    except LoginException:
        return render_index(
            lang,
            selected_type=media_type,
            page_slug=page_slug,
            modal_show=True,
            modal_title=t["modal_private_title"],
            modal_message=t["modal_private_body"],
        )
    except ConnectionException as exc:
        return render_index(lang, selected_type=media_type, page_slug=page_slug, error=f"Connection error: {exc}")
    except Exception as exc:  # pragma: no cover
        return render_index(lang, selected_type=media_type, page_slug=page_slug, error=f"Unexpected error: {exc}")


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


@app.route("/<lang>/contact", methods=["GET", "POST"])
def contact(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    notice = None
    error = None
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not message:
            error = "Please enter a message."
        else:
            ok, err_msg = send_contact_email(name, email, message)
            if ok:
                notice = "Thanks! Your message has been sent."
            else:
                error = err_msg
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
        page_notice=notice,
        page_error=error,
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
    base = base_url()
    urls: List[str] = []

    for lang in LANG_ORDER:
        urls.append(f"{base}/{lang}")
        urls.append(f"{base}/{lang}/{MEDIA_SLUGS['video']}")
        urls.append(f"{base}/{lang}/{MEDIA_SLUGS['reels']}")
        urls.append(f"{base}/{lang}/{MEDIA_SLUGS['photo']}")
        urls.append(f"{base}/{lang}/about")
        urls.append(f"{base}/{lang}/contact")
        urls.append(f"{base}/{lang}/privacy")

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{url}</loc>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    return Response("\n".join(xml_lines), mimetype="application/xml")

@app.route("/ads.txt")
def ads_txt():
    return Response(ADS_TXT + "\n", mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
