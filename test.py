import os
import tarfile
import gzip
import shutil
from debian import arfile

# Define package details
package_name = 'ab-hello'
version = '0.0.1'
arch = 'amd64'
deb_filename = f'{package_name}_{version}_{arch}.deb'

# Step 1: Create the debian-binary file
with open('debian-binary', 'w') as f:
    f.write('2.0\n')

# Step 2: Create the control.tar.gz archive
os.mkdir('control')
control_content = f"""\
Package: {package_name}
Version: {version}
Section: main
Priority: optional
Architecture: {arch}
Maintainer: Your Name <your.email@example.com>
Description: A simple hello world package
"""
with open('control/control', 'w') as f:
    f.write(control_content)

with tarfile.open('control.tar.gz', 'w:gz') as tar:
    tar.add('control', arcname='.')

shutil.rmtree('control')

# Step 3: Create the data.tar.gz archive
os.makedirs('data/usr/bin', exist_ok=True)
script_content = '#!/bin/sh\necho hello\n'
with open('data/usr/bin/ab-hello', 'w') as f:
    f.write(script_content)
os.chmod('data/usr/bin/ab-hello', 0o755)

with tarfile.open('data.tar.gz', 'w:gz') as tar:
    tar.add('data', arcname='.')

shutil.rmtree('data')

# Step 4: Assemble the .deb package using arfile
# Step 4: Assemble the .deb package using arfile
deb_fp = open(deb_filename, 'wb')
ar = arfile.ArFile(deb_fp, mode='w')

ar.addfile(arfile.ArInfo('debian-binary', size=os.path.getsize('debian-binary')), open('debian-binary', 'rb'))
ar.addfile(arfile.ArInfo('control.tar.gz', size=os.path.getsize('control.tar.gz')), open('control.tar.gz', 'rb'))
ar.addfile(arfile.ArInfo('data.tar.gz', size=os.path.getsize('data.tar.gz')), open('data.tar.gz', 'rb'))

ar.close()
deb_fp.close()

# Clean up intermediate files
os.remove('debian-binary')
os.remove('control.tar.gz')
os.remove('data.tar.gz')

print(f'Debian package {deb_filename} created successfully.')

