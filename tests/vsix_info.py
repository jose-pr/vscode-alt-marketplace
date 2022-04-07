import json
from pathlib import Path
from typing import Dict, List
import zipfile, xmltodict, uuid, semver
from src.models.gallery import GalleryExtension
from src.models.vsixmanifest import PackageManifest
from src.utils.extension import gallery_ext_from_manifest

vsix_path = Path("examples")
ids_cache =  vsix_path / "ids.json"


ids = json.loads(ids_cache.read_text()) if ids_cache.exists() else {}

exts:Dict[str, GalleryExtension] = {}

for file in vsix_path.iterdir():
    if file.suffix == ".vsix":
        with zipfile.ZipFile(file, mode="r") as vsix_file:
            manifest: PackageManifest = xmltodict.parse(
                vsix_file.read("extension.vsixmanifest").decode()
            )["PackageManifest"]
            ext = gallery_ext_from_manifest(manifest)
            pub = ext["publisher"]["publisherName"]
            uid = f'{pub}.{ext["extensionName"]}'
            ext["extensionId"] = ids[uid] if uid in ids else str(uuid.uuid4())
            ids[uid] = ext["extensionId"]
            ext["publisher"]["publisherId"] = ids[pub] if pub in ids else str(uuid.uuid4())
            ids[pub] = ext["publisher"]["publisherId"]
            if uid in exts:
                _ext = exts[uid]
                version = semver.Version.parse(ext["versions"][0]["version"])
                latest = True

                for v in _ext["versions"]:
                    _ver = semver.Version.parse(v["version"])
                    if _ver > version:
                        latest = False
                if latest:
                    print(version)
                    exts[uid] = ext
                    ext["versions"] += _ext["versions"]
            else:
                exts[uid] = ext



ids_cache.write_text(json.dumps(ids))
pass
