# Belge Soru-Cevap Sistemi (RAG)

[Uygulama Tanıtım Videosu](https://drive.google.com/file/d/1mg9MxmaNgIGG5fIQPAaVA66a3bVLs7Ik/view?usp=sharing)

PDF ve resim (JPG/PNG) dosyaları yükleyip Türkçe veya İngilizce soru sormanızı sağlayan yerel RAG uygulaması. Sistem yalnızca yüklenen belgelerdeki bilgilere dayanarak yanıt üretir, tahmin veya çıkarım yapmaz.

## Mimari

```
Kullanıcı → Streamlit UI → FastAPI Backend
                               ├── pdfplumber          (PDF metin çıkarma)
                               ├── pytesseract OCR     (resim → metin, Türkçe+İngilizce)
                               ├── multilingual-e5-small (embedding)
                               ├── ChromaDB            (vektör arama, yerel kalıcı)
                               └── OpenAI gpt-4o-mini  (yanıt üretme)
```

## Kurulum (Docker — Önerilen)

**Ön gereksinim:** Docker Desktop kurulu ve çalışıyor olmalı.

```bash
# 1. Projeyi klonla
git clone https://github.com/iremalgul/belge-analiz-soru-cevap.git
cd belge-analiz-soru-cevap/document-qa

# 2. API anahtarını ayarla
cp .env.example .env
# .env dosyasını aç → OPENAI_API_KEY değerini gir

# 3. Başlat
docker-compose up --build
```

- **Arayüz:** http://localhost:8501
- **API dokümantasyonu:** http://localhost:8000/docs

## Kurulum (Yerel — Docker olmadan)

### Ön gereksinimler

**Tesseract OCR** (Türkçe dil paketiyle):

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-tur

# macOS
brew install tesseract tesseract-lang

# Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

### Backend

```bash
cd document-qa/backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

cp ../.env.example ../.env
# OPENAI_API_KEY değerini gir

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd document-qa/frontend
pip install -r requirements.txt
streamlit run app.py
```

## Ortam Değişkenleri

| Değişken | Zorunlu | Varsayılan | Açıklama |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API anahtarı |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | Kullanılacak model |
| `CHROMA_PERSIST_DIR` | ❌ | `./chroma_db` | ChromaDB kalıcı dizin |

## API Endpoint'leri

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/health` | Servis sağlık kontrolü |
| POST | `/upload` | Belge yükle (multipart/form-data) |
| POST | `/ask` | Soru sor, yanıt ve kaynak al |
| GET | `/documents` | Yüklü belgeleri listele |
| DELETE | `/documents/{doc_id}` | Belge sil |
| POST | `/debug/search` | LLM'e gitmeden retrieval sonuçlarını gör |

### POST /ask — İstek / Yanıt

```json
// İstek
{
  "question": "Başvuru sahibinin adı nedir?",
  "doc_ids": ["uuid-1"],   // boş = tüm belgeler
  "top_k": 10
}

// Yanıt
{
  "answer": "Mehmet Yılmaz",
  "sources": [
    {
      "filename": "form.jpg",
      "relevance_score": 0.87,
      "chunk_index": 0,
      "snippet": "Ad Soyad: Mehmet Yılmaz..."
    }
  ],
  "model": "gpt-4o-mini"
}
```

## Desteklenen Dosya Türleri

| Tür | İşlem | Not |
|---|---|---|
| `.pdf` | pdfplumber | Metin katmanı olan PDF'ler |
| `.jpg` / `.jpeg` | pytesseract OCR | Türkçe + İngilizce |
| `.png` | pytesseract OCR | Türkçe + İngilizce |

> Taramalı (scanned) PDF için önce resme dönüştürün; resim olarak yükleyin.

## Sistem Davranışı

- Soru yalnızca yüklenen belgelerin içeriğiyle yanıtlanır, model kendi bilgisini kullanmaz
- Belgede bilgi yoksa "Bu bilgi belgede yer almamaktadır" yanıtı döner (LLM'e gönderilmez)
- Dil otomatik tespit edilir: Türkçe soruya Türkçe, İngilizce soruya İngilizce yanıt verilir
- Her yanıtta hangi belgeden, kaçıncı bölümden alındığı ve metin snippet'i gösterilir
- Birden fazla belge yüklüyken skor filtrelemesiyle yalnızca ilgili belge kaynak olarak gösterilir

## Geliştirme Notları

- [DEVLOG.md](DEVLOG.md) — Geliştirme süreci, alınan kararlar, deneyip vazgeçilenler
- [TESTING.md](TESTING.md) — Test senaryoları, başarılı/başarısız durumlar, sistem sınırları
