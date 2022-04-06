from ..constants import GALLERY_API_ENDPOINT, MARKETPLACE_FQDN
from ..models import *
from .common import IGallery, IExtensionSrc
from ..utils import collect_from_generator


class Gallery(IGallery):
    def __init__(self, exts_src: IExtensionSrc) -> None:
        self.exts_src = exts_src

    def extension_query(self, query: GalleryExtensionQuery) -> GalleryQueryResult:

        flags = GalleryFlags(query["flags"])
        assetTypes = query["assetTypes"]

        result: GalleryQueryResult = {"results": []}

        for filter in query["filters"]:
            exts, meta = collect_from_generator(
                self.exts_src.generate_page(
                    filter["criteria"],
                    flags,
                    assetTypes,
                    filter["pageNumber"],
                    filter["pageSize"],
                    SortBy(filter["sortBy"]),
                    SortOrder(filter["sortOrder"]),
                )
            )
            result["results"].append({"extensions": exts, "resultMetadata": meta})
        return result


try:
    import requests

    class ExternalGallery(IGallery):
        def __init__(self, src: str = None) -> None:
            self._src = src or f"https://{MARKETPLACE_FQDN}{GALLERY_API_ENDPOINT}"

        def extension_query(
            self, query: GalleryExtensionQuery, *, session: requests.Session = None
        ) -> GalleryQueryResult:
            session: requests.Session
            return (
                (session or requests)
                .post(
                    self._src + "extensionquery",
                    headers={"Accept": "application/json;api-version=3.0-preview.1"},
                    json=query,
                )
                .json()
            )

except ModuleNotFoundError:
    pass
