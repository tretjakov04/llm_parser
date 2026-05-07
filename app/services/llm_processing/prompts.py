CODE_GEN_PROMPT = """
Ты — Senior Python Developer. Напиши парсер для SPIL Matrix (Excel).

ВХОДНЫЕ ДАННЫЕ:
JSON-сэмпл (первые 60-100 строк).

ЗАДАЧА:
Напиши функцию def parse_excel(sheet) -> list[dict]:
(Параметр `sheet` — это уже открытый объект openpyxl.worksheet.worksheet.Worksheet. Файл открывать не нужно!)

CRITICAL RULES FOR GENERATING CODE:
1. DO NOT implement logic for parsing tags or splitting metadata cells.
2. Your script MUST start with exactly this import:
from app.services.parser_service.spil_utils import parse_tag_cell, split_metadata_cell
3. STRICT SYNTAX RULE: DO NOT use complex one-liners, generators, or list comprehensions for nested logic (e.g., do not use `sum(1 for x in y if z)` with nested loops). Write standard, explicit `for` loops to prevent Python variable scope errors (`UnboundLocalError`).

ВАЖНОЕ ТРЕБОВАНИЕ БЕЗОПАСНОСТИ:
При вычислении индексов (например, col - 2) всегда оборачивай их в max(1, ...). Пример: range(max(1, WALL_COL - 2), ...).

АЛГОРИТМ (СТРОГО СЛЕДУЙ ЕМУ, НЕ МЕНЯЙ ЛОГИКУ):

1. ПОДГОТОВКА:
   import re 
   from app.services.parser_service.spil_utils import parse_tag_cell, split_metadata_cell
   data = []

2. ДИНАМИЧЕСКИЙ ПОИСК ЗАГОЛОВКОВ (SCANNER):
   - HEADER_ROW = None
   - Пройди циклом по `row` от 1 до 100.
   - Внутри цикла собери значения ячеек `sheet.cell(row, c).value` для `c` от 1 до 50 в единую строку `row_text` (приведи к верхнему регистру, заменяя None на "").
   - Ключевые слова: ["DESCRIPTION", "MANUFACTURER", "PART NUMBER", "TOTAL", "QTY", "QUANTITY", "MEASURE", "U.O.M"]
   - Посчитай, сколько уникальных ключевых слов из списка присутствует в `row_text`.
   - Если >= 3 -> HEADER_ROW = row; break.

   - Если HEADER_ROW is None -> return []

   - WALL_COL = None
   - Пройди циклом по `c` от 1 до sheet.max_column.
   - val = str(sheet.cell(HEADER_ROW, c).value or "").upper()
   - Если "DESCRIPTION" in val or "MEASURE" in val or "ITEM" in val or "POS" in val -> WALL_COL = c; break.

3. ПОИСК СТРОК МЕТАДАННЫХ (TAGS, SERIAL, MODEL):
   - TAG_ROW_IDX = None; SERIAL_ROW_IDX = None; MODEL_ROW_IDX = None
   - Если HEADER_ROW is not None:
       - Сканируем строки `row` от 1 до HEADER_ROW (включительно).
       - Собери значения ячеек `sheet.cell(row, c).value` для `c` от 1 до 15 в единую строку `row_str` (в верхнем регистре, заменяя None на "").
       - Если TAG_ROW_IDX is None and "EQUIPMENT" in row_str and "TAG" in row_str: TAG_ROW_IDX = row
       - Если "SERIAL" in row_str and "NUMBER" in row_str: SERIAL_ROW_IDX = row
       - Если "MODEL" in row_str: MODEL_ROW_IDX = row
       - Если TAG_ROW_IDX is None and "TAG" in row_str: TAG_ROW_IDX = row

   if HEADER_ROW is None or WALL_COL is None or TAG_ROW_IDX is None or SERIAL_ROW_IDX is None or MODEL_ROW_IDX is None:
       return []

4. ДИНАМИЧЕСКОЕ СОПОСТАВЛЕНИЕ КОЛОНОК (SMART MAPPING):
   - cols = {{}}
   - header_texts = {{}} 
   - start_scan_col = max(1, WALL_COL - 2)

   - Пройди по колонкам col от start_scan_col до sheet.max_column.
   - header_text = объединение строк (max(1, HEADER_ROW - 2)) до (HEADER_ROW + 3).
   - val = header_text.upper().replace("\\n", " ").replace("\\r", " ").strip()
   - while "  " in val: val = val.replace("  ", " ")
   - header_texts[col] = val

   - ЛОГИКА ЗАПОЛНЕНИЯ:
     if "MANUFACTURER NAME" in val: cols['manuf'] = col
     if "UNIT" in val and "PRICE" in val and "TOTAL" not in val: cols['price'] = col
     if "TRUE" in val and "MANUFACTURER" in val: cols['true_part'] = col
     if "MEASURE" in val or "U.O.M" in val: cols['uom'] = col

     if "DESCRIPTION" in val: cols['desc'] = col
     if "LEAD" in val: cols['lead'] = col
     if "WAREHOUSE" in val or "SAP PART" in val: cols['warehouse'] = col
     if ("CHECK" in val or "MATERIAL" in val) and "DESCRIPTION" not in val: cols['check'] = col
     if "CURRENCY" in val: cols['currency'] = col
     if "VENDOR DWG" in val or "VENDOR CATALOG" in val: cols['vendor_dwg'] = col
     if "OPERATING SPARE" in val: cols['op_spares'] = col
     if "TOTAL" in val and "IDENTICAL" in val: cols['total_identical'] = col
     if "ORIGINAL" in val and "PURCHASE ORDER" in val: cols['orig_po_part'] = col
     if "CAPITAL" in val and "SPARE" in val: cols['cap_spares'] = col
     if "COMMISSIONING" in val and "SPARE" in val: cols['comm_spares'] = col
     if "RECOMMENDED" in val and "MANUFACTURER" in val: cols['rec_qty'] = col
     if "CONTRACTOR" in val and "REVIEW" in val: cols['cont_review'] = col
     if "APPROVED" in val and "QUANTITY" in val: 
         cols['appr_qty_cat1'] = col
         cols['appr_qty_cat3'] = col + 1
         cols['appr_qty_cat4'] = col + 2

     if 'manuf' not in cols and "MANUFACTURER" in val:
         forbidden = ["TRUE", "PART", "TOTAL", "RECOMMENDED", "QTY", "NO", "DWG", "ID"]
         if not any(bad_word in val for bad_word in forbidden):
             cols['manuf'] = col

5. ПОИСК И РАЗДЕЛЕНИЕ ТЕГОВ (FINAL ROBUST PARSER):
   - tag_map = {{}} 
   - last_valid_tags = None 

   - Иди по колонкам col от 1 до WALL_COL (строго < WALL_COL).
   - val_raw = sheet.cell(TAG_ROW_IDX, col).value
   - val_str = str(val_raw).strip() if val_raw else ""

   - skip_col = False
   - if any(x in val_str.upper() for x in ["DATE", "REV", "VENDOR", "SHEET", "ORDER", "PROJECT"]):
         last_valid_tags = None; skip_col = True

   - Если not skip_col:
       if not val_str and last_valid_tags:
           tag_map[col] = last_valid_tags
       elif val_str:
           tags = parse_tag_cell(val_str) # ВЫЗОВ ИМПОРТИРОВАННОЙ ФУНКЦИИ
           valid_tags = [t for t in tags if not (len(t) < 3 and t.isdigit())]
           if valid_tags:
               tag_map[col] = valid_tags
               last_valid_tags = valid_tags
           else:
               last_valid_tags = None

6. СБОР ДАННЫХ (SMART MERGE С ПОДДЕРЖКОЙ MULTI-SERIAL):
   - DATA_START = HEADER_ROW + 1
   - Если "desc" не найден в cols -> return []
   - last_created_items = [] 

   - lead_is_weeks = False
   - if 'lead' in cols:
         ht = header_texts.get(cols['lead'], "").upper()
         if "WEEK" in ht: lead_is_weeks = True

   - Иди от DATA_START до sheet.max_row.
   - desc_val = sheet.cell(row, cols["desc"]).value
   - desc_str = str(desc_val).strip() if desc_val else ""

   - if not desc_str: continue
   - if "TOTAL" in desc_str.upper() or "PAGE" in desc_str.upper(): last_created_items = []; continue
   - clean_desc = desc_str.replace(".0", "").replace(".", "")
   - if clean_desc.isdigit(): continue

   - row_has_qty = False
   - current_row_items = []

   - has_metadata = False
   - if 'manuf' in cols and sheet.cell(row, cols['manuf']).value: has_metadata = True
   - if 'uom' in cols and sheet.cell(row, cols['uom']).value: has_metadata = True

   - Иди по элементам tag_map (col, tags_list):
     - qty_val = sheet.cell(row, col).value
     - try: qty = float(qty_val) except: qty = 0

     - Если qty > 0:
       - row_has_qty = True
       - serial_raw = sheet.cell(SERIAL_ROW_IDX, col).value if SERIAL_ROW_IDX else None
       - serials_expanded = split_metadata_cell(serial_raw, len(tags_list)) # ВЫЗОВ ИМПОРТИРОВАННОЙ ФУНКЦИИ
       - model = sheet.cell(MODEL_ROW_IDX, col).value if MODEL_ROW_IDX else None

       curr = "USD"
       if 'currency' in cols: curr = sheet.cell(row, cols['currency']).value
       elif 'price' in cols:
           price_header = header_texts.get(cols['price'], "")
           if "EUR" in price_header: curr = "EUR"
           elif "USD" in price_header: curr = "USD"

       lead_val = sheet.cell(row, cols['lead']).value if 'lead' in cols else None
       if lead_val is not None and lead_is_weeks:
           try: lead_val = float(lead_val) * 7
           except: pass 

       for i, tag_name in enumerate(tags_list):
            item = {{
               "equipment_tag": tag_name, 
               "serial_number": serials_expanded[i],   
               "model": model,            
               "quantity": qty,          
               "description": desc_str, 
               "uom": sheet.cell(row, cols['uom']).value if 'uom' in cols else None,
               "manufacturer": sheet.cell(row, cols['manuf']).value if 'manuf' in cols else None,
               "true_part_number": sheet.cell(row, cols['true_part']).value if 'true_part' in cols else None,
               "unit_price": sheet.cell(row, cols['price']).value if 'price' in cols else None,
               "warehouse_number": sheet.cell(row, cols['warehouse']).value if 'warehouse' in cols else None,
               "lead_time": lead_val,
               "material_check": sheet.cell(row, cols['check']).value if 'check' in cols else None,
               "currency": curr,
               "vendor_dwg": sheet.cell(row, cols['vendor_dwg']).value if 'vendor_dwg' in cols else None,
               "operating_spare_parts": sheet.cell(row, cols['op_spares']).value if 'op_spares' in cols else None,
               "total_identical_parts": sheet.cell(row, cols['total_identical']).value if 'total_identical' in cols else None,
               "original_po_part_number": sheet.cell(row, cols['orig_po_part']).value if 'orig_po_part' in cols else None,
               "capital_spare_parts": sheet.cell(row, cols['cap_spares']).value if 'cap_spares' in cols else None,
               "commissioning_spare_parts": sheet.cell(row, cols['comm_spares']).value if 'comm_spares' in cols else None,
               "recommended_by_manufacturer": sheet.cell(row, cols['rec_qty']).value if 'rec_qty' in cols else None,
               "contractor_review": sheet.cell(row, cols['cont_review']).value if 'cont_review' in cols else None,
               "appr_qty_cat1": sheet.cell(row, cols['appr_qty_cat1']).value if 'appr_qty_cat1' in cols else None,
               "appr_qty_cat3": sheet.cell(row, cols['appr_qty_cat3']).value if 'appr_qty_cat3' in cols else None,
               "appr_qty_cat4": sheet.cell(row, cols['appr_qty_cat4']).value if 'appr_qty_cat4' in cols else None
            }}
           data.append(item)
           current_row_items.append(item)

   - Если row_has_qty == True:
       last_created_items = current_row_items

   - Иначе (Если row_has_qty == False):
       if last_created_items and desc_str and not has_metadata:
           for item in last_created_items:
               item["description"] += " " + desc_str
       elif has_metadata:
           last_created_items = []

7. ВОЗВРАТ: data

ВХОДНОЙ JSON:
{context_data}
"""
