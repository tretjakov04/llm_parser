from typing import (
    List,
    Optional,
    Union,
    Literal,
    Annotated,
)
from pydantic import BaseModel, Field


class GeneratedParser(BaseModel):

    explanation: str = Field(
        description="Объяснение логики: какие колонки выбраны для Тегов и Описания"
    )
    python_code: str = Field(description="Полный Python-скрипт с функцией parse_excel")


class EquipmentItem(BaseModel):
    type: Literal["equipment"]
    tag_number: str
    description: Optional[str] = ""
    model_number: Optional[str] = ""
    serial_number: Optional[str] = ""
    quantity: float = 0.0
    operator: str = "RP01"
    source: str
    approved: bool = False
    eq_file_name: List[str] = []


class MaterialItem(BaseModel):
    type: Literal["material"]
    material_number: str
    description: Optional[str] = ""
    unit: Optional[str] = ""
    manufacturer: Optional[str] = ""
    part_number: Optional[str] = ""
    dummy_number: Optional[str] = ""
    file_name: Optional[str] = ""
    price: Optional[str] = ""
    leadtime: Optional[str] = ""
    currency: Optional[str] = ""
    source: str
    operator: str = "RP01"
    stock_level: str = "0"
    approved: bool = False
    vendor_dwg: Optional[str] = None
    operating_spare_parts: Optional[str] = None
    total_identical_parts: Optional[str] = None
    original_po_part_number: Optional[str] = None
    capital_spare_parts: Optional[str] = None
    commissioning_spare_parts: Optional[str] = None
    recommended_by_manufacturer: Optional[str] = None
    contractor_review: Optional[str] = None
    appr_qty_cat1: Optional[str] = None
    appr_qty_cat3: Optional[str] = None
    appr_qty_cat4: Optional[str] = None


InventoryItem = Annotated[
    Union[EquipmentItem, MaterialItem], Field(discriminator="type")
]

CommitPayload = List[InventoryItem]
