from __future__ import annotations
import math
from pydantic import BaseModel, ConfigDict

def to_camel(string: str) -> str:
    parts = string.split('_')
    return parts[0] + ''.join((word.capitalize() for word in parts[1:]))

class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

class Page[T](CamelModel):
    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int

def paginate[T](items: list[T], *, page: int, page_size: int, total_items: int) -> Page[T]:
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    return Page(items=items, page=page, page_size=page_size, total_items=total_items, total_pages=total_pages)

def calculate_total_pages(total_items: int, page_size: int) -> int:
    if page_size <= 0:
        return 0
    return math.ceil(total_items / page_size)
