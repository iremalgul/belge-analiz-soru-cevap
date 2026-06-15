"""
FastAPI uygulaması — belge yükleme, listeleme, silme ve soru-cevap endpoint'leri.
"""

import os
import uuid
from typing import List, Optional

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ingestion import process_document
from qa import generate_answer
from retrieval import (
    _get_collection,
    _get_model,
    add_document_chunks,
    delete_document,
    list_documents,
    search_similar_chunks,
)

# .env dosyasını yükle (Docker'da env değişkenleri zaten mevcut olur)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlarken modeli ve DB bağlantısını ısıt — ilk istekte gecikme olmaz."""
    _get_model()
    _get_collection()
    yield


app = FastAPI(
    title="Belge Soru-Cevap API",
    description="PDF ve resim dosyaları üzerinden RAG tabanlı soru-cevap sistemi",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Streamlit frontend'inin API'ye erişmesine izin verir
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Üretimde spesifik origin'leri kullan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


# ── Pydantic şemaları ──────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    doc_ids: Optional[List[str]] = Field(
        default=None,
        description="Sorguda kullanılacak belge ID'leri. Boş → tüm belgeler.",
    )
    top_k: int = Field(default=10, ge=1, le=20)


class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    model: str


# ── Endpoint'ler ───────────────────────────────────────────────────────────────

class DebugSearchRequest(BaseModel):
    question: str
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=20)


@app.post("/debug/search", tags=["Debug"])
async def debug_search(request: DebugSearchRequest):
    """
    Retrieval katmanını test eder — LLM çağrısı YAPILMAZ.
    Hangi chunk'ların getirildiğini ve skorlarını gösterir.
    Cevap bulunamıyor sorununu teşhis etmek için kullanın.
    """
    chunks = search_similar_chunks(
        query=request.question,
        doc_ids=request.doc_ids,
        top_k=request.top_k,
    )
    return {
        "question": request.question,
        "retrieved_chunk_count": len(chunks),
        "chunks": [
            {
                "rank": i + 1,
                "score": c["score"],
                "filename": c["metadata"]["filename"],
                "chunk_index": c["metadata"]["chunk_index"],
                "text_preview": c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
                "full_text": c["text"],
            }
            for i, c in enumerate(chunks)
        ],
    }


@app.get("/health", tags=["Sistem"])
async def health_check():
    """Servis sağlık kontrolü — docker-compose healthcheck için kullanılır."""
    return {"status": "ok"}


@app.post("/upload", response_model=DocumentInfo, tags=["Belgeler"])
async def upload_document(file: UploadFile = File(...)):
    """
    Belge yükler ve işler:
    - PDF → pdfplumber ile metin çıkar
    - Resim (JPG/PNG) → pytesseract OCR (Türkçe+İngilizce)
    Metin chunk'lara bölünür ve ChromaDB'ye embedding olarak kaydedilir.
    """
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Desteklenmeyen dosya türü: '{ext}'. "
                f"İzin verilenler: {', '.join(ALLOWED_EXTENSIONS)}"
            ),
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Dosya çok büyük. Maksimum: {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    doc_id = str(uuid.uuid4())

    try:
        chunks = process_document(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Belge işlenirken hata: {exc}"
        ) from exc

    try:
        chunk_count = add_document_chunks(doc_id, filename, chunks)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Embedding kaydedilirken hata: {exc}"
        ) from exc

    return DocumentInfo(doc_id=doc_id, filename=filename, chunk_count=chunk_count)


@app.post("/ask", response_model=QuestionResponse, tags=["Soru-Cevap"])
async def ask_question(request: QuestionRequest):
    """
    Yüklü belgeler üzerinden soru sorar.
    1. İlgili chunk'lar ChromaDB'den çekilir (vektör benzerliği).
    2. Chunk'lar context olarak LLM'e gönderilir.
    3. Türkçe/İngilizce yanıt döner.
    """
    try:
        similar_chunks = search_similar_chunks(
            query=request.question,
            doc_ids=request.doc_ids,
            top_k=request.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Benzerlik araması sırasında hata: {exc}"
        ) from exc

    if not similar_chunks:
        return QuestionResponse(
            answer="Sorunuzla ilgili içerik bulunamadı. Lütfen önce belge yükleyin.",
            sources=[],
            model="N/A",
        )

    try:
        result = generate_answer(request.question, similar_chunks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Cevap üretilirken hata: {exc}"
        ) from exc

    return QuestionResponse(**result)


@app.get("/documents", response_model=List[DocumentInfo], tags=["Belgeler"])
async def get_documents():
    """Sisteme yüklenmiş tüm belgeleri listeler."""
    try:
        docs = list_documents()
        return [DocumentInfo(**d) for d in docs]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Belgeler listelenirken hata: {exc}"
        ) from exc


@app.delete("/documents/{doc_id}", tags=["Belgeler"])
async def remove_document(doc_id: str):
    """Belgeyi ve tüm embedding'lerini ChromaDB'den siler."""
    try:
        deleted = delete_document(doc_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Belge silinirken hata: {exc}"
        ) from exc

    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Belge bulunamadı: {doc_id}")

    return {
        "message": "Belge başarıyla silindi.",
        "doc_id": doc_id,
        "deleted_chunks": deleted,
    }
