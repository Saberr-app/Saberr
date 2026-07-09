from datetime import datetime

from config import config
from utils.helpers.text_helpers import get_human_readable_time, get_human_readable_size, shorten_text
from constants import ExternalLink, NotificationLevel


def construct_discord_webhook_payload_for_processing_finished(
        anime_title: str,
        anilist_id: int,
        mal_id: int | None,
        nyaa_id: str,
        tvdb_series_id: int | None,
        season_number: int,
        anime_episode_number: int,
        tvdb_episode_numbers: list[int],
        tvdb_episode_part: int | None,
        tvdb_episode_title: str | None,
        tvdb_episode_overview: str | None,
        destination_path: str,
        release_group: str,
        release_title: str,
        file_size_bytes: int | None,
        file_extension: str,
        resolution: str,
        encoding: str,
        resolved_audio_languages: list[str],
        resolved_duration_seconds: int | None,
        resolved_source: str | None,
        is_an_upgrade: bool,
        poster_url: str | None,
        episode_image_url: str | None,
        banner_url: str | None,
        anilist_rating: int | None,
        time: datetime,
) -> dict:
    base_url = config.user_settings.published_url
    saberr_url = (base_url.rstrip('/') + f"/browse?anilist_id={anilist_id}") if base_url else None
    anilist_url = ExternalLink.ANILIST_ANIME.format(id=str(anilist_id))
    mal_url = ExternalLink.MAL_ANIME.format(id=str(mal_id)) if mal_id else None
    nyaa_url = ExternalLink.NYAA_TORRENT.format(id=nyaa_id)
    links_str = f"[Anilist]({anilist_url}) • [MyAnimeList]({mal_url}) • [Nyaa]({nyaa_url})"
    if tvdb_series_id:
        tvdb_series_url = ExternalLink.TVDB_SERIES.format(id=str(tvdb_series_id))
        links_str += f" • [TheTVDB]({tvdb_series_url})"

    specs_str = (f"File: `{file_extension.upper()}` • `{get_human_readable_size(file_size_bytes)}`"
                 f"\nVideo: `{resolution}` • `{encoding}`")
    if resolved_source:
        specs_str += f" • `{resolved_source}`"
    if resolved_duration_seconds is not None:
        specs_str += f" • `{get_human_readable_time(resolved_duration_seconds)}`"
    if resolved_audio_languages:
        specs_str += "\nAudio: " + " • ".join(f"`{lang.upper()}`" for lang in resolved_audio_languages)

    tvdb_episode_str = ""
    if tvdb_episode_numbers:
        season_number_str = str(season_number)
        if len(tvdb_episode_numbers) == 1:
            episode_number_str = str(tvdb_episode_numbers[0])
        else:
            episode_number_str = "-".join(str(num) for num in tvdb_episode_numbers)
        tvdb_episode_str = f"Season {season_number_str} ⨯ Episode {episode_number_str}"
        if tvdb_episode_part:
            tvdb_episode_str += f" Part {tvdb_episode_part}"
        if tvdb_episode_title:
            tvdb_episode_str += f" - {tvdb_episode_title}"
    episode_str = f"Episode {str(anime_episode_number)}"

    if is_an_upgrade:
        embed_description = f"Upgraded release."
        embed_color = 0x304EB6
    else:
        embed_description = f"New release."
        embed_color = 0x4BA049

    fields = [
        {"name": "Episode", "value": episode_str, "inline": False},
        {"name": "TVDB Episode", "value": tvdb_episode_str, "inline": False},
    ]
    if tvdb_episode_overview:
        fields.append({"name": "Overview", "value": shorten_text(tvdb_episode_overview, 500), "inline": False})
    fields.extend([
        {"name": "Specs", "value": specs_str, "inline": False},
        {"name": "Release group", "value": release_group, "inline": False},
        {"name": "Release title", "value": f"```{release_title}```", "inline": False},
        {"name": "Import destination", "value": f"`{destination_path}`", "inline": False},
        {"name": "Links", "value": links_str, "inline": False},
    ])

    embed = {
        "title": shorten_text(anime_title, 250) + f" - E{anime_episode_number:02d}",
        "author": {"name": f"Saberr"},
        "description": embed_description,
        "color": embed_color,
        "fields": fields,
        "timestamp": time.isoformat(),
    }
    if saberr_url:
        embed["url"] = saberr_url
    if poster_url:
        embed["thumbnail"] = {"url": poster_url}
    if episode_image_url:
        embed["image"] = {"url": episode_image_url}
    elif banner_url:
        embed["image"] = {"url": banner_url}
    if anilist_rating is not None:
        embed["footer"] = {"text": f"Anilist rating: {anilist_rating / 10}/10"}

    return {
        "embeds": [embed],
    }


def construct_discord_webhook_payload_for_notification(notification_id: int,
                                                       description: str,
                                                       level: NotificationLevel,
                                                       fields: list[dict[str, str]],
                                                       title: str,
                                                       time: datetime) -> dict:
    fields = [{"name": field["name"], "value": field["value"], "inline": False} for field in fields
              if field['value']]
    if base_url := config.user_settings.published_url:
        saberr_url = base_url.rstrip('/') + f"/notifications?notification_id={notification_id}"
        fields.append({"name": f"Saberr", "value": f"[Go to dashboard]({saberr_url})", "inline": False})
    content = None
    match level:
        case NotificationLevel.INFO:
            color = 0x4971A0
        case NotificationLevel.WARNING:
            color = 0xD65F45
        case NotificationLevel.ERROR:
            color = 0xB63030
            if config.user_settings.discord_user_id:
                content = f"<@{config.user_settings.discord_user_id}>"
        case _:
            raise ValueError(f"Unknown notification level: {level}")
    return {
        "embeds": [{
            "author": {"name": f"Saberr"},
            "title": shorten_text(title, 250),
            "description": description,
            "color": color,
            "fields": fields,
            "timestamp": time.isoformat(),
        }],
    } | ({"content": content} if content else {})
