"""Build on Windows x64. Does not pretend that a Linux build is a Windows executable."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--with-browser",action="store_true",help="Bundle Chromium for the optional browser login")
    parser.add_argument("--onefile",action="store_true",help="Single exe; larger/slower with Chromium")
    args=parser.parse_args()
    if sys.platform!="win32" or struct.calcsize("P")*8!=64:
        parser.error("Compile em Windows com Python x64. Este projeto não declara suporte x86.")
    subprocess.run([sys.executable,"-m","pytest","-q"],cwd=ROOT,check=True)
    version=(ROOT/"VERSION").read_text().strip()
    command=[sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onefile" if args.onefile else "--onedir","--windowed","--noupx","--name","ResellerManager","--paths",str(ROOT),"--icon",str(ROOT/"app/static/icon.ico"),"--add-data",f"{ROOT/'app/static'}:app/static","--collect-submodules","app","--collect-submodules","uvicorn","--collect-submodules","websockets","--collect-all","cryptography","--distpath",str(ROOT/"dist"),"--workpath",str(ROOT/"build/pyinstaller"),"--specpath",str(ROOT/"build")]
    env=os.environ.copy()
    if args.with_browser:
        env["PLAYWRIGHT_BROWSERS_PATH"]="0"
        subprocess.run([sys.executable,"-m","playwright","install","chromium"],env=env,cwd=ROOT,check=True)
        command.extend(["--collect-all","playwright"])
    else: command.extend(["--exclude-module","playwright"])
    command.append(str(ROOT/"packaging/launcher.py"))
    subprocess.run(command,cwd=ROOT,env=env,check=True)
    executable=ROOT/"dist"/("ResellerManager.exe" if args.onefile else "ResellerManager/ResellerManager.exe")
    with executable.open("rb") as f:
        f.seek(0x3c);offset=struct.unpack("<I",f.read(4))[0];f.seek(offset)
        if f.read(4)!=b"PE\0\0" or struct.unpack("<H",f.read(2))[0]!=0x8664:raise RuntimeError("Executável não é PE x64.")
    subprocess.run([sys.executable,str(ROOT/"scripts/smoke_runtime.py"),"--executable",str(executable)],cwd=ROOT,check=True)
    artifacts=ROOT/"artifacts";artifacts.mkdir(exist_ok=True)
    name=f"reseller-manager-{version}-windows-x64"+("-browser" if args.with_browser else "")+("-single" if args.onefile else "")
    stage=ROOT/"build"/name
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir(parents=True)
    if args.onefile:shutil.copy2(executable,stage/executable.name)
    else:
        for item in executable.parent.iterdir():
            if item.is_dir():shutil.copytree(item,stage/item.name)
            else:shutil.copy2(item,stage/item.name)
    shutil.copy2(ROOT/"README.md",stage/"README.md");shutil.copytree(ROOT/"docs",stage/"docs")
    (stage/"manifest.json").write_text(json.dumps({"version":version,"python":platform.python_version(),"windows_arch":"x64","browser_bundled":args.with_browser,"http_smoke":"passed","production_koffice_validated":False},indent=2),encoding="utf-8")
    archive=Path(shutil.make_archive(str(artifacts/name),"zip",stage.parent,stage.name))
    (artifacts/(name+".sha256")).write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+"  "+archive.name+"\n")
    print(archive)

if __name__=="__main__":main()
