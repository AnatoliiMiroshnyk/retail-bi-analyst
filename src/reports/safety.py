"""Context-specific escaping and atomic, same-directory report replacement."""
import json
import os
import tempfile
from html import escape
from pathlib import Path


def script_json(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False)
            .replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def markdown_cell(value):
    # Numeric entities preserve literal symbols and cannot split a Markdown row.
    return (escape(str(value), quote=True).replace('\\', '&#92;')
            .replace('|', '&#124;').replace('`', '&#96;').replace('*','&#42;')
            .replace('_','&#95;').replace('[','&#91;').replace(']','&#93;')
            .replace('\r\n','\n').replace('\r','\n').replace('\n','<br>'))


def atomic_write(path, writer):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+path.stem+'_', suffix=path.suffix, delete=False) as handle:
            temporary = Path(handle.name)
        writer(temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_text_report(path, content):
    atomic_write(path, lambda target: target.write_text(content, encoding='utf-8'))
