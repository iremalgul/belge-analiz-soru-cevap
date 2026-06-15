"""
Streamlit arayüzü — belge yükleme, yönetim ve sohbet tabanlı soru-cevap.
"""

import os

import requests
import streamlit as st

# Backend URL: Docker'da "backend" servis adı; yerel çalıştırmada localhost
API_URL = os.getenv("API_URL", "http://localhost:8000")
REQUEST_TIMEOUT_UPLOAD = 120  # saniye
REQUEST_TIMEOUT_ASK = 60
REQUEST_TIMEOUT_SHORT = 10

st.set_page_config(
    page_title="Belge Soru-Cevap",
    page_icon="📄",
    layout="wide",
)

# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────────

def api_upload(file) -> dict:
    files = {"file": (file.name, file.getvalue(), file.type)}
    resp = requests.post(f"{API_URL}/upload", files=files, timeout=REQUEST_TIMEOUT_UPLOAD)
    resp.raise_for_status()
    return resp.json()


def api_debug_search(question: str, doc_ids: list, top_k: int = 10) -> dict:
    payload = {
        "question": question,
        "doc_ids": doc_ids if doc_ids else None,
        "top_k": top_k,
    }
    resp = requests.post(f"{API_URL}/debug/search", json=payload, timeout=REQUEST_TIMEOUT_ASK)
    resp.raise_for_status()
    return resp.json()


def api_ask(question: str, doc_ids: list, top_k: int = 10) -> dict:
    payload = {
        "question": question,
        "doc_ids": doc_ids if doc_ids else None,
        "top_k": top_k,
    }
    resp = requests.post(f"{API_URL}/ask", json=payload, timeout=REQUEST_TIMEOUT_ASK)
    resp.raise_for_status()
    return resp.json()


def api_list_documents() -> list:
    resp = requests.get(f"{API_URL}/documents", timeout=REQUEST_TIMEOUT_SHORT)
    resp.raise_for_status()
    return resp.json()


def api_delete_document(doc_id: str) -> dict:
    resp = requests.delete(f"{API_URL}/documents/{doc_id}", timeout=REQUEST_TIMEOUT_SHORT)
    resp.raise_for_status()
    return resp.json()


def _http_error_detail(exc: requests.HTTPError) -> str:
    """HTTPError yanıtından okunabilir hata mesajı çıkarır."""
    try:
        return exc.response.json().get("detail", str(exc))
    except Exception:
        return str(exc)


# ── Oturum durumu başlatma ─────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages: list = []

if "selected_doc_ids" not in st.session_state:
    st.session_state.selected_doc_ids: list = []


# ── Sol panel: belge yönetimi ──────────────────────────────────────────────────

