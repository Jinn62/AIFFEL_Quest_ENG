"""Streamlit client for the translation API."""

import csv
import io
import json
import os
import time
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


load_dotenv()
DEFAULT_API_URL = os.getenv("TRANSLATION_API_URL", "http://127.0.0.1:8000")
LANGUAGES = {
    "한국어": "ko",
    "English": "en",
    "简体中文": "zh",
    "日本語": "ja",
}
MAX_FILE_ROWS = 50
MAX_TEXT_LENGTH = 1_000


def request_translation(
    api_url: str, google_id_token: str, text: str, source_language: str, target_language: str
) -> tuple[dict | None, str | None]:
    """Send one translation request and return either its result or an error."""
    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/predict",
            json={"text": text, "source_language": source_language, "target_language": target_language},
            headers={"Authorization": f"Bearer {google_id_token}"},
            timeout=60,
        )
    except requests.RequestException as error:
        return None, f"Could not reach the API server: {error}"

    if response.ok:
        return response.json(), None

    try:
        detail = response.json().get("detail", response.text)
    except requests.JSONDecodeError:
        detail = response.text
    return None, f"Request failed ({response.status_code}): {detail}"


def split_text(text: str, maximum_length: int = MAX_TEXT_LENGTH) -> list[str]:
    """Split a text file into API-safe chunks while preserving line boundaries."""
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > maximum_length:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(line[index : index + maximum_length] for index in range(0, len(line), maximum_length))
        elif len(current) + len(line) > maximum_length:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]


def add_history(result: dict, source_text: str) -> None:
    """Store a compact record in the Streamlit session only."""
    st.session_state.translation_history.insert(
        0,
        {
            "source": source_text,
            "translated": result["translated_text"],
            "source_language": result["source_language"],
            "target_language": result["target_language"],
            "created_at": datetime.now().strftime("%H:%M:%S"),
        },
    )
    del st.session_state.translation_history[20:]


def render_copy_button(text: str) -> None:
    """Render a button that writes only the supplied translation to the clipboard."""
    serialized_text = json.dumps(text).replace("</", "<\\/")
    components.html(
        f"""
        <button id="copy-translation" type="button">📋 Copy translation</button>
        <span id="copy-status" style="margin-left: 0.5rem;"></span>
        <script>
        const text = {serialized_text};
        const status = document.getElementById("copy-status");
        document.getElementById("copy-translation").addEventListener("click", async () => {{
            try {{
                await navigator.clipboard.writeText(text);
                status.textContent = "Copied";
            }} catch (error) {{
                const fallback = document.createElement("textarea");
                fallback.value = text;
                document.body.appendChild(fallback);
                fallback.select();
                document.execCommand("copy");
                fallback.remove();
                status.textContent = "Copied";
            }}
        }});
        </script>
        """,
        height=42,
    )


def render_translation_box(text: str) -> None:
    """Show a plain result box without Streamlit's built-in code copy control."""
    with st.container(border=True):
        st.write(text)


def get_google_id_token() -> str:
    """Return the exposed ID token, or ask the user to sign in again after expiry."""

    expires_at = st.user.get("exp")
    if expires_at is not None and time.time() >= float(expires_at):
        st.warning("Your Google sign-in has expired. Sign in again to continue translating.")
        st.button("Sign in again", type="primary", on_click=st.logout)
        st.stop()

    try:
        return st.user.tokens["id"]
    except KeyError:
        st.error("Google login is configured without an exposed ID token. Set expose_tokens = \"id\".")
        st.stop()


st.set_page_config(page_title="Translation Service", page_icon="🌐")

if not getattr(st.user, "is_logged_in", False):
    st.title("🌐 Translation Service")
    st.caption("Sign in with Google to use the translation service.")
    st.button("Sign in with Google", type="primary", on_click=st.login)
    st.stop()

google_id_token = get_google_id_token()

if "translation_history" not in st.session_state:
    st.session_state.translation_history = []
if "latest_translation" not in st.session_state:
    st.session_state.latest_translation = None

st.title("🌐 Translation Service")
st.caption("Translate between Korean, English, Simplified Chinese, and Japanese through the FastAPI model service.")

with st.sidebar:
    api_url = DEFAULT_API_URL
    st.caption(f"API endpoint: {api_url}")
    st.caption(f"Signed in as {st.user.get('email', st.user.get('name', 'Google user'))}")
    st.button("Log out", on_click=st.logout, use_container_width=True)
    st.divider()
    st.subheader("Translation history")
    if st.session_state.translation_history:
        if st.button("Clear history", use_container_width=True):
            st.session_state.translation_history = []
            st.rerun()
        for item in st.session_state.translation_history:
            with st.expander(f"{item['created_at']} · {item['source_language']} → {item['target_language']}"):
                st.caption("Original")
                st.write(item["source"])
                st.caption("Translation")
                render_translation_box(item["translated"])
                render_copy_button(item["translated"])
    else:
        st.caption("Translations from this browser session appear here.")


def render_language_selectors(key_prefix: str) -> tuple[str, str]:
    """Render a source-target selector pair with unique Streamlit widget keys."""
    left, middle, right = st.columns([5, 1, 5])
    with left:
        source_label = st.selectbox("From", options=list(LANGUAGES), index=0, key=f"{key_prefix}_source")
    with middle:
        st.markdown("<div style='text-align:center; padding-top: 2rem'>→</div>", unsafe_allow_html=True)
    with right:
        target_options = [label for label in LANGUAGES if label != source_label]
        target_label = st.selectbox("To", options=target_options, key=f"{key_prefix}_target")
    return LANGUAGES[source_label], LANGUAGES[target_label]


text_tab, file_tab = st.tabs(["Text translation", "File translation"])

with text_tab:
    text_source_language, text_target_language = render_language_selectors("text")
    source_text = st.text_area("Text to translate", height=180, max_chars=MAX_TEXT_LENGTH)

    if st.button("Translate", type="primary", use_container_width=True):
        if not source_text.strip():
            st.error("Enter text to translate.")
        else:
            with st.spinner("Translating..."):
                result, error = request_translation(
                    api_url, google_id_token, source_text, text_source_language, text_target_language
                )
            if error:
                st.error(error)
            else:
                add_history(result, source_text)
                st.session_state.latest_translation = result
                st.rerun()

    latest_translation = st.session_state.latest_translation
    if latest_translation is not None:
        st.subheader("Translation")
        render_translation_box(latest_translation["translated_text"])
        render_copy_button(latest_translation["translated_text"])
        st.caption(f"Model: {latest_translation['model_id']} · {latest_translation['elapsed_ms']} ms")

with file_tab:
    file_source_language, file_target_language = render_language_selectors("file")
    st.caption(f"TXT files are split into {MAX_TEXT_LENGTH}-character chunks. CSV files translate up to {MAX_FILE_ROWS} rows.")
    uploaded_file = st.file_uploader("Upload a TXT or CSV file", type=["txt", "csv"])

    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".txt"):
            file_text = uploaded_file.getvalue().decode("utf-8-sig")
            st.caption(f"{len(file_text):,} characters · {len(split_text(file_text))} API requests")
            if st.button("Translate TXT file", use_container_width=True):
                chunks = split_text(file_text)
                if not chunks:
                    st.error("The TXT file must contain text to translate.")
                else:
                    translated_chunks: list[str] = []
                    progress = st.progress(0, text="Translating text file...")
                    for index, chunk in enumerate(chunks, start=1):
                        result, error = request_translation(
                            api_url, google_id_token, chunk, file_source_language, file_target_language
                        )
                        if error:
                            progress.empty()
                            st.error(f"Chunk {index} failed: {error}")
                            break
                        translated_chunks.append(result["translated_text"])
                        progress.progress(index / len(chunks), text=f"Translating chunk {index}/{len(chunks)}")
                    else:
                        progress.empty()
                        translated_file = "\n".join(translated_chunks)
                        st.success("TXT translation completed.")
                        render_translation_box(translated_file)
                        st.download_button(
                            "Download translated TXT",
                            data=translated_file.encode("utf-8"),
                            file_name=f"translated_{uploaded_file.name}",
                            mime="text/plain",
                        )
        else:
            decoded_csv = uploaded_file.getvalue().decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(decoded_csv)))
            if not rows or not rows[0]:
                st.error("The CSV file must include a header row and at least one data row.")
            elif len(rows) > MAX_FILE_ROWS:
                st.error(f"This demo supports up to {MAX_FILE_ROWS} rows per CSV file.")
            else:
                source_column = st.selectbox("Column to translate", options=list(rows[0]), key="csv_source_column")
                st.dataframe(rows[:5], use_container_width=True)
                if st.button("Translate CSV file", use_container_width=True):
                    translated_rows: list[dict[str, str]] = []
                    progress = st.progress(0, text="Translating CSV rows...")
                    for index, row in enumerate(rows, start=1):
                        result, error = request_translation(
                            api_url, google_id_token, row[source_column], file_source_language, file_target_language
                        )
                        if error:
                            progress.empty()
                            st.error(f"Row {index} failed: {error}")
                            break
                        translated_rows.append({**row, "translated_text": result["translated_text"]})
                        progress.progress(index / len(rows), text=f"Translating row {index}/{len(rows)}")
                    else:
                        progress.empty()
                        output = io.StringIO()
                        writer = csv.DictWriter(output, fieldnames=[*rows[0].keys(), "translated_text"])
                        writer.writeheader()
                        writer.writerows(translated_rows)
                        st.success("CSV translation completed.")
                        st.download_button(
                            "Download translated CSV",
                            data=output.getvalue().encode("utf-8-sig"),
                            file_name=f"translated_{uploaded_file.name}",
                            mime="text/csv",
                        )
