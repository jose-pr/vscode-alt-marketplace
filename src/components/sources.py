from typing import Callable, Generator, Iterable, List

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
        ) -> Generator[GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]]:
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
        short_on_qty: bool = False
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
    def __init__(self, src:IExtensionSrc, proxy_url:Callable[[str,str,GalleryExtension, GalleryExtensionVersion], str]) -> None:
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
        sortOrder: SortOrder = SortOrder.Default
    ) -> Generator[GalleryExtension, None, List[GalleryExtensionQueryResultMetadata]]:
        gen = self.src.generate_page(criteria, flags, assetTypes, page, pageSize, sortBy, sortOrder)
        while True:
            try:
                ext:GalleryExtension = next(gen)
                for ver in ext.get("versions", []):
                    for uri in ["assetUri", "fallbackAssetUri"]:
                        if uri in ver:
                            ver[uri] = self.proxy_url(ver[uri], uri, ext, ver)
                yield ext
            except StopIteration as ex:
                return ex.value

