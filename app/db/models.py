from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
from app.db.database import Base
from sqlalchemy.orm import relationship
from datetime import datetime


class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    tag_number = Column(String, index=True)
    description = Column(String)
    model_number = Column(String)
    serial_number = Column(String)
    quantity = Column(Float, default=0.0)
    operator = Column(String)
    source = Column(String)
    approved = Column(Boolean, default=False)
    eq_file_name = Column(ARRAY(String), default=list)


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    material_number = Column(String, index=True)
    description = Column(String)
    unit = Column(String)
    manufacturer = Column(String)
    part_number = Column(String)
    dummy_number = Column(String)
    file_name = Column(String)
    price = Column(String)
    leadtime = Column(String)
    currency = Column(String)
    source = Column(String)
    operator = Column(String)
    stock_level = Column(String, default="0")
    approved = Column(Boolean, default=False)
    vendor_dwg = Column(String, nullable=True)
    operating_spare_parts = Column(String, nullable=True)
    total_identical_parts = Column(String, nullable=True)
    original_po_part_number = Column(String, nullable=True)
    capital_spare_parts = Column(String, nullable=True)
    commissioning_spare_parts = Column(String, nullable=True)
    recommended_by_manufacturer = Column(String, nullable=True)
    contractor_review = Column(String, nullable=True)
    appr_qty_cat1 = Column(String, nullable=True)
    appr_qty_cat3 = Column(String, nullable=True)
    appr_qty_cat4 = Column(String, nullable=True)


class Doc(Base):
    __tablename__ = "docs"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, unique=True, index=True)
    last_update = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status = Column(String, default="uploaded")
    parsed_data = Column(JSON, nullable=True)


class MasterList(Base):
    __tablename__ = "master_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "MasterListItem", back_populates="master_list", cascade="all, delete-orphan"
    )


class MasterListItem(Base):
    __tablename__ = "master_list_items"

    id = Column(Integer, primary_key=True, index=True)
    master_list_id = Column(Integer, ForeignKey("master_lists.id"))
    file_name = Column(String, index=True)
    process = Column(String)  # 'yes' или 'no'

    master_list = relationship("MasterList", back_populates="items")
