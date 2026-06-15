"""
Soru-Cevap modülü: OpenAI API (gpt-4o-mini) ile cevap üretir.
"""

import os
import re
from typing import Any, Dict, List, Tuple

from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_CONTEXT_CHARS = 12_000

# Bu eşiğin altında chunk yoksa LLM çağrılmaz; doğrudan yanıt döner
MIN_ANSWER_SCORE = 0.40

NO_ANSWER_MSG = "Bu belgede bu soruyla ilgili içerik bulunamadı."

SYSTEM_PROMPT = """You are a document analysis assistant. You are given numbered document excerpts.

RULES — follow strictly:
1. Use ONLY the information in the provided document excerpts. Never add your own knowledge, guesses, or completions.
2. Information may be phrased differently or indirectly — read carefully.
3. If you can answer the question — even partially — just give that answer. Do NOT append a "not found" note after a valid answer. Only say the information is not found when the question cannot be answered at all from the excerpts — and say it in the same language as the question.
4. CRITICAL: Detect the language of the user's question and respond in that exact same language. If the question is in English, your entire answer must be in English. If the question is in Turkish, your entire answer must be in Turkish.
5. Keep your answer clear and concise; use bullet points when helpful.
6. At the very END of your response, list only the excerpt numbers you actually used, in this exact format (nothing else after it):
SOURCES: 2,5"""


def _build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, Dict[int, Dict]]:
    """Numaralı context metni ve numara→chunk eşlemesi döndürür."""
    parts: List[str] = []
    num_to_chunk: Dict[int, Dict] = {}
    total_chars = 0
    for i, chunk in enumerate(chunks, 1):
        filename = chunk["metadata"].get("filename", "Bilinmeyen")
        idx = chunk["metadata"].get("chunk_index", 0)
        entry = f"[{i}] {filename} — Section {idx + 1}\n{chunk['text']}"
        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            break
        parts.append(entry)
        num_to_chunk[i] = chunk
        total_chars += len(entry)
    return "\n\n---\n\n".join(parts), num_to_chunk


def generate_answer(question: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY ortam değişkeni tanımlı değil.")

    client = OpenAI(api_key=api_key)

    # Hiç chunk yoksa veya en yüksek skor eşiğin altındaysa: LLM'e dil tespiti yaptır
    if not context_chunks or max(c["score"] for c in context_chunks) < MIN_ANSWER_SCORE:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "The user asked a question but no relevant content was found in the uploaded documents. In one sentence, tell the user this in the same language as their question."},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=60,
        )
        return {"answer": resp.choices[0].message.content or NO_ANSWER_MSG, "sources": [], "model": OPENAI_MODEL}

    context_text, num_to_chunk = _build_context(context_chunks)
    if not context_text.strip():
        return {"answer": NO_ANSWER_MSG, "sources": [], "model": OPENAI_MODEL}

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Document excerpts:\n\n{context_text}\n\nQuestion: {question}"},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content or ""

    # LLM'in belirttiği kaynak numaralarını ayıkla
    used_nums: set = set()
    match = re.search(r'(?:KAYNAKLAR|SOURCES):\s*([\d,\s]+)', raw)
    if match:
        used_nums = {int(n) for n in re.findall(r'\d+', match.group(1))}
        answer = raw[:match.start()].rstrip()
    else:
        answer = raw

    # Kullanılan chunk'lardan kaynak listesi oluştur
    cited = [num_to_chunk[n] for n in sorted(used_nums) if n in num_to_chunk]
    # LLM hiç belirtmediyse en yüksek skorlu 3 chunk'ı fallback olarak kullan
    if not cited:
        cited = sorted(context_chunks, key=lambda c: c["score"], reverse=True)[:3]

    seen: set = set()
    sources: List[Dict] = []
    for chunk in cited:
        doc_id = chunk["metadata"]["doc_id"]
        if doc_id not in seen:
            seen.add(doc_id)
            sources.append({
                "doc_id": doc_id,
                "filename": chunk["metadata"]["filename"],
                "relevance_score": chunk["score"],
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
                "snippet": chunk["text"][:300],
            })

    return {"answer": answer, "sources": sources, "model": OPENAI_MODEL}
