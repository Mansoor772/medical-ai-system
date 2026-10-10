from datetime import datetime

from pydantic import BaseModel


class BookResponse(BaseModel):
    id: int
    title: str
    author: str | None
    description: str | None
    file_name: str
    upload_status: str
    chunk_count: int
    uploaded_by: int
    created_at: datetime
    processed_at: datetime | None
    error_message: str | None

    class Config:
        from_attributes = True


class BookListItem(BaseModel):
    id: int
    title: str
    author: str | None
    upload_status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True
