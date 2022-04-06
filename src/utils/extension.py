from typing import Iterable, List

from . import epoch_from_iso
from ..models import GalleryExtension, GalleryExtensionVersion, GalleryFlags, SortBy, SortOrder


def get_statistic(ext: GalleryExtension, name: str, default=None):
    return next(
        [s["value"] for s in ext["statistics"] if s["statisticName"] == name], default
    )

def sanitize_extension(flags: GalleryFlags, assets: List[str], ext: GalleryExtension):
    versions = []
    _ext: GalleryExtension = {**ext}
    if (
        GalleryFlags.IncludeVersions in flags
        or GalleryFlags.IncludeFiles in flags
        or GalleryFlags.IncludeVersionProperties in flags
        or GalleryFlags.IncludeLatestVersionOnly
    ):
        latest = None
        for version in ext["versions"]:
            if not versions:
                latest = version["version"]
            if (
                GalleryFlags.IncludeLatestVersionOnly in flags
                and latest != version["version"]
            ):
                break
            ver: GalleryExtensionVersion = {**version}
            if not GalleryFlags.IncludeFiles:
                ver["files"] = [
                    file for file in ver["files"] if file["assetType"] in assets
                ]
            if not GalleryFlags.IncludeVersionProperties:
                del ver["properties"]
            if not GalleryFlags.IncludeAssetUri:
                del ver["assetUri"]
                del ver["fallbackAssetUri"]
            if GalleryFlags.ExcludeNonValidated and "validated" not in ver["flags"]:
                continue
            versions.append(ver)
    _ext["versions"] = versions
    return _ext


def sort_extensions(exts:Iterable[GalleryExtension], sortOrder: SortOrder, sortBy: SortBy):
        defAsc = SortOrder.Descending == sortOrder
        defDsc = SortOrder.Ascending != sortOrder
        if sortBy is SortBy.AverageRating:
            exts = sorted(
                exts, key=lambda e: get_statistic(e, "averagerating", 0), reverse=defDsc
            )
        elif sortBy is SortBy.InstallCount:
            exts = sorted(
                exts, key=lambda e: get_statistic(e, "install", 0), reverse=defDsc
            )
        elif sortBy is SortBy.WeightedRating:
            exts = sorted(
                exts,
                key=lambda e: get_statistic(e, "weightedRating", 0),
                reverse=defDsc,
            )
        elif sortBy is SortBy.Title:
            exts = sorted(exts, key=lambda e: e["displayName"], reverse=defAsc)
        elif sortBy is SortBy.PublisherName:
            exts = sorted(
                exts, key=lambda e: e["publisher"]["displayName"], reverse=defAsc
            )
        elif sortBy is SortBy.PublishedDate:
            exts = sorted(
                exts, key=lambda e: epoch_from_iso(e["publishedDate"]), reverse=defAsc
            )
        elif sortBy is SortBy.LastUpdatedDate:
            exts = sorted(
                exts, key=lambda e: epoch_from_iso(e["lastUpdated"]), reverse=defAsc
            )
        elif defAsc:
            exts = reversed(exts)
        return iter(exts)