from typing import Callable, Dict, Generator, Iterable, List
from pathlib import Path

from src.models.gallery import AssetType

from .common import IExtensionSrc

from ..utils.matching import CriteriaMatcher
from ..utils.extension import sanitize_extension, sort_extensions

from ..models import *

try:
    from .gallery import ExternalGallery

    class MirrorExtensionSrc(IExtensionSrc):
        def __init__(self, src: str = None) -> None:
            super().__init__()
            self._gallery = ExternalGallery(src)

        def _sanitize_extension(self, ext: GalleryExtension):
            return ext

        def generate_page(
            self,
            criteria: List[GalleryCriterium],
            flags: GalleryFlags,
            assetTypes: List[str],
            page: int = 1,
            pageSize: int = 10,
            sortBy: SortBy = SortBy.NoneOrRelevance,
            sortOrder: SortOrder = SortOrder.Default,
        ) -> Generator[
            GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]
        ]:
            resp = self._gallery.extension_query(
                {
                    "filters": [
                        {
                            "criteria": criteria,
                            "pageNumber": page,
                            "pageSize": pageSize,
                            "sortBy": sortBy,
                            "sortOrder": sortOrder,
                        }
                    ],
                    "assetTypes": assetTypes,
                    "flags": flags,
                },
            )

            for ext in resp["results"][0]["extensions"]:
                yield self._sanitize_extension(ext)
            return resp["results"][0]["resultMetadata"]

except ModuleNotFoundError:
    pass


class IterExtensionSrc(IExtensionSrc):
    def __init__(self, exts: Iterable[GalleryExtension]) -> None:
        super().__init__()
        self._exts = exts

    def _sanitize_extension(
        self, flags: GalleryFlags, assetTypes: List[str], ext: GalleryExtension
    ):
        return sanitize_extension(flags, assetTypes, ext)

    def generate_page(
        self,
        criteria: List[GalleryCriterium],
        flags: GalleryFlags,
        assetTypes: List[str],
        page: int = 1,
        pageSize: int = 10,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
        *,
        short_on_qty: bool = False,
    ) -> Generator[GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]]:
        matcher: CriteriaMatcher = CriteriaMatcher(criteria)
        matched = 0
        start = ((page or 1) - 1) * pageSize
        end = start + pageSize
        cats = {}

        for ext in sort_extensions(self._exts, sortOrder, sortBy):
            if (
                GalleryFlags.ExcludeNonValidated in flags
                and "validated" not in ext["flags"]
            ):
                continue
            if matcher.is_match(ext):
                matched += 1
                for cat in ext.get("categories", []):
                    cats[cat] = cats.get(cat, 0) + 1
                if matched > start and matched <= end:
                    yield self._sanitize_extension(flags, assetTypes, ext)
                if matched >= end and short_on_qty:
                    break

        return [
            {
                "metadataType": "ResultCount",
                "metadataItems": [
                    {"name": "TotalCount", "count": matched},
                ],
            },
            {
                "metadataType": "Categories",
                "metadataItems": [
                    {"name": cat, "count": count} for cat, count in cats.items()
                ],
            },
        ]


class ProxyExtensionSrc(IExtensionSrc):
    def __init__(
        self,
        src: IExtensionSrc,
        proxy_url: Callable[[str, str, GalleryExtension, GalleryExtensionVersion], str],
    ) -> None:
        super().__init__()
        self.src = src
        self.proxy_url = proxy_url

    def generate_page(
        self,
        criteria: List[GalleryCriterium],
        flags: GalleryFlags,
        assetTypes: List[str],
        page: int = 1,
        pageSize: int = 10,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
    ) -> Generator[GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]]:
        gen = self.src.generate_page(
            criteria, flags, assetTypes, page, pageSize, sortBy, sortOrder
        )
        while True:
            try:
                ext: GalleryExtension = next(gen)
                for ver in ext.get("versions", []):
                    for uri in ["assetUri", "fallbackAssetUri"]:
                        if uri in ver:
                            ver[uri] = self.proxy_url(ver[uri], uri, ext, ver)
                yield ext
            except StopIteration as ex:
                return ex.value


class LocalGallerySrc(IterExtensionSrc):
    def __init__(
        self,
        path: str,
        proxy_url: Callable[[str, str, GalleryExtension, GalleryExtensionVersion], str],
        id_cache: str = None,
    ) -> None:
        self._path = Path(path)
        self._proxy_url = proxy_url
        self._ids_cache = Path(id_cache) if id_cache else self._path / "ids.json"
        self._load()

    @property
    def _exts(self):
        return self.exts.values()

    def _get_asset(self, path: str, asset: str):
        import zipfile, mimetypes

        with zipfile.ZipFile(self._path / path, mode="r") as file:
            p =  self.assets[path][asset]
            return file.read(p), mimetypes.guess_type(p)[0]


    def _load(self):
        import json, zipfile, xmltodict, semver, uuid
        from ..utils.extension import gallery_ext_from_manifest
        from ..models.vsixmanifest import PackageManifest

        ids = (
            json.loads(self._ids_cache.read_text()) if self._ids_cache.exists() else {}
        )
        self.exts: Dict[str, GalleryExtension] = {}
        self.assets: Dict[str, Dict[AssetType, str]] = {}

        for file in self._path.iterdir():
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
                    ext["publisher"]["publisherId"] = (
                        ids[pub] if pub in ids else str(uuid.uuid4())
                    )
                    ext["versions"][0]["assetUri"] = str(file.name)
                    ext["versions"][0]["fallbackAssetUri"] = str(file.name)
                    ext["versions"][0]["flags"] += " validated"
                    ext["flags"] += " validated"
                    ext["versions"][0]["files"].append(
                        {"source": file.name, "assetType": AssetType.VSIX.value}
                    )
                    self.assets[file.name] = {
                        f["assetType"]: f["source"] for f in ext["versions"][0]["files"]
                    }

                    ids[pub] = ext["publisher"]["publisherId"]
                    if uid in self.exts:
                        _ext = self.exts[uid]
                        version = semver.Version.parse(ext["versions"][0]["version"])
                        latest = True

                        for v in _ext["versions"]:
                            _ver = semver.Version.parse(v["version"])
                            if _ver > version:
                                latest = False
                        if latest:
                            self.exts[uid] = ext
                            ext["versions"] += _ext["versions"]
                    else:
                        self.exts[uid] = ext
        self._ids_cache.write_text(json.dumps(ids))

    def generate_page(
        self,
        criteria: List[GalleryCriterium],
        flags: GalleryFlags,
        assetTypes: List[str],
        page: int = 1,
        pageSize: int = 10,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
    ) -> Generator[GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]]:
        gen = super().generate_page(
            criteria, flags, assetTypes, page, pageSize, sortBy, sortOrder
        )
        while True:
            try:
                ext: GalleryExtension = next(gen)
                for ver in ext.get("versions", []):
                    for uri in ["assetUri", "fallbackAssetUri"]:
                        ver[uri] = self._proxy_url(ver[uri], uri, ext, ver)
                yield ext
            except StopIteration as ex:
                return ex.value
