#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import re
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
        "meta_description": "Download Instagram videos, reels, and photos from public posts. Paste a link and get previews with direct downloads.",
        "meta_keywords": "instagram downloader, instagram video downloader, instagram reels downloader, instagram photo downloader, download instagram media",
        "brand": "Media Vault",
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
        "page_contact_title": "Contact us",
        "page_contact_body": "For support or inquiries, email: support@example.com",
        "page_privacy_title": "Privacy policy",
        "page_privacy_body": "We do not store the media you download. Requests are processed in real time.",
        "preview_alt": "Instagram media preview",
    },
    "ar": {
        "title": "أداة تنزيل وسائط إنستغرام",
        "meta_description": "حمّل فيديوهات وصور وريـلز إنستغرام من المنشورات العامة. الصق الرابط وشاهد المعاينة.",
        "meta_keywords": "تحميل انستغرام, تنزيل ريلز, تحميل فيديو انستغرام, تنزيل صور انستغرام",
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
        "placeholder": "الصق رابط منشور أو ريلز إنستغرام",
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
        "modal_mismatch_title": "Nieprawidłowy typ",
        "modal_mismatch_video": "Ten link to obraz. Wybierz zakładkę Zdjęcie.",
        "modal_mismatch_photo": "Ten link to wideo. Wybierz Wideo lub Reels.",
        "modal_mismatch_reel": "To nie jest reels. Wybierz Wideo.",
        "seo_title": "Szybki downloader Instagrama dla publicznych postów",
        "footer_contact": "Kontakt",
        "footer_about": "O nas",
        "footer_privacy": "Polityka prywatności",
    },
    "pt": {
        "title": "Downloader de mídia do Instagram",
        "meta_description": "Baixe vídeos, reels e fotos do Instagram de posts públicos. Cole o link para visualizar.",
        "meta_keywords": "instagram downloader, baixar instagram, reels instagram, baixar fotos",
        "status": "Somente posts públicos",
        "language_label": "Idioma",
        "tab_video": "Vídeo",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Baixe todo o conteúdo do Instagram aqui",
        "headline_video": "Downloader de vídeos do Instagram",
        "headline_reels": "Downloader de Reels do Instagram",
        "headline_photo": "Downloader de fotos do Instagram",
        "sub": "Cole um link de post ou reels público. Contas privadas mostram alerta.",
        "placeholder": "Cole o link do post ou reels do Instagram",
        "paste": "Colar",
        "clear": "Limpar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Baixar",
        "modal_private_title": "Conta privada",
        "modal_private_body": "Esta conta é privada. Não é possível baixar.",
        "modal_mismatch_title": "Tipo de mídia incorreto",
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
        "meta_description": "Скачивайте видео, reels и фото Instagram из публичных постов. Вставьте ссылку и посмотрите превью.",
        "meta_keywords": "instagram downloader, скачать инстаграм, reels instagram, скачать фото",
        "status": "Только публичные посты",
        "language_label": "Язык",
        "tab_video": "Видео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Скачивайте весь контент Instagram здесь",
        "headline_video": "Загрузчик видео Instagram",
        "headline_reels": "Загрузчик Reels Instagram",
        "headline_photo": "Загрузчик фото Instagram",
        "sub": "Вставьте ссылку на публичный пост или reels. Для приватных аккаунтов будет предупреждение.",
        "placeholder": "Вставьте ссылку на пост или reels Instagram",
        "paste": "Вставить",
        "clear": "Очистить",
        "search": "Поиск",
        "results": "Результаты",
        "download": "Скачать",
        "modal_private_title": "Приватный аккаунт",
        "modal_private_body": "Этот аккаунт приватный. Нельзя скачать медиа.",
        "modal_mismatch_title": "Неверный тип",
        "modal_mismatch_video": "Эта ссылка — изображение. Выберите вкладку Фото.",
        "modal_mismatch_photo": "Эта ссылка — видео. Выберите Видео или Reels.",
        "modal_mismatch_reel": "Эта ссылка не reels. Выберите Видео.",
        "seo_title": "Быстрый загрузчик Instagram для публичных постов",
        "footer_contact": "Контакты",
        "footer_about": "О нас",
        "footer_privacy": "Политика конфиденциальности",
    },
    "es": {
        "title": "Descargador de medios de Instagram",
        "meta_description": "Descarga videos, reels y fotos de Instagram desde publicaciones públicas. Pega el enlace para previsualizar.",
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
        "placeholder": "Pega el enlace de un post o reel de Instagram",
        "paste": "Pegar",
        "clear": "Limpiar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Descargar",
        "modal_private_title": "Cuenta privada",
        "modal_private_body": "Esta cuenta es privada. No se puede descargar.",
        "modal_mismatch_title": "Tipo incorrecto",
        "modal_mismatch_video": "Este enlace es una imagen. Selecciona la pestaña Foto.",
        "modal_mismatch_photo": "Este enlace es un video. Selecciona Video o Reels.",
        "modal_mismatch_reel": "Este enlace no es reel. Selecciona Video.",
        "seo_title": "Descargador rápido de Instagram para publicaciones públicas",
        "footer_contact": "Contacto",
        "footer_about": "Sobre nosotros",
        "footer_privacy": "Política de privacidad",
    },
    "sw": {
        "title": "Kipakua Media za Instagram",
        "meta_description": "Pakua video, reels na picha za Instagram kutoka kwenye posti za umma. Bandika kiungo ili kuona mwonekano.",
        "meta_keywords": "instagram downloader, pakua instagram, reels instagram, pakua picha",
        "status": "Machapisho ya umma tu",
        "language_label": "Lugha",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Picha",
        "kicker": "Pakua maudhui yote ya Instagram hapa",
        "headline_video": "Kipakua Video za Instagram",
        "headline_reels": "Kipakua Reels za Instagram",
        "headline_photo": "Kipakua Picha za Instagram",
        "sub": "Bandika kiungo cha post au reels ya umma. Akaunti binafsi zitaonyesha tahadhari.",
        "placeholder": "Bandika kiungo cha post au reels ya Instagram",
        "paste": "Bandika",
        "clear": "Futa",
        "search": "Tafuta",
        "results": "Matokeo",
        "download": "Pakua",
        "modal_private_title": "Akaunti Binafsi",
        "modal_private_body": "Akaunti hii ni binafsi. Haiwezi kupakua media.",
        "modal_mismatch_title": "Aina ya media si sahihi",
        "modal_mismatch_video": "Kiungo hiki ni picha. Chagua kichupo cha Picha.",
        "modal_mismatch_photo": "Kiungo hiki ni video. Chagua Video au Reels.",
        "modal_mismatch_reel": "Kiungo hiki sio reels. Chagua Video.",
        "seo_title": "Kipakua cha haraka cha Instagram kwa posti za umma",
        "footer_contact": "Wasiliana nasi",
        "footer_about": "Kuhusu sisi",
        "footer_privacy": "Sera ya faragha",
    },
    "te": {
        "title": "ఇన్‌స్టాగ్రామ్ మీడియా డౌన్‌లోడర్",
        "meta_description": "పబ్లిక్ పోస్టుల నుండి Instagram వీడియోలు, రీల్స్, ఫోటోలు డౌన్‌లోడ్ చేయండి. లింక్ పేస్ట్ చేసి ప్రివ్యూ చూడండి.",
        "meta_keywords": "instagram downloader, రీల్స్ డౌన్‌లోడ్, వీడియో డౌన్‌లోడ్, ఫోటో డౌన్‌లోడ్",
        "status": "పబ్లిక్ పోస్టులు మాత్రమే",
        "language_label": "భాష",
        "tab_video": "వీడియో",
        "tab_reels": "రీల్స్",
        "tab_photo": "ఫోటో",
        "kicker": "ఇక్కడ అన్ని Instagram కంటెంట్ డౌన్‌లోడ్ చేయండి",
        "headline_video": "Instagram వీడియో డౌన్‌లోడర్",
        "headline_reels": "Instagram రీల్స్ డౌన్‌లోడర్",
        "headline_photo": "Instagram ఫోటో డౌన్‌లోడర్",
        "sub": "పబ్లిక్ పోస్ట్ లేదా రీల్ లింక్ పేస్ట్ చేయండి. ప్రైవేట్ ఖాతాల్లో హెచ్చరిక కనిపిస్తుంది.",
        "placeholder": "Instagram పోస్ట్ లేదా రీల్ లింక్ పేస్ట్ చేయండి",
        "paste": "పేస్ట్",
        "clear": "క్లియర్",
        "search": "సెర్చ్",
        "results": "ఫలితాలు",
        "download": "డౌన్‌లోడ్",
        "modal_private_title": "ప్రైవేట్ అకౌంట్",
        "modal_private_body": "ఈ అకౌంట్ ప్రైవేట్. మీడియాను డౌన్‌లోడ్ చేయలేరు.",
        "modal_mismatch_title": "తప్పు మీడియా టైప్",
        "modal_mismatch_video": "ఈ లింక్ చిత్రం. ఫోటో ట్యాబ్ ఎంచుకోండి.",
        "modal_mismatch_photo": "ఈ లింక్ వీడియో. వీడియో లేదా రీల్స్ ట్యాబ్ ఎంచుకోండి.",
        "modal_mismatch_reel": "ఈ లింక్ రీల్ కాదు. వీడియో ఎంచుకోండి.",
        "seo_title": "పబ్లిక్ పోస్టుల కోసం వేగమైన Instagram డౌన్‌లోడర్",
        "footer_contact": "సంప్రదించండి",
        "footer_about": "మా గురించి",
        "footer_privacy": "ప్రైవసీ పాలసీ",
    },
    "th": {
        "title": "เครื่องมือดาวน์โหลดสื่อ Instagram",
        "meta_description": "ดาวน์โหลดวิดีโอ รีลส์ และรูปภาพ Instagram จากโพสต์สาธารณะ วางลิงก์เพื่อดูตัวอย่าง",
        "meta_keywords": "instagram downloader, ดาวน์โหลด instagram, reels instagram, ดาวน์โหลดรูป",
        "status": "เฉพาะโพสต์สาธารณะ",
        "language_label": "ภาษา",
        "tab_video": "วิดีโอ",
        "tab_reels": "รีลส์",
        "tab_photo": "รูปภาพ",
        "kicker": "ดาวน์โหลดทุกอย่างจาก Instagram ได้ที่นี่",
        "headline_video": "ดาวน์โหลดวิดีโอ Instagram",
        "headline_reels": "ดาวน์โหลด Reels Instagram",
        "headline_photo": "ดาวน์โหลดรูปภาพ Instagram",
        "sub": "วางลิงก์โพสต์หรือรีลส์สาธารณะ บัญชีส่วนตัวจะแสดงการแจ้งเตือน",
        "placeholder": "วางลิงก์โพสต์หรือรีลส์ Instagram",
        "paste": "วาง",
        "clear": "ล้าง",
        "search": "ค้นหา",
        "results": "ผลลัพธ์",
        "download": "ดาวน์โหลด",
        "modal_private_title": "บัญชีส่วนตัว",
        "modal_private_body": "บัญชีนี้เป็นส่วนตัว ไม่สามารถดาวน์โหลดได้",
        "modal_mismatch_title": "ชนิดสื่อไม่ถูกต้อง",
        "modal_mismatch_video": "ลิงก์นี้เป็นรูปภาพ กรุณาเลือกแท็บรูปภาพ",
        "modal_mismatch_photo": "ลิงก์นี้เป็นวิดีโอ กรุณาเลือกวิดีโอหรือรีลส์",
        "modal_mismatch_reel": "ลิงก์นี้ไม่ใช่รีลส์ กรุณาเลือกวิดีโอ",
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

MEDIA_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/(p|reel|reels|tv)/([^/?#]+)/?",
    re.IGNORECASE,
)

ALLOWED_HOST_SUFFIXES = ("cdninstagram.com", "fbcdn.net", "instagram.com")


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


def render_index(
    lang: str,
    *,
    selected_type: str = "video",
    items: Optional[List[Dict[str, str]]] = None,
    error: Optional[str] = None,
    modal_show: bool = False,
    modal_title: Optional[str] = None,
    modal_message: Optional[str] = None,
):
    t = build_strings(lang)
    return render_template(
        "index.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        default_lang=DEFAULT_LANG,
        selected_type=selected_type,
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
    return render_index(lang)


@app.route("/<lang>/download", methods=["POST"])
def download(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)

    media_url = (request.form.get("media_url") or "").strip()
    media_type = (request.form.get("media_type") or "video").strip()

    parsed = parse_media_url(media_url)
    if not parsed:
        return render_index(lang, selected_type=media_type, error=t["error_invalid_link"])

    url_kind, shortcode = parsed

    try:
        loader = make_loader()
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        owner_profile = getattr(post, "owner_profile", None)
        if owner_profile and getattr(owner_profile, "is_private", False):
            return render_index(
                lang,
                selected_type=media_type,
                modal_show=True,
                modal_title=t["modal_private_title"],
                modal_message=t["modal_private_body"],
            )

        if media_type == "reels" and not (url_kind == "reel" or is_reel(post)):
            return render_index(
                lang,
                selected_type=media_type,
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
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=mismatch,
            )

        return render_index(lang, selected_type=media_type, items=items)

    except LoginException:
        return render_index(
            lang,
            selected_type=media_type,
            modal_show=True,
            modal_title=t["modal_private_title"],
            modal_message=t["modal_private_body"],
        )
    except ConnectionException as exc:
        return render_index(lang, selected_type=media_type, error=f"Connection error: {exc}")
    except Exception as exc:  # pragma: no cover
        return render_index(lang, selected_type=media_type, error=f"Unexpected error: {exc}")


@app.route("/media-proxy")
def media_proxy():
    url = request.args.get("url", "")
    if not is_allowed_media_url(url):
        abort(400)
    resp = requests.get(url, stream=True, timeout=20)
    if resp.status_code != 200:
        abort(404)
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return Response(stream_with_context(resp.iter_content(chunk_size=8192)), content_type=content_type)


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
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_about_title"],
        page_body=t["page_about_body"],
        page_slug="about",
        default_lang=DEFAULT_LANG,
    )


@app.route("/<lang>/contact")
def contact(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_contact_title"],
        page_body=t["page_contact_body"],
        page_slug="contact",
        default_lang=DEFAULT_LANG,
    )


@app.route("/<lang>/privacy")
def privacy(lang: str):
    lang = get_lang(lang)
    t = build_strings(lang)
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        t=t,
        languages=get_languages(),
        base_url=base_url(),
        page_title=t["page_privacy_title"],
        page_body=t["page_privacy_body"],
        page_slug="privacy",
        default_lang=DEFAULT_LANG,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
