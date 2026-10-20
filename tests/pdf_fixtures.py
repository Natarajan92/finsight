"""Small authored PDFs generated in tests, without binary fixtures or extra dependencies."""

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def write_pdf(path: Path, texts: list[str | None], *, encrypted: bool = False) -> Path:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        if text is not None:
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 740 Td ({escaped}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("fixture-password")
    path.parent.mkdir(parents=True, exist_ok=True)
    writer.write(path)
    return path


def add_valid_pdfs(data_dir: Path) -> Path:
    write_pdf(
        data_dir / "pdfs/AMD_2022_10K.pdf",
        ["Revenue: $12 million. Operating loss: (1,234).", None, "Cash flow: 7.5%."],
    )
    write_pdf(data_dir / "pdfs/OTHER_2023_10K.pdf", ["Other company revenue: $42."])
    return data_dir
