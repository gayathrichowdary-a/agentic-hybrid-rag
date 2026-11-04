from docx import Document
from docx.oxml.ns import qn
from langchain.schema import Document as LangDocument

_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _lines_from(root):
    """Return the text lines under `root` in reading order.

    Covers normal paragraphs, table cells and text boxes. Text boxes are stored
    twice in Word files (a modern copy and a fallback copy), so the fallback
    copy is skipped to avoid duplicated text.
    """
    groups = {}
    order = []
    for node in root.iter(qn("w:t"), qn("w:tab")):
        paragraph = None
        skip = False
        ancestor = node.getparent()
        while ancestor is not None:
            if ancestor.tag == _FALLBACK:
                skip = True
                break
            if paragraph is None and ancestor.tag == qn("w:p"):
                paragraph = ancestor
            ancestor = ancestor.getparent()
        if skip or paragraph is None:
            continue
        if paragraph not in groups:
            groups[paragraph] = []
            order.append(paragraph)
        groups[paragraph].append("\t" if node.tag == qn("w:tab") else (node.text or ""))

    lines = []
    for paragraph in order:
        line = "".join(groups[paragraph]).strip()
        if line:
            lines.append(line)
    return lines


def load_docx(file_path):
    doc = Document(file_path)

    lines = _lines_from(doc.element.body)

    # Headers and footers (skip repeats, since sections often share them).
    seen = set(lines)
    for section in doc.sections:
        for part in (section.header, section.footer):
            for line in _lines_from(part._element):
                if line not in seen:
                    seen.add(line)
                    lines.append(line)

    return [
        LangDocument(
            page_content="\n".join(lines)
        )
    ]