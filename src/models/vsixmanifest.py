from typing import List, TypedDict

Identity = TypedDict("Identity", {"@Language": str, "@Version": str, "@Publisher": str, "@Id":str})
Property = TypedDict("Property", {"@Id": str, "@Value": str})


class Properties(TypedDict):
    Property: List[Property]

TextNode = TypedDict("TextNode", {"#text":str})


class Metadata(TypedDict):
    Identity: Identity
    DisplayName: str
    Description: TextNode
    Tags: str
    Categories: str
    GalleryFlags: str
    Badges: str
    Properties: Properties
    Icon: str


InstallationTarget = TypedDict("InstallationTarget", {"@Id": str})


class Installation(TypedDict):
    InstallationTarget: InstallationTarget


Asset = TypedDict("Asset", {"@Type": str, "@Path": str, "@Addressable": bool})


class Assets(TypedDict):
    Asset: List[Asset]


PackageManifest = TypedDict(
    "PackageManifest",
    {
        "@Version": str,
        "Metadata": Metadata,
        "Installation": Installation,
        "Dependencies": str,
        "Assets": Assets,
    },
)

class PackageManifestRoot(TypedDict):
    PackageManifest:PackageManifest