with st.sidebar:
    st.title("📂 Belge Yönetimi")

    # Yükleme alanı
    st.subheader("Belge Yükle")
    uploaded = st.file_uploader(
        "PDF veya resim seçin",
        type=["pdf", "jpg", "jpeg", "png"],
        help="Maksimum dosya boyutu: 20 MB",
    )

    if uploaded and st.button("Yükle ve İşle", type="primary", use_container_width=True):
        with st.spinner(f"'{uploaded.name}' işleniyor…"):
            try:
                result = api_upload(uploaded)
                st.success(
                    f"✅ **{result['filename']}** yüklendi — "
                    f"{result['chunk_count']} bölüme ayrıldı."
                )
                st.rerun()
            except requests.HTTPError as exc:
                st.error(f"Yükleme hatası: {_http_error_detail(exc)}")
            except requests.ConnectionError:
                st.error("⛔ Backend'e bağlanılamıyor. Servisin çalıştığından emin olun.")

    st.divider()

    # Belge listesi ve seçimi
    st.subheader("Yüklü Belgeler")

    try:
        documents = api_list_documents()
    except requests.ConnectionError:
        st.warning("Backend bağlantısı yok.")
        documents = []
    except Exception as exc:
        st.error(f"Liste alınamadı: {exc}")
        documents = []

    if not documents:
        st.info("Henüz belge yüklenmedi.")
    else:
        # Belge adı → doc_id eşlemesi
        label_to_id = {
            f"{d['filename']}  ({d['chunk_count']} bölüm)": d["doc_id"]
            for d in documents
        }

        selected_labels = st.multiselect(
            "Sorguda kullanılacak belgeler (boş = hepsi):",
            options=list(label_to_id.keys()),
            default=list(label_to_id.keys()),
        )
        st.session_state.selected_doc_ids = [label_to_id[l] for l in selected_labels]

        st.divider()

        # Belge silme
        st.subheader("Belge Sil")
        del_options = ["— Seçin —"] + [d["filename"] for d in documents]
        to_delete = st.selectbox("Silinecek belge:", del_options)

        if to_delete != "— Seçin —" and st.button(
            "Sil", type="secondary", use_container_width=True
        ):
            target_id = next(
                (d["doc_id"] for d in documents if d["filename"] == to_delete), None
            )
            if target_id:
                try:
                    api_delete_document(target_id)
                    st.success(f"'{to_delete}' silindi.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(f"Silme hatası: {_http_error_detail(exc)}")

    st.divider()
    st.caption("🔧 **Model:** gpt-4o-mini (OpenAI)")
    st.caption("🗄️ **Vektör DB:** ChromaDB (local)")
    st.caption("🧠 **Embedding:** multilingual-e5-small")


# ── Debug sekmesi ──────────────────────────────────────────────────────────────

with st.expander("🔍 Retrieval Debug — Hangi chunk'lar getiriliyor?", expanded=False):
    st.caption(
        "Sorunuzu yazın, LLM'ye gönderilmeden önce hangi belge parçalarının "
        "seçildiğini ve benzerlik skorlarını görün."
    )
    debug_question = st.text_input("Debug sorusu:", key="debug_q")
    if st.button("Retrieval'ı Test Et") and debug_question.strip():
        with st.spinner("Aranıyor…"):
            try:
                result = api_debug_search(
                    debug_question,
                    st.session_state.selected_doc_ids,
                )
                count = result["retrieved_chunk_count"]
                if count == 0:
                    st.warning(
                        "Hiç chunk getirilemedi. Belge yüklü mü? "
                        "Skor eşiği (0.30) tüm chunk'ları filtrelemiş olabilir."
                    )
                else:
                    st.success(f"{count} chunk bulundu.")
                    for ch in result["chunks"]:
                        score_color = (
                            "green" if ch["score"] >= 0.55
                            else "orange" if ch["score"] >= 0.40
                            else "red"
                        )
                        st.markdown(
                            f"**#{ch['rank']}** — "
                            f":{score_color}[skor: {ch['score']}] — "
                            f"`{ch['filename']}` bölüm {ch['chunk_index'] + 1}"
                        )
                        st.text_area(
                            label="",
                            value=ch["full_text"],
                            height=120,
                            key=f"chunk_{ch['rank']}",
                            disabled=True,
                        )
            except Exception as exc:
                st.error(f"Debug hatası: {exc}")


# ── Ana alan: sohbet ───────────────────────────────────────────────────────────

st.title("📄 Belge Soru-Cevap Sistemi")
st.caption("Yüklediğiniz PDF ve resimlere Türkçe veya İngilizce soru sorun.")

# Geçmiş mesajları göster
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 Kaynaklar"):
                for src in msg["sources"]:
                    score_pct = int(src["relevance_score"] * 100)
                    st.markdown(
                        f"**{src['filename']}** — Bölüm {src.get('chunk_index', 0) + 1} — uyum: `%{score_pct}`"
                    )
                    if src.get("snippet"):
                        st.caption(f"…{src['snippet']}…")

# Sohbet giriş kutusu (enter veya gönder butonu ile tetiklenir)
if prompt := st.chat_input("Sorunuzu yazın…"):
    # Kullanıcı mesajını göster ve kaydet
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Asistan yanıtını üret
    with st.chat_message("assistant"):
        with st.spinner("Yanıt hazırlanıyor…"):
            try:
                result = api_ask(
                    question=prompt,
                    doc_ids=st.session_state.selected_doc_ids,
                )
                st.markdown(result["answer"])

                if result.get("sources"):
                    with st.expander("📎 Kaynaklar"):
                        for src in result["sources"]:
                            score_pct = int(src["relevance_score"] * 100)
                            st.markdown(
                                f"**{src['filename']}** — Bölüm {src.get('chunk_index', 0) + 1} — uyum: `%{score_pct}`"
                            )
                            if src.get("snippet"):
                                st.caption(f"…{src['snippet']}…")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("sources", []),
                    }
                )
            except requests.HTTPError as exc:
                err = _http_error_detail(exc)
                st.error(f"API Hatası: {err}")
            except requests.ConnectionError:
                st.error("⛔ Backend'e bağlanılamıyor.")
            except Exception as exc:
                st.error(f"Beklenmeyen hata: {exc}")

# Sohbet temizleme
if st.session_state.messages:
    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.messages = []
        st.rerun()
