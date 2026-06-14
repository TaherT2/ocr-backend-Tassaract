import fitz
import pytesseract
from PIL import Image
import arabic_reshaper
from bidi.algorithm import get_display
import tempfile


def detect_script(text):
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"


def clean_text(text):
    return "".join(ch for ch in text if ord(ch) >= 32).strip()


def fix_arabic(text):
    # Proper Arabic shaping + RTL fix
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def build_block(block_id, text, bbox, script, confidence, source):
    x0, y0, x1, y1 = bbox

    width = x1 - x0
    height = y1 - y0

    return {
        "id": block_id,
        "text": text,
        "box": bbox,

        "x": x0,
        "y": y0,
        "width": width,
        "height": height,

        "center_x": x0 + width / 2,
        "center_y": y0 + height / 2,

        "script": script,
        "confidence": confidence,
        "source": source,
        "editable": True
    }


def process_pdf(pdf_bytes):
    result = {"pages": []}

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []

        text_dict = page.get_text("dict")
        has_real_text = False

        # -------------------------
        # PDF text extraction
        # -------------------------
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = clean_text(span.get("text", ""))

                    if not text:
                        continue

                    has_real_text = True
                    script = detect_script(text)

                    blocks.append(build_block(
                        block_id,
                        text,
                        span["bbox"],
                        script,
                        1.0,
                        "pdf"
                    ))
                    block_id += 1

        # -------------------------
        # OCR fallback (Tesseract)
        # -------------------------
        if not has_real_text:
            print(f"Page {page_index + 1}: OCR fallback (Tesseract)")

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                pix.save(tmp.name)

                image = Image.open(tmp.name)

                data = pytesseract.image_to_data(
                    image,
                    lang="ara+eng",
                    output_type=pytesseract.Output.DICT
                )

                for i in range(len(data["text"])):
                    text = clean_text(data["text"][i])

                    if not text:
                        continue

                    x = data["left"][i]
                    y = data["top"][i]
                    w = data["width"][i]
                    h = data["height"][i]

                    bbox = [x, y, x + w, y + h]
                    script = detect_script(text)

                    if script == "arabic":
                        text = fix_arabic(text)

                    blocks.append(build_block(
                        block_id,
                        text,
                        bbox,
                        script,
                        data["conf"][i] / 100,
                        "ocr"
                    ))
                    block_id += 1

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    pdf.close()
    return result
