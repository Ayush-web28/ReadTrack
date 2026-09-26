"""
routers/authors.py: all endpoints under /authors.

A ROUTER is a group of related routes kept in its own file, so main.py
doesn't turn into one giant file. main.py plugs each router in.

CRUD -> HTTP verb mapping used here:
    Create -> POST   /authors
    Read   -> GET    /authors        (list)  and  GET /authors/{id}  (one)
    Update -> PATCH  /authors/{id}
    Delete -> DELETE /authors/{id}
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

# prefix: every route below automatically starts with /authors
# tags:   groups these routes together in the /docs page
router = APIRouter(prefix="/authors", tags=["Authors"])


@router.get("", response_model=list[schemas.AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    """List all authors."""
    # select(Author) is SQLAlchemy for: SELECT * FROM authors
    # .scalars().all() turns the result rows into a list of Author objects.
    return db.execute(select(models.Author).order_by(models.Author.name)).scalars().all()


@router.get("/{author_id}", response_model=schemas.AuthorOut)
def get_author(author_id: int, db: Session = Depends(get_db)):
    """Get one author. `author_id` comes from the URL (a PATH PARAMETER)."""
    author = db.get(models.Author, author_id)   # db.get() looks up by primary key
    if author is None:
        # HTTPException stops the function and sends an error response.
        # 404 = "that resource does not exist".
        raise HTTPException(status_code=404, detail="Author not found")
    return author


@router.get("/{author_id}/books", response_model=list[schemas.BookOut])
def list_author_books(author_id: int, db: Session = Depends(get_db)):
    """
    NESTED RESOURCE URL: /authors/3/books reads as "the books of author 3".
    author.books is the relationship defined in models.py.
    """
    author = db.get(models.Author, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return sorted(author.books, key=lambda b: b.title)


# status_code=201 means "Created". It is the correct success code for POST.
@router.post("", response_model=schemas.AuthorOut, status_code=status.HTTP_201_CREATED)
def create_author(payload: schemas.AuthorCreate, db: Session = Depends(get_db)):
    """
    Create an author. `payload` is the JSON body of the request. FastAPI
    validates it against AuthorCreate BEFORE this function runs.
    """
    # payload.model_dump() -> {"name": "...", "bio": ...}; ** unpacks it into
    # keyword arguments: Author(name="...", bio=...)
    author = models.Author(**payload.model_dump())
    db.add(author)        # stage the new row
    db.commit()           # actually write it to the database
    db.refresh(author)    # reload it so we get the auto-generated id
    return author


@router.patch("/{author_id}", response_model=schemas.AuthorOut)
def update_author(author_id: int, payload: schemas.AuthorUpdate, db: Session = Depends(get_db)):
    """Partially update an author: only the fields the client sent are changed."""
    author = db.get(models.Author, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    # exclude_unset=True -> include ONLY fields the client actually sent.
    # This is what makes it a PATCH: {"bio": "New bio"} leaves the name alone.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(author, field, value)   # same as: author.bio = "New bio"

    db.commit()
    db.refresh(author)
    return author


@router.delete("/{author_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_author(author_id: int, db: Session = Depends(get_db)):
    """Delete an author. Refuses if they still have books."""
    author = db.get(models.Author, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")

    # 409 Conflict = "the request is valid but clashes with the current state".
    # Without this check we'd leave books pointing at an author that no longer exists.
    if author.books:
        raise HTTPException(
            status_code=409,
            detail="Author still has books; delete or reassign them first",
        )

    db.delete(author)
    db.commit()
    # 204 No Content = "success, and there is nothing to send back".
    return Response(status_code=status.HTTP_204_NO_CONTENT)
