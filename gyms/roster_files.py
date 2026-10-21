"""Bounded CSV/OpenXML reading and template-based exports; no macros or formulas."""
import csv
import io
import json
import posixpath
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from django.core.exceptions import ValidationError
from .roster_schema import SCHEMAS

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MAX_ROWS = 1500
MAX_BYTES = 4 * 1024 * 1024


def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValidationError('XML declarations are not supported.')
    return ET.fromstring(data)


def normalize_table(sheet, matrix, csv_source=False):
    if not matrix: raise ValidationError(f'{sheet}: missing header row.')
    headers = [str(v or '').strip().lower() for v in matrix[0]]
    while headers and not headers[-1]: headers.pop()
    if headers != SCHEMAS[sheet]:
        raise ValidationError(f'{sheet}: keep the template columns in their original order: {", ".join(SCHEMAS[sheet])}.')
    rows = []
    for index, values in enumerate(matrix[1:], 2):
        if not any(v not in ('', None) for v in values): continue
        if len(values) > len(headers) and any(values[len(headers):]):
            raise ValidationError(f'{sheet}, row {index}: data outside the template columns.')
        values = list(values) + [''] * max(0, len(headers)-len(values))
        row = {key: str(value or '').strip() for key,value in zip(headers, values)}
        if csv_source:
            row = {key: value[1:] if value.startswith("'") and value[1:].lstrip().startswith(('=', '+', '-', '@')) else value for key,value in row.items()}
        if any(len(value) > 2000 for value in row.values()): raise ValidationError('A cell exceeds 2,000 characters.')
        row.update(sheet=sheet, row=index)
        rows.append(row)
        if len(rows) > MAX_ROWS: raise ValidationError(f'Limit each import to {MAX_ROWS} people.')
    return rows


def parse_uploads(workbook=None, csv_files=None):
    rows = []
    try:
        if workbook:
            if not workbook.name.lower().endswith('.xlsx') or workbook.size > MAX_BYTES:
                raise ValidationError('Upload an .xlsx workbook up to 4 MB.')
            with zipfile.ZipFile(workbook) as archive:
                infos = archive.infolist()
                if len(infos)>120 or sum(info.file_size for info in infos)>16*1024*1024 or len({i.filename for i in infos}) != len(infos):
                    raise ValidationError('Workbook is too large or has duplicate internal files.')
                if any('vba' in i.filename.lower() or 'externallinks/' in i.filename.lower() for i in infos):
                    raise ValidationError('Macros and external workbook links are not supported.')
                book = xml(archive.read('xl/workbook.xml'))
                prop = book.find(f'{{{NS}}}workbookPr')
                is_1904 = prop is not None and prop.get('date1904') in ('1','true')
                relationships = {item.get('Id'): item.get('Target') for item in xml(archive.read('xl/_rels/workbook.xml.rels')) if item.get('TargetMode') != 'External'}
                shared = []
                if 'xl/sharedStrings.xml' in archive.namelist():
                    shared = [''.join(item.itertext()) for item in xml(archive.read('xl/sharedStrings.xml'))]
                seen = set()
                for sheet in book.find(f'{{{NS}}}sheets'):
                    name = sheet.get('name')
                    if name == 'Instructions': continue
                    if name not in SCHEMAS or name in seen: raise ValidationError('Use only the original roster tabs and Instructions tab.')
                    seen.add(name)
                    target = relationships.get(sheet.get(f'{{{REL}}}id'), '')
                    path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
                    if not path.startswith('xl/worksheets/'): raise ValidationError('Invalid worksheet reference.')
                    root = xml(archive.read(path)); matrix=[]
                    data = root.find(f'{{{NS}}}sheetData')
                    if data is None: raise ValidationError('Worksheet has no cells.')
                    for r in data:
                        if int(r.get('r', '1')) > MAX_ROWS+1: raise ValidationError(f'Limit each tab to {MAX_ROWS} people; remove unused formatted rows.')
                        values=[]
                        for cell in r:
                            if cell.find(f'{{{NS}}}f') is not None: raise ValidationError(f'{name}: replace formulas with values before importing.')
                            ref=cell.get('r','A1'); col=0
                            for letter in ref:
                                if letter.isalpha(): col=col*26+ord(letter.upper())-64
                            if not 1<=col<=30: raise ValidationError('Unexpected worksheet columns.')
                            while len(values)<col: values.append('')
                            text=cell.find(f'{{{NS}}}v'); value=text.text if text is not None else ''
                            kind=cell.get('t')
                            if kind=='s': value=shared[int(value)]
                            elif kind=='inlineStr': value=''.join(cell.find(f'{{{NS}}}is').itertext())
                            elif kind=='e': raise ValidationError(f'{name}: fix spreadsheet error cells before importing.')
                            elif name=='Athletes' and col==7 and value and kind not in ('str','d'):
                                number=float(value)
                                if number != int(number) or not 1<=number<=100000: raise ValidationError('Use whole dates of birth.')
                                value=((date(1904,1,1) if is_1904 else date(1899,12,30))+timedelta(days=int(number))).isoformat()
                            values[col-1]=value or ''
                        matrix.append(values)
                    rows.extend(normalize_table(name,matrix))
                if not seen: raise ValidationError('No roster tabs found.')
        else:
            for sheet, upload in (csv_files or {}).items():
                if upload:
                    if not upload.name.lower().endswith('.csv') or upload.size>MAX_BYTES: raise ValidationError('CSV files must be UTF-8 and no larger than 4 MB.')
                    text=upload.read(MAX_BYTES+1).decode('utf-8-sig')
                    if '\x00' in text: raise ValidationError('Invalid CSV content.')
                    matrix=[]
                    for row in csv.reader(io.StringIO(text)):
                        matrix.append(row)
                        if len(matrix)>MAX_ROWS+1: raise ValidationError(f'Limit each import to {MAX_ROWS} people.')
                    rows.extend(normalize_table(sheet,matrix,csv_source=True))
    except ValidationError: raise
    except (ValueError, KeyError, IndexError, TypeError, ET.ParseError, zipfile.BadZipFile, UnicodeError, csv.Error, OverflowError, OSError, AttributeError, RuntimeError, NotImplementedError) as error:
        raise ValidationError('This file could not be read. Download the template, paste values, and save it as .xlsx or UTF-8 CSV.') from error
    if not rows: raise ValidationError('Add at least one person before uploading.')
    if len(rows)>MAX_ROWS: raise ValidationError(f'Limit each import to {MAX_ROWS} people across all tabs.')
    return rows


def workbook_bytes(tables=None):
    """Fill the pre-authored workbook using literal OpenXML cells, never formulas."""
    template=Path(__file__).with_name('roster_template.xlsx.b64')
    import base64
    content=base64.b64decode(template.read_bytes())
    if tables is None: return content
    output=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as dest:
        book=xml(source.read('xl/workbook.xml'))
        rels={item.get('Id'):item.get('Target') for item in xml(source.read('xl/_rels/workbook.xml.rels'))}
        replacements={}
        for sheet in book.find(f'{{{NS}}}sheets'):
            name=sheet.get('name')
            if name not in tables: continue
            target=rels[sheet.get(f'{{{REL}}}id')]
            path=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
            root=xml(source.read(path)); data=root.find(f'{{{NS}}}sheetData')
            # Keep formatting and headers; replace only the data region.
            for child in list(data):
                if child.get('r')!='1': data.remove(child)
            for row_index, values in enumerate(tables[name],2):
                row=ET.SubElement(data,f'{{{NS}}}row',{'r':str(row_index)})
                for col,value in enumerate(values,1):
                    letters=''; n=col
                    while n: n,rem=divmod(n-1,26); letters=chr(65+rem)+letters
                    cell=ET.SubElement(row,f'{{{NS}}}c',{'r':f'{letters}{row_index}','t':'inlineStr'})
                    text=ET.SubElement(ET.SubElement(cell,f'{{{NS}}}is'),f'{{{NS}}}t')
                    text.text='' if value is None else str(value)
            dim=root.find(f'{{{NS}}}dimension')
            if dim is not None: dim.set('ref',f'A1:{chr(64+len(SCHEMAS[name]))}{max(1,len(tables[name])+1)}')
            replacements[path]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        for info in source.infolist(): dest.writestr(info.filename,replacements.get(info.filename,source.read(info.filename)))
    return output.getvalue()
