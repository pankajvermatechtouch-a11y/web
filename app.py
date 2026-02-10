#!/usr/bin/env python3
"""Instagram media downloader web app.

Use only for your own content or with explicit permission, and comply with
Instagram's Terms of Use and applicable laws.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    stream_with_context,
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

STRINGS: Dict[str, Dict[str, object]] = {
    "en": {
        "title": "Instagram Media Downloader",
        "brand": "Media Vault",
        "status_public": "Public posts only",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Photo",
        "kicker": "Download all Instagram stuff here",
        "headline_video": "Instagram Video Downloader",
        "headline_reels": "Instagram Reels Downloader",
        "headline_photo": "Instagram Photo Downloader",
        "subhead": "Paste a public post or reel link. Private accounts will show a privacy alert.",
        "placeholder": "Paste Instagram post or reel link",
        "paste": "Paste",
        "clear": "Clear",
        "search": "Search",
        "results": "Results",
        "download": "Download",
        "error_invalid_url": "Please paste a valid Instagram post or reel link.",
        "modal_private_title": "Private Account",
        "modal_private_msg": "This Instagram account is private. Media cannot be downloaded.",
        "modal_mismatch_title": "Wrong Media Type",
        "modal_mismatch_image": "This link is an image. Please select the Photo tab.",
        "modal_mismatch_video": "This link is a video. Please select Video or Reels.",
        "modal_mismatch_reel": "This link is not a reel. Please select Video.",
        "seo_heading": "Fast Instagram Media Downloader",
        "seo_paragraphs": [
            "Download Instagram photos, videos, and reels from public posts in seconds. Paste a link, preview the media, and save it in original quality with one click.",
            "This tool is built for creators, marketers, and researchers who need quick access to public media for inspiration, planning, or personal archiving.",
            "Private accounts are not supported and will show a privacy alert. Respect copyright and only download content you own or have permission to use.",
        ],
        "meta_description": "Free Instagram media downloader for public posts. Paste a link to download photos, videos, and reels with previews in original quality.",
        "meta_keywords": "instagram downloader, instagram video downloader, instagram photo downloader, reels downloader, ig downloader, download instagram media",
        "contact": "Contact us",
        "about": "About us",
        "privacy": "Privacy policy",
        "preview_alt": "Instagram media preview",
        "footer_disclaimer": (
            "This website is intended for educational and personal use only. All videos, photos, and "
            "media remain the property of their respective owners. We do not claim any rights over "
            "the content downloaded through this tool. All copyrights and trademarks belong to their "
            "rightful owners. Instagram and the Instagram logo are trademarks of Meta Platforms, Inc."
        ),
        "copyright": "© {year} Media Vault. All rights reserved.",
        "page_about_title": "About Us",
        "page_about_body": "Media Vault helps you download public Instagram media for personal and educational use. We do not host content and we respect creators' rights.",
        "page_contact_title": "Contact Us",
        "page_contact_body": "For support or takedown requests, email us at support@example.com.",
        "page_privacy_title": "Privacy Policy",
        "page_privacy_body": "We do not store downloaded content. Your requests are processed to fetch public media only.",
        "language_label": "Language",
    },
    "ar": {
        "title": "أداة تنزيل وسائط إنستغرام",
        "status_public": "المشاركات العامة فقط",
        "tab_video": "فيديو",
        "tab_reels": "ريلز",
        "tab_photo": "صور",
        "kicker": "حمّل كل محتوى إنستغرام هنا",
        "headline_video": "أداة تنزيل فيديو إنستغرام",
        "headline_reels": "أداة تنزيل ريلز إنستغرام",
        "headline_photo": "أداة تنزيل صور إنستغرام",
        "subhead": "الصق رابط منشور أو ريلز عام. الحسابات الخاصة ستظهر تنبيهًا بالخصوصية.",
        "placeholder": "الصق رابط منشور أو ريلز من إنستغرام",
        "paste": "لصق",
        "clear": "مسح",
        "search": "بحث",
        "results": "النتائج",
        "download": "تنزيل",
        "seo_heading": "أداة سريعة لتنزيل وسائط إنستغرام",
        "seo_paragraphs": [
            "حمّل صور وفيديوهات وريـلز إنستغرام من المنشورات العامة خلال ثوانٍ. الصق الرابط، شاهد المعاينة، ثم احفظ بالجودة الأصلية.",
            "مفيد للمبدعين والمسوقين والباحثين الذين يحتاجون إلى وصول سريع للمحتوى العام.",
            "الحسابات الخاصة غير مدعومة وسيظهر تنبيه بالخصوصية. احترم حقوق النشر ولا تنزّل إلا المحتوى المصرّح به.",
        ],
        "meta_description": "أداة مجانية لتنزيل وسائط إنستغرام من المنشورات العامة. الصق الرابط لتنزيل الصور والفيديوهات والريلز مع المعاينة.",
        "contact": "اتصل بنا",
        "about": "من نحن",
        "privacy": "سياسة الخصوصية",
        "language_label": "اللغة",
    },
    "bn": {
        "title": "ইনস্টাগ্রাম মিডিয়া ডাউনলোডার",
        "status_public": "শুধু পাবলিক পোস্ট",
        "tab_video": "ভিডিও",
        "tab_reels": "রিলস",
        "tab_photo": "ছবি",
        "kicker": "এখানেই সব ইনস্টাগ্রাম কনটেন্ট ডাউনলোড করুন",
        "headline_video": "ইনস্টাগ্রাম ভিডিও ডাউনলোডার",
        "headline_reels": "ইনস্টাগ্রাম রিলস ডাউনলোডার",
        "headline_photo": "ইনস্টাগ্রাম ছবি ডাউনলোডার",
        "subhead": "পাবলিক পোস্ট বা রিল লিঙ্ক পেস্ট করুন। প্রাইভেট অ্যাকাউন্টে প্রাইভেসি সতর্কতা দেখাবে।",
        "placeholder": "ইনস্টাগ্রাম পোস্ট বা রিল লিঙ্ক পেস্ট করুন",
        "paste": "পেস্ট",
        "clear": "ক্লিয়ার",
        "search": "সার্চ",
        "results": "ফলাফল",
        "download": "ডাউনলোড",
        "seo_heading": "দ্রুত ইনস্টাগ্রাম মিডিয়া ডাউনলোডার",
        "seo_paragraphs": [
            "পাবলিক ইনস্টাগ্রাম পোস্ট থেকে ছবি, ভিডিও ও রিলস দ্রুত ডাউনলোড করুন। লিঙ্ক পেস্ট করুন, প্রিভিউ দেখুন, এক ক্লিকে সেভ করুন।",
            "ক্রিয়েটর, মার্কেটার ও গবেষকদের জন্য দ্রুত পাবলিক মিডিয়া অ্যাক্সেস।",
            "প্রাইভেট অ্যাকাউন্ট সমর্থিত নয়। কপিরাইট সম্মান করুন এবং অনুমতি থাকলেই ডাউনলোড করুন।",
        ],
        "meta_description": "পাবলিক ইনস্টাগ্রাম পোস্টের জন্য ফ্রি মিডিয়া ডাউনলোডার। লিঙ্ক পেস্ট করে ছবি, ভিডিও ও রিলস ডাউনলোড করুন।",
        "contact": "যোগাযোগ",
        "about": "আমাদের সম্পর্কে",
        "privacy": "গোপনীয়তা নীতি",
        "language_label": "ভাষা",
    },
    "zh": {
        "title": "Instagram 媒体下载器",
        "status_public": "仅公开帖子",
        "tab_video": "视频",
        "tab_reels": "短片",
        "tab_photo": "照片",
        "kicker": "在这里下载所有 Instagram 内容",
        "headline_video": "Instagram 视频下载器",
        "headline_reels": "Instagram Reels 下载器",
        "headline_photo": "Instagram 照片下载器",
        "subhead": "粘贴公开帖子或短片链接。私密账号会显示隐私提示。",
        "placeholder": "粘贴 Instagram 帖子或短片链接",
        "paste": "粘贴",
        "clear": "清除",
        "search": "搜索",
        "results": "结果",
        "download": "下载",
        "seo_heading": "快速 Instagram 媒体下载器",
        "seo_paragraphs": [
            "从公开帖子快速下载 Instagram 照片、视频和 Reels。粘贴链接即可预览并保存原始质量。",
            "适合创作者、营销人员和研究者获取公开媒体用于灵感和整理。",
            "不支持私密账号。请尊重版权，仅下载你拥有或获授权的内容。",
        ],
        "meta_description": "公开 Instagram 帖子的免费媒体下载器。粘贴链接即可下载照片、视频和 Reels。",
        "contact": "联系我们",
        "about": "关于我们",
        "privacy": "隐私政策",
        "language_label": "语言",
    },
    "fr": {
        "title": "Téléchargeur de médias Instagram",
        "status_public": "Publications publiques uniquement",
        "tab_video": "Vidéo",
        "tab_reels": "Reels",
        "tab_photo": "Photo",
        "kicker": "Téléchargez tout le contenu Instagram ici",
        "headline_video": "Téléchargeur vidéo Instagram",
        "headline_reels": "Téléchargeur Reels Instagram",
        "headline_photo": "Téléchargeur photo Instagram",
        "subhead": "Collez un lien de post ou reel public. Les comptes privés affichent une alerte.",
        "placeholder": "Collez un lien de post ou reel Instagram",
        "paste": "Coller",
        "clear": "Effacer",
        "search": "Rechercher",
        "results": "Résultats",
        "download": "Télécharger",
        "seo_heading": "Téléchargeur Instagram rapide",
        "seo_paragraphs": [
            "Téléchargez rapidement photos, vidéos et reels depuis des posts publics. Collez le lien, prévisualisez, puis enregistrez en qualité originale.",
            "Conçu pour les créateurs, marketeurs et chercheurs qui ont besoin d’un accès rapide aux médias publics.",
            "Les comptes privés ne sont pas pris en charge. Respectez le droit d’auteur et téléchargez uniquement avec permission.",
        ],
        "meta_description": "Téléchargeur gratuit de médias Instagram pour posts publics. Collez un lien pour télécharger photos, vidéos et reels.",
        "contact": "Contact",
        "about": "À propos",
        "privacy": "Politique de confidentialité",
        "language_label": "Langue",
    },
    "de": {
        "title": "Instagram Medien-Downloader",
        "status_public": "Nur öffentliche Beiträge",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Alle Instagram-Inhalte hier herunterladen",
        "headline_video": "Instagram Video Downloader",
        "headline_reels": "Instagram Reels Downloader",
        "headline_photo": "Instagram Foto Downloader",
        "subhead": "Füge einen öffentlichen Post- oder Reel-Link ein. Private Konten zeigen eine Warnung.",
        "placeholder": "Instagram Post- oder Reel-Link einfügen",
        "paste": "Einfügen",
        "clear": "Löschen",
        "search": "Suchen",
        "results": "Ergebnisse",
        "download": "Download",
        "seo_heading": "Schneller Instagram Medien-Downloader",
        "seo_paragraphs": [
            "Lade Instagram Fotos, Videos und Reels aus öffentlichen Beiträgen in Sekunden herunter. Link einfügen, Vorschau ansehen, speichern.",
            "Ideal für Creator, Marketer und Researcher mit Bedarf an schnellen Medien-Zugriffen.",
            "Private Konten werden nicht unterstützt. Urheberrecht beachten und nur mit Erlaubnis herunterladen.",
        ],
        "meta_description": "Kostenloser Instagram Medien-Downloader für öffentliche Posts. Link einfügen und Fotos, Videos, Reels herunterladen.",
        "contact": "Kontakt",
        "about": "Über uns",
        "privacy": "Datenschutz",
        "language_label": "Sprache",
    },
    "hi": {
        "title": "इंस्टाग्राम मीडिया डाउनलोडर",
        "status_public": "केवल सार्वजनिक पोस्ट",
        "tab_video": "वीडियो",
        "tab_reels": "रील्स",
        "tab_photo": "फोटो",
        "kicker": "यहाँ सभी इंस्टाग्राम कंटेंट डाउनलोड करें",
        "headline_video": "इंस्टाग्राम वीडियो डाउनलोडर",
        "headline_reels": "इंस्टाग्राम रील्स डाउनलोडर",
        "headline_photo": "इंस्टाग्राम फोटो डाउनलोडर",
        "subhead": "किसी सार्वजनिक पोस्ट या रील का लिंक पेस्ट करें। प्राइवेट अकाउंट पर प्राइवेसी अलर्ट दिखेगा।",
        "placeholder": "इंस्टाग्राम पोस्ट या रील लिंक पेस्ट करें",
        "paste": "पेस्ट",
        "clear": "क्लियर",
        "search": "सर्च",
        "results": "परिणाम",
        "download": "डाउनलोड",
        "seo_heading": "तेज़ इंस्टाग्राम मीडिया डाउनलोडर",
        "seo_paragraphs": [
            "सार्वजनिक पोस्ट से फोटो, वीडियो और रील्स तुरंत डाउनलोड करें। लिंक पेस्ट करें, प्रिव्यू देखें और सेव करें।",
            "क्रिएटर्स, मार्केटर्स और रिसर्च के लिए तेज़ और आसान टूल।",
            "प्राइवेट अकाउंट सपोर्टेड नहीं हैं। केवल अनुमति वाले कंटेंट डाउनलोड करें।",
        ],
        "meta_description": "सार्वजनिक इंस्टाग्राम पोस्ट के लिए फ्री मीडिया डाउनलोडर। लिंक पेस्ट करके फोटो, वीडियो और रील्स डाउनलोड करें।",
        "contact": "संपर्क करें",
        "about": "हमारे बारे में",
        "privacy": "प्राइवेसी पॉलिसी",
        "language_label": "भाषा",
    },
    "hu": {
        "title": "Instagram média letöltő",
        "status_public": "Csak nyilvános posztok",
        "tab_video": "Videó",
        "tab_reels": "Reels",
        "tab_photo": "Fotó",
        "kicker": "Tölts le minden Instagram tartalmat itt",
        "headline_video": "Instagram videó letöltő",
        "headline_reels": "Instagram Reels letöltő",
        "headline_photo": "Instagram fotó letöltő",
        "subhead": "Illessz be egy nyilvános poszt vagy reels linket. Privát fióknál figyelmeztetés jelenik meg.",
        "placeholder": "Instagram poszt vagy reels link beillesztése",
        "paste": "Beillesztés",
        "clear": "Törlés",
        "search": "Keresés",
        "results": "Eredmények",
        "download": "Letöltés",
        "seo_heading": "Gyors Instagram média letöltő",
        "seo_paragraphs": [
            "Nyilvános posztokból gyorsan tölts le fotókat, videókat és reelseket. Link beillesztése, előnézet, mentés.",
            "Ideális alkotóknak, marketingeseknek és kutatóknak.",
            "Privát fiókok nem támogatottak. Tartsd tiszteletben a szerzői jogokat.",
        ],
        "meta_description": "Ingyenes Instagram média letöltő nyilvános posztokhoz. Link beillesztése és letöltés.",
        "contact": "Kapcsolat",
        "about": "Rólunk",
        "privacy": "Adatvédelem",
        "language_label": "Nyelv",
    },
    "id": {
        "title": "Pengunduh Media Instagram",
        "status_public": "Hanya posting publik",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Unduh semua konten Instagram di sini",
        "headline_video": "Pengunduh Video Instagram",
        "headline_reels": "Pengunduh Reels Instagram",
        "headline_photo": "Pengunduh Foto Instagram",
        "subhead": "Tempel tautan posting atau reels publik. Akun privat akan menampilkan peringatan.",
        "placeholder": "Tempel tautan post atau reels Instagram",
        "paste": "Tempel",
        "clear": "Hapus",
        "search": "Cari",
        "results": "Hasil",
        "download": "Unduh",
        "seo_heading": "Pengunduh Media Instagram Cepat",
        "seo_paragraphs": [
            "Unduh foto, video, dan reels dari posting publik dengan cepat. Tempel tautan, pratinjau, lalu simpan.",
            "Cocok untuk kreator, marketer, dan peneliti.",
            "Akun privat tidak didukung. Hormati hak cipta dan unduh dengan izin.",
        ],
        "meta_description": "Pengunduh media Instagram gratis untuk posting publik. Tempel tautan untuk mengunduh foto, video, dan reels.",
        "contact": "Hubungi kami",
        "about": "Tentang kami",
        "privacy": "Kebijakan privasi",
        "language_label": "Bahasa",
    },
    "it": {
        "title": "Downloader media Instagram",
        "status_public": "Solo post pubblici",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Scarica tutti i contenuti Instagram qui",
        "headline_video": "Downloader video Instagram",
        "headline_reels": "Downloader Reels Instagram",
        "headline_photo": "Downloader foto Instagram",
        "subhead": "Incolla un link di post o reel pubblico. Gli account privati mostrano un avviso.",
        "placeholder": "Incolla link post o reel Instagram",
        "paste": "Incolla",
        "clear": "Pulisci",
        "search": "Cerca",
        "results": "Risultati",
        "download": "Scarica",
        "seo_heading": "Downloader Instagram veloce",
        "seo_paragraphs": [
            "Scarica foto, video e reels da post pubblici in pochi secondi. Incolla il link, guarda l’anteprima e salva.",
            "Perfetto per creator, marketer e ricercatori.",
            "Account privati non supportati. Rispetta il copyright.",
        ],
        "meta_description": "Downloader gratuito di media Instagram per post pubblici. Incolla un link per scaricare foto, video e reels.",
        "contact": "Contatti",
        "about": "Chi siamo",
        "privacy": "Privacy",
        "language_label": "Lingua",
    },
    "ja": {
        "title": "Instagram メディアダウンローダー",
        "status_public": "公開投稿のみ",
        "tab_video": "動画",
        "tab_reels": "リール",
        "tab_photo": "写真",
        "kicker": "ここでInstagramのすべてをダウンロード",
        "headline_video": "Instagram 動画ダウンローダー",
        "headline_reels": "Instagram リールダウンローダー",
        "headline_photo": "Instagram 写真ダウンローダー",
        "subhead": "公開投稿またはリールのリンクを貼り付けてください。非公開アカウントは警告が表示されます。",
        "placeholder": "Instagram投稿またはリールのリンクを貼り付け",
        "paste": "貼り付け",
        "clear": "クリア",
        "search": "検索",
        "results": "結果",
        "download": "ダウンロード",
        "seo_heading": "高速 Instagram メディアダウンローダー",
        "seo_paragraphs": [
            "公開投稿から写真・動画・リールを素早くダウンロード。リンクを貼り付けてプレビューし保存。",
            "クリエイターやマーケター、研究者向けの便利なツール。",
            "非公開アカウントは非対応。著作権を尊重してください。",
        ],
        "meta_description": "公開Instagram投稿用の無料メディアダウンローダー。リンクを貼り付けて写真・動画・リールをダウンロード。",
        "contact": "お問い合わせ",
        "about": "私たちについて",
        "privacy": "プライバシーポリシー",
        "language_label": "言語",
    },
    "ko": {
        "title": "인스타그램 미디어 다운로더",
        "status_public": "공개 게시물만",
        "tab_video": "동영상",
        "tab_reels": "릴스",
        "tab_photo": "사진",
        "kicker": "여기에서 모든 인스타그램 콘텐츠 다운로드",
        "headline_video": "인스타그램 동영상 다운로더",
        "headline_reels": "인스타그램 릴스 다운로더",
        "headline_photo": "인스타그램 사진 다운로더",
        "subhead": "공개 पोस्ट 또는 릴스 링크를 붙여넣으세요. 비공개 계정은 경고가 표시됩니다.",
        "placeholder": "인스타그램 게시물 또는 릴스 링크 붙여넣기",
        "paste": "붙여넣기",
        "clear": "지우기",
        "search": "검색",
        "results": "결과",
        "download": "다운로드",
        "seo_heading": "빠른 인스타그램 미디어 다운로더",
        "seo_paragraphs": [
            "공개 게시물에서 사진, 동영상, 릴스를 빠르게 다운로드하세요. 링크를 붙여넣고 미리보기 후 저장.",
            "크리에이터와 마케터, 연구자를 위한 도구입니다.",
            "비공개 계정은 지원되지 않습니다. 저작권을 احترام하세요.",
        ],
        "meta_description": "공개 인스타그램 게시물용 무료 미디어 다운로더. 링크를 붙여넣어 사진, 동영상, 릴스를 다운로드하세요.",
        "contact": "문의하기",
        "about": "회사 소개",
        "privacy": "개인정보처리방침",
        "language_label": "언어",
    },
    "pl": {
        "title": "Pobieranie mediów z Instagram",
        "status_public": "Tylko publiczne posty",
        "tab_video": "Wideo",
        "tab_reels": "Reels",
        "tab_photo": "Zdjęcie",
        "kicker": "Pobierz wszystkie treści z Instagram tutaj",
        "headline_video": "Pobieranie wideo z Instagram",
        "headline_reels": "Pobieranie Reels z Instagram",
        "headline_photo": "Pobieranie zdjęć z Instagram",
        "subhead": "Wklej link do publicznego posta lub reels. Prywatne konta pokażą alert.",
        "placeholder": "Wklej link do posta lub reels z Instagram",
        "paste": "Wklej",
        "clear": "Wyczyść",
        "search": "Szukaj",
        "results": "Wyniki",
        "download": "Pobierz",
        "seo_heading": "Szybki downloader Instagram",
        "seo_paragraphs": [
            "Pobieraj zdjęcia, wideo i reels z publicznych postów w kilka sekund. Wklej link, zobacz podgląd i zapisz.",
            "Dla twórców, marketerów i badaczy.",
            "Prywatne konta nie są obsługiwane. Szanuj prawa autorskie.",
        ],
        "meta_description": "Darmowy downloader mediów Instagram dla publicznych postów. Wklej link i pobierz zdjęcia, wideo, reels.",
        "contact": "Kontakt",
        "about": "O nas",
        "privacy": "Polityka prywatności",
        "language_label": "Język",
    },
    "pt": {
        "title": "Baixador de mídia do Instagram",
        "status_public": "Somente posts públicos",
        "tab_video": "Vídeo",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Baixe todo o conteúdo do Instagram aqui",
        "headline_video": "Baixador de vídeos do Instagram",
        "headline_reels": "Baixador de Reels do Instagram",
        "headline_photo": "Baixador de fotos do Instagram",
        "subhead": "Cole um link de post ou reel público. Contas privadas exibem alerta.",
        "placeholder": "Cole o link do post ou reel do Instagram",
        "paste": "Colar",
        "clear": "Limpar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Baixar",
        "seo_heading": "Baixador rápido do Instagram",
        "seo_paragraphs": [
            "Baixe fotos, vídeos e reels de posts públicos em segundos. Cole o link, visualize e salve.",
            "Ideal para criadores, profissionais de marketing e pesquisadores.",
            "Contas privadas não são suportadas. Respeite direitos autorais.",
        ],
        "meta_description": "Baixador grátis de mídia do Instagram para posts públicos. Cole um link para baixar fotos, vídeos e reels.",
        "contact": "Contato",
        "about": "Sobre nós",
        "privacy": "Política de privacidade",
        "language_label": "Idioma",
    },
    "ru": {
        "title": "Загрузчик медиа Instagram",
        "status_public": "Только публичные посты",
        "tab_video": "Видео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Скачивайте весь контент Instagram здесь",
        "headline_video": "Загрузчик видео Instagram",
        "headline_reels": "Загрузчик Reels Instagram",
        "headline_photo": "Загрузчик фото Instagram",
        "subhead": "Вставьте ссылку на публичный пост или reels. Для приватных аккаунтов покажется предупреждение.",
        "placeholder": "Вставьте ссылку на пост или reels Instagram",
        "paste": "Вставить",
        "clear": "Очистить",
        "search": "Поиск",
        "results": "Результаты",
        "download": "Скачать",
        "seo_heading": "Быстрый загрузчик Instagram",
        "seo_paragraphs": [
            "Скачивайте фото, видео и reels из публичных постов за секунды. Вставьте ссылку, просмотрите и сохраните.",
            "Подходит для создателей, маркетологов и исследователей.",
            "Приватные аккаунты не поддерживаются. Уважайте авторские права.",
        ],
        "meta_description": "Бесплатный загрузчик медиа Instagram для публичных постов. Вставьте ссылку и скачайте фото, видео, reels.",
        "contact": "Контакты",
        "about": "О нас",
        "privacy": "Политика конфиденциальности",
        "language_label": "Язык",
    },
    "es": {
        "title": "Descargador de medios de Instagram",
        "status_public": "Solo publicaciones públicas",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Foto",
        "kicker": "Descarga todo el contenido de Instagram aquí",
        "headline_video": "Descargador de videos de Instagram",
        "headline_reels": "Descargador de Reels de Instagram",
        "headline_photo": "Descargador de fotos de Instagram",
        "subhead": "Pega un enlace de publicación o reel público. Las cuentas privadas mostrarán una alerta.",
        "placeholder": "Pega el enlace de un post o reel de Instagram",
        "paste": "Pegar",
        "clear": "Limpiar",
        "search": "Buscar",
        "results": "Resultados",
        "download": "Descargar",
        "seo_heading": "Descargador rápido de Instagram",
        "seo_paragraphs": [
            "Descarga fotos, videos y reels de publicaciones públicas en segundos. Pega el enlace, previsualiza y guarda.",
            "Ideal para creadores, marketers e investigadores.",
            "Las cuentas privadas no están soportadas. Respeta los derechos de autor.",
        ],
        "meta_description": "Descargador gratuito de medios de Instagram para publicaciones públicas. Pega un enlace para descargar fotos, videos y reels.",
        "contact": "Contacto",
        "about": "Acerca de",
        "privacy": "Política de privacidad",
        "language_label": "Idioma",
    },
    "sw": {
        "title": "Kipakua Media za Instagram",
        "status_public": "Machapisho ya umma tu",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Picha",
        "kicker": "Pakua maudhui yote ya Instagram hapa",
        "headline_video": "Kipakua Video za Instagram",
        "headline_reels": "Kipakua Reels za Instagram",
        "headline_photo": "Kipakua Picha za Instagram",
        "subhead": "Bandika kiungo cha post au reel ya umma. Akaunti binafsi zitaonyesha tahadhari.",
        "placeholder": "Bandika kiungo cha post au reel ya Instagram",
        "paste": "Bandika",
        "clear": "Futa",
        "search": "Tafuta",
        "results": "Matokeo",
        "download": "Pakua",
        "seo_heading": "Kipakua cha Haraka cha Instagram",
        "seo_paragraphs": [
            "Pakua picha, video na reels kutoka machapisho ya umma kwa sekunde chache. Bandika kiungo, ona muonekano, hifadhi.",
            "Kwa wabunifu, wauzaji na watafiti wanaohitaji ufikiaji wa haraka.",
            "Akaunti binafsi hazisaidiwi. Heshimu hakimiliki.",
        ],
        "meta_description": "Kipakua cha bure cha media za Instagram kwa machapisho ya umma. Bandika kiungo kupakua picha, video na reels.",
        "contact": "Wasiliana nasi",
        "about": "Kuhusu sisi",
        "privacy": "Sera ya faragha",
        "language_label": "Lugha",
    },
    "te": {
        "title": "ఇన్‌స్టాగ్రామ్ మీడియా డౌన్‌లోడర్",
        "status_public": "పబ్లిక్ పోస్టులు మాత్రమే",
        "tab_video": "వీడియో",
        "tab_reels": "రీల్స్",
        "tab_photo": "ఫోటో",
        "kicker": "ఇక్కడ అన్ని ఇన్‌స్టాగ్రామ్ కంటెంట్ డౌన్‌లోడ్ చేయండి",
        "headline_video": "ఇన్‌స్టాగ్రామ్ వీడియో డౌన్‌లోడర్",
        "headline_reels": "ఇన్‌స్టాగ్రామ్ రీల్స్ డౌన్‌లోడర్",
        "headline_photo": "ఇన్‌స్టాగ్రామ్ ఫోటో డౌన్‌లోడర్",
        "subhead": "పబ్లిక్ పోస్ట్ లేదా రీల్ లింక్‌ను పేస్ట్ చేయండి. ప్రైవేట్ అకౌంట్లకు ప్రైవసీ అలర్ట్ కనిపిస్తుంది.",
        "placeholder": "ఇన్‌స్టాగ్రామ్ పోస్ట్ లేదా రీల్ లింక్‌ను పేస్ట్ చేయండి",
        "paste": "పేస్ట్",
        "clear": "క్లియర్",
        "search": "సెర్చ్",
        "results": "ఫలితాలు",
        "download": "డౌన్‌లోడ్",
        "seo_heading": "త్వరిత ఇన్‌స్టాగ్రామ్ మీడియా డౌన్‌లోడర్",
        "seo_paragraphs": [
            "పబ్లిక్ పోస్టుల నుంచి ఫోటోలు, వీడియోలు, రీల్స్‌ను త్వరగా డౌన్‌లోడ్ చేయండి. లింక్ పేస్ట్ చేసి ప్రివ్యూ చూడండి.",
            "క్రియేటర్లు, మార్కెటర్లు, పరిశోధకులకు ఉపయోగకరం.",
            "ప్రైవేట్ అకౌంట్లు సపోర్ట్ చేయవు. కాపీరైట్‌ను గౌరవించండి.",
        ],
        "meta_description": "పబ్లిక్ ఇన్‌స్టాగ్రామ్ పోస్టుల కోసం ఫ్రీ మీడియా డౌన్‌లోడర్. లింక్ పేస్ట్ చేసి ఫోటోలు, వీడియోలు, రీల్స్ డౌన్‌లోడ్ చేయండి.",
        "contact": "సంప్రదించండి",
        "about": "మా గురించి",
        "privacy": "గోప్యతా విధానం",
        "language_label": "భాష",
    },
    "th": {
        "title": "ตัวดาวน์โหลดสื่อ Instagram",
        "status_public": "เฉพาะโพสต์สาธารณะ",
        "tab_video": "วิดีโอ",
        "tab_reels": "รีลส์",
        "tab_photo": "รูปภาพ",
        "kicker": "ดาวน์โหลดทุกอย่างจาก Instagram ได้ที่นี่",
        "headline_video": "ตัวดาวน์โหลดวิดีโอ Instagram",
        "headline_reels": "ตัวดาวน์โหลด Reels Instagram",
        "headline_photo": "ตัวดาวน์โหลดรูปภาพ Instagram",
        "subhead": "วางลิงก์โพสต์หรือรีลส์สาธารณะ บัญชีส่วนตัวจะแสดงการแจ้งเตือนความเป็นส่วนตัว",
        "placeholder": "วางลิงก์โพสต์หรือรีลส์ Instagram",
        "paste": "วาง",
        "clear": "ล้าง",
        "search": "ค้นหา",
        "results": "ผลลัพธ์",
        "download": "ดาวน์โหลด",
        "seo_heading": "ตัวดาวน์โหลด Instagram ที่รวดเร็ว",
        "seo_paragraphs": [
            "ดาวน์โหลดรูปภาพ วิดีโอ และรีลส์จากโพสต์สาธารณะได้อย่างรวดเร็ว วางลิงก์ ดูตัวอย่าง และบันทึก",
            "เหมาะสำหรับครีเอเตอร์ นักการตลาด และนักวิจัย",
            "ไม่รองรับบัญชีส่วนตัว กรุณาเคารพลิขสิทธิ์",
        ],
        "meta_description": "ตัวดาวน์โหลดสื่อ Instagram ฟรีสำหรับโพสต์สาธารณะ วางลิงก์เพื่อดาวน์โหลดรูปภาพ วิดีโอ และรีลส์",
        "contact": "ติดต่อเรา",
        "about": "เกี่ยวกับเรา",
        "privacy": "นโยบายความเป็นส่วนตัว",
        "language_label": "ภาษา",
    },
    "tr": {
        "title": "Instagram Medya İndirici",
        "status_public": "Yalnızca herkese açık gönderiler",
        "tab_video": "Video",
        "tab_reels": "Reels",
        "tab_photo": "Fotoğraf",
        "kicker": "Tüm Instagram içeriklerini buradan indir",
        "headline_video": "Instagram Video İndirici",
        "headline_reels": "Instagram Reels İndirici",
        "headline_photo": "Instagram Fotoğraf İndirici",
        "subhead": "Herkese açık bir gönderi veya reels bağlantısı yapıştırın. Özel hesaplarda uyarı gösterilir.",
        "placeholder": "Instagram gönderi veya reels bağlantısı yapıştırın",
        "paste": "Yapıştır",
        "clear": "Temizle",
        "search": "Ara",
        "results": "Sonuçlar",
        "download": "İndir",
        "seo_heading": "Hızlı Instagram Medya İndirici",
        "seo_paragraphs": [
            "Herkese açık gönderilerden fotoğraf, video ve reels’i saniyeler içinde indirin. Bağlantıyı yapıştırın, önizleyin, kaydedin.",
            "İçerik üreticileri ve pazarlamacılar için hızlı erişim sağlar.",
            "Özel hesaplar desteklenmez. Telif haklarına saygı gösterin.",
        ],
        "meta_description": "Herkese açık Instagram gönderileri için ücretsiz medya indirici. Bağlantı yapıştırarak fotoğraf, video ve reels indirin.",
        "contact": "Bize ulaşın",
        "about": "Hakkımızda",
        "privacy": "Gizlilik Politikası",
        "language_label": "Dil",
    },
    "uk": {
        "title": "Завантажувач медіа Instagram",
        "status_public": "Лише публічні пости",
        "tab_video": "Відео",
        "tab_reels": "Reels",
        "tab_photo": "Фото",
        "kicker": "Завантажуйте весь контент Instagram тут",
        "headline_video": "Завантажувач відео Instagram",
        "headline_reels": "Завантажувач Reels Instagram",
        "headline_photo": "Завантажувач фото Instagram",
        "subhead": "Вставте посилання на публічний пост або reels. Приватні акаунти покажуть попередження.",
        "placeholder": "Вставте посилання на пост або reels Instagram",
        "paste": "Вставити",
        "clear": "Очистити",
        "search": "Пошук",
        "results": "Результати",
        "download": "Завантажити",
        "seo_heading": "Швидкий завантажувач Instagram",
        "seo_paragraphs": [
            "Завантажуйте фото, відео та reels з публічних постів за секунди. Вставте посилання, перегляньте і збережіть.",
            "Для творців, маркетологів та дослідників.",
            "Приватні акаунти не підтримуються. Поважайте авторські права.",
        ],
        "meta_description": "Безкоштовний завантажувач медіа Instagram для публічних постів. Вставте посилання та завантажте фото, відео, reels.",
        "contact": "Контакти",
        "about": "Про нас",
        "privacy": "Політика конфіденційності",
        "language_label": "Мова",
    },
}

# If a language has only partial translations, fall back to English for the rest.
def build_strings(lang: str) -> Dict[str, object]:
    base = STRINGS[DEFAULT_LANG].copy()
    base.update(STRINGS.get(lang, {}))
    return base


MEDIA_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/(p|reel|reels|tv)/([^/?#]+)/?",
    re.IGNORECASE,
)


def get_lang(lang: str) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


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
            url = node.video_url if is_video else node.display_url
            if not url:
                continue
            if media_type == "photo" and is_video:
                continue
            if media_type in {"video", "reels"} and not is_video:
                continue
            kind = "video" if is_video else "photo"
            if media_type == "reels":
                kind = "reel"
            ext = ".mp4" if is_video else ".jpg"
            filename = safe_filename(f"{post.shortcode}_{idx}{ext}")
            items.append({"kind": kind, "url": url, "filename": filename})
    else:
        is_video = getattr(post, "is_video", False)
        url = post.video_url if is_video else post.url
        if not url:
            return []
        if media_type == "photo" and is_video:
            return []
        if media_type in {"video", "reels"} and not is_video:
            return []
        kind = "video" if is_video else "photo"
        if media_type == "reels":
            kind = "reel"
        ext = ".mp4" if is_video else ".jpg"
        filename = safe_filename(f"{post.shortcode}{ext}")
        items.append({"kind": kind, "url": url, "filename": filename})

    return items


def build_media_links(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    enriched = []
    for item in items:
        url_encoded = quote(item["url"], safe="")
        filename_encoded = quote(item["filename"])
        enriched.append(
            {
                **item,
                "proxy_url": f"/media-proxy?url={url_encoded}",
                "download_url": f"/download-file?url={url_encoded}&filename={filename_encoded}",
            }
        )
    return enriched


def alt_langs(page_slug: str) -> List[Dict[str, str]]:
    links = []
    for code in LANG_ORDER:
        suffix = f"/{page_slug}" if page_slug else ""
        links.append(
            {
                "code": code,
                "label": LANGS[code]["label"],
                "url": f"/{code}{suffix}",
            }
        )
    return links


def render_index(
    lang: str,
    *,
    error: Optional[str] = None,
    modal_show: bool = False,
    modal_title: Optional[str] = None,
    modal_message: Optional[str] = None,
    results: Optional[List[Dict[str, str]]] = None,
    selected_type: str = "video",
):
    strings = build_strings(lang)
    return render_template(
        "index.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        strings=strings,
        languages=[{"code": c, "label": LANGS[c]["label"]} for c in LANG_ORDER],
        alt_langs=alt_langs(""),
        error=error,
        modal_show=modal_show,
        modal_title=modal_title,
        modal_message=modal_message,
        results=results or [],
        selected_type=selected_type,
    )


@app.route("/")
def root_redirect():
    return redirect(f"/{DEFAULT_LANG}", code=302)


@app.route("/<lang>")
@app.route("/<lang>/")
def index_lang(lang: str):
    lang = get_lang(lang)
    return render_index(lang)


@app.route("/<lang>/download", methods=["POST"])
def download(lang: str):
    lang = get_lang(lang)
    strings = build_strings(lang)

    media_url = (request.form.get("media_url") or "").strip()
    media_type = (request.form.get("media_type") or "video").strip()

    parsed = parse_media_url(media_url)
    if not parsed:
        return render_index(lang, error=strings["error_invalid_url"], selected_type=media_type)

    url_kind, shortcode = parsed

    try:
        loader = make_loader()
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        owner_profile = getattr(post, "owner_profile", None)
        if owner_profile and getattr(owner_profile, "is_private", False):
            return render_index(
                lang,
                modal_show=True,
                modal_title=strings["modal_private_title"],
                modal_message=strings["modal_private_msg"],
                selected_type=media_type,
            )

        if media_type == "reels":
            if not (url_kind == "reel" or is_reel(post)):
                return render_index(
                    lang,
                    modal_show=True,
                    modal_title=strings["modal_mismatch_title"],
                    modal_message=strings["modal_mismatch_reel"],
                    selected_type=media_type,
                )

        items = extract_items(post, media_type)
        if not items:
            if media_type == "photo":
                msg = strings["modal_mismatch_image"]
            else:
                msg = strings["modal_mismatch_video"]
            return render_index(
                lang,
                modal_show=True,
                modal_title=strings["modal_mismatch_title"],
                modal_message=msg,
                selected_type=media_type,
            )

        results = build_media_links(items)
        return render_index(lang, results=results, selected_type=media_type)

    except LoginException:
        return render_index(
            lang,
            modal_show=True,
            modal_title=strings["modal_private_title"],
            modal_message=strings["modal_private_msg"],
            selected_type=media_type,
        )
    except ConnectionException as exc:
        return render_index(lang, error=f"Connection error: {exc}", selected_type=media_type)
    except Exception as exc:  # pragma: no cover
        return render_index(lang, error=f"Unexpected error: {exc}", selected_type=media_type)


@app.route("/media-proxy")
def media_proxy():
    url = request.args.get("url", "")
    if not url.startswith("https://"):
        abort(400)
    resp = requests.get(url, stream=True, timeout=20)
    if resp.status_code != 200:
        abort(404)
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return Response(
        stream_with_context(resp.iter_content(chunk_size=8192)),
        content_type=content_type,
    )


@app.route("/download-file")
def download_file():
    url = request.args.get("url", "")
    filename = safe_filename(request.args.get("filename", "instagram_media"))
    if not url.startswith("https://"):
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
def about_page(lang: str):
    lang = get_lang(lang)
    strings = build_strings(lang)
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        strings=strings,
        title=strings["page_about_title"],
        body=strings["page_about_body"],
        alt_langs=alt_langs("about"),
        languages=[{"code": c, "label": LANGS[c]["label"]} for c in LANG_ORDER],
    )


@app.route("/<lang>/contact")
def contact_page(lang: str):
    lang = get_lang(lang)
    strings = build_strings(lang)
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        strings=strings,
        title=strings["page_contact_title"],
        body=strings["page_contact_body"],
        alt_langs=alt_langs("contact"),
        languages=[{"code": c, "label": LANGS[c]["label"]} for c in LANG_ORDER],
    )


@app.route("/<lang>/privacy")
def privacy_page(lang: str):
    lang = get_lang(lang)
    strings = build_strings(lang)
    return render_template(
        "page.html",
        lang=lang,
        lang_dir=LANGS[lang]["dir"],
        strings=strings,
        title=strings["page_privacy_title"],
        body=strings["page_privacy_body"],
        alt_langs=alt_langs("privacy"),
        languages=[{"code": c, "label": LANGS[c]["label"]} for c in LANG_ORDER],
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
