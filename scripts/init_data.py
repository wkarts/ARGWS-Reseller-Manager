"""One-shot permission initialization for the explicitly mounted /data bind volume."""
from pathlib import Path
import os
ROOT=Path('/data')
ROOT.mkdir(exist_ok=True)
if ROOT.is_symlink():raise SystemExit('/data must not be a symlink')
for directory, dirs, files in os.walk(ROOT,followlinks=False):
    path=Path(directory)
    os.chown(path,10001,10001);os.chmod(path,0o700)
    dirs[:]=[name for name in dirs if not (path/name).is_symlink()]
    for name in files:
        file=path/name
        if file.is_symlink():continue
        os.chown(file,10001,10001);os.chmod(file,0o600)
print('Data volume prepared. No database contents were read or altered.')
