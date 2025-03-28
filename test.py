import os
import tarfile
import tempfile
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define package details
package_name = 'ab-hello'
version = '0.0.1'
arch = 'amd64'
deb_filename = f'{package_name}_{version}_{arch}.deb'

control_content = f"""\
Package: {package_name}
Version: {version}
Depends:
Recommends:
Section: main
Priority: optional
Homepage: https://github.com
Architecture: amd64
Installed-Size: 10
Maintainer: My Name <myemail@example.com>
Description: ab-hello
"""

def create_control_tar_gz(control_tar_path: Path):
    with tempfile.TemporaryDirectory() as control_tmpdir:
        control_dir = Path(control_tmpdir)
        control_file = control_dir / "control"
        control_file.write_text(control_content)

        with tarfile.open(control_tar_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            tar.add(control_file, arcname="control")

def create_data_tar_gz(data_tar_path: Path):
    with tempfile.TemporaryDirectory() as data_tmpdir:
        data_dir = Path(data_tmpdir)
        usr_bin = data_dir / "usr/bin"
        usr_bin.mkdir(parents=True)
        ab_hello = usr_bin / "ab-hello"
        ab_hello.write_text("#!/bin/sh\necho hello\n")
        os.chmod(ab_hello, 0o755)

        with tarfile.open(data_tar_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
            tar.add(data_dir / "usr", arcname="usr")

def build_deb(deb_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("created temporary workspace: %s", tmpdir)
        tmp_path = Path(tmpdir)

        # 1. debian-binary
        debian_binary = tmp_path / "debian-binary"
        debian_binary.write_text("2.0\n")

        # 2. control.tar.gz
        control_tar = tmp_path / "control.tar.gz"
        create_control_tar_gz(control_tar)

        # 3. data.tar.gz
        data_tar = tmp_path / "data.tar.gz"
        create_data_tar_gz(data_tar)

        # 4. Final .deb using ar
        command = ["ar", "vr", deb_path.absolute(), "debian-binary", "control.tar.gz", "data.tar.gz"]
        logger.info("Building debian binary in %s with command %s, contents: %s", tmpdir, command, [*Path(tmpdir).iterdir()])
        subprocess.run(command, cwd=tmp_path, check=True)

        logger.info("✅ Created .deb package: %s", deb_path)

if __name__ == "__main__":
    build_deb(Path(deb_filename))
