import logging
import tarfile
from tempfile import TemporaryDirectory
from abc import ABC
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from subprocess import run
from textwrap import dedent
from typing import List, Optional, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- File Spec Types ---


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


ContentTarFileSpec = Union[TextTarFileSpec, BinaryTarFileSpec]


# --- Config Structs ---


@dataclass
class PackageMeta:
    name: str
    version: str
    arch: str

    @property
    def deb_filename(self) -> str:
        return f"{self.name}_{self.version}_{self.arch}.deb"


@dataclass
class DebFileSpec:
    control_files: List[ContentTarFileSpec]
    data_files: List[ContentTarFileSpec]


@dataclass
class ControlExtras:
    depends: str = ""
    recommends: str = ""
    section: str = "main"
    priority: str = "optional"
    homepage: str = ""
    maintainer: str = ""
    description: str = ""

    def render(self, meta: PackageMeta) -> str:
        return dedent(f"""\
            Package: {meta.name}
            Version: {meta.version}
            Depends: {self.depends}
            Recommends: {self.recommends}
            Section: {self.section}
            Priority: {self.priority}
            Homepage: {self.homepage}
            Architecture: {meta.arch}
            Installed-Size: 10
            Maintainer: {self.maintainer}
            Description: {self.description}
        """).strip() + "\n"


@dataclass
class DebPackageConfig:
    meta: PackageMeta
    control: ControlExtras
    files: DebFileSpec


# --- Archive Builder ---


def create_tar_gz_bytes(
    files: List[ContentTarFileSpec], base_dir: Optional[str] = None
) -> bytes:
    with TemporaryDirectory() as tmpdir:
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
                full_path.chmod(f.mode)

        # Package into in-memory tar.gz
        buf = BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.GNU_FORMAT) as tar:
            if base_dir:
                tar.add(tmp_path / base_dir, arcname=base_dir)
            else:
                for f in files:
                    tar.add(tmp_path / f.path, arcname=f.path)

        return buf.getvalue()


# --- DEB Builder ---


def build_deb(config: DebPackageConfig):
    output_path = Path(config.meta.deb_filename)
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        logger.info("Created workspace: %s", tmp_path)

        # debian-binary
        (tmp_path / "debian-binary").write_text("2.0\n")

        # control.tar.gz
        control_content = config.control.render(config.meta)
        control_spec = TextTarFileSpec(path="control", content=control_content, mode=None)
        control_bytes = create_tar_gz_bytes(config.files.control_files + [control_spec])
        (tmp_path / "control.tar.gz").write_bytes(control_bytes)

        # data.tar.gz
        data_bytes = create_tar_gz_bytes(config.files.data_files, base_dir="usr")
        (tmp_path / "data.tar.gz").write_bytes(data_bytes)

        # Build .deb
        logger.info("Creating .deb package: %s", output_path)
        run(
            [
                "ar",
                "vr",
                output_path.absolute(),
                "debian-binary",
                "control.tar.gz",
                "data.tar.gz",
            ],
            cwd=tmp_path,
            check=True,
        )
        logger.info("Created .deb package: %s", output_path)


# --- Entrypoint ---

if __name__ == "__main__":
    build_deb(
        DebPackageConfig(
            meta=PackageMeta(
                name="ab-hello",
                version="0.0.1",
                arch="amd64",
            ),
            control=ControlExtras(
                section="main",
                priority="optional",
                homepage="https://github.com",
                maintainer="My Name <myemail@example.com>",
                description="ab-hello",
            ),
            files=DebFileSpec(
                control_files=[],
                data_files=[
                    TextTarFileSpec(
                        path="usr/bin/ab-hello",
                        content="#!/bin/sh\necho hello\n",
                        mode=0o755,
                    )
                ],
            ),
        )
    )
