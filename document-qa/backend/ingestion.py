"""
Belge işleme modülü: PDF ve resim dosyalarından metin çıkarır,
metni ChromaDB için uygun boyutlarda parçalara böler.
"""

import io
import re
from typing import List

import pdfplumber
import pytesseract
from PIL import Image, ImageFilter, ImageOps

# Chunk boyutu (kelime sayısı) ve örtüşme miktarı
CHUNK_SIZE = 250
CHUNK_OVERLAP = 80


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """PDF'in tüm sayfalarından metin çıkarır."""
    parts: List[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)

    if not parts:
        raise ValueError("PDF'den metin çıkarılamadı. Taramalı (scanned) PDF olabilir.")

    return "\n\n".join(parts)


def _preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """OCR öncesi görüntüyü iyileştirir: checkbox gibi küçük sembollerin okunmasını artırır."""
    # Gri tonlamaya çevir
    image = image.convert("L")
    # 2x büyüt — düşük çözünürlükte bozulan semboller netleşir
    w, h = image.size
    image = image.resize((w * 2, h * 2), Image.LANCZOS)
    # Keskinleştir — kenar geçişleri (köşeli parantez, X işareti) belirginleşir
    image = image.filter(ImageFilter.SHARPEN)
    # Kontrast normalize et — farklı aydınlatma koşullarını dengeler
    image = ImageOps.autocontrast(image)
    # Binary threshold — gri tonları siyah/beyaza indirir, OCR gürültüsü azalır
    image = image.point(lambda p: 255 if p > 150 else 0)
    return image


def extract_text_from_image(file_bytes: bytes) -> str:
    """Resim dosyasından Türkçe+İngilizce OCR uygular."""
    image = Image.open(io.BytesIO(file_bytes))
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")

    image = _preprocess_for_ocr(image)

    # Tesseract dil paketi: Türkçe + İngilizce
    text = pytesseract.image_to_string(image, lang="tur+eng")
    return text


def clean_text(text: str) -> str:
    """Metni normalize eder: çoklu boşluklar, satır sonları vb."""
    # Birden fazla boşluğu/sekme/satırı tek boşluğa indir
    text = re.sub(r"[ \t]+", " ", text)
    # Üçten fazla ardışık satır sonunu ikiye indir
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Metni örtüşen (overlapping) kelime bazlı parçalara böler.
    Küçük metinlerde tek chunk döner.
    """
    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap  # örtüşme için geri adım
        if end >= len(words):
            break

    return chunks


def process_document(file_bytes: bytes, filename: str) -> List[str]:
    """
    Dosya türüne göre metin çıkarır, temizler ve parçalara böler.
    Desteklenen türler: .pdf, .jpg, .jpeg, .png
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        raw_text = extract_text_from_pdf(file_bytes)
    elif ext in ("jpg", "jpeg", "png"):
        raw_text = extract_text_from_image(file_bytes)
    else:
        raise ValueError(
            f"Desteklenmeyen dosya formatı: .{ext}. "
            "Kabul edilenler: .pdf, .jpg, .jpeg, .png"
        )

    cleaned = clean_text(raw_text)

    if len(cleaned) < 20:
        raise ValueError(
            "Belgeden anlamlı metin çıkarılamadı. "
            "Lütfen okunabilir (non-scanned) bir belge deneyin."
        )

    chunks = split_into_chunks(cleaned)

    if not chunks:
        raise ValueError("Metin parçalara bölünemedi.")

    return chunks
