import fitz


def rebuild_pdf(original_pdf_bytes, ocr_data):
    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    for page_data in ocr_data["pages"]:
        page = pdf[page_data["page"] - 1]

        redactions = []

        for block in page_data["blocks"]:
            if "edited_text" not in block:
                continue

            x0, y0, x1, y1 = block["box"]
            rect = fitz.Rect(x0, y0, x1, y1)

            page.add_redact_annot(rect, fill=(1, 1, 1))
            redactions.append(block)

        if redactions:
            page.apply_redactions()

        for block in redactions:
            x0, y0, x1, y1 = block["box"]
            font_size = 12

            page.insert_text(
                (x0, y1),
                block["edited_text"],
                fontsize=font_size,
                fontname="helv",
                color=(0, 0, 0)
            )

    output = pdf.tobytes()
    pdf.close()
    return output
