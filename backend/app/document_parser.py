"""Safe, multi-strategy text extraction for complaint documents."""
import email
import io
from email import policy

import docx
from pypdf import PdfReader


class DocumentExtractionError(ValueError):
    """An upload is valid, but its content cannot be read usefully."""


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    """Return readable document text or raise a user-safe extraction error."""
    if not content:
        raise DocumentExtractionError("The uploaded file is empty.")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if ext == "pdf":
            return _extract_pdf(content)
        if ext == "docx":
            return _extract_docx(content)
        if ext == "eml":
            return _extract_eml(content)
        return content.decode("utf-8", errors="ignore")
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("This document could not be read. Please upload a valid, unprotected file.") from exc


def _extract_pdf(content: bytes) -> str:
    """Extract selectable text, then OCR image-only pages when available."""
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentExtractionError("This PDF is password-protected. Remove the password and upload it again.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("This PDF is corrupt or uses an unsupported encoding.") from exc
    if text:
        return text
    ocr_text = _ocr_pdf(content)
    if ocr_text:
        return ocr_text
    raise DocumentExtractionError(
        "No readable text was found in this PDF. It appears to be a scanned/image PDF; "
        "enable the optional OCR dependencies or upload a searchable PDF."
    )


def _ocr_pdf(content: bytes) -> str:
    """OCR scans when PyMuPDF and the local Tesseract engine are installed."""
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
        document = fitz.open(stream=content, filetype="pdf")
        pages = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            pages.append(pytesseract.image_to_string(image))
        return "\n".join(pages).strip()
    except Exception:
        # Do not expose OCR-engine paths or internals to API users.
        return ""


def _extract_docx(content: bytes) -> str:
    document = docx.Document(io.BytesIO(content))
    parts = [paragraph.text for paragraph in document.paragraphs]
    # Complaint forms often put all values in tables, not paragraphs.
    for table in document.tables:
        for row in table.rows:
            parts.append(" ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def _extract_eml(content: bytes) -> str:
    msg = email.message_from_bytes(content, policy=policy.default)
    subject = msg.get("subject", "")
    sender = msg.get("from", "")
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                body_parts.append(part.get_content())
    else:
        body_parts.append(msg.get_content())
    body = "\n".join(body_parts)
    return f"From: {sender}\nSubject: {subject}\n\n{body}"
