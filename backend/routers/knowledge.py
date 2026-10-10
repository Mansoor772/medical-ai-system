import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_tenant_session
from core.rag import process_book_background
from models.tenant_models import AuditLog, DocumentChunk, KnowledgeBook
from schemas.knowledge import BookListItem, BookResponse

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

UPLOAD_DIR = "uploads"


def _require_doctor_or_admin(user: dict) -> dict:
    if user.get("role") not in ("doctor", "super_admin"):
        raise HTTPException(status_code=403, detail="Doctor or admin access required")
    return user


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def upload_book(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str | None = Form(None),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    _require_doctor_or_admin(user)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    book = KnowledgeBook(
        title=title,
        author=author,
        description=description,
        file_name=file.filename,
        file_path=file_path,
        upload_status="pending",
        uploaded_by=int(user["sub"]),
    )
    db.add(book)
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="book_uploaded",
        resource_type="knowledge_book",
        details=f"Book '{title}' uploaded, processing started",
    ))
    db.commit()
    db.refresh(book)

    # Process PDF in background (extract → chunk → embed → store)
    background_tasks.add_task(
        process_book_background,
        book.id,
        file_path,
        user["db_name"],
    )

    return book


@router.get("/books", response_model=list[BookListItem])
def list_books(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    _require_doctor_or_admin(user)
    return db.query(KnowledgeBook).order_by(KnowledgeBook.created_at.desc()).all()


@router.get("/books/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    _require_doctor_or_admin(user)
    book = db.query(KnowledgeBook).filter(KnowledgeBook.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/books/{book_id}", status_code=status.HTTP_200_OK)
def delete_book(
    book_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin",):
        raise HTTPException(status_code=403, detail="Super admin access required to delete books")

    book = db.query(KnowledgeBook).filter(KnowledgeBook.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Delete chunks first
    db.query(DocumentChunk).filter(DocumentChunk.book_id == book_id).delete()

    # Delete file from disk
    if os.path.exists(book.file_path):
        os.remove(book.file_path)

    db.delete(book)
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="book_deleted",
        resource_type="knowledge_book",
        resource_id=book_id,
        details=f"Book '{book.title}' and all its chunks deleted",
    ))
    db.commit()
    return {"message": f"Book '{book.title}' deleted"}
