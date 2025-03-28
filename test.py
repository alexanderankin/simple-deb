import os
import tarfile
import tempfile
import subprocess
import logging
import io
from abc import ABC
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
package_name = 'ab-hello'
version = '0.0.1'
arch = 'amd64'
deb_filename = f'{package_name}_{version}_{arch}.deb'

# --- Dataclasses ---

@dataclass
class TarFileSpec(ABC):
    path: str  # Path inside the archive (relative)
    mode: Optional[int]  # File mode (optional)


@dataclass
class TextTarFileSpec(TarFileSpec):
    content: str


@dataclass
class BinaryTarFileSpec(TarFileSpec):
    content: bytes


# --- Archive builder ---

def create_tar_gz_bytes(files: List[TarFileSpec], base_dir: Optional[str] = None) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Write files into temp dir
        for f in files:
            full_path = tmp_path / f.path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(f, TextTarFileSpec):
                full_path.write_text(f.content)
            elif isinstance(f, BinaryTarFileSpec):
                full_path.write_bytes(f.content)
            else:
                raise Exception(f"unknown type: {type(f)} for {f}")

            if f.mode is not None:
                os.chmod(full_path, f.mode)

        # Package into in-memory tar.gz
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
            if base_dir:
                tar.add(tmp_path / base_dir, arcname=base_dir)
            else:
                for f in files:
                    tar.add(tmp_path / f.path, arcname=f.path)

        return buf.getvalue()


# --- Package content ---

CONTROL_FILES: List[TarFileSpec] = [
    TextTarFileSpec(
        path="control",
        mode=None,
        content=f"""\
Package: {package_name}
Version: {version}
Depends:
Recommends:
Section: main
Priority: optional
Homepage: https://github.com
Architecture: {arch}
Installed-Size: 10
Maintainer: My Name <myemail@example.com>
Description: ab-hello
"""
    )
]

DATA_FILES: List[TarFileSpec] = [
    TextTarFileSpec(path="usr/bin/ab-hello", content="#!/bin/sh\necho hello\n", mode=0o755),
]


# --- DEB Builder ---

def build_deb(deb_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        logger.info("Created workspace: %s", tmp_path)

        # Write debian-binary
        (tmp_path / "debian-binary").write_text("2.0\n")

        # Write tar.gz files
        (tmp_path / "control.tar.gz").write_bytes(create_tar_gz_bytes(CONTROL_FILES))
        (tmp_path / "data.tar.gz").write_bytes(create_tar_gz_bytes(DATA_FILES, base_dir="usr"))

        # Assemble with ar
        subprocess.run(
            ["ar", "vr", deb_path.absolute(), "debian-binary", "control.tar.gz", "data.tar.gz"],
            cwd=tmp_path,
            check=True
        )

        logger.info("✅ Created .deb package: %s", deb_path)


# --- Entrypoint ---

if __name__ == "__main__":
    build_deb(Path(deb_filename))
