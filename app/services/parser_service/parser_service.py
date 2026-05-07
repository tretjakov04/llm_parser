import os
import json
import time
import asyncio
import pandas as pd
import openpyxl
import importlib.util

from sqlalchemy.orm import Session
from app.services.llm_processing.llm_service import CodeGeneratorService

OUTPUT_FOLDER = "gpt_parser"
SCRIPTS_FOLDER = "gpt_parsers"


def get_excel_snippet(ws, rows_count=60):
    snippet_data = {}
    row_count = 0
    for row in ws.iter_rows(min_row=1, max_row=rows_count):
        row_has_data = False
        for cell in row:
            if cell.value is not None:
                val = str(cell.value).strip()
                if val:
                    key = f"Row {cell.row}, Col {cell.column_letter}"
                    snippet_data[key] = val
                    row_has_data = True
        if row_has_data:
            row_count += 1
    return json.dumps(snippet_data, ensure_ascii=False), row_count


async def process_single_sheet(
    sheet_name: str,
    input_file_path: str,
    snippet_json: str,
    rows_with_data: int,
    ws,
    service: CodeGeneratorService,
    semaphore: asyncio.Semaphore,
):
    print(f"⏳ Лист '{sheet_name}': ожидает свободного слота...")

    async with semaphore:
        start_time = time.time()
        print(f"🚀 Лист '{sheet_name}': СТАРТ обработки")

        if rows_with_data < 5:
            print(f"⏭️ Лист '{sheet_name}': ПРОПУСК (мало данных)")
            return []

        print(f"🧠 Лист '{sheet_name}': отправлен запрос в GPT...")
        parser_obj = await service.generate_parser_code_async(snippet_json)

        if not parser_obj.python_code:
            print(f"❌ Лист '{sheet_name}': ОШИБКА (GPT не вернул код)")
            return []

        safe_name = "".join(
            c for c in sheet_name if c.isalnum() or c in (" ", "_", "-")
        ).strip()

        script_filename = f"parser_{safe_name}_{int(time.time() * 1000)}.py"
        script_path = os.path.join(SCRIPTS_FOLDER, script_filename)

        code_content = parser_obj.python_code.replace("```python", "").replace(
            "```", ""
        )
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code_content)

        print(f"⚙️ Лист '{sheet_name}': код сгенерирован, запускаем парсер...")
        try:
            spec = importlib.util.spec_from_file_location(
                f"mod_{safe_name}", script_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "parse_excel"):
                sheet_data = await asyncio.to_thread(module.parse_excel, ws)

                elapsed = round(time.time() - start_time, 2)
                if sheet_data:
                    print(f"✅ Лист '{sheet_name}': УСПЕХ! (заняло {elapsed} сек)")
                    return sheet_data
                else:
                    print(f"⚠️ Лист '{sheet_name}': нет записей (заняло {elapsed} сек)")
                    return []
        except Exception as e:
            print(f"❌ Лист '{sheet_name}': Ошибка при выполнении скрипта - {e}")
            return []
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except Exception as cleanup_error:
                    print(
                        f"⚠️ Лист '{sheet_name}': Не удалось удалить временный файл - {cleanup_error}"
                    )


async def process_excel_file(
    input_file_path: str, original_filename: str, db: Session
) -> list[dict]:
    global_start_time = time.time()

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists(SCRIPTS_FOLDER):
        os.makedirs(SCRIPTS_FOLDER)

    print(
        f"📂 Файл '{original_filename}': начинаем предварительное чтение сниппетов..."
    )

    wb = openpyxl.load_workbook(input_file_path, data_only=True)
    visible_sheets = [sheet.title for sheet in wb if sheet.sheet_state == "visible"]

    snippets_data = {}
    for sheet_name in visible_sheets:
        snippets_data[sheet_name] = get_excel_snippet(wb[sheet_name])

    print(f"✅ Сниппеты для {len(visible_sheets)} листов готовы! Запуск пула...")

    service = CodeGeneratorService()

    max_concurrent_tasks = 30
    semaphore = asyncio.Semaphore(max_concurrent_tasks)

    tasks = [
        process_single_sheet(
            sheet_name,
            input_file_path,
            snippets_data[sheet_name][0],
            snippets_data[sheet_name][1],
            wb[sheet_name],
            service,
            semaphore,
        )
        for sheet_name in visible_sheets
    ]

    results = await asyncio.gather(*tasks)

    wb.close()

    all_data_merged = []
    for sheet_data in results:
        if sheet_data:
            all_data_merged.extend(sheet_data)

    global_elapsed = round(time.time() - global_start_time, 2)
    print(
        f"🏁 Файл полностью обработан за {global_elapsed} сек. Собрано записей: {len(all_data_merged)}"
    )

    if all_data_merged:
        df = pd.DataFrame(all_data_merged)
        template_filename = f"template_{original_filename}"
        template_path = os.path.join(OUTPUT_FOLDER, template_filename)
        try:
            df.to_excel(template_path, index=False)
            print(f"💾 ПРОМЕЖУТОЧНЫЙ ШАБЛОН СОХРАНЕН: {template_path}")
        except Exception as e:
            print(f"⚠️ Ошибка при сохранении промежуточного шаблона: {e}")
        rename_map = {
            "equipment_tag": "Equipment Tag Number",
            "serial_number": "Serial Number",
            "model": "Model",
            "quantity": "Quantity",
            "description": "DESCRIPTION OF PART",
            "uom": "UNIT OF MEASURE",
            "manufacturer": "MANUFACTURER NAME",
            "true_part_number": "TRUE MANUFACTURER'S PART NUMBER",
            "material_check": "MATERIAL CHECK ASTM JIS DIN",
            "lead_time": 'LEADTIME READY TO SHIP AFTER RECEIPT OF ORDER "ARO" (days)',
            "unit_price": "UNIT PRICE",
            "currency": "CURRENCY",
            "warehouse_number": "Company Warehouse Number. (Company SAP Part No.) To Be Provided by Company",
            "vendor_dwg": "vendor_dwg",
            "operating_spare_parts": "operating_spare_parts",
            "total_identical_parts": "total_identical_parts",
            "original_po_part_number": "original_po_part_number",
            "capital_spare_parts": "capital_spare_parts",
            "commissioning_spare_parts": "commissioning_spare_parts",
            "recommended_by_manufacturer": "recommended_by_manufacturer",
            "contractor_review": "contractor_review",
            "appr_qty_cat1": "appr_qty_cat1",
            "appr_qty_cat3": "appr_qty_cat3",
            "appr_qty_cat4": "appr_qty_cat4",
        }
        df = df.rename(columns=rename_map)

        desired_order = list(rename_map.values())
        for col in desired_order:
            if col not in df.columns:
                df[col] = ""
        df = df[desired_order]

        from app.services.inventory_service.inventory_parser import generate_preview

        preview_data = generate_preview(df, original_filename, db)

        return preview_data
    else:
        raise ValueError(
            "Нет данных для сохранения. Скрипты не нашли нужную структуру."
        )
