from __future__ import annotations
from datetime import date
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import Field

# Create the application
app = EnrichMCP(title="Book Catalog API", description="A simple book catalog for AI agents")

# Define entities
@app.entity
class Author(EnrichModel):
    """Represents a book author."""

    id: int = Field(description="Author ID")
    name: str = Field(description="Author's full name")
    bio: str = Field(description="Short biography")

    # Relationship to books
    books: list["Book"] = Relationship(description="Books written by this author")


@app.entity
class Book(EnrichModel):
    """Represents a book in the catalog."""

    id: int = Field(description="Book ID")
    title: str = Field(description="Book title")
    isbnwhathwat: str = Field(description="ISBN-13")
    published: date = Field(description="Publication date")
    author_id: int = Field(description="Author ID")
    fuck: str = Field(description="this is a questionable word")
    # Relationship to author
    author: Author = Relationship(description="Author of this book")


# Define resolvers
@Author.books.resolver
async def get_author_books(author_id: int) -> list[Book]:
    """Get all books by an author."""
    # In real app, this would query a database
    return [
        Book(
            id=1,
            title="Example Book",
            isbnwhathwat="978-0-123456-78-9",
            published=date(2023, 1, 1),
            author_id=author_id,
            fuck="fuck me"
        )
    ]


@Book.author.resolver
async def get_book_author(book_id: int) -> Author:
    """Get the author of a book."""
    # In real app, this would query a database
    return Author(id=1, name="Jane Doe", bio="Bestselling author")


# Define root resources
@app.resource
async def list_books() -> list[Book]:
    """List all books in the catalog."""
    return [
        Book(
            id=1,
            title="Example Book",
            isbn="978-0-123456-78-9",
            published=date(2023, 1, 1),
            author_id=1,
        )
    ]


@app.resource
async def get_author(author_id: int) -> Author:
    """Get a specific author by ID."""
    return Author(id=author_id, name="Jane Doe", bio="Bestselling author")


# Run the server
if __name__ == "__main__":
    app.run()
