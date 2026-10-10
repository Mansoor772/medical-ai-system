import os
from datetime import datetime, timezone

from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy.orm import Session

from .config import settings

_client: OpenAI | None = None


def _openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ── PDF extraction ─────────────────────────────────────────────────────────────

def extract_pages(file_path: str) -> list[tuple[int, str]]:
    """Return list of (page_number, text) for each non-empty page."""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i + 1, text.strip()))
    return pages


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


# ── Embeddings ─────────────────────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    response = _openai().embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text[:8000],  # safety trim
    )
    return response.data[0].embedding


# ── Book processing (runs as background task) ──────────────────────────────────

def process_book_background(book_id: int, file_path: str, db_name: str) -> None:
    from sqlalchemy.orm import sessionmaker
    from core.database import _get_tenant_engine
    from models.tenant_models import DocumentChunk, KnowledgeBook

    engine = _get_tenant_engine(db_name)
    SessionLocal = sessionmaker(bind=engine)
    db: Session = SessionLocal()

    try:
        book = db.query(KnowledgeBook).filter(KnowledgeBook.id == book_id).first()
        if not book:
            return

        book.upload_status = "processing"
        db.commit()

        pages = extract_pages(file_path)
        if not pages:
            book.upload_status = "failed"
            book.error_message = "No readable text found in PDF"
            db.commit()
            return

        total_chunks = 0
        for page_num, page_text in pages:
            for idx, chunk in enumerate(chunk_text(page_text)):
                embedding = get_embedding(chunk)
                db.add(DocumentChunk(
                    book_id=book_id,
                    page_number=page_num,
                    chunk_index=idx,
                    content=chunk,
                    embedding=embedding,
                ))
                total_chunks += 1

        book.upload_status = "processed"
        book.chunk_count = total_chunks
        book.processed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        book = db.query(KnowledgeBook).filter(KnowledgeBook.id == book_id).first()
        if book:
            book.upload_status = "failed"
            book.error_message = str(e)[:500]
            db.commit()
    finally:
        db.close()


# ── Retrieval ──────────────────────────────────────────────────────────────────

def retrieve_chunks(query: str, db: Session, top_k: int = 5) -> list[dict]:
    """Embed query and return top-k most similar document chunks."""
    from models.tenant_models import DocumentChunk, KnowledgeBook

    query_embedding = get_embedding(query)

    # Only retrieve from processed books
    processed_book_ids = [
        r.id for r in db.query(KnowledgeBook.id)
        .filter(KnowledgeBook.upload_status == "processed")
        .all()
    ]
    if not processed_book_ids:
        return []

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.book_id.in_(processed_book_ids))
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
        .all()
    )

    results = []
    for chunk in chunks:
        book = db.query(KnowledgeBook).filter(KnowledgeBook.id == chunk.book_id).first()
        results.append({
            "book_id": chunk.book_id,
            "book_title": book.title if book else "Unknown",
            "author": book.author if book else None,
            "page_number": chunk.page_number,
            "chunk_text": chunk.content,
        })
    return results
