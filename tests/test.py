import json, pathlib
from src import *
from pathlib import Path
from src.utils.misc import diff_query_results, reduceResultMeta

query: GalleryExtensionQuery = {
    "filters": [
        {
            "criteria": [
                {"filterType": FilterType.Target, "value": "Microsoft.VisualStudio.Code"},
                {"filterType": FilterType.Category, "value": "Programming Languages"},
                {"filterType": FilterType.Category, "value": "Data Science"},
                {"filterType": FilterType.Category, "value": "Notebooks"},
                {"filterType": FilterType.ExcludeWithFlags, "value": "4096"},
            ],
            "pageNumber": 1,
            "pageSize": 50,
            "sortBy": 0,
            "sortOrder": 0,
        }
    ],
    "assetTypes": [],
    "flags": 439,
}

flags = GalleryFlags(439)
exts_cache = json.loads(Path("examples/extensions.json").read_text())
list_gallery = Gallery(IterExtensionSrc(exts_cache))
mirror_gallery = ExternalGallery()
resp_local = list_gallery.extension_query(query)["results"][0]
resp_ext = mirror_gallery.extension_query(query)["results"][0]


meta_local = reduceResultMeta(resp_local["resultMetadata"])
meta_ext = reduceResultMeta(resp_ext["resultMetadata"])

missing_local, missing_ext = diff_query_results(resp_local, resp_ext)

pass
