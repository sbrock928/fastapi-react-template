from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_session
from app.documentation.models import NoteBase, NoteRead
from app.documentation.service import DocumentationService

router = APIRouter(prefix="/user-guide", tags=["User Guide"])


@router.get("/notes", response_model=List[NoteRead])
async def get_all_notes(session: Session = Depends(get_session)):
    """Get all user guide notes"""
    service = DocumentationService(session)
    return await service.get_all_notes()


@router.get("/notes/{note_id}", response_model=NoteRead)
async def get_note(note_id: int, session: Session = Depends(get_session)):
    """Get a specific note by ID"""
    service = DocumentationService(session)
    note = await service.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes", response_model=NoteRead, status_code=201)
async def create_note(note: NoteBase, session: Session = Depends(get_session)):
    """Create a new note"""
    service = DocumentationService(session)
    return await service.create_note(note)


@router.put("/notes/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: int, note_data: NoteBase, session: Session = Depends(get_session)
):
    """Update an existing note"""
    service = UserGuideService(session)
    updated_note = await service.update_note(note_id, note_data)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated_note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, session: Session = Depends(get_session)):
    """Delete a note"""
    service = DocumentationService(session)
    result = await service.delete_note(note_id)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return None


@router.get("/notes/category/{category}", response_model=List[NoteRead])
async def get_notes_by_category(category: str, session: Session = Depends(get_session)):
    """Get notes filtered by category"""
    service = DocumentationService(session)
    return await service.get_notes_by_category(category)
