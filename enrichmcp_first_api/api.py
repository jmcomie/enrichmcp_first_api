from __future__ import annotations
from datetime import date
from typing import Optional
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import Field
import base64
from io import BytesIO
import enrichmcp_first_api.world_builder as world_builder
from pytmx import TiledMap, TiledTileset


import logging
import enrichmcp_first_api
from enrichmcp_first_api.lib.logger import FileLogger

# Use module root directory as log file directory
LOG: FileLogger =  FileLogger(
    log_file=f"{enrichmcp_first_api.__path__[0]}/logs/enrichmcp_first_api.log",
    level=logging.INFO,
    domain="EnrichMCPFirstAPI"
)

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


def get_default_tiled_map() -> TiledMap:
    return world_builder.get_tiled_map("/Users/justinmcomie/Projects/enrichmcp_first_api/enrichmcp_first_api/map_metadata_templates/MiniWorldSprites/map.tmx")


@app.resource
def get_gid_descriptions() -> dict[int, str]:
    """
    Returns a dictionary of GID descriptions from the default tiled map. These descriptions
    are used to create matries of tiles as list[list[int]] where the int is the GID of the tile.
    If asked to create a matrix of tiles, the GID will be used to look up the description.
    """
    gid_data: dict[int, world_builder.GIDData] = world_builder.get_gid_data(get_default_tiled_map())
    return {gid: data.description for gid, data in gid_data.items() if data.description is not None}




@app.entity
class Character(EnrichModel):
    """
    Register character attributes.
    """
    id: Optional[str] = Field(default=None, description="The unique identifier for the character.")
    name: Optional[str] = Field(default=None, description="The name of the character.")
    description: Optional[str] = Field(default=None, description="A description of the character.")
    age: Optional[int] = Field(default=None, description="The age of the character.")
    backstory: Optional[str] = Field(default=None, description="The backstory of the character.")


@app.entity
class Deity(EnrichModel):
    """
    Register character attributes.
    """
    id: Optional[str] = Field(default=None, description="The unique identifier for the character.")
    name: Optional[str] = Field(default=None, description="The name of the character.")
    description: Optional[str] = Field(default=None, description="A description of the character.")
    age: Optional[int] = Field(default=None, description="The age of the character.")
    backstory: Optional[str] = Field(default=None, description="The backstory of the character.")


def pillow_image_to_base64(pil_image, format='PNG'):
    """
    Converts a PIL image to a base64-encoded resource payload dict.
    
    :param pil_image: PIL Image object
    :param format: Image format, e.g. 'PNG', 'JPEG'
    :return: Dict with content and base64-encoded image
    """
    buffer = BytesIO()
    pil_image.save(buffer, format=format)
    img_data = buffer.getvalue()
    base64_data = base64.b64encode(img_data).decode('utf-8')

    mime_type = f"image/{format.lower()}"
    return {
        "content": [
            {
                "type": "resource",
                "resource": {
                    "uri": "resource://example",
                    "mimeType": mime_type,
                    "blob": base64_data
                }
            }
        ]
    }




@app.entity
class Book(EnrichModel):
    """Represents a book in the catalog."""

    id: int = Field(description="Book ID")
    title: str = Field(description="Book title")
    isbnwhathwat: str = Field(description="ISBN-13")
    published: date = Field(description="Publication date")
    author_id: int = Field(description="Author ID")
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
        )
    ]

@app.resource
async def get_image_from_tile_matrix(
    tile_matrix: list[list[int]],
) -> str:
    """Get an image from a tile matrix. Call after producing a matrix of tiles to get a display image."""
    tiled_map: TiledMap = get_default_tiled_map()
    map_image = world_builder.get_image_from_tile_matrix(tile_matrix, tiled_map)
    return pillow_image_to_base64(map_image)


# Define root resources
@app.resource
async def get_image() -> str:
    """Get an image from the tiled map. A generic function for now to call if asked to product an image."""
    tiled_map: TiledMap = get_default_tiled_map()
    map_image = world_builder.get_image_from_tile_matrix([[0,0,0], [1,1,1], [2,2,2], [3,3,3]], tiled_map)
    return pillow_image_to_base64(map_image)


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
async def create_book(
    book: Book,
) -> Book:
    """Create a new book in the catalog."""
    # In real app, this would save to a database
    LOG.info(f"Creating book: {book.model_dump_json()}")
    return book


@app.resource
async def create_character(
    character: Character,
) -> Character:
    """Create a new character in the catalog."""
    # In real app, this would save to a database
    LOG.info(f"Creating character: {character.model_dump_json()}")
    return character


@app.resource
async def get_author(author_id: int) -> Author:
    """Get a specific author by ID."""
    return Author(id=author_id, name="Jane Doe", bio="Bestselling author")


LOG.info("EnrichMCP has been imported...")

# Run the server
if __name__ == "__main__":
    LOG.info("Starting EnrichMCP First API...")
    app.run()
