"""Builds tiny text PDFs for tests. Content is labeled FIXTURE and is not real legal text."""


def _escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str]) -> bytes:
    """One-page PDF with one text line per entry (empty list = a page with no text, like a scan)."""
    shown = " ".join(f"({_escape(line)}) Tj T*" for line in lines)
    content = f"BT /F1 11 Tf 14 TL 50 800 Td {shown} ET" if lines else ""
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


FIXTURE_LINES = [
    "[FIXTURE] PERATURAN CONTOH NOMOR 1 TAHUN 2026",
    "TENTANG PAJAK ATAS SEWA UNTUK KEPERLUAN PENGUJIAN",
    "Pasal 1",
    "Atas penghasilan berupa sewa dipotong pajak sebesar sepuluh persen dari jumlah bruto.",
    "Pasal 2",
    "Pemotongan dilakukan oleh penyewa yang ditunjuk sebagai pemotong pajak.",
]
