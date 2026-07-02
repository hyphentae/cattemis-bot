"""Artist link management for Cattemis Bot.

Loads artist art URLs from ``artists.json`` and exposes a helper to pick a
random link, optionally filtered by artist ID.

artists.json format::

    {
      "artists": [
        {
          "id": "artist_handle",
          "label": "Display Name",
          "enabled": true,
          "urls": ["https://example.com/art1.jpg", ...]
        }
      ]
    }
"""

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtistLink:
    """A single artwork URL associated with an artist."""

    artist_id: str
    label: str
    url: str


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def load_artists_config(config_path: Path) -> list[ArtistLink]:
    """Load and parse *config_path* (artists.json).

    Returns an empty list (without raising) if the file does not exist.
    """
    if not config_path.exists():
        logger.warning("artists.json not found at %s — /art won't work", config_path)
        return []

    with config_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    artists = data.get("artists") or []
    links: list[ArtistLink] = []

    for artist in artists:
        if not artist.get("enabled", True):
            continue

        artist_id = str(artist.get("id") or "").strip()
        label = str(artist.get("label") or artist_id or "artist").strip()

        for raw_url in artist.get("urls") or []:
            url = _normalize_url(str(raw_url))
            if url:
                links.append(ArtistLink(artist_id=artist_id, label=label, url=url))

    logger.info("Artists loaded: %d links from %s", len(links), config_path)
    return links


# ---------------------------------------------------------------------------
# Random picker
# ---------------------------------------------------------------------------

def random_artist_link(
    artists: list[ArtistLink],
    artist_id: str | None = None,
) -> ArtistLink | None:
    """Return a random ``ArtistLink``, optionally filtered by *artist_id*.

    Returns None if no matching links are available.
    """
    if not artists:
        return None

    if artist_id:
        candidates = [lnk for lnk in artists if lnk.artist_id.lower() == artist_id.lower()]
        return random.choice(candidates) if candidates else None

    return random.choice(artists)
