from sqlalchemy.orm import Session
from app.db.models import Equipment, Material


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_inventory(self):
        equipments = self.db.query(Equipment).all()
        materials = self.db.query(Material).all()

        result = []
        for e in equipments:
            result.append(
                {
                    "type": "equipment",
                    "tag_number": e.tag_number,
                    "description": e.description,
                    "model_number": e.model_number,
                    "serial_number": e.serial_number,
                    "quantity": e.quantity,
                    "operator": e.operator,
                    "source": e.source,
                    "approved": e.approved,
                    "eq_file_name": e.eq_file_name,
                }
            )

        for m in materials:
            result.append(
                {
                    "type": "material",
                    "material_number": m.material_number,
                    "description": m.description,
                    "unit": m.unit,
                    "manufacturer": m.manufacturer,
                    "part_number": m.part_number,
                    "price": m.price,
                    "currency": m.currency,
                    "source": m.source,
                    "operator": m.operator,
                    "dummy_number": m.dummy_number,
                    "file_name": m.file_name,
                    "leadtime": m.leadtime,
                    "stock_level": m.stock_level,
                    "approved": m.approved,
                    "vendor_dwg": m.vendor_dwg,
                    "operating_spare_parts": m.operating_spare_parts,
                    "total_identical_parts": m.total_identical_parts,
                    "original_po_part_number": m.original_po_part_number,
                    "capital_spare_parts": m.capital_spare_parts,
                    "commissioning_spare_parts": m.commissioning_spare_parts,
                    "recommended_by_manufacturer": m.recommended_by_manufacturer,
                    "contractor_review": m.contractor_review,
                    "appr_qty_cat1": m.appr_qty_cat1,
                    "appr_qty_cat3": m.appr_qty_cat3,
                    "appr_qty_cat4": m.appr_qty_cat4,
                }
            )
        return result
