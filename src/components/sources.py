from typing import Callable, Generator, Iterable
from pathlib import Path

from ..utils.misc import iter_bytes_read

from .common import IAssetSrc, IExtensionSrc

from ..utils.matching import CriteriaMatcher
from ..utils.extension import (
    get_asset_from_vsix,
    get_version,
    get_version_asset,
    get_vsix_manifest,
    sanitize_extension,
    sort_extensions,
)

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
            criteria: "list[GalleryCriterium]",
            flags: GalleryFlags,
            assetTypes: "list[str]",
            page: int = 1,
            pageSize: int = 10,
            sortBy: SortBy = SortBy.NoneOrRelevance,
            sortOrder: SortOrder = SortOrder.Default,
        ) -> Generator[
            GalleryExtension, None, "list[GalleryExtensionQueryResultMetadata]"
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

    def iter(self):
        return self._exts

    def _sanitize_extension(
        self, flags: GalleryFlags, assetTypes: "list[str]", ext: GalleryExtension
    ):
        return sanitize_extension(flags, assetTypes, ext)

    def generate_page(
        self,
        criteria: "list[GalleryCriterium]",
        flags: GalleryFlags,
        assetTypes: "list[str]",
        page: int = 1,
        pageSize: int = 10,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
        *,
        short_on_qty: bool = False,
    ) -> Generator[GalleryExtension, None, "list[GalleryExtensionQueryResultMetadata]"]:
        matcher: CriteriaMatcher = CriteriaMatcher(criteria)
        matched = 0
        start = ((page or 1) - 1) * pageSize
        end = start + pageSize
        cats = {}

        for ext in sort_extensions(self.iter(), sortOrder, sortBy):
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
        criteria: 'list[GalleryCriterium]',
        flags: GalleryFlags,
        assetTypes: 'list[str]',
        page: int = 1,
        pageSize: int = 10,
        sortBy: SortBy = SortBy.NoneOrRelevance,
        sortOrder: SortOrder = SortOrder.Default,
    ) -> Generator[GalleryExtension, None, 'list[GalleryExtensionQueryResultMetadata]']:
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


class LocalGallerySrc(IterExtensionSrc, IAssetSrc):
    def __init__(
        self,
        path: str,
        asset_uri: Callable[[str, str, GalleryExtension, GalleryExtensionVersion], str],
        id_cache: str = None,
    ) -> None:
        self._path = Path(path)
        self._asset_uri = asset_uri
        self._ids_cache = Path(id_cache) if id_cache else self._path / "ids.json"
        self._load()

    def iter(self):
        return self._exts.values()

    def get_extension(
        self,
        extensionId: str,
        flags: GalleryFlags = GalleryFlags.IncludeAssetUri
        | GalleryFlags.IncludeCategoryAndTags
        | GalleryFlags.IncludeFiles
        | GalleryFlags.IncludeInstallationTargets
        | GalleryFlags.IncludeStatistics
        | GalleryFlags.IncludeVersionProperties
        | GalleryFlags.IncludeVersions,
        assetTypes: 'list[str]' = [],
    ):
        extuid = self.uid_map.get(extensionId.lower())
        ext = self._exts[extuid] if extuid else self._exts.get(extensionId, None)
        if ext:
            ext = self._sanitize_extension(flags, assetTypes, ext)
        return ext

    def get_extension_asset(self, extensionId: str, version: 'str | None', asset: str):
        ext = self.get_extension(extensionId)
        if ext:
            ver = get_version(ext, version)
            if ver:
                return self.get_asset(get_version_asset(ver, AssetType.VSIX), asset)
        return None, None

    def get_asset(self, src: str, asset: "str|AssetType"):
        vsix = self._path / src
        if src in self.assets and vsix.exists():
            if asset == AssetType.VSIX:
                return iter_bytes_read(vsix), src
            else:
                return get_asset_from_vsix(vsix, asset, assets_map=self.assets[src])

        return None, None

    def _load(self):
        import json, semver, uuid
        from ..utils.extension import gallery_ext_from_manifest

        ids = (
            json.loads(self._ids_cache.read_text()) if self._ids_cache.exists() else {}
        )
        self._exts: 'dict[str, GalleryExtension]' = {}
        self.assets: 'dict[str, dict[AssetType, str]]' = {}
        self.uid_map = {}

        for file in self._path.iterdir():
            if file.suffix == ".vsix":
                manifest = get_vsix_manifest(file)
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
                if uid in self._exts:
                    _ext = self._exts[uid]
                    version = semver.Version.parse(ext["versions"][0]["version"])
                    latest = True

                    for v in _ext["versions"]:
                        _ver = semver.Version.parse(v["version"])
                        if _ver > version:
                            latest = False
                    if latest:
                        self._exts[uid] = ext
                        ext["versions"] += _ext["versions"]
                else:
                    self._exts[uid] = ext
                    self.uid_map[ext["extensionId"]] = uid
        self._ids_cache.write_text(json.dumps(ids))

    def _sanitize_extension(
        self, flags: GalleryFlags, assetTypes: 'list[str]', ext: GalleryExtension
    ):
        ext = super()._sanitize_extension(flags, assetTypes, ext)
        for ver in ext.get("versions", []):
            for uri in ["assetUri", "fallbackAssetUri"]:
                ver[uri] = self._asset_uri(ver[uri], uri, ext, ver)
        return ext
