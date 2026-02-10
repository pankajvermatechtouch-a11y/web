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
from flask import Flask, Response, abort, redirect, render_template, request, stream_with_context, url_for

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

BASE_TRANSLATIONS: Dict[str, str] = {
    "label": "English",
    "dir": "ltr",
    "title": "Instagram Media Downloader",
    "meta_description": "Download Instagram videos, reels, and photos from public posts. Paste a link and get clean previews with direct downloads.",
    "meta_keywords": "instagram downloader, instagram video downloader, instagram reels downloader, instagram photo downloader, download instagram",
    "brand": "Media Vault",
    "status": "Public posts only",
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
    "error_not_reel": "This link is not a reel.",
    "error_no_media": "No media found for that selection.",
    "modal_private_title": "Private Account",
    "modal_private_body": "This Instagram account is private. Media cannot be downloaded.",
    "modal_mismatch_title": "Wrong Media Type",
    "modal_mismatch_video": "This link is an image. Please select the Photo tab.",
    "modal_mismatch_photo": "This link is a video. Please select the Video or Reels tab.",
    "seo_title": "Fast Instagram Media Downloader for Public Posts",
    "seo_p1": "Use this Instagram downloader to save public videos, reels, and photos directly from post links. It is simple, fast, and works without login.",
    "seo_p2": "Paste a link, preview the media, and download each item individually. Carousels show every photo or video with its own download button.",
    "seo_list_title": "Features",
    "seo_list_1": "Supports public Instagram posts, reels, and photos",
    "seo_list_2": "Clean previews and one-click downloads",
    "seo_list_3": "Handles carousels with multiple items",
    "seo_list_4": "Privacy-aware: private accounts show a warning",
    "footer_contact": "Contact Us",
    "footer_about": "About Us",
    "footer_privacy": "Privacy Policy",
    "footer_disclaimer": "This website is intended for educational and personal use only. All videos, photos, and media remain the property of their respective owners. We do not claim any rights over the content downloaded through this tool. All copyrights and trademarks belong to their rightful owners. Instagram and the Instagram logo are trademarks of Meta Platforms, Inc.",
    "footer_copy": "Copyright © 2026 Media Vault. All rights reserved.",
    "page_about_title": "About Us",
    "page_about_body": "Media Vault provides a simple way to preview and download public Instagram media for personal use. We focus on speed, clarity, and responsible use.",
    "page_contact_title": "Contact Us",
    "page_contact_body": "For support or inquiries, please email: support@example.com",
    "page_privacy_title": "Privacy Policy",
    "page_privacy_body": "We do not store the media you download. Requests are processed in real time and no user data is sold or shared.",
}

