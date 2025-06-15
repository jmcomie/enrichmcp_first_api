from functools import cache
from pathlib import Path
from typing import Any, Optional, Type
from pytmx import TiledMap, TiledTileset
from enrichmcp import EnrichMCP, EnrichModel, Relationship
from pydantic import Field, model_validator
from PIL import Image, ImageDraw
import io
import numpy as np


class GIDData(EnrichModel):
    description: Optional[str] = Field(default=None, description="A description of the tile.")
    image_data: Optional[bytes] = Field(default=None, description="The image data for the tile.")


class MapRect(EnrichModel):
    x: int
    y: int
    width: int
    height: int
    layer_index: Optional[int] = None

    def to_tuple(self):
        # Include type as string, layer, and rect.
        return (self.x, self.y, self.width, self.height, self.layer_index, str(type(self)))

    @classmethod
    def from_tuple(cls: Type["MapRect"], tup):
        # Include type as string, layer, and rect.
        return cls(x=tup[0], y=tup[1], width=tup[2], height=tup[3], layer_index=tup[4])

    @model_validator(mode='after')
    def check_layer_index(self) -> Any:
        if self.layer_index is not None and self.layer_index < 0:
            raise ValueError("Layer index cannot be less than 0.")
        return self


@cache
def get_image_from_filepath(image_filepath: Path) -> Image:
    return Image.open(image_filepath)

def draw_image_border_at_rect(image: Image, rect: tuple[int, int, int, int], border_thickness: int) -> Image:
    """
    Draws a black border around a specified rectangle in an image.
    
    :param image_path: Path to the image file.
    :param rect: A tuple (left, top, right, bottom) specifying the rectangle.
    :param border_thickness: Thickness of the border to draw.
    """
    draw: ImageDraw = ImageDraw.Draw(image)
    # Calculate coordinates for the outer rectangle based on the border thickness
    left, top, right, bottom = rect
    outer_rect = (left - border_thickness, top - border_thickness, 
                    right + border_thickness, bottom + border_thickness)

    # Draw two rectangles, outer rectangle in black
    draw.rectangle(outer_rect, outline="black", width=border_thickness)
    return image


@cache
def get_tileset_tile_image(image_filepath: Path, x: int, y: int, width: int, height: int) -> bytes:
    image = get_image_from_filepath(image_filepath)
    crop_box = (x, y, x+width, y+height)
    cropped_image = image.crop(crop_box)
    buffer = io.BytesIO()
    cropped_image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()


def get_gid_data(tiled_map: TiledMap) -> dict[int, GIDData]:
    gid_data: dict[int, dict[str, GIDData]] = {}
    for tileset in tiled_map.tilesets:
        assert isinstance(tileset, TiledTileset)
        path_to_asset_file: Path = Path(tiled_map.filename).parent / tileset.source
        for gid in range(tileset.firstgid, tileset.firstgid+tileset.tilecount):
            gid_data[gid] = GIDData(**{
                "description": tiled_map.get_tile_properties_by_gid(gid).get("description", None),
                "image_data": get_tileset_tile_image(path_to_asset_file, *(tiled_map.get_tile_image_by_gid(gid)[1]))
            })
    return gid_data


def get_tiled_map(path_to_file: Path|str) -> TiledMap:
    return TiledMap(filename=str(path_to_file))


def get_image(self, draw_border_around_map_rect: Optional[MapRect] = None, layer_indices: Optional[list[int]] = None) -> Image.Image:
    if layer_indices is None:
        layer_indices = range(len(self.data.layer_names))
    image: Optional[Image.Image] = None
    for layer_index in layer_indices:
        if image is None:
            image: Image.Image = get_image_from_tile_matrix(self.get_tile_matrix(layer_index).tolist(), self.get_tiled_map())
            continue
        image = get_image_from_tile_matrix(self.get_tile_matrix(layer_index).tolist(), self.get_tiled_map(), image_base=image)

    if draw_border_around_map_rect:
        image = draw_image_border_at_rect(image, self.layout.get_map_rect_pixel_rect(draw_border_around_map_rect, self.tile_shape), 1)
    return image


def get_image_from_tile_matrix(tile_matrix: list[list[int]], tiled_map: TiledMap, image_base: Optional[Image.Image] = None) -> Image:
    gid_data: dict[int, GIDData] = get_gid_data(tiled_map)
    height, width = np.array(tile_matrix).shape
    tile_width = tiled_map.tilewidth
    tile_height = tiled_map.tileheight
    buffer_width_px = width * tile_width
    buffer_height_px = height * tile_height
    if image_base is not None:
        if image_base.size != (buffer_width_px, buffer_height_px):
            raise ValueError("Image base size does not match tile matrix size.")
        new_image_buffer: Image = image_base
    else:
        new_image_buffer: Image = Image.new('RGB', (buffer_width_px, buffer_height_px), 'green')

    for cell_y, row in enumerate(tile_matrix):
        for cell_x, gid in enumerate(row):
            if gid not in gid_data:
                continue
            if not gid_data[gid].image_data:
                print(f"gid: {gid} has no image data.")
                continue
            cell_image = Image.open(io.BytesIO(gid_data[gid].image_data))
            px_x = cell_x * tile_width
            px_y = cell_y * tile_height
            new_image_buffer.paste(cell_image, (px_x, px_y))

    return new_image_buffer
