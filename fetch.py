"""MSHA Data Fetcher & Streaming Loader entry point."""

from msha_triage.fetch import (  # noqa: F401, F403
    ARLWEB_BASE_URL,
    DEFAULT_LOCAL_DIR,
    DEFAULT_STAGING_DIR,
    MINES_ZIP_URL,
    VIOLATIONS_ZIP_URL,
    download_dataset,
    ensure_mines_file,
    ensure_violations_file,
    find_dataset_file,
    load_mines_mapping,
    open_stream,
    stream_pipe_delimited,
)

if __name__ == "__main__":
    print("MSHA Fetch module loaded successfully.")
