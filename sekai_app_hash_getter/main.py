from sekai_app_hash_getter.const import *
from sekai_app_hash_getter.exceptions import UnableToFindVersion
from sekai_app_hash_getter.kv import CloudflareKV
from bs4 import BeautifulSoup
from tempfile import mkdtemp
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import requests
import shutil
import UnityPy
import os
import json
import cloudscraper


def get_app_ver(url: str):
    scraper = cloudscraper.create_scraper()
    req = scraper.get(
        url,
        headers=DEFAULT_HEADER,
    )
    content = req.text
    page = BeautifulSoup(content, features="html.parser")
    page_details = page.select_one("p[class=details_sdk] > span:not([class])")
    version = page_details.text  # type: ignore
    if not bool(SEMVER_PATTERN.search(version)):
        raise UnableToFindVersion(
            f"unable to find version, scraped version returned : {version}"
        )
    return version


def download(url: str, dest: Path):
    scraper = cloudscraper.create_scraper()
    req = scraper.get(
        url,
        headers=DEFAULT_HEADER,
    )
    with open(dest, "wb") as f:
        f.write(req.content)


def find_app_hash(data_dir: Path) -> Optional[str]:
    try:
        env = UnityPy.load(str((data_dir / "globalgamemanagers")))
        # find all external assets files
        # could maybe just find all files in the directory
        # but this is more sure-fire
        externals = env.assets[0].externals
        paths = [x.path for x in externals]
        for p in paths:
            env = UnityPy.load(str(data_dir / p))
            for obj in env.objects:
                if obj.type.name == "MonoBehaviour":
                    data = obj.read()
                    if data.name == "production_android":  # type: ignore
                        for match in re.finditer(UUID_PATTERN, str(data.raw_data)):  # type: ignore
                            return match.group()
        # didn't find anything, maybe they changed the location?
        return None
    except:
        return None


def main():
    load_dotenv()
    kv = CloudflareKV(os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_KEY"])
    old_ver_key = {"version": "0.0.0", "appHash": "none"}
    stored_key = kv.get(os.environ["CF_KV_NAMESPACE"], "app_hash")
    if stored_key is not None:
        old_ver_key = stored_key
    old_version = old_ver_key["version"]  # type: ignore
    print("checking for version")
    version = get_app_ver(APKPURE_PJSEKAI_URL)
    print(f"current version = {version}, stored version = {old_version}")
    if old_version.strip() != version.strip():
        print(f"updating to {version}...")
        temp_dir = Path(mkdtemp())
        sekai_unzipped_path = temp_dir / "sekai"
        sekai_unzipped_path.mkdir(exist_ok=True)
        print(f"downloading and unzipping {version}...")
        download(APKPURE_PJSEKAI_DL, temp_dir / "sekai.zip")
        shutil.unpack_archive(temp_dir / "sekai.zip", sekai_unzipped_path)
        print(f"searching for app hash...")
        app_hash = find_app_hash(sekai_unzipped_path / "assets" / "bin" / "Data")
        if app_hash is not None:
            kv.write(
                os.environ["CF_KV_NAMESPACE"],
                "app_hash",
                json.dumps({"version": version, "appHash": app_hash.strip()}),
                json.dumps({}),
            )
            print(f"updated to {version} - {app_hash}")
        else:
            print(f"failed to update to {version}")
        # clean up
        shutil.rmtree(temp_dir)
    else:
        print("latest version, no need to update")


if __name__ == "__main__":
    main()
