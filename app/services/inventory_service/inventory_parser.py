import pandas as pd
import re
from sqlalchemy.orm import Session
from app.repositories.inventory_repo import InventoryRepository
from datetime import datetime


def get_last_material_counter(db: Session) -> int:
    repo = InventoryRepository(db)
    inventory_data = repo.get_all_inventory()
    max_counter = 0
    for item in inventory_data:
        if item.get("type") == "material":
            val = item.get("material", item.get("material_number", ""))
            match = re.search(r"-(\d+)$", str(val).strip())
            if match:
                idx = int(match.group(1))
                if idx > max_counter:
                    max_counter = idx
    return max_counter


def get_flexible_val(row: pd.Series, possible_names: list) -> str:
    # 1. Проверяем точные совпадения
    for name in possible_names:
        if name in row and pd.notna(row[name]):
            val = str(row[name]).strip()
            if val.lower() not in ("nan", "none", ""):
                return val

    row_keys_cleaned = {
        str(k).lower().replace(" ", "").replace("_", ""): k for k in row.keys()
    }
    for name in possible_names:
        clean_name = name.lower().replace(" ", "").replace("_", "")
        if clean_name in row_keys_cleaned:
            actual_key = row_keys_cleaned[clean_name]
            val = str(row[actual_key]).strip()
            if pd.notna(row[actual_key]) and val.lower() not in ("nan", "none", ""):
                return val
    return ""


def generate_preview(
    template_df: pd.DataFrame, original_filename: str, db: Session
) -> list[dict]:
    material_counter = get_last_material_counter(db) + 1
    parts = original_filename.split("-")
    source_val = f"Unit{parts[1]}" if len(parts) > 1 else "Unit_Unknown"
    base_material_num = parts[4] if len(parts) > 4 else "Unknown"

    parsed_data = []
    equipment_dict = {}

    for _, row in template_df.iterrows():
        tag = str(row.get("Equipment Tag Number", row.get("equipment_tag", ""))).strip()
        if not tag or tag.lower() == "nan":
            continue

        qty_val = row.get("Quantity", row.get("quantity", 0.0))
        qty = pd.to_numeric(qty_val, errors="coerce")
        if pd.isna(qty):
            qty = 0.0

        if tag in equipment_dict:
            equipment_dict[tag]["quantity"] += qty
        else:
            equipment_dict[tag] = {
                "type": "equipment",
                "tag_number": tag,
                "description": f"{tag} {row.get('Model', row.get('model', ''))} {row.get('Serial Number', row.get('serial_number', ''))}".strip(),
                "model_number": str(row.get("Model", row.get("model", ""))),
                "serial_number": str(
                    row.get("Serial Number", row.get("serial_number", ""))
                ),
                "quantity": qty,
                "operator": "RP01",
                "source": source_val,
                "approved": False,
                "eq_file_name": [original_filename],
            }

    parsed_data.extend(list(equipment_dict.values()))

    for _, row in template_df.iterrows():
        tag = row.get("Equipment Tag Number", row.get("equipment_tag"))
        desc = row.get("DESCRIPTION OF PART", row.get("description"))

        if pd.isna(tag) or desc:
            record_mat = {
                "type": "material",
                "material_number": f"{base_material_num}-{material_counter:03d}",
                "description": str(desc if pd.notna(desc) else ""),
                "unit": str(row.get("UNIT OF MEASURE", row.get("uom", ""))),
                "manufacturer": str(
                    row.get("MANUFACTURER NAME", row.get("manufacturer", ""))
                ),
                "part_number": str(
                    row.get(
                        "TRUE MANUFACTURER'S PART NUMBER",
                        row.get("true_part_number", ""),
                    )
                ),
                "dummy_number": str(
                    row.get(
                        "Company Warehouse Number. (Company SAP Part No.) To Be Provided by Company",
                        row.get("warehouse_number", ""),
                    )
                ),
                "file_name": original_filename,
                "price": str(row.get("UNIT PRICE", row.get("unit_price", ""))),
                "leadtime": str(
                    row.get(
                        'LEADTIME READY TO SHIP AFTER RECEIPT OF ORDER "ARO" (days)',
                        row.get("lead_time", ""),
                    )
                ),
                "currency": str(row.get("CURRENCY", row.get("currency", "USD"))),
                "source": source_val,
                "operator": "RP01",
                "stock_level": "0",
                "approved": False,
                # НОВЫЕ СТОЛБЦЫ
                "vendor_dwg": get_flexible_val(row, ["vendor_dwg", "Vendor DWG"]),
                "operating_spare_parts": get_flexible_val(
                    row, ["operating_spare_parts", "Operating Spare Parts", "op_spares"]
                ),
                "total_identical_parts": get_flexible_val(
                    row,
                    [
                        "total_identical_parts",
                        "Total Identical Parts",
                        "total_identical",
                    ],
                ),
                "original_po_part_number": get_flexible_val(
                    row,
                    [
                        "original_po_part_number",
                        "Original PO Part Number",
                        "orig_po_part",
                    ],
                ),
                "capital_spare_parts": get_flexible_val(
                    row, ["capital_spare_parts", "Capital Spare Parts", "cap_spares"]
                ),
                "commissioning_spare_parts": get_flexible_val(
                    row,
                    [
                        "commissioning_spare_parts",
                        "Commissioning Spare Parts",
                        "comm_spares",
                    ],
                ),
                "recommended_by_manufacturer": get_flexible_val(
                    row,
                    [
                        "recommended_by_manufacturer",
                        "Recommended by Manufacturer",
                        "rec_qty",
                    ],
                ),
                "contractor_review": get_flexible_val(
                    row, ["contractor_review", "Contractor Review", "cont_review"]
                ),
                "appr_qty_cat1": get_flexible_val(
                    row, ["appr_qty_cat1", "Appr Qty Cat1"]
                ),
                "appr_qty_cat3": get_flexible_val(
                    row, ["appr_qty_cat3", "Appr Qty Cat3"]
                ),
                "appr_qty_cat4": get_flexible_val(
                    row, ["appr_qty_cat4", "Appr Qty Cat4"]
                ),
            }

            # На всякий случай зачищаем строку 'nan' если она проскочила
            for k, v in record_mat.items():
                if isinstance(v, str) and v.lower() == "nan":
                    record_mat[k] = ""

            parsed_data.append(record_mat)
            material_counter += 1

    return parsed_data


def commit_to_inventory(new_data: list[dict], db: Session):
    from app.db.models import Equipment, Material

    equipments_to_db = []
    materials_to_db = []

    for item in new_data:
        data_to_save = {k: v for k, v in item.items() if k != "type"}

        if item.get("type") == "equipment":
            equipments_to_db.append(data_to_save)
        else:
            materials_to_db.append(data_to_save)

    if equipments_to_db:
        db.bulk_insert_mappings(Equipment, equipments_to_db)
    if materials_to_db:
        db.bulk_insert_mappings(Material, materials_to_db)

    db.commit()


def get_inventory_data(db: Session) -> list[dict]:
    repo = InventoryRepository(db)
    return repo.get_all_inventory()


def remove_existing_records(filename: str, db: Session):
    from app.db.models import Material, Equipment

    db.query(Material).filter(Material.file_name == filename).delete(
        synchronize_session=False
    )

    equipments = db.query(Equipment).all()
    for eq in equipments:
        if isinstance(eq.eq_file_name, list) and filename in eq.eq_file_name:
            db.delete(eq)
        elif eq.eq_file_name == filename:
            db.delete(eq)

    db.commit()
