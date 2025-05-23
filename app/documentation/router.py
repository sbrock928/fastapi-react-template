"""API router for the documentation module with endpoints for managing notes."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.dependencies import SessionDep
from app.documentation.schemas import NoteCreate, NoteUpdate, NoteRead
from app.documentation.service import DocumentationService
from app.documentation.dao import DocumentationDAO

router = APIRouter(prefix="/user-guide", tags=["User Guide"])


def get_documentation_service(session: SessionDep) -> DocumentationService:
    return DocumentationService(DocumentationDAO(session))


@router.get("/notes", response_model=List[NoteRead])
async def get_all_notes(
    service: DocumentationService = Depends(get_documentation_service),
) -> List[NoteRead]:
    """Get all user guide notes"""
    return await service.get_all_notes()


@router.get("/notes/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: int, service: DocumentationService = Depends(get_documentation_service)
) -> NoteRead:
    """Get a specific note by ID"""
    note = await service.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes", response_model=NoteRead, status_code=201)
async def create_note(
    note: NoteCreate, service: DocumentationService = Depends(get_documentation_service)
) -> NoteRead:
    """Create a new note"""
    return await service.create_note(note)


@router.put("/notes/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    service: DocumentationService = Depends(get_documentation_service),
) -> NoteRead:
    """Update an existing note"""
    updated_note = await service.update_note(note_id, note_data)
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated_note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int, service: DocumentationService = Depends(get_documentation_service)
) -> None:
    """Delete a note"""
    result = await service.delete_note(note_id)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return None


@router.get("/notes/category/{category}", response_model=List[NoteRead])
async def get_notes_by_category(
    category: str, service: DocumentationService = Depends(get_documentation_service)
) -> List[NoteRead]:
    """Get notes filtered by category"""
    return await service.get_notes_by_category(category)
