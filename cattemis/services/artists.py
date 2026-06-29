import json
import random
from dataclasses import dataclass

from ..config import ARTISTS_CONFIG_PATH
from ..media.links import normalize_possible_url


@dataclass
class ArtistLink:
    artist_id: str
    label: str
    url: str


_artists_cache: list[ArtistLink] = []


def load_artists_config() -> None:
    global _artists_cache

    if not ARTISTS_CONFIG_PATH.exists():
        print(f"[artists] файл {ARTISTS_CONFIG_PATH} не найден, /art работать не будет")
        _artists_cache = []
        return

    with ARTISTS_CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    artists = data.get("artists") or []
    links: list[ArtistLink] = []

    for artist in artists:
        if not artist.get("enabled", True):
            continue

        artist_id = str(artist.get("id") or "").strip()
        label = str(artist.get("label") or artist_id or "artist").strip()
        urls = artist.get("urls") or []

        for raw_url in urls:
            url = normalize_possible_url(str(raw_url))
            if not url:
                continue
            links.append(ArtistLink(artist_id=artist_id, label=label, url=url))

    _artists_cache = links
    print(f"[artists] загружено {len(_artists_cache)} ссылок")


def random_artist_link(artist_id: str | None = None) -> ArtistLink | None:
    if not _artists_cache:
        return None

    if artist_id:
        candidates = [l for l in _artists_cache if l.artist_id.lower() == artist_id.lower()]
        if not candidates:
            return None
        return random.choice(candidates)

    return random.choice(_artists_cache)
