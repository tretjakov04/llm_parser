import os
import zipfile
import pandas as pd
import io
from typing import List
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from fastapi import APIRouter, Body

from app.api.schemas.schemas import CommitPayload
from app.services.parser_service.parser_service import process_excel_file
from app.services.inventory_service.inventory_parser import (
    get_inventory_data,
    commit_to_inventory,
    remove_existing_records,
)
from app.db.database import get_db, SessionLocal
from app.db.models import Doc
from datetime import datetime
from fastapi import UploadFile, File, HTTPException, Depends
from app.db.models import Doc, MasterList, MasterListItem
from app.services.inventory_service.inventory_parser import remove_existing_records

router = APIRouter(prefix="/parser", tags=["Excel Parser"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def process_file_background(file_path: str, original_filename: str):
    db = SessionLocal()
    try:
        preview_data = await process_excel_file(file_path, original_filename, db)
        doc = db.query(Doc).filter(Doc.file_name == original_filename).first()
        if doc:
            if preview_data:
                remove_existing_records(original_filename, db)
                commit_to_inventory(preview_data, db)
                doc.status = "not approved"
                doc.parsed_data = preview_data
            else:
                doc.status = "error"
        db.commit()
    except Exception as e:
        db.rollback()
        doc = db.query(Doc).filter(Doc.file_name == original_filename).first()
        if doc:
            doc.status = "error"
            db.commit()
        print(f"Ошибка фоновой обработки: {e}")
    finally:
        db.close()


@router.post("/upload/bulk/")
def upload_bulk(
    rename: bool = False,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    valid_files = [f for f in files if f.filename.endswith((".xlsx", ".xls"))]
    conflicts = []

    if not rename:
        for file in valid_files:
            if db.query(Doc).filter(Doc.file_name == file.filename).first():
                conflicts.append(file.filename)

        if conflicts:
            return {
                "status": "conflict",
                "conflicts": conflicts,
                "message": "Некоторые файлы уже существуют",
            }

    uploaded_files = []
    for file in valid_files:
        final_filename = file.filename
        existing_doc = db.query(Doc).filter(Doc.file_name == final_filename).first()

        if existing_doc and rename:
            name_only, ext = os.path.splitext(final_filename)
            counter = 1
            while True:
                new_filename = f"{name_only} copy {counter}{ext}"
                is_in_db = (
                    db.query(Doc).filter(Doc.file_name == new_filename).first()
                    is not None
                )
                is_in_fs = os.path.exists(os.path.join(UPLOAD_DIR, new_filename))
                if not is_in_db and not is_in_fs:
                    final_filename = new_filename
                    break
                counter += 1

        file_path = os.path.join(UPLOAD_DIR, final_filename)
        file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        doc = Doc(file_name=final_filename, status="uploaded")
        db.add(doc)
        uploaded_files.append(final_filename)

    db.commit()
    return {"status": "success", "message": f"Загружено файлов: {len(uploaded_files)}"}


@router.post("/upload/zip/")
def upload_zip(
    rename: bool = False,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Поддерживаются только .zip архивы")

    file_bytes = file.file.read()
    conflicts = []
    uploaded_files = []

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        valid_items = [
            item
            for item in archive.namelist()
            if item.endswith((".xlsx", ".xls"))
            and not item.startswith("__MACOSX")
            and "/." not in item
        ]

        if not rename:
            for item in valid_items:
                filename = os.path.basename(item)
                if db.query(Doc).filter(Doc.file_name == filename).first():
                    conflicts.append(filename)

            if conflicts:
                return {
                    "status": "conflict",
                    "conflicts": conflicts,
                    "message": "Файлы из архива уже существуют",
                }

        for item in valid_items:
            filename = os.path.basename(item)
            final_filename = filename
            existing_doc = db.query(Doc).filter(Doc.file_name == filename).first()

            if existing_doc and rename:
                name_only, ext = os.path.splitext(filename)
                counter = 1
                while True:
                    new_filename = f"{name_only} copy {counter}{ext}"
                    is_in_db = (
                        db.query(Doc).filter(Doc.file_name == new_filename).first()
                        is not None
                    )
                    is_in_fs = os.path.exists(os.path.join(UPLOAD_DIR, new_filename))
                    if not is_in_db and not is_in_fs:
                        final_filename = new_filename
                        break
                    counter += 1

            file_path = os.path.join(UPLOAD_DIR, final_filename)
            with open(file_path, "wb") as f_out:
                f_out.write(archive.read(item))

            doc = Doc(file_name=final_filename, status="uploaded")
            db.add(doc)
            uploaded_files.append(final_filename)

    db.commit()
    return {
        "status": "success",
        "message": f"Архив распакован. Загружено файлов: {len(uploaded_files)}",
    }


@router.post("/master-lists/upload/")
def upload_master_list(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Только Excel файлы")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name_only, ext = os.path.splitext(file.filename)
    new_filename = f"{name_only}_{timestamp}{ext}"

    try:
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        if "file_name" not in df.columns or "Process" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="Файл должен содержать колонки 'file_name' и 'Process'",
            )

        new_master = MasterList(name=new_filename)
        db.add(new_master)
        db.commit()
        db.refresh(new_master)

        items_to_add = []
        for _, row in df.iterrows():
            item = MasterListItem(
                master_list_id=new_master.id,
                file_name=str(row["file_name"]).strip(),
                process=str(row["Process"]).strip().lower(),
            )
            items_to_add.append(item)

        db.add_all(items_to_add)
        db.commit()

        return {
            "status": "success",
            "message": "Мастер-лист успешно загружен",
            "name": new_filename,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/master-lists/")
def get_master_lists(db: Session = Depends(get_db)):
    lists = db.query(MasterList).order_by(MasterList.uploaded_at.desc()).all()
    result = []
    for lst in lists:
        items = (
            db.query(MasterListItem)
            .filter(MasterListItem.master_list_id == lst.id)
            .all()
        )
        result.append(
            {
                "id": lst.id,
                "name": lst.name,
                "uploaded_at": lst.uploaded_at,
                "items": [
                    {"file_name": i.file_name, "process": i.process} for i in items
                ],
            }
        )
    return {"status": "success", "data": result}


@router.post("/upload/")
def upload_excel(
    rename: bool = False,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400, detail="Только файлы .xlsx или .xls поддерживаются"
        )

    final_filename = file.filename

    existing_doc = db.query(Doc).filter(Doc.file_name == final_filename).first()

    if existing_doc:
        if not rename:
            raise HTTPException(
                status_code=409, detail="Файл с таким именем уже существует"
            )

        name_only, ext = os.path.splitext(final_filename)
        counter = 1
        while True:
            new_filename = f"{name_only} copy {counter}{ext}"
            is_in_db = (
                db.query(Doc).filter(Doc.file_name == new_filename).first() is not None
            )
            is_in_fs = os.path.exists(os.path.join(UPLOAD_DIR, new_filename))

            if not is_in_db and not is_in_fs:
                final_filename = new_filename
                break
            counter += 1

    file_path = os.path.join(UPLOAD_DIR, final_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = Doc(file_name=final_filename, status="uploaded")
    db.add(doc)
    db.commit()

    return {"status": "success", "message": f"Файл '{final_filename}' успешно загружен"}


@router.post("/docs/{file_name}/parse")
def start_parsing(
    file_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    doc = db.query(Doc).filter(Doc.file_name == file_name).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="Исходный файл физически не найден на сервере"
        )

    doc.status = "processing"
    db.commit()

    background_tasks.add_task(process_file_background, file_path, file_name)

    return {"status": "success", "message": "Парсер успешно запущен"}


@router.get("/docs/{file_name}/download")
def download_original_file(file_name: str):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/docs/")
def view_docs(db: Session = Depends(get_db)):
    try:
        docs = db.query(Doc).order_by(Doc.last_update.desc()).all()
        result = [
            {
                "file_name": d.file_name,
                "status": d.status,
                "last_update": (
                    d.last_update.strftime("%Y-%m-%d %H:%M:%S") if d.last_update else ""
                ),
            }
            for d in docs
        ]
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/docs/{file_name}/data")
def get_doc_data(file_name: str, db: Session = Depends(get_db)):
    doc = db.query(Doc).filter(Doc.file_name == file_name).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return {"status": "success", "data": doc.parsed_data or []}


@router.post("/docs/{file_name}/save")
def save_doc_changes(
    file_name: str, payload: CommitPayload, db: Session = Depends(get_db)
):
    doc = db.query(Doc).filter(Doc.file_name == file_name).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    data_as_dicts = [item.model_dump() for item in payload]

    remove_existing_records(file_name, db)
    commit_to_inventory(data_as_dicts, db)

    doc.parsed_data = data_as_dicts
    db.commit()
    return {"status": "success", "message": "Данные сохранены в инвентарь"}


@router.post("/docs/{file_name}/approve")
def approve_doc(file_name: str, db: Session = Depends(get_db)):
    from app.db.models import Material, Equipment

    doc = db.query(Doc).filter(Doc.file_name == file_name).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    doc.status = "approved"

    if doc.parsed_data:
        updated_data = []
        for item in doc.parsed_data:
            item["approved"] = True
            updated_data.append(item)

        doc.parsed_data = updated_data

        flag_modified(doc, "parsed_data")

    db.query(Material).filter(Material.file_name == file_name).update(
        {"approved": True}
    )

    equipments = db.query(Equipment).all()
    for eq in equipments:
        if isinstance(eq.eq_file_name, list) and file_name in eq.eq_file_name:
            eq.approved = True
        elif eq.eq_file_name == file_name:
            eq.approved = True

    db.commit()
    return {"status": "success"}


@router.get("/inventory/")
def view_inventory(db: Session = Depends(get_db)):
    try:
        data = get_inventory_data(db)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/docs/{file_name}")
async def delete_document(file_name: str, db: Session = Depends(get_db)):

    doc = db.query(Doc).filter(Doc.file_name == file_name).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        remove_existing_records(file_name, db)

        db.delete(doc)
        db.commit()

        file_path = os.path.join("uploads", file_name)
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "status": "success",
            "message": f"Document '{file_name}' and all associated data were successfully deleted.",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}"
        )
