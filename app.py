import streamlit as st
import yt_dlp
import os
import tempfile
import re
from pathlib import Path

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT Downloader",
    page_icon="▶️",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Syne', sans-serif;
    }

    .stApp {
        background: #0d0d0d;
        color: #f0f0f0;
    }

    h1, h2, h3 {
        font-family: 'Syne', sans-serif !important;
        font-weight: 800 !important;
    }

    .hero-title {
        font-family: 'Syne', sans-serif;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff0040, #ff6b35, #ffd700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }

    .hero-sub {
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        color: #666;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 2.5rem;
    }

    .card {
        background: #161616;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .info-item {
        background: #1e1e1e;
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
    }

    .info-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .info-value {
        font-size: 0.95rem;
        font-weight: 700;
        color: #f0f0f0;
        margin-top: 0.1rem;
    }

    .stTextInput > div > div > input {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #f0f0f0 !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.85rem !important;
        padding: 0.75rem 1rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #ff0040 !important;
        box-shadow: 0 0 0 1px #ff0040 !important;
    }

    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #ff0040, #ff4500) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 0.75rem !important;
        letter-spacing: 0.05em;
        transition: opacity 0.2s;
    }

    .stButton > button:hover {
        opacity: 0.85;
    }

    .stSelectbox > div > div {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #f0f0f0 !important;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #ff0040, #ff6b35) !important;
    }

    .tag {
        display: inline-block;
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 20px;
        padding: 0.2rem 0.7rem;
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem;
        color: #888;
        margin-right: 0.4rem;
    }

    .tag.red { border-color: #ff004044; color: #ff6060; }
    .tag.green { border-color: #00ff8844; color: #44ffaa; }

    .divider {
        border: none;
        border-top: 1px solid #222;
        margin: 1.5rem 0;
    }

    .footer {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: #333;
        text-align: center;
        margin-top: 3rem;
        letter-spacing: 0.1em;
    }
</style>
""", unsafe_allow_html=True)

# ── Helper Functions ──────────────────────────────────────────────────────────

def is_valid_youtube_url(url: str) -> bool:
    patterns = [
        r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+",
        r"(https?://)?(www\.)?youtube\.com/playlist\?list=[\w-]+",
    ]
    return any(re.search(p, url) for p in patterns)


def get_video_info(url: str) -> dict | None:
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        st.error(f"Fehler beim Laden der Video-Infos: {e}")
        return None


def format_duration(seconds: int) -> str:
    if not seconds:
        return "–"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def format_views(n) -> str:
    if not n:
        return "–"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def download_video(url: str, quality: str, output_dir: str) -> tuple[bool, str]:
    """Download video and return (success, filepath_or_error)."""

    # Quality mapping
    quality_map = {
        "1080p (Full HD)":  "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p (HD)":        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p":             "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p":             "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]",
        "Nur Audio (MP3)":  "bestaudio/best",
    }

    fmt = quality_map.get(quality, quality_map["1080p (Full HD)"])
    audio_only = "Nur Audio" in quality

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": fmt,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4" if not audio_only else None,
    }

    if audio_only:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Find the downloaded file
        files = list(Path(output_dir).iterdir())
        if files:
            return True, str(files[0])
        return False, "Datei nicht gefunden nach Download."
    except Exception as e:
        return False, str(e)


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown('<p class="hero-title">YT Downloader</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">YouTube → MP4 / MP3 · Full HD · Streamlit Cloud</p>', unsafe_allow_html=True)

# Input
url = st.text_input(
    label="YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed",
)

# Quality selector
quality_options = [
    "1080p (Full HD)",
    "720p (HD)",
    "480p",
    "360p",
    "Nur Audio (MP3)",
]

col1, col2 = st.columns([2, 1])
with col1:
    quality = st.selectbox("Qualität", quality_options, label_visibility="collapsed")
with col2:
    fetch_btn = st.button("🔍 Info laden", use_container_width=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Fetch Video Info ──────────────────────────────────────────────────────────
if fetch_btn or (url and "video_info" not in st.session_state):
    if url:
        if not is_valid_youtube_url(url):
            st.error("⚠️ Keine gültige YouTube-URL erkannt.")
        else:
            with st.spinner("Lade Video-Infos …"):
                info = get_video_info(url)
                if info:
                    st.session_state["video_info"] = info
                    st.session_state["video_url"] = url

if "video_info" in st.session_state and st.session_state.get("video_url") == url:
    info = st.session_state["video_info"]

    # Thumbnail
    thumb = info.get("thumbnail")
    if thumb:
        st.image(thumb, use_container_width=True)

    # Info Card
    st.markdown(f"""
    <div class="card">
        <div style="font-size:1.1rem; font-weight:700; margin-bottom:0.75rem;">{info.get('title', '–')}</div>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Kanal</div>
                <div class="info-value">{info.get('uploader', '–')}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Dauer</div>
                <div class="info-value">{format_duration(info.get('duration'))}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Aufrufe</div>
                <div class="info-value">{format_views(info.get('view_count'))}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Hochgeladen</div>
                <div class="info-value">{info.get('upload_date', '–')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Download Button
    if st.button("⬇️ Jetzt herunterladen", use_container_width=True):
        with st.spinner("Download läuft …"):
            with tempfile.TemporaryDirectory() as tmpdir:
                success, result = download_video(url, quality, tmpdir)

                if success:
                    with open(result, "rb") as f:
                        file_bytes = f.read()

                    filename = Path(result).name
                    mime = "audio/mpeg" if filename.endswith(".mp3") else "video/mp4"

                    st.success("✅ Download fertig! Klicke unten zum Speichern.")
                    st.download_button(
                        label=f"💾 {filename} speichern",
                        data=file_bytes,
                        file_name=filename,
                        mime=mime,
                        use_container_width=True,
                    )
                else:
                    st.error(f"❌ Download fehlgeschlagen: {result}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    NUR FÜR PERSÖNLICHEN GEBRAUCH · RESPEKTIERE URHEBERRECHTE<br>
    BUILT WITH STREAMLIT + YT-DLP
</div>
""", unsafe_allow_html=True)
