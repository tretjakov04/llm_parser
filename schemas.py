from typing import List, Optional
from pydantic import BaseModel, Field

# 1. То, что мы хотим получить в итоге от сгенерированного скрипта
class SpilItem(BaseModel):
    equipment_tag: str
    quantity: float
    serial_number: Optional[str] = None
    model: Optional[str] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    # Остальные поля...


class GeneratedParser(BaseModel):
    """Модель ответа от GPT с кодом"""
    explanation: str = Field(description="Объяснение логики: какие колонки выбраны для Тегов и Описания")
    python_code: str = Field(description="Полный Python-скрипт с функцией parse_excel")

# (Класс SpilItem здесь не обязателен, так как GPT генерирует словарь внутри кода,
# но мы держим его в голове как цель)