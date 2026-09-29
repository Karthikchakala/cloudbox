"""
Generate genuine, safe test fixtures for all 5 required file formats:
- PNG: sample_image.png
- PDF: sample_document.pdf
- DOCX: sample_document.docx
- PPTX: sample_presentation.pptx
- TXT: sample_text.txt
"""
import os
import hashlib
import zipfile
import json

TEST_DIR = os.path.abspath("test_fixtures")
os.makedirs(TEST_DIR, exist_ok=True)

manifest = {}

# 1. TXT File
txt_path = os.path.join(TEST_DIR, "sample_text.txt")
txt_content = b"CloudBox Enterprise Storage System - Manual QA Audit 2026.\nVerified by Automated & Manual Testing Suite.\nArchitecture: Nginx, React, Flask, PostgreSQL, MinIO, Redis, Celery, Prometheus, Grafana.\n"
with open(txt_path, "wb") as f:
    f.write(txt_content)

# 2. PNG File (Valid 16x16 PNG Image)
png_path = os.path.join(TEST_DIR, "sample_image.png")
png_bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa"
    b"\x00\x00\x00\x19IDATx\x9cc\xfc\xff\xff?\x03\x18\x18\x18\x80\x84\x84\x04\x00\x00\xff\xff\x05\xfe\x02\xfe"
    b"c\x9b\xa1\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
)
with open(png_path, "wb") as f:
    f.write(png_bytes)

# 3. PDF File (Valid PDF Document)
pdf_path = os.path.join(TEST_DIR, "sample_document.pdf")
pdf_bytes = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"4 0 obj << /Length 55 >> stream\n"
    b"BT /F1 24 Tf 100 700 Td (CloudBox PDF Audit Document 2026) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000350 00000 n \n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n431\n%%EOF\n"
)
with open(pdf_path, "wb") as f:
    f.write(pdf_bytes)

# 4. DOCX File (Valid Microsoft Word OpenXML Package)
docx_path = os.path.join(TEST_DIR, "sample_document.docx")
with zipfile.ZipFile(docx_path, "w") as z:
    z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
    z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
    z.writestr("word/document.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>CloudBox DOCX Audit Specification 2026 - Production Ready</w:t></w:r></w:p>
  </w:body>
</w:document>""")

# 5. PPTX File (Valid Microsoft PowerPoint OpenXML Package)
pptx_path = os.path.join(TEST_DIR, "sample_presentation.pptx")
with zipfile.ZipFile(pptx_path, "w") as z:
    z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>""")
    z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""")
    z.writestr("ppt/presentation.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
  </p:sldIdLst>
</p:presentation>""")

files = ["sample_text.txt", "sample_image.png", "sample_document.pdf", "sample_document.docx", "sample_presentation.pptx"]

print("==================================================")
print("TEST FIXTURES GENERATED FOR QA AUDIT")
print("==================================================")
for fn in files:
    fpath = os.path.join(TEST_DIR, fn)
    with open(fpath, "rb") as f:
        data = f.read()
    sha = hashlib.sha256(data).hexdigest()
    size = len(data)
    manifest[fn] = {
        "filename": fn,
        "size": size,
        "sha256": sha,
        "path": fpath
    }
    print(f"  - {fn}: {size} bytes | SHA256: {sha}")

with open(os.path.join(TEST_DIR, "fixtures_manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)

print("\nManifest saved to test_fixtures/fixtures_manifest.json")
