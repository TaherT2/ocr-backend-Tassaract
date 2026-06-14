from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from ocr_engine import process_pdf
from pdf_editor import rebuild_pdf

app = FastAPI()

pdf_bytes_store = None
ocr_store = None


class EditRequest(BaseModel):
    block_id: int
    new_text: str


@app.get("/")
def home():
    return {"status": "Tesseract OCR + PDF Editor running"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    global pdf_bytes_store, ocr_store

    pdf_bytes_store = await file.read()
    ocr_store = process_pdf(pdf_bytes_store)

    return ocr_store


@app.post("/edit")
def edit_block(request: EditRequest):
    global ocr_store

    if not ocr_store:
        return {"error": "No PDF loaded"}

    for page in ocr_store["pages"]:
        for block in page["blocks"]:
            if block["id"] == request.block_id:
                block["edited_text"] = request.new_text
                return {
                    "success": True,
                    "block_id": request.block_id,
                    "old_text": block["text"],
                    "new_text": request.new_text
                }

    return {"error": "Block not found"}


@app.get("/export")
def export_pdf():
    global pdf_bytes_store, ocr_store

    if not pdf_bytes_store or not ocr_store:
        return {"error": "No PDF loaded"}

    final_pdf = rebuild_pdf(pdf_bytes_store, ocr_store)

    return Response(
        content=final_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=edited.pdf"}
    )
