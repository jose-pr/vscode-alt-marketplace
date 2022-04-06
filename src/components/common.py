from typing import List, Generator

from ..models import (
    GalleryExtensionQuery,
    GalleryExtension,
    GalleryExtensionQueryResultMetadata,
    GalleryFlags,
    GalleryCriterium,
    GalleryQueryResult,
    SortBy,
    SortOrder,
)


class IExtensionSrc:
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
        raise NotImplementedError()


class IGallery:

    def extension_query(
        self, query: GalleryExtensionQuery
    ) -> GalleryQueryResult:
        raise NotImplementedError()