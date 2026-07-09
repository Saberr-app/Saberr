__all__ = ['main']

import asyncio
import io
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import aiohttp

RELATIONS_DIR = Path(__file__).parent.parent.parent / 'data' / 'relations'


@dataclass
class AnilistEpisodeCount:
    anilist_id: int
    episode_count: int
    expires_at: int

    def serialize(self) -> str:
        return f"{self.anilist_id}:{self.episode_count}:{self.expires_at}"


async def get_anilist_ids() -> set[int]:
    file_path = RELATIONS_DIR / 'anime-relations.txt'
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as handle:
        iterator = io.StringIO(await handle.read())

    anilist_ids = set()
    pattern = re.compile(r'^-\s*(?:\d+|[?~])\|(?:\d+|[?~])\|(?P<left>\d+|[?~])'
                         r':.*->\s*(?:\d+|[?~])\|(?:\d+|[?~])\|(?P<right>\d+|[?~]):')

    for line in iterator:
        match = pattern.match(line.strip())
        if not match:
            continue
        left_id = match.group('left')
        right_id = match.group('right')
        if left_id.isdigit():
            anilist_ids.add(int(left_id))
        if right_id.isdigit():
            anilist_ids.add(int(right_id))

    return anilist_ids


async def get_existing_episode_counts() -> dict[int, AnilistEpisodeCount]:
    file_path = RELATIONS_DIR / 'anime-relations-anilist-episode-count.txt'
    if not file_path.exists():
        return {}
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as handle:
        iterator = io.StringIO(await handle.read())

    episode_counts = {}
    pattern = re.compile(r'^(?P<id>\d+):(?P<count>\d+):(?P<expires>\d+)$')

    for line in iterator:
        match = pattern.match(line.strip())
        if not match:
            continue
        anilist_id = int(match.group('id'))
        episode_count = int(match.group('count'))
        expires_at = int(match.group('expires'))
        episode_counts[anilist_id] = AnilistEpisodeCount(
            anilist_id=anilist_id,
            episode_count=episode_count,
            expires_at=expires_at
        )

    return episode_counts


def get_anilist_date(fuzzy_date: dict) -> datetime | None:
    if not fuzzy_date or not fuzzy_date.get('year'):
        return None
    year = fuzzy_date['year']
    month = fuzzy_date.get('month', 1)
    day = fuzzy_date.get('day', 1)
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


async def _main():
    anilist_ids = await get_anilist_ids()
    existing_counts = await get_existing_episode_counts()
    now = datetime.now()

    ids_to_fetch = [anilist_id for anilist_id in anilist_ids
                    if anilist_id not in existing_counts
                    or existing_counts[anilist_id].expires_at < now.timestamp()]
    ids_to_fetch.sort()

    batch_size = 50
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(ids_to_fetch), batch_size):
            batch_ids = ids_to_fetch[i:i + batch_size]
            async with session.post(
                "https://graphql.anilist.co",
                json={
                    "query": """
                    query ($ids: [Int]) {
                      Page(perPage: 50, page: 1) {
                        media(id_in: $ids, type: ANIME) {
                          id
                          episodes
                          endDate {
                            day
                            month
                            year
                          }
                          startDate {
                            year
                            month
                            day
                          }
                        }
                      }
                    }
                    """,
                    "variables": {"ids": batch_ids}
                }
            ) as response:
                response = await response.json()
            for media in response['data']['Page']['media']:
                anilist_id = media['id']
                episode_count = media['episodes'] or 0
                start_date = get_anilist_date(media['startDate'])
                end_date = get_anilist_date(media['endDate'])
                if not episode_count:
                    if start_date:
                        if start_date > now:
                            expires_at = min(now + timedelta(weeks=1), start_date - timedelta(weeks=1))
                        else:
                            expires_at = now + timedelta(days=3)
                    else:
                        expires_at = now + timedelta(weeks=1)
                else:
                    if end_date:
                        if end_date < (now - timedelta(weeks=4)):
                            expires_at = now + timedelta(weeks=300)
                        elif end_date < now:
                            expires_at = now + timedelta(weeks=4)
                        else:
                            expires_at = min(now + timedelta(weeks=1), end_date - timedelta(weeks=1))
                    else:
                        expires_at = now + timedelta(weeks=1)
                existing_counts[anilist_id] = AnilistEpisodeCount(
                    anilist_id=anilist_id,
                    episode_count=episode_count,
                    expires_at=int(expires_at.timestamp())
                )
            if i + 50 < len(ids_to_fetch):
                await asyncio.sleep(1)

    file_path = RELATIONS_DIR / 'anime-relations-anilist-episode-count.txt'
    async with aiofiles.open(file_path,
                             'w',
                             encoding='utf-8') as handle:
        await handle.write('\n'.join(count.serialize() for count in existing_counts.values()))


async def main():
    try:
        await _main()
    except Exception as e:
        print(f"An error occurred while running anime relations episode count refresh script: {e}",
              traceback.format_exc())
