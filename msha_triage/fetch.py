"""Fetch and streaming data loader for MSHA open government datasets.

Streams Violations.txt and Mines.txt without loading entire multi-gigabyte
files into memory. Supports direct text files, zip archives, local cache,
and remote arlweb URLs.
"""

import csv
import io
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Generator, Iterator, Optional, Union

# Official MSHA Open Government Data endpoints (public, no authentication)
ARLWEB_BASE_URL = "https://arlweb.msha.gov/opengovernmentdata/DataSets"
MINES_ZIP_URL = f"{ARLWEB_BASE_URL}/Mines.zip"
VIOLATIONS_ZIP_URL = f"{ARLWEB_BASE_URL}/Violations.zip"

DEFAULT_STAGING_DIR = Path("/home/user/.hermes/cache/scratch/msha")
DEFAULT_LOCAL_DIR = Path(__file__).resolve().parent.parent / "data"


def open_stream(
    source_path: Union[str, Path], inner_filename: Optional[str] = None
) -> io.TextIOBase:
    """Open a file or an inner file inside a zip as a text stream.

    Args:
        source_path: Path to the .txt or .zip file.
        inner_filename: Optional name of the member file inside a .zip archive.

    Returns:
        io.TextIOBase: Text stream in 'latin1' encoding.
    """
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file does not exist: {path}")

    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path, "r")
        if inner_filename:
            target_name = inner_filename
        else:
            # Pick first .txt file inside zip
            txt_members = [m for m in zf.namelist() if m.lower().endswith(".txt")]
            if not txt_members:
                raise ValueError(f"No .txt member found in zip archive: {path}")
            target_name = txt_members[0]
        binary_stream = zf.open(target_name, "r")
        return io.TextIOWrapper(binary_stream, encoding="latin1", errors="replace")

    return open(path, "r", encoding="latin1", errors="replace")


def stream_pipe_delimited(
    source_path: Union[str, Path], inner_filename: Optional[str] = None
) -> Generator[Dict[str, str], None, None]:
    """Stream pipe-delimited rows from a file or zip archive as dictionaries.

    Never loads the full file into memory. Yields one dictionary per row.
    """
    stream = open_stream(source_path, inner_filename)
    try:
        reader = csv.reader(stream, delimiter="|")
        try:
            header = next(reader)
        except StopIteration:
            return

        header = [col.strip().strip('"') for col in header]

        for row in reader:
            if not row or not any(row):
                continue
            # Pad row if columns are shorter than header
            if len(row) < len(header):
                row.extend([""] * (len(header) - len(row)))
            row_dict = {
                header[i]: row[i].strip().strip('"') for i in range(len(header))
            }
            yield row_dict
    finally:
        stream.close()


def find_dataset_file(
    filename_base: str, search_dirs: Optional[list] = None
) -> Optional[Path]:
    """Locate a dataset file (.txt or .zip) across designated search directories.

    Args:
        filename_base: Base filename without extension (e.g. 'Violations' or 'Mines').
        search_dirs: Optional list of directories to search.

    Returns:
        Path to existing file or None.
    """
    if search_dirs is None:
        search_dirs = [DEFAULT_STAGING_DIR, DEFAULT_LOCAL_DIR]

    candidates = [
        f"{filename_base}.txt",
        f"{filename_base}.zip",
        f"{filename_base.lower()}.txt",
        f"{filename_base.lower()}.zip",
    ]

    for s_dir in search_dirs:
        dir_path = Path(s_dir)
        if not dir_path.is_dir():
            continue
        for candidate in candidates:
            fp = dir_path / candidate
            if fp.is_file() and fp.stat().st_size > 0:
                return fp

    return None


def download_dataset(url: str, dest_path: Union[str, Path], chunk_size: int = 1024 * 1024) -> Path:
    """Download a file with streaming chunks.

    Args:
        url: Remote URL to download.
        dest_path: Destination path on disk.
        chunk_size: Streaming buffer chunk size in bytes.

    Returns:
        Path to downloaded file.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_dest = dest.with_suffix(".download")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MSHA-Triage-Engine/1.0"
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp, open(temp_dest, "wb") as out_f:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_f.write(chunk)

    temp_dest.replace(dest)
    return dest


def ensure_violations_file(cache_dir: Optional[Union[str, Path]] = None) -> Path:
    """Ensure Violations dataset is available locally, downloading if necessary."""
    target_dir = Path(cache_dir) if cache_dir else DEFAULT_LOCAL_DIR
    found = find_dataset_file("Violations", [target_dir, DEFAULT_STAGING_DIR])
    if found:
        return found

    # Download if not found in cache or staging
    target_zip = target_dir / "Violations.zip"
    print(f"Downloading Violations.zip from {VIOLATIONS_ZIP_URL}...")
    return download_dataset(VIOLATIONS_ZIP_URL, target_zip)


def ensure_mines_file(cache_dir: Optional[Union[str, Path]] = None) -> Path:
    """Ensure Mines dataset is available locally, downloading if necessary."""
    target_dir = Path(cache_dir) if cache_dir else DEFAULT_LOCAL_DIR
    found = find_dataset_file("Mines", [target_dir, DEFAULT_STAGING_DIR])
    if found:
        return found

    target_zip = target_dir / "Mines.zip"
    print(f"Downloading Mines.zip from {MINES_ZIP_URL}...")
    return download_dataset(MINES_ZIP_URL, target_zip)


def load_mines_mapping(mines_path: Union[str, Path]) -> Dict[str, Dict[str, str]]:
    """Stream and build in-memory lookup table of Mine ID to metadata.

    Mines table is ~39MB, mapping takes ~15MB RAM and provides instant
    operator and state lookups for all citations.

    Returns:
        Dict[mine_id, {mine_name, operator_name, state, county, ...}]
    """
    mapping: Dict[str, Dict[str, str]] = {}
    for row in stream_pipe_delimited(mines_path, "Mines.txt"):
        mid = row.get("MINE_ID", "").strip()
        if not mid:
            continue
        mapping[mid] = {
            "mine_name": row.get("CURRENT_MINE_NAME", "").strip(),
            "operator_name": row.get("CURRENT_OPERATOR_NAME", "").strip(),
            "state": row.get("STATE", "").strip(),
            "county": row.get("FIPS_CNTY_NM", "").strip(),
            "coal_metal_ind": row.get("COAL_METAL_IND", "").strip(),
            "mine_type": row.get("CURRENT_MINE_TYPE", "").strip(),
            "status": row.get("CURRENT_MINE_STATUS", "").strip(),
            "controller_name": row.get("CURRENT_CONTROLLER_NAME", "").strip(),
        }
    return mapping
