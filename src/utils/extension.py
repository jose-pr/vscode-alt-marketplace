from typing import Iterable, List

from ..models.vsixmanifest import PackageManifest

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


def gallery_ext_from_manifest(manifest:PackageManifest):
    ext: GalleryExtension = {}
    ext["categories"] = manifest["Metadata"]["Categories"].split(",")
    ext["displayName"] = manifest["Metadata"]["DisplayName"]
    ext["extensionName"] = manifest["Metadata"]["Identity"]["@Id"]
    ext["flags"] = [f.lower() for f in manifest["Metadata"]["GalleryFlags"].split()]
    ext["publisher"] = {}
    ext["publisher"]["publisherName"] = manifest["Metadata"]["Identity"]["@Publisher"]
    ext["shortDescription"] = manifest["Metadata"]["Description"]["#text"]
    ext["tags"] = manifest["Metadata"]["Tags"].split(",")
    ver: GalleryExtensionVersion = {}
    ver["flags"] = ext["flags"]
    ver["files"] = [
        {"assetType": asset["@Type"], "source": asset["@Path"]}
        for asset in manifest["Assets"]["Asset"]
    ]
    ver["properties"] = [
        {"key": prop["@Id"], "value": prop["@Value"]}
        for prop in manifest["Metadata"]["Properties"]["Property"]
    ]
    ver["targetPlatform"] = manifest["Installation"]["InstallationTarget"]["@Id"]
    ver["version"] = manifest["Metadata"]["Identity"]["@Version"]
    ext["versions"] = [ver]

    return ext