import json, pathlib
from time import sleep
from typing import List

from src import *
from src.constants import GALLERY_API_ENDPOINT, MARKETPLACE_FQDN

local_path = pathlib.Path("examples/extensions.json")

query: GalleryExtensionQuery = {
    "filters": [
        {
            "criteria": [
                {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
                {"filterType": FilterType.ExcludeWithFlags, "value": 37888}
            ],
            "pageNumber": 1,
            "pageSize": 1000,
            "sortBy": SortBy.InstallCount,
            "sortOrder": SortOrder.Descending,
        }
    ],
    "assetTypes": [],
    "flags": GalleryFlags(870),
}

gallery = ExternalGallery()


def dedups(a: List[GalleryExtension]):
    uni = []
    dups = []
    for ext in a:
        id = ext["extensionId"]
        if id not in uni:
            uni.append(id)
            uni
        else:
            dups.append(ext)
    return dups


exts = {}
import requests

session = requests.session()
tfs_session = None
total = None
pages = []
while True:
  #  resp = mirror_gallery.extension_query(query, session=session)
  #Not sure if it helps setting the tfs session and using one requests session but trying to get all the pages
    req = session.post(
            gallery._src + "/extensionquery",
            headers={"Accept": "application/json;api-version=3.0-preview.1", "x-tfs-sessoion": tfs_session},
            json=query,
        )
    if tfs_session is None:
        tfs_session = req.headers["x-tfs-session"]
    resp = req.json()
    result = resp["results"][0]   
    pages.append(result["extensions"]) 
    if len(result["extensions"]) < query["filters"][0]["pageSize"]:
        break
    total_new = result['resultMetadata'][0]['metadataItems'][0]["count"]
    print(f'Got page: {query["filters"][0]["pageNumber"]} qty: {len(result["extensions"])} total: {total_new}')

    if total is not None and total != total_new:
        #Well we are either missing of having dups now due to stuff moving around lets try again
        query["filters"][0]["pageNumber"] = 1
        session = requests.session()
        total = None
        tfs_session = None
        sleep(1)
    else:        
        total = total_new
        query["filters"][0]["pageNumber"] += 1

for page in pages:
    for ext in page:
            exts[ext["extensionId"]] = ext
local_path.write_text(json.dumps(list(exts.values())))