LANG_OVERRIDES: Dict[str, Dict[str, str]] = {
    "en": {},
    "ar": {
        "label": "العربية",
        "dir": "rtl",
        "title": "أداة تنزيل محتوى إنستغرام",
        "meta_description": "حمّل فيديوهات وريـلز وصور إنستغرام من المنشورات العامة. الصق الرابط وشاهد المعاينة ثم نزّل.",
        "status": "منشورات عامة فقط",
        "tab_video": "فيديو",
        "tab_reels": "ريلز",
        "tab_photo": "صور",
        "kicker": "حمّل كل محتوى إنستغرام هنا",
        "headline_video": "تحميل فيديو إنستغرام",
        "headline_reels": "تحميل ريلز إنستغرام",
        "headline_photo": "تحميل صور إنستغرام",
        "sub": "الصق رابط منشور عام أو ريلز. الحسابات الخاصة ستظهر تنبيهاً.",
        "placeholder": "الصق رابط منشور أو ريلز إنستغرام",
        "paste": "لصق",
        "clear": "مسح",
        "search": "بحث",
        "results": "النتائج",
        "download": "تنزيل",
        "error_invalid_link": "يرجى لصق رابط إنستغرام صالح.",
        "error_not_reel": "هذا الرابط ليس ريلز.",
        "error_no_media": "لم يتم العثور على وسائط لهذا الاختيار.",
        "modal_private_title": "حساب خاص",
        "modal_private_body": "هذا الحساب خاص ولا يمكن تنزيل المحتوى.",
        "modal_mismatch_title": "نوع غير صحيح",
        "modal_mismatch_video": "هذا الرابط لصورة. الرجاء اختيار تبويب الصور.",
        "modal_mismatch_photo": "هذا الرابط لفيديو. الرجاء اختيار تبويب الفيديو أو الريلز.",
        "footer_contact": "اتصل بنا",
        "footer_about": "من نحن",
        "footer_privacy": "سياسة الخصوصية",
        "page_about_title": "من نحن",
        "page_about_body": "Media Vault يوفر طريقة بسيطة لمعاينة وتنزيل محتوى إنستغرام العام للاستخدام الشخصي.",
        "page_contact_title": "اتصل بنا",
        "page_contact_body": "للدعم أو الاستفسارات: support@example.com",
        "page_privacy_title": "سياسة الخصوصية",
        "page_privacy_body": "لا نقوم بتخزين الوسائط التي يتم تنزيلها. تتم معالجة الطلبات في الوقت الحقيقي.",
    },
    "bn": {
        "label": "বাংলা",
        "title": "ইনস্টাগ্রাম মিডিয়া ডাউনলোডার",
        "meta_description": "পাবলিক পোস্ট থেকে ইনস্টাগ্রাম ভিডিও, রিল এবং ছবি ডাউনলোড করুন। লিংক পেস্ট করে প্রিভিউ ও ডাউনলোড করুন।",
        "status": "শুধু পাবলিক পোস্ট",
        "tab_video": "ভিডিও",
        "tab_reels": "রিলস",
        "tab_photo": "ফটো",
        "kicker": "সব ইনস্টাগ্রাম কন্টেন্ট এখানে ডাউনলোড করুন",
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
        "error_invalid_link": "দয়া করে একটি বৈধ ইনস্টাগ্রাম লিংক পেস্ট করুন।",
        "error_not_reel": "এই লিংকটি রিল নয়।",
        "error_no_media": "এই নির্বাচনের জন্য কোনো মিডিয়া পাওয়া যায়নি।",
        "modal_private_title": "প্রাইভেট অ্যাকাউন্ট",
        "modal_private_body": "এই ইনস্টাগ্রাম অ্যাকাউন্টটি প্রাইভেট। মিডিয়া ডাউনলোড করা যাবে না।",
        "modal_mismatch_title": "ভুল মিডিয়া টাইপ",
        "modal_mismatch_video": "এই লিংকটি ছবি। অনুগ্রহ করে ফটো ট্যাব নির্বাচন করুন।",
        "modal_mismatch_photo": "এই লিংকটি ভিডিও। ভিডিও বা রিলস ট্যাব নির্বাচন করুন।",
        "footer_contact": "যোগাযোগ",
        "footer_about": "আমাদের সম্পর্কে",
        "footer_privacy": "প্রাইভেসি পলিসি",
        "page_about_title": "আমাদের সম্পর্কে",
        "page_about_body": "Media Vault পাবলিক ইনস্টাগ্রাম মিডিয়া প্রিভিউ ও ডাউনলোডের সহজ উপায় দেয়।",
        "page_contact_title": "যোগাযোগ",
        "page_contact_body": "সাপোর্ট: support@example.com",
        "page_privacy_title": "প্রাইভেসি পলিসি",
        "page_privacy_body": "আমরা কোনো মিডিয়া সংরক্ষণ করি না। অনুরোধ রিয়েল-টাইমে প্রসেস হয়।",
    },
    "zh": {
        "label": "中文",
        "title": "Instagram 媒体下载器",
        "meta_description": "从公开帖子下载 Instagram 视频、Reels 和照片。粘贴链接即可预览并下载。",
        "status": "仅限公开帖子",
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
        "error_invalid_link": "请粘贴有效的 Instagram 链接。",
        "error_not_reel": "该链接不是 Reels。",
        "error_no_media": "未找到可用媒体。",
        "modal_private_title": "私密账号",
        "modal_private_body": "该账号为私密账号，无法下载媒体。",
        "modal_mismatch_title": "类型不匹配",
        "modal_mismatch_video": "该链接是图片，请选择照片标签。",
        "modal_mismatch_photo": "该链接是视频，请选择视频或 Reels 标签。",
        "footer_contact": "联系我们",
        "footer_about": "关于我们",
        "footer_privacy": "隐私政策",
        "page_about_title": "关于我们",
        "page_about_body": "Media Vault 提供简单的公开 Instagram 媒体预览与下载方式。",
        "page_contact_title": "联系我们",
        "page_contact_body": "支持邮箱：support@example.com",
        "page_privacy_title": "隐私政策",
        "page_privacy_body": "我们不存储下载的媒体。请求实时处理。",
    },
    "fr": {
        "label": "Français",
        "title": "Téléchargeur Instagram",
        "meta_description": "Téléchargez des vidéos, Reels et photos Instagram depuis des posts publics. Collez le lien pour télécharger.",
        "status": "Posts publics uniquement",
        "tab_video": "Vidéo",
        "tab_reels": "Reels",
        "tab_photo": "Photo",
        "kicker": "Téléchargez du contenu Instagram ici",
        "headline_video": "Téléchargeur Vidéo Instagram",
        "headline_reels": "Téléchargeur Reels Instagram",
        "headline_photo": "Téléchargeur Photo Instagram",
        "sub": "Collez un lien de post public ou de Reel.",
        "placeholder": "Collez le lien Instagram",
        "paste": "Coller",
        "clear": "Effacer",
        "search": "Rechercher",
        "results": "Résultats",
        "download": "Télécharger",
        "error_invalid_link": "Veuillez coller un lien Instagram valide.",
        "error_not_reel": "Ce lien n’est pas un Reel.",
        "error_no_media": "Aucun média trouvé pour cette sélection.",
        "modal_private_title": "Compte privé",
        "modal_private_body": "Ce compte Instagram est privé. Téléchargement impossible.",
        "modal_mismatch_title": "Mauvais type",
        "modal_mismatch_video": "Ce lien est une image. Choisissez l’onglet Photo.",
        "modal_mismatch_photo": "Ce lien est une vidéo. Choisissez Vidéo ou Reels.",
        "footer_contact": "Contact",
        "footer_about": "À propos",
        "footer_privacy": "Confidentialité",
        "page_about_title": "À propos",
        "page_about_body": "Media Vault permet de prévisualiser et télécharger du contenu public Instagram.",
        "page_contact_title": "Contact",
        "page_contact_body": "Support : support@example.com",
        "page_privacy_title": "Confidentialité",
        "page_privacy_body": "Nous ne stockons pas les médias téléchargés.",
    },
    "de": {
        "label": "Deutsch",
        "title": "Instagram Medien-Downloader",
        "meta_description": "Lade Instagram-Videos, Reels und Fotos aus öffentlichen Beiträgen herunter. Link einfügen und herunterladen.",
        "status": "Nur öffentliche Beiträge",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Instagram-Inhalte hier herunterladen",
        "headline_video": "Instagram Video Downloader",
        "headline_reels": "Instagram Reels Downloader",
        "headline_photo": "Instagram Foto Downloader",
        "sub": "Füge einen öffentlichen Post- oder Reel-Link ein.",
        "placeholder": "Instagram-Link einfügen",
        "paste": "Einfügen",
        "clear": "Löschen",
        "search": "Suchen",
        "results": "Ergebnisse",
        "download": "Download",
        "error_invalid_link": "Bitte einen gültigen Instagram-Link einfügen.",
        "error_not_reel": "Dieser Link ist kein Reel.",
        "error_no_media": "Keine Medien für diese Auswahl gefunden.",
        "modal_private_title": "Privates Konto",
        "modal_private_body": "Dieses Konto ist privat. Medien können nicht heruntergeladen werden.",
        "modal_mismatch_title": "Falscher Typ",
        "modal_mismatch_video": "Dieser Link ist ein Bild. Foto-Tab wählen.",
        "modal_mismatch_photo": "Dieser Link ist ein Video. Video oder Reels wählen.",
        "footer_contact": "Kontakt",
        "footer_about": "Über uns",
        "footer_privacy": "Datenschutz",
        "page_about_title": "Über uns",
        "page_about_body": "Media Vault hilft beim Anzeigen und Herunterladen öffentlicher Instagram-Medien.",
        "page_contact_title": "Kontakt",
        "page_contact_body": "Support: support@example.com",
        "page_privacy_title": "Datenschutz",
        "page_privacy_body": "Wir speichern keine heruntergeladenen Medien.",
    },
    "hi": {
        "label": "हिन्दी",
        "title": "इंस्टाग्राम मीडिया डाउनलोडर",
        "meta_description": "पब्लिक पोस्ट से इंस्टाग्राम वीडियो, रील्स और फोटो डाउनलोड करें। लिंक पेस्ट करें और डाउनलोड करें।",
        "status": "केवल सार्वजनिक पोस्ट",
        "tab_video": "वीडियो",
        "tab_reels": "रील्स",
        "tab_photo": "फ़ोटो",
        "kicker": "यहाँ इंस्टाग्राम कंटेंट डाउनलोड करें",
        "headline_video": "इंस्टाग्राम वीडियो डाउनलोडर",
        "headline_reels": "इंस्टाग्राम रील्स डाउनलोडर",
        "headline_photo": "इंस्टाग्राम फ़ोटो डाउनलोडर",
        "sub": "पब्लिक पोस्ट या रील का लिंक पेस्ट करें।",
        "placeholder": "इंस्टाग्राम लिंक पेस्ट करें",
        "paste": "पेस्ट",
        "clear": "हटाएँ",
        "search": "खोजें",
        "results": "परिणाम",
        "download": "डाउनलोड",
        "error_invalid_link": "कृपया वैध इंस्टाग्राम लिंक पेस्ट करें।",
        "error_not_reel": "यह लिंक रील नहीं है।",
        "error_no_media": "इस चयन के लिए कोई मीडिया नहीं मिला।",
        "modal_private_title": "प्राइवेट अकाउंट",
        "modal_private_body": "यह अकाउंट प्राइवेट है। मीडिया डाउनलोड नहीं किया जा सकता।",
        "modal_mismatch_title": "गलत मीडिया प्रकार",
        "modal_mismatch_video": "यह लिंक इमेज है। कृपया फ़ोटो टैब चुनें।",
        "modal_mismatch_photo": "यह लिंक वीडियो है। वीडियो या रील्स टैब चुनें।",
        "footer_contact": "संपर्क करें",
        "footer_about": "हमारे बारे में",
        "footer_privacy": "गोपनीयता नीति",
        "page_about_title": "हमारे बारे में",
        "page_about_body": "Media Vault पब्लिक इंस्टाग्राम मीडिया देखने और डाउनलोड करने का आसान तरीका देता है।",
        "page_contact_title": "संपर्क करें",
        "page_contact_body": "सपोर्ट: support@example.com",
        "page_privacy_title": "गोपनीयता नीति",
        "page_privacy_body": "हम डाउनलोड की गई मीडिया स्टोर नहीं करते।",
    },
    "hu": {
        "label": "Magyar",
        "title": "Instagram letöltő",
        "meta_description": "Tölts le Instagram videókat, Reels-eket és fotókat nyilvános posztokból. Illeszd be a linket és töltsd le.",
        "status": "Csak nyilvános posztok",
        "tab_video": "Videó",
        "tab_reels": "Reels",
        "tab_photo": "Fotó",
        "kicker": "Instagram tartalmak letöltése itt",
        "headline_video": "Instagram videó letöltő",
        "headline_reels": "Instagram Reels letöltő",
        "headline_photo": "Instagram fotó letöltő",
        "sub": "Illessz be egy nyilvános poszt vagy Reels linket.",
        "placeholder": "Illeszd be az Instagram linket",
        "paste": "Beillesztés",
        "clear": "Törlés",
        "search": "Keresés",
        "results": "Eredmények",
        "download": "Letöltés",
        "error_invalid_link": "Kérjük, illessz be egy érvényes Instagram linket.",
        "error_not_reel": "Ez a link nem Reels.",
        "error_no_media": "Nincs média ehhez a választáshoz.",
        "modal_private_title": "Privát fiók",
        "modal_private_body": "Ez a fiók privát. A média nem tölthető le.",
        "modal_mismatch_title": "Rossz típus",
        "modal_mismatch_video": "Ez a link kép. Válaszd a Fotó fület.",
        "modal_mismatch_photo": "Ez a link videó. Válaszd a Videó vagy Reels fület.",
        "footer_contact": "Kapcsolat",
        "footer_about": "Rólunk",
        "footer_privacy": "Adatvédelem",
        "page_about_title": "Rólunk",
        "page_about_body": "A Media Vault segít a nyilvános Instagram médiák megtekintésében és letöltésében.",
        "page_contact_title": "Kapcsolat",
        "page_contact_body": "Támogatás: support@example.com",
        "page_privacy_title": "Adatvédelem",
        "page_privacy_body": "Nem tároljuk a letöltött médiát.",
    },
    "id": {
        "label": "Bahasa Indonesia",
        "title": "Pengunduh Media Instagram",
        "meta_description": "Unduh video, Reels, dan foto Instagram dari posting publik. Tempel tautan lalu unduh.",
        "status": "Hanya posting publik",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Unduh konten Instagram di sini",
        "headline_video": "Pengunduh Video Instagram",
        "headline_reels": "Pengunduh Reels Instagram",
        "headline_photo": "Pengunduh Foto Instagram",
        "sub": "Tempel tautan posting atau Reels publik.",
        "placeholder": "Tempel tautan Instagram",
        "paste": "Tempel",
        "clear": "Hapus",
        "search": "Cari",
        "results": "Hasil",
        "download": "Unduh",
        "error_invalid_link": "Tempel tautan Instagram yang valid.",
        "error_not_reel": "Tautan ini bukan Reels.",
        "error_no_media": "Tidak ada media untuk pilihan ini.",
        "modal_private_title": "Akun Privat",
        "modal_private_body": "Akun ini privat. Media tidak dapat diunduh.",
        "modal_mismatch_title": "Tipe salah",
        "modal_mismatch_video": "Tautan ini adalah gambar. Pilih tab Foto.",
        "modal_mismatch_photo": "Tautan ini adalah video. Pilih tab Video atau Reels.",
        "footer_contact": "Kontak",
        "footer_about": "Tentang",
        "footer_privacy": "Kebijakan Privasi",
        "page_about_title": "Tentang",
        "page_about_body": "Media Vault membantu pratinjau dan unduh media Instagram publik.",
        "page_contact_title": "Kontak",
        "page_contact_body": "Dukungan: support@example.com",
        "page_privacy_title": "Kebijakan Privasi",
        "page_privacy_body": "Kami tidak menyimpan media yang diunduh.",
    },
    "it": {
        "label": "Italiano",
        "title": "Downloader Instagram",
        "meta_description": "Scarica video, Reels e foto Instagram da post pubblici. Incolla il link e scarica.",
        "status": "Solo post pubblici",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Scarica contenuti Instagram qui",
        "headline_video": "Downloader Video Instagram",
        "headline_reels": "Downloader Reels Instagram",
        "headline_photo": "Downloader Foto Instagram",
        "sub": "Incolla il link di un post o Reel pubblico.",
        "placeholder": "Incolla il link Instagram",
        "paste": "Incolla",
        "clear": "Cancella",
        "search": "Cerca",
        "results": "Risultati",
        "download": "Scarica",
        "error_invalid_link": "Incolla un link Instagram valido.",
        "error_not_reel": "Questo link non è un Reel.",
        "error_no_media": "Nessun media trovato per questa selezione.",
        "modal_private_title": "Account privato",
        "modal_private_body": "Questo account è privato. Non è possibile scaricare i media.",
        "modal_mismatch_title": "Tipo errato",
        "modal_mismatch_video": "Questo link è un'immagine. Seleziona Foto.",
        "modal_mismatch_photo": "Questo link è un video. Seleziona Video o Reels.",
        "footer_contact": "Contatti",
        "footer_about": "Chi siamo",
        "footer_privacy": "Privacy",
        "page_about_title": "Chi siamo",
        "page_about_body": "Media Vault aiuta a visualizzare e scaricare media Instagram pubblici.",
        "page_contact_title": "Contatti",
        "page_contact_body": "Supporto: support@example.com",
        "page_privacy_title": "Privacy",
        "page_privacy_body": "Non memorizziamo i media scaricati.",
    },
    "ja": {
        "label": "日本語",
        "title": "Instagram メディアダウンローダー",
        "meta_description": "公開投稿から Instagram の動画、Reels、写真をダウンロード。リンクを貼り付けて取得。",
        "status": "公開投稿のみ",
        "tab_video": "動画",
        "tab_reels": "リール",
        "tab_photo": "写真",
        "kicker": "Instagram コンテンツをここでダウンロード",
        "headline_video": "Instagram 動画ダウンローダー",
        "headline_reels": "Instagram リールダウンローダー",
        "headline_photo": "Instagram 写真ダウンローダー",
        "sub": "公開投稿またはリールのリンクを貼り付けてください。",
        "placeholder": "Instagram のリンクを貼り付け",
        "paste": "貼り付け",
        "clear": "クリア",
        "search": "検索",
        "results": "結果",
        "download": "ダウンロード",
        "error_invalid_link": "有効な Instagram リンクを貼り付けてください。",
        "error_not_reel": "このリンクはリールではありません。",
        "error_no_media": "選択したメディアが見つかりません。",
        "modal_private_title": "非公開アカウント",
        "modal_private_body": "このアカウントは非公開です。ダウンロードできません。",
        "modal_mismatch_title": "種類が違います",
        "modal_mismatch_video": "このリンクは画像です。写真タブを選択してください。",
        "modal_mismatch_photo": "このリンクは動画です。動画またはリールタブを選択してください。",
        "footer_contact": "お問い合わせ",
        "footer_about": "私たちについて",
        "footer_privacy": "プライバシーポリシー",
        "page_about_title": "私たちについて",
        "page_about_body": "Media Vault は公開 Instagram メディアのプレビューとダウンロードを提供します。",
        "page_contact_title": "お問い合わせ",
        "page_contact_body": "サポート: support@example.com",
        "page_privacy_title": "プライバシーポリシー",
        "page_privacy_body": "ダウンロードしたメディアは保存しません。",
    },
    "ko": {
        "label": "한국어",
        "title": "인스타그램 미디어 다운로더",
        "meta_description": "공개 게시물에서 Instagram 동영상, Reels, 사진을 다운로드하세요. 링크를 붙여넣고 다운로드.",
        "status": "공개 게시물만",
        "tab_video": "동영상",
        "tab_reels": "릴스",
        "tab_photo": "사진",
        "kicker": "인스타그램 콘텐츠를 여기서 다운로드",
        "headline_video": "인스타그램 동영상 다운로더",
        "headline_reels": "인스타그램 릴스 다운로더",
        "headline_photo": "인스타그램 사진 다운로더",
        "sub": "공개 게시물 또는 릴스 링크를 붙여넣으세요.",
        "placeholder": "인스타그램 링크 붙여넣기",
        "paste": "붙여넣기",
        "clear": "지우기",
        "search": "검색",
        "results": "결과",
        "download": "다운로드",
        "error_invalid_link": "유효한 인스타그램 링크를 붙여넣으세요.",
        "error_not_reel": "이 링크는 릴스가 아닙니다.",
        "error_no_media": "선택한 미디어를 찾을 수 없습니다.",
        "modal_private_title": "비공개 계정",
        "modal_private_body": "이 계정은 비공개입니다. 다운로드할 수 없습니다.",
        "modal_mismatch_title": "유형 불일치",
        "modal_mismatch_video": "이 링크는 이미지입니다. 사진 탭을 선택하세요.",
        "modal_mismatch_photo": "이 링크는 동영상입니다. 동영상 또는 릴스 탭을 선택하세요.",
        "footer_contact": "문의하기",
        "footer_about": "소개",
        "footer_privacy": "개인정보 처리방침",
        "page_about_title": "소개",
        "page_about_body": "Media Vault는 공개 Instagram 미디어 미리보기와 다운로드를 제공합니다.",
        "page_contact_title": "문의하기",
        "page_contact_body": "지원: support@example.com",
        "page_privacy_title": "개인정보 처리방침",
        "page_privacy_body": "다운로드한 미디어를 저장하지 않습니다.",
    },
    "pl": {
        "label": "Polski",
        "title": "Pobieracz Instagrama",
        "meta_description": "Pobieraj filmy, Reels i zdjęcia z publicznych postów Instagram. Wklej link i pobierz.",
        "status": "Tylko publiczne posty",
        "tab_video": "Wideo",
        "tab_reels": "Reels",
        "tab_photo": "Zdjęcie",
        "kicker": "Pobieraj treści z Instagrama tutaj",
        "headline_video": "Pobieracz wideo z Instagrama",
        "headline_reels": "Pobieracz Reels z Instagrama",
        "headline_photo": "Pobieracz zdjęć z Instagrama",
        "sub": "Wklej link do publicznego posta lub Reels.",
        "placeholder": "Wklej link z Instagrama",
        "paste": "Wklej",
        "clear": "Wyczyść",
        "search": "Szukaj",
        "results": "Wyniki",
        "download": "Pobierz",
        "error_invalid_link": "Wklej prawidłowy link Instagram.",
        "error_not_reel": "To nie jest Reels.",
        "error_no_media": "Nie znaleziono mediów dla tego wyboru.",
        "modal_private_title": "Prywatne konto",
        "modal_private_body": "To konto jest prywatne. Nie można pobrać mediów.",
        "modal_mismatch_title": "Nieprawidłowy typ",
        "modal_mismatch_video": "To jest obraz. Wybierz Zdjęcie.",
        "modal_mismatch_photo": "To jest wideo. Wybierz Wideo lub Reels.",
        "footer_contact": "Kontakt",
        "footer_about": "O nas",
        "footer_privacy": "Polityka prywatności",
        "page_about_title": "O nas",
        "page_about_body": "Media Vault ułatwia podgląd i pobieranie publicznych mediów z Instagrama.",
        "page_contact_title": "Kontakt",
        "page_contact_body": "Wsparcie: support@example.com",
        "page_privacy_title": "Polityka prywatności",
        "page_privacy_body": "Nie przechowujemy pobranych mediów.",
    },
    "pt": {
        "label": "Português",
        "title": "Baixador de Instagram",
        "meta_description": "Baixe vídeos, Reels e fotos do Instagram de posts públicos. Cole o link e faça o download.",
        "status": "Apenas posts públicos",
        "tab_video": "Vídeo",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Baixe conteúdos do Instagram aqui",
        "headline_video": "Baixador de Vídeos do Instagram",
        "headline_reels": "Baixador de Reels do Instagram",
        "headline_photo": "Baixador de Fotos do Instagram",
        "sub": "Cole o link de um post ou Reel público.",
        "placeholder": "Cole o link do Instagram",
        "paste": "Colar",
        "clear": "Limpar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Baixar",
        "error_invalid_link": "Cole um link válido do Instagram.",
        "error_not_reel": "Este link não é um Reel.",
        "error_no_media": "Nenhuma mídia encontrada para esta seleção.",
        "modal_private_title": "Conta privada",
        "modal_private_body": "Esta conta é privada. Não é possível baixar mídia.",
        "modal_mismatch_title": "Tipo incorreto",
        "modal_mismatch_video": "Este link é uma imagem. Selecione Foto.",
        "modal_mismatch_photo": "Este link é um vídeo. Selecione Vídeo ou Reels.",
        "footer_contact": "Contato",
        "footer_about": "Sobre nós",
        "footer_privacy": "Política de Privacidade",
        "page_about_title": "Sobre nós",
        "page_about_body": "Media Vault ajuda a visualizar e baixar mídia pública do Instagram.",
        "page_contact_title": "Contato",
        "page_contact_body": "Suporte: support@example.com",
        "page_privacy_title": "Política de Privacidade",
        "page_privacy_body": "Não armazenamos a mídia baixada.",
    },
    "ru": {
        "label": "Русский",
        "title": "Загрузчик Instagram",
        "meta_description": "Скачивайте видео, Reels и фото из публичных постов Instagram. Вставьте ссылку и скачайте.",
        "status": "Только публичные посты",
        "tab_video": "Видео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Скачивайте контент Instagram здесь",
        "headline_video": "Загрузчик видео Instagram",
        "headline_reels": "Загрузчик Reels Instagram",
        "headline_photo": "Загрузчик фото Instagram",
        "sub": "Вставьте ссылку на публичный пост или Reels.",
        "placeholder": "Вставьте ссылку Instagram",
        "paste": "Вставить",
        "clear": "Очистить",
        "search": "Поиск",
        "results": "Результаты",
        "download": "Скачать",
        "error_invalid_link": "Вставьте корректную ссылку Instagram.",
        "error_not_reel": "Эта ссылка не является Reels.",
        "error_no_media": "Медиа для выбора не найдено.",
        "modal_private_title": "Закрытый аккаунт",
        "modal_private_body": "Этот аккаунт закрыт. Нельзя скачать медиа.",
        "modal_mismatch_title": "Неверный тип",
        "modal_mismatch_video": "Ссылка ведет на изображение. Выберите Фото.",
        "modal_mismatch_photo": "Ссылка ведет на видео. Выберите Видео или Reels.",
        "footer_contact": "Контакты",
        "footer_about": "О нас",
        "footer_privacy": "Политика конфиденциальности",
        "page_about_title": "О нас",
        "page_about_body": "Media Vault помогает просматривать и скачивать публичные медиа Instagram.",
        "page_contact_title": "Контакты",
        "page_contact_body": "Поддержка: support@example.com",
        "page_privacy_title": "Политика конфиденциальности",
        "page_privacy_body": "Мы не храним скачанные медиа.",
    },
    "es": {
        "label": "Español",
        "title": "Descargador de Instagram",
        "meta_description": "Descarga videos, reels y fotos de Instagram desde publicaciones públicas. Pega el enlace y descarga.",
        "status": "Solo publicaciones públicas",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Descarga contenido de Instagram aquí",
        "headline_video": "Descargador de Videos de Instagram",
        "headline_reels": "Descargador de Reels de Instagram",
        "headline_photo": "Descargador de Fotos de Instagram",
        "sub": "Pega el enlace de un post o reel público.",
        "placeholder": "Pega el enlace de Instagram",
        "paste": "Pegar",
        "clear": "Borrar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Descargar",
        "error_invalid_link": "Pega un enlace válido de Instagram.",
        "error_not_reel": "Este enlace no es un reel.",
        "error_no_media": "No se encontró contenido para esa opción.",
        "modal_private_title": "Cuenta privada",
        "modal_private_body": "Esta cuenta es privada. No se puede descargar contenido.",
        "modal_mismatch_title": "Tipo incorrecto",
        "modal_mismatch_video": "Este enlace es una imagen. Selecciona Foto.",
        "modal_mismatch_photo": "Este enlace es un video. Selecciona Video o Reels.",
        "footer_contact": "Contacto",
        "footer_about": "Acerca de",
        "footer_privacy": "Privacidad",
        "page_about_title": "Acerca de",
        "page_about_body": "Media Vault ayuda a previsualizar y descargar contenido público de Instagram.",
        "page_contact_title": "Contacto",
        "page_contact_body": "Soporte: support@example.com",
        "page_privacy_title": "Privacidad",
        "page_privacy_body": "No almacenamos el contenido descargado.",
    },
    "sw": {
        "label": "Kiswahili",
        "title": "Kipakua Media za Instagram",
        "meta_description": "Pakua video, Reels na picha za Instagram kutoka machapisho ya umma. Bandika kiungo kisha pakua.",
        "status": "Machapisho ya umma tu",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Picha",
        "kicker": "Pakua maudhui ya Instagram hapa",
        "headline_video": "Kipakua Video za Instagram",
        "headline_reels": "Kipakua Reels za Instagram",
        "headline_photo": "Kipakua Picha za Instagram",
        "sub": "Bandika kiungo cha chapisho au Reel ya umma.",
        "placeholder": "Bandika kiungo cha Instagram",
        "paste": "Bandika",
        "clear": "Futa",
        "search": "Tafuta",
        "results": "Matokeo",
        "download": "Pakua",
        "error_invalid_link": "Tafadhali bandika kiungo halali cha Instagram.",
        "error_not_reel": "Kiungo hiki si Reel.",
        "error_no_media": "Hakuna media kwa chaguo hili.",
        "modal_private_title": "Akaunti ya Faragha",
        "modal_private_body": "Akaunti hii ni ya faragha. Media haiwezi kupakuliwa.",
        "modal_mismatch_title": "Aina Isiyolingana",
        "modal_mismatch_video": "Kiungo hiki ni picha. Chagua kichupo cha Picha.",
        "modal_mismatch_photo": "Kiungo hiki ni video. Chagua Video au Reels.",
        "footer_contact": "Wasiliana",
        "footer_about": "Kuhusu",
        "footer_privacy": "Sera ya Faragha",
        "page_about_title": "Kuhusu",
        "page_about_body": "Media Vault husaidia kutazama na kupakua media za umma za Instagram.",
        "page_contact_title": "Wasiliana",
        "page_contact_body": "Msaada: support@example.com",
        "page_privacy_title": "Sera ya Faragha",
        "page_privacy_body": "Hatuifadhi media zilizopakuliwa.",
    },
    "te": {
        "label": "తెలుగు",
        "title": "ఇన్‌స్టాగ్రామ్ మీడియా డౌన్‌లోడర్",
        "meta_description": "పబ్లిక్ పోస్టుల నుండి ఇన్‌స్టాగ్రామ్ వీడియోలు, రీల్స్, ఫోటోలు డౌన్‌లోడ్ చేయండి. లింక్ పేస్ట్ చేసి డౌన్‌లోడ్ చేయండి.",
        "status": "పబ్లిక్ పోస్టులు మాత్రమే",
        "tab_video": "వీడియో",
        "tab_reels": "రీల్స్",
        "tab_photo": "ఫోటో",
        "kicker": "ఇన్‌స్టాగ్రామ్ కంటెంట్ ఇక్కడ డౌన్‌లోడ్ చేయండి",
        "headline_video": "ఇన్‌స్టాగ్రామ్ వీడియో డౌన్‌లోడర్",
        "headline_reels": "ఇన్‌స్టాగ్రామ్ రీల్స్ డౌన్‌లోడర్",
        "headline_photo": "ఇన్‌స్టాగ్రామ్ ఫోటో డౌన్‌లోడర్",
        "sub": "పబ్లిక్ పోస్ట్ లేదా రీల్ లింక్‌ను పేస్ట్ చేయండి.",
        "placeholder": "ఇన్‌స్టాగ్రామ్ లింక్‌ను పేస్ట్ చేయండి",
        "paste": "పేస్ట్",
        "clear": "తొలగించండి",
        "search": "శోధించండి",
        "results": "ఫలితాలు",
        "download": "డౌన్‌లోడ్",
        "error_invalid_link": "దయచేసి సరైన ఇన్‌స్టాగ్రామ్ లింక్‌ను పేస్ట్ చేయండి.",
        "error_not_reel": "ఈ లింక్ రీల్ కాదు.",
        "error_no_media": "ఈ ఎంపికకు మీడియా కనిపించలేదు.",
        "modal_private_title": "ప్రైవేట్ ఖాతా",
        "modal_private_body": "ఈ ఖాతా ప్రైవేట్. మీడియా డౌన్‌లోడ్ చేయలేరు.",
        "modal_mismatch_title": "తప్పుడు మీడియా రకం",
        "modal_mismatch_video": "ఈ లింక్ చిత్రం. ఫోటో ట్యాబ్‌ను ఎంచుకోండి.",
        "modal_mismatch_photo": "ఈ లింక్ వీడియో. వీడియో లేదా రీల్స్ ట్యాబ్‌ను ఎంచుకోండి.",
        "footer_contact": "సంప్రదించండి",
        "footer_about": "మా గురించి",
        "footer_privacy": "గోప్యతా విధానం",
        "page_about_title": "మా గురించి",
        "page_about_body": "Media Vault పబ్లిక్ ఇన్‌స్టాగ్రామ్ మీడియాను చూడటానికి మరియు డౌన్‌లోడ్ చేయటానికి సహాయపడుతుంది.",
        "page_contact_title": "సంప్రదించండి",
        "page_contact_body": "సపోర్ట్: support@example.com",
        "page_privacy_title": "గోప్యతా విధానం",
        "page_privacy_body": "మేము డౌన్‌లోడ్ చేసిన మీడియాను నిల్వ చేయము.",
    },
    "th": {
        "label": "ไทย",
        "title": "ตัวดาวน์โหลดสื่อ Instagram",
        "meta_description": "ดาวน์โหลดวิดีโอ Reels และรูปภาพจากโพสต์สาธารณะของ Instagram เพียงวางลิงก์แล้วดาวน์โหลด",
        "status": "เฉพาะโพสต์สาธารณะ",
        "tab_video": "วิดีโอ",
        "tab_reels": "รีลส์",
        "tab_photo": "รูปภาพ",
        "kicker": "ดาวน์โหลดคอนเทนต์ Instagram ได้ที่นี่",
        "headline_video": "ตัวดาวน์โหลดวิดีโอ Instagram",
        "headline_reels": "ตัวดาวน์โหลดรีลส์ Instagram",
        "headline_photo": "ตัวดาวน์โหลดรูปภาพ Instagram",
        "sub": "วางลิงก์โพสต์หรือรีลส์สาธารณะ",
        "placeholder": "วางลิงก์ Instagram",
        "paste": "วาง",
        "clear": "ล้าง",
        "search": "ค้นหา",
        "results": "ผลลัพธ์",
        "download": "ดาวน์โหลด",
        "error_invalid_link": "กรุณาวางลิงก์ Instagram ที่ถูกต้อง",
        "error_not_reel": "ลิงก์นี้ไม่ใช่รีลส์",
        "error_no_media": "ไม่พบสื่อสำหรับตัวเลือกนี้",
        "modal_private_title": "บัญชีส่วนตัว",
        "modal_private_body": "บัญชีนี้เป็นส่วนตัว ไม่สามารถดาวน์โหลดสื่อได้",
        "modal_mismatch_title": "ประเภทไม่ตรงกัน",
        "modal_mismatch_video": "ลิงก์นี้เป็นรูปภาพ โปรดเลือกแท็บรูปภาพ",
        "modal_mismatch_photo": "ลิงก์นี้เป็นวิดีโอ โปรดเลือกแท็บวิดีโอหรือรีลส์",
        "footer_contact": "ติดต่อเรา",
        "footer_about": "เกี่ยวกับเรา",
        "footer_privacy": "นโยบายความเป็นส่วนตัว",
        "page_about_title": "เกี่ยวกับเรา",
        "page_about_body": "Media Vault ช่วยให้คุณดูและดาวน์โหลดสื่อ Instagram สาธารณะได้ง่ายขึ้น",
        "page_contact_title": "ติดต่อเรา",
        "page_contact_body": "ฝ่ายสนับสนุน: support@example.com",
        "page_privacy_title": "นโยบายความเป็นส่วนตัว",
        "page_privacy_body": "เราไม่จัดเก็บสื่อที่ดาวน์โหลด",
    },
    "tr": {
        "label": "Türkçe",
        "title": "Instagram Medya İndirici",
        "meta_description": "Herkese açık Instagram gönderilerinden video, Reels ve fotoğraf indirin. Linki yapıştırın ve indirin.",
        "status": "Yalnızca herkese açık gönderiler",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Fotoğraf",
        "kicker": "Instagram içeriklerini buradan indirin",
        "headline_video": "Instagram Video İndirici",
        "headline_reels": "Instagram Reels İndirici",
        "headline_photo": "Instagram Fotoğraf İndirici",
        "sub": "Herkese açık gönderi veya Reel bağlantısını yapıştırın.",
        "placeholder": "Instagram bağlantısını yapıştırın",
        "paste": "Yapıştır",
        "clear": "Temizle",
        "search": "Ara",
        "results": "Sonuçlar",
        "download": "İndir",
        "error_invalid_link": "Lütfen geçerli bir Instagram bağlantısı yapıştırın.",
        "error_not_reel": "Bu bağlantı bir Reels değil.",
        "error_no_media": "Bu seçim için medya bulunamadı.",
        "modal_private_title": "Gizli Hesap",
        "modal_private_body": "Bu hesap gizli. Medya indirilemez.",
        "modal_mismatch_title": "Yanlış Tür",
        "modal_mismatch_video": "Bu bağlantı bir görsel. Fotoğraf sekmesini seçin.",
        "modal_mismatch_photo": "Bu bağlantı bir video. Video veya Reels sekmesini seçin.",
        "footer_contact": "İletişim",
        "footer_about": "Hakkımızda",
        "footer_privacy": "Gizlilik Politikası",
        "page_about_title": "Hakkımızda",
        "page_about_body": "Media Vault, herkese açık Instagram medyalarını görüntüleme ve indirmeye yardımcı olur.",
        "page_contact_title": "İletişim",
        "page_contact_body": "Destek: support@example.com",
        "page_privacy_title": "Gizlilik Politikası",
        "page_privacy_body": "İndirilen medya saklanmaz.",
    },
    "uk": {
        "label": "Українська",
        "title": "Завантажувач Instagram",
        "meta_description": "Завантажуйте відео, Reels і фото з публічних дописів Instagram. Вставте посилання та завантажте.",
        "status": "Лише публічні дописи",
        "tab_video": "Відео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Завантажуйте контент Instagram тут",
        "headline_video": "Завантажувач відео Instagram",
        "headline_reels": "Завантажувач Reels Instagram",
        "headline_photo": "Завантажувач фото Instagram",
        "sub": "Вставте посилання на публічний допис або Reels.",
        "placeholder": "Вставте посилання Instagram",
        "paste": "Вставити",
        "clear": "Очистити",
        "search": "Пошук",
        "results": "Результати",
        "download": "Завантажити",
        "error_invalid_link": "Вставте дійсне посилання Instagram.",
        "error_not_reel": "Це посилання не є Reels.",
        "error_no_media": "Медіа для цього вибору не знайдено.",
        "modal_private_title": "Приватний акаунт",
        "modal_private_body": "Цей акаунт приватний. Неможливо завантажити медіа.",
        "modal_mismatch_title": "Невірний тип",
        "modal_mismatch_video": "Це зображення. Оберіть вкладку Фото.",
        "modal_mismatch_photo": "Це відео. Оберіть Відео або Reels.",
        "footer_contact": "Контакти",
        "footer_about": "Про нас",
        "footer_privacy": "Політика конфіденційності",
        "page_about_title": "Про нас",
        "page_about_body": "Media Vault допомагає переглядати та завантажувати публічні медіа Instagram.",
        "page_contact_title": "Контакти",
        "page_contact_body": "Підтримка: support@example.com",
        "page_privacy_title": "Політика конфіденційності",
        "page_privacy_body": "Ми не зберігаємо завантажені медіа.",
    },
}

LANG_ORDER = [
    "en", "ar", "bn", "zh", "fr", "de", "hi", "hu", "id", "it", "ja", "ko",
    "pl", "pt", "ru", "es", "sw", "te", "th", "tr", "uk",
]


def translate(lang: str) -> Dict[str, str]:
    base = dict(BASE_TRANSLATIONS)
    override = LANG_OVERRIDES.get(lang, {})
    base.update(override)
    return base


def normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        lang = "en"
    lang = lang.lower()
    if lang not in LANG_OVERRIDES:
        return "en"
    return lang


def safe_segment(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ._@-]+", "_", name).strip()
    return cleaned or "untitled"


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


def render_index(lang: str, **kwargs):
    t = translate(lang)
    base_url = request.url_root.rstrip("/")
    ctx = {
        "lang": lang,
        "t": t,
        "languages": [(code, translate(code)["label"]) for code in LANG_ORDER],
        "base_url": base_url,
        "selected_type": kwargs.get("selected_type"),
        "canonical_url": f"{base_url}/{lang}",
        "alt_suffix": "",
    }
    ctx.update(kwargs)
    return render_template("index.html", **ctx)


def render_page(lang: str, page_title: str, page_body: str, page_slug: str):
    t = translate(lang)
    base_url = request.url_root.rstrip("/")
    return render_template(
        "page.html",
        lang=lang,
        t=t,
        languages=[(code, translate(code)["label"]) for code in LANG_ORDER],
        base_url=base_url,
        page_title=page_title,
        page_body=page_body,
        canonical_url=f"{base_url}/{lang}/{page_slug}",
        page_slug=page_slug,
        alt_suffix=f\"/{page_slug}\",
    )


@app.route("/")
def root():
    return redirect(url_for("index_lang", lang="en"))


@app.route("/<lang>", strict_slashes=False)
def index_lang(lang: str):
    lang = normalize_lang(lang)
    return render_index(lang)


@app.route("/<lang>/about", strict_slashes=False)
def about(lang: str):
    lang = normalize_lang(lang)
    t = translate(lang)
    return render_page(lang, t["page_about_title"], t["page_about_body"], "about")


@app.route("/<lang>/contact", strict_slashes=False)
def contact(lang: str):
    lang = normalize_lang(lang)
    t = translate(lang)
    return render_page(lang, t["page_contact_title"], t["page_contact_body"], "contact")


@app.route("/<lang>/privacy", strict_slashes=False)
def privacy(lang: str):
    lang = normalize_lang(lang)
    t = translate(lang)
    return render_page(lang, t["page_privacy_title"], t["page_privacy_body"], "privacy")


def stream_media(media_url: str, *, as_attachment: bool) -> Response:
    if not media_url or not is_allowed_media_url(media_url):
        return abort(400, "Invalid media URL")

    range_header = request.headers.get("Range")
    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        upstream = requests.get(media_url, stream=True, timeout=20, allow_redirects=False, headers=headers)
        upstream.raise_for_status()
    except requests.RequestException:
        return abort(502, "Failed to fetch media")

    content_type = upstream.headers.get("Content-Type", "application/octet-stream")
    base_name = (request.args.get("name") or "media").strip()
    filename = safe_segment(base_name) + guess_extension(content_type)

    response_headers = {"Content-Type": content_type}
    if as_attachment:
        response_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        response_headers["Content-Disposition"] = "inline"

    for header_name in ("Content-Length", "Content-Range", "Accept-Ranges"):
        if header_name in upstream.headers:
            response_headers[header_name] = upstream.headers[header_name]

    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        headers=response_headers,
        status=upstream.status_code,
    )


@app.route("/download-file", methods=["GET"])
def download_file():
    media_url = (request.args.get("url") or "").strip()
    return stream_media(media_url, as_attachment=True)


@app.route("/media-proxy", methods=["GET"])
def media_proxy():
    media_url = (request.args.get("url") or "").strip()
    return stream_media(media_url, as_attachment=False)


@app.route("/<lang>/download", methods=["POST"], strict_slashes=False)
def download_lang(lang: str):
    lang = normalize_lang(lang)
    t = translate(lang)
    media_url = (request.form.get("media_url") or request.form.get("target_input") or "").strip()
    media_type = (request.form.get("media_type") or "video").strip()

    parsed = parse_media_url(media_url)
    if not parsed:
        return render_index(lang, error=t["error_invalid_link"], selected_type=media_type)

    url_kind, shortcode = parsed

    loader = instaloader.Instaloader(quiet=True)
    loader.context.max_connection_attempts = 3

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        owner = getattr(post, "owner_username", "instagram")
        safe_owner = safe_segment(owner)
        owner_profile = getattr(post, "owner_profile", None)
        if owner_profile and getattr(owner_profile, "is_private", False):
            return render_index(
                lang,
                modal_show=True,
                modal_title=t["modal_private_title"],
                modal_message=t["modal_private_body"],
                selected_type=media_type,
            )

        is_video = getattr(post, "is_video", False)
        is_carousel = getattr(post, "typename", "") == "GraphSidecar"

        if media_type == "reels":
            if not is_video or not (url_kind == "reel" or is_reel(post)):
                return render_index(lang, error=t["error_not_reel"], selected_type=media_type)

        items: List[dict] = []
        has_video = False
        has_image = False

        if is_carousel:
            for idx, node in enumerate(post.get_sidecar_nodes(), start=1):
                node_is_video = getattr(node, "is_video", False)
                has_video = has_video or node_is_video
                has_image = has_image or (not node_is_video)

                if media_type == "photo" and node_is_video:
                    continue
                if media_type in {"video", "reels"} and not node_is_video:
                    continue

                media_link = node.video_url if node_is_video else node.display_url
                if not media_link:
                    continue
                label = "video" if node_is_video else "photo"
                items.append({"type": label, "url": media_link, "name": f"{safe_owner}_{shortcode}_{idx}"})
        else:
            has_video = is_video
            has_image = not is_video
            media_link = post.video_url if is_video else post.url
            if media_link:
                label = "video" if is_video else "photo"
                if media_type == "photo" and label != "photo":
                    items = []
                elif media_type in {"video", "reels"} and label != "video":
                    items = []
                else:
                    items.append({"type": label, "url": media_link, "name": f"{safe_owner}_{shortcode}"})

        if media_type in {"video", "reels"} and not has_video:
            return render_index(
                lang,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=t["modal_mismatch_video"],
                selected_type=media_type,
            )
        if media_type == "photo" and not has_image:
            return render_index(
                lang,
                modal_show=True,
                modal_title=t["modal_mismatch_title"],
                modal_message=t["modal_mismatch_photo"],
                selected_type=media_type,
            )

        if not items:
            return render_index(lang, error=t["error_no_media"], selected_type=media_type)

        return render_index(lang, items=items, selected_type=media_type)

    except LoginException:
        return render_index(
            lang,
            modal_show=True,
            modal_title=t["modal_private_title"],
            modal_message=t["modal_private_body"],
            selected_type=media_type,
        )
    except ConnectionException as exc:
        return render_index(lang, error=f"Connection error: {exc}", selected_type=media_type)
    except Exception as exc:  # pragma: no cover
        return render_index(lang, error=f"Unexpected error: {exc}", selected_type=media_type)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
