from __future__ import annotations
import hashlib
import io
import re
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
from ecotrace.core.ai.providers import detect_language
from ecotrace.core.ai_constants import DOCUMENT_TYPES
from ecotrace.modules.knowledge.application.chunking import clean_text

def detect_document_type(file_name: str, content_type: str, text: str) -> str:
    lower = file_name.lower()
    blob = f'{lower} {content_type} {text[:500].lower()}'
    mapping = [('policy', ('policy', 'politika')), ('procedure', ('procedure', 'prosedür', 'procedure')), ('report', ('report', 'rapor')), ('meeting_notes', ('meeting', 'toplanti', 'minutes')), ('supplier_document', ('supplier', 'tedarik')), ('manual', ('manual', 'kilavuz')), ('training', ('training', 'egitim')), ('technical', ('technical', 'teknik')), ('passport_document', ('passport', 'dpp')), ('invoice', ('invoice', 'fatura')), ('certificate', ('certificate', 'sertifika'))]
    for doc_type, keys in mapping:
        if any((k in blob for k in keys)):
            return doc_type if doc_type in DOCUMENT_TYPES else 'other'
    return 'other'

def extract_text_from_bytes(*, content: bytes, file_name: str, content_type: str, ocr_engine: Any | None=None) -> tuple[str, dict[str, Any]]:
    name = file_name.lower()
    meta: dict[str, Any] = {'extractor': 'raw'}
    text = ''
    if name.endswith('.zip') or content_type == 'application/zip':
        text, meta = _extract_zip(content, ocr_engine=ocr_engine)
    elif name.endswith('.eml') or content_type == 'message/rfc822':
        text, meta = _extract_eml(content)
    elif name.endswith(('.md', '.txt', '.csv', '.html', '.htm', '.json', '.xml')):
        text = content.decode('utf-8', errors='ignore')
        meta['extractor'] = Path(name).suffix.lstrip('.') or 'text'
    elif name.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp', '.gif')):
        if ocr_engine is not None:
            text = ocr_engine.extract_text(content=content, content_type=content_type, file_name=file_name)
            meta['extractor'] = getattr(ocr_engine, 'name', 'ocr')
        else:
            text = ''
            meta['extractor'] = 'ocr_unavailable'
    elif name.endswith('.pdf'):
        text = _extract_pdf(content)
        meta['extractor'] = 'pdf'
        if not text.strip() and ocr_engine is not None:
            text = ocr_engine.extract_text(content=content, content_type=content_type, file_name=file_name)
            meta['extractor'] = 'pdf+ocr'
    elif name.endswith('.docx'):
        text = _extract_docx(content)
        meta['extractor'] = 'docx'
    elif name.endswith('.pptx'):
        text = _extract_pptx(content)
        meta['extractor'] = 'pptx'
    elif name.endswith('.xlsx'):
        text = _extract_xlsx(content)
        meta['extractor'] = 'xlsx'
    else:
        text = content.decode('utf-8', errors='ignore')
        meta['extractor'] = 'fallback_utf8'
    cleaned = clean_text(text)
    meta['language'] = detect_language(cleaned)
    meta['char_count'] = len(cleaned)
    meta['document_type'] = detect_document_type(file_name, content_type, cleaned)
    return (cleaned, meta)

def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub('[^a-z0-9çğıöşü]+', '-', value)
    value = re.sub('-+', '-', value).strip('-')
    return value[:200] or 'document'

def _extract_zip(content: bytes, *, ocr_engine: Any | None) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for info in zf.infolist()[:50]:
            if info.is_dir():
                continue
            data = zf.read(info)
            text, _ = extract_text_from_bytes(content=data, file_name=info.filename, content_type='application/octet-stream', ocr_engine=ocr_engine)
            if text:
                parts.append(f'# {info.filename}\n{text}')
    return ('\n\n'.join(parts), {'extractor': 'zip', 'files': len(parts)})

def _extract_eml(content: bytes) -> tuple[str, dict[str, Any]]:
    msg = BytesParser(policy=policy.default).parsebytes(content)
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body += part.get_content() + '\n'
    else:
        body = str(msg.get_content())
    headers = f"Subject: {msg.get('subject')}\nFrom: {msg.get('from')}\nTo: {msg.get('to')}\n"
    return (clean_text(headers + '\n' + body), {'extractor': 'eml'})

def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return '\n'.join((page.extract_text() or '' for page in reader.pages))
    except Exception:
        return content.decode('latin-1', errors='ignore')

def _extract_docx(content: bytes) -> str:
    try:
        import zipfile as zf
        with zf.ZipFile(io.BytesIO(content)) as archive:
            xml = archive.read('word/document.xml').decode('utf-8', errors='ignore')
        return clean_text(re.sub('<[^>]+>', ' ', xml))
    except Exception:
        return content.decode('utf-8', errors='ignore')

def _extract_pptx(content: bytes) -> str:
    try:
        import zipfile as zf
        texts: list[str] = []
        with zf.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                    xml = archive.read(name).decode('utf-8', errors='ignore')
                    texts.append(re.sub('<[^>]+>', ' ', xml))
        return clean_text('\n'.join(texts))
    except Exception:
        return content.decode('utf-8', errors='ignore')

def _extract_xlsx(content: bytes) -> str:
    try:
        import zipfile as zf
        with zf.ZipFile(io.BytesIO(content)) as archive:
            shared = ''
            if 'xl/sharedStrings.xml' in archive.namelist():
                shared = archive.read('xl/sharedStrings.xml').decode('utf-8', errors='ignore')
            sheets = [archive.read(n).decode('utf-8', errors='ignore') for n in archive.namelist() if n.startswith('xl/worksheets/sheet')]
        blob = shared + '\n' + '\n'.join(sheets)
        return clean_text(re.sub('<[^>]+>', ' ', blob))
    except Exception:
        return content.decode('utf-8', errors='ignore')
