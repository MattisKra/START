"""Decrypting and loading a case.

Decrypted case files are untrusted data: we only read them as text/images,
never execute anything from the extracted directory.
"""

import io
import mimetypes
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class Case:
    case_dir: Path
    policy: str
    description: str
    invoice_text: str
    images: list[Path] = field(default_factory=list)
    # (mime, bytes) per image, downscaled and re-encoded for the model APIs
    image_blobs: list[tuple[str, bytes]] = field(default_factory=list)


MAX_IMAGE_EDGE = 2000  # px, long edge
MAX_IMAGE_BYTES = 3_500_000  # raw bytes; base64 adds a third, API limits start at 5 MB


def prepare_image(path: Path) -> tuple[str, bytes] | None:
    """Downscale to MAX_IMAGE_EDGE and re-encode as JPEG. None if the image cannot be made small enough."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
            for quality in (85, 70, 50):
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=quality)
                if buf.tell() <= MAX_IMAGE_BYTES:
                    return "image/jpeg", buf.getvalue()
    except Exception as e:  # noqa: BLE001 - a bad photo must not cost the round
        print(f"image {path.name}: could not re-encode ({e!r})")
    raw = path.read_bytes()
    if len(raw) <= MAX_IMAGE_BYTES:
        return mimetypes.guess_type(path.name)[0] or "image/png", raw
    print(f"image {path.name}: too large ({len(raw)} bytes), sending the case without it")
    return None


def _sevenzip() -> str:
    exe = shutil.which("7zz") or shutil.which("7z")
    if not exe:
        raise RuntimeError("7-Zip not found (brew install sevenzip)")
    return exe


def extract_zip(zip_path: Path, password: str, dest: Path) -> Path:
    """Extracts into a fresh, empty directory and returns it."""
    dest = Path(dest)
    n = 1
    base = dest
    while dest.exists():
        n += 1
        dest = base.with_name(f"{base.name}_{n}")
    dest.mkdir(parents=True)
    proc = subprocess.run(
        [_sevenzip(), "x", f"-p{password}", f"-o{dest}", "-y", str(zip_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"7-Zip failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout[-500:]}")
    return dest


def pdf_text(path: Path) -> str:
    """Layout-preserving text via poppler's pdftotext if present, else pypdf."""
    exe = shutil.which("pdftotext")
    if exe:
        proc = subprocess.run([exe, "-layout", str(path), "-"], capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _files(case_dir: Path) -> list[Path]:
    return sorted(
        p for p in case_dir.rglob("*")
        if p.is_file() and "__MACOSX" not in p.parts and not p.name.startswith(".")
    )


def _pick(files: list[Path], stem_prefix: str, suffixes: set[str]) -> Path | None:
    for p in files:
        if p.stem.lower().startswith(stem_prefix) and p.suffix.lower() in suffixes:
            return p
    return None


def load_case(case_dir: Path) -> Case:
    files = _files(Path(case_dir))
    policy = _pick(files, "policy", {".txt"})
    description = _pick(files, "description", {".txt"})
    invoice = _pick(files, "invoice", {".pdf"})
    missing = [n for n, p in [("policy.txt", policy), ("description.txt", description), ("invoice*.pdf", invoice)] if p is None]
    if missing:
        raise FileNotFoundError(f"{case_dir}: missing {', '.join(missing)}; found {[p.name for p in files]}")
    images = [p for p in files if p.suffix.lower() in IMAGE_SUFFIXES]
    return Case(
        case_dir=Path(case_dir),
        policy=policy.read_text(errors="replace"),
        description=description.read_text(errors="replace"),
        invoice_text=pdf_text(invoice),
        images=images,
        image_blobs=[b for b in (prepare_image(p) for p in images) if b is not None],
    )
