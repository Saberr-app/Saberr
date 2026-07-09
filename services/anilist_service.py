import re
from datetime import datetime
from typing import Iterable

from common.exceptions import ExternalServiceException
from config import config
from constants import AnilistAnimeSeason, AnilistAnimeUserStatus, AnilistAnimeStatus, AnilistAnimeFormat, \
    AnilistAnimeSource
from dto.anilist import AnilistDate
from system import UNSET
from services import ThirdPartyService


class AnilistService(ThirdPartyService):
    BASE_URL = "https://graphql.anilist.co"

    def __init__(self):
        super().__init__()

    @property
    def user_token(self) -> str | None:
        return config.user_settings.anilist_user_token

    async def get_future_airing_schedule(self, anilist_anime_ids: list[int]) -> list[dict]:
        self.logger.debug(f"Getting future airing schedule for {anilist_anime_ids}")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.FUTURE_AIRING_SCHEDULE),
                                           "variables": {
                                               "idIn": anilist_anime_ids
                                           }
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        return self._process_response(response)["data"]["Page"]["media"]

    async def get_airing_schedule(self, anilist_anime_ids: list[int],
                                  datetime_greater_than: datetime | None = None,
                                  datetime_less_than: datetime | None = None,
                                  episode_greater_than: int | None = None,
                                  episode_less_than: int | None = None,
                                  page: int = 1) -> list[dict]:
        self.logger.debug(f"Getting airing schedule for {anilist_anime_ids}.")
        variables = {"mediaIdIn": anilist_anime_ids, "page": page}
        if datetime_greater_than is not None:
            variables["airingAtGreater"] = int(datetime_greater_than.timestamp())
        if datetime_less_than is not None:
            variables["airingAtLesser"] = int(datetime_less_than.timestamp())
        if episode_greater_than is not None:
            variables["episodeGreater"] = episode_greater_than
        if episode_less_than is not None:
            variables["episodeLesser"] = episode_less_than
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.AIRING_SCHEDULE),
                                           "variables": variables
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        return self._process_response(response)["data"]["Page"]["airingSchedules"]

    async def get_anime_data(self, anilist_anime_ids: list[int]) -> list[dict]:
        if not anilist_anime_ids:
            return []
        self.logger.debug(f"Getting anime data for {anilist_anime_ids}")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.ANIME_DATA_BY_IDS),
                                           "variables": {
                                               "idIn": anilist_anime_ids,
                                           }
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        return self._process_response(response)["data"]["Page"]["media"]

    async def get_anime_extra_data(self, anilist_id: int) -> dict:
        if not anilist_id:
            return {}
        self.logger.debug(f"Getting anime extra data for {anilist_id}")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.ANIME_EXTRA_DATA),
                                           "variables": {
                                               "mediaId": anilist_id,
                                           }
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        return self._process_response(response)["data"]["Media"]

    async def search_anime(self,
                           query: str | None = None,
                           statuses: list[AnilistAnimeStatus] | None = None,
                           season: AnilistAnimeSeason | None = None,
                           season_year: int | None = None,
                           formats: list[AnilistAnimeFormat] | None = None,
                           sources: list[AnilistAnimeSource] | None = None,
                           genres: list[str] | None = None,
                           tags: list[str] | None = None,
                           exclude_genres: list[str] | None = None,
                           exclude_tags: list[str] | None = None,
                           on_list: bool | None = None,
                           per_page: int = 50,
                           page: int = 1,
                           sort: list[str] | None = None,
                           include_all_media_fields: bool = True,
                           force_fetch: bool = False) -> list[dict]:
        self.logger.debug("Searching anime")
        variables: dict = {"perPage": per_page}
        if query:
            variables["search"] = query
        if statuses:
            variables["statusIn"] = [status.value for status in statuses]
        if season:
            variables["season"] = season.value
        if season_year:
            variables["seasonYear"] = season_year
        if formats:
            variables["formatIn"] = [format_.value for format_ in formats]
        if sources:
            variables["sourceIn"] = [source.value for source in sources]
        if genres:
            variables["genreIn"] = genres
        if tags:
            variables["tagIn"] = tags
        if exclude_genres:
            variables["genreNotIn"] = exclude_genres
        if exclude_tags:
            variables["tagNotIn"] = exclude_tags
        if on_list is not None and self.user_token:
            variables["onList"] = on_list
        if page:
            variables["page"] = page
        if sort:
            variables["sort"] = sort

        if include_all_media_fields:
            query = self.Queries.ANIME_SEARCH.replace("{full_media_fields}", self.Queries.FULL_MEDIA_FIELDS)
        else:
            query = self.Queries.ANIME_SEARCH.replace("{full_media_fields}", "id")

        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(query),
                                           "variables": variables
                                       },
                                       force_fetch=force_fetch,
                                       cache_duration=60 * 60 * 6,
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        return self._process_response(response)["data"]["Page"]["media"]

    async def multi_search_anime(self, queries: Iterable[str],
                                 force_fetch: bool = False) -> dict[str, dict]:
        self.logger.debug(f"Multi-searching anime: {queries}")
        if not queries:
            return {}
        queries = list(set(queries))
        full_query = self._build_multi_search_query(queries)
        response = await self._request("POST",
                                       self.BASE_URL,
                                       json_={"query": self._minify_query(full_query),
                                              "variables": {f"search{i}": query
                                                            for i, query in enumerate(queries)}},
                                       force_fetch=force_fetch,
                                       cache_duration=60 * 60 * 6,
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        response = self._process_response(response)
        result = {}
        for i, query in enumerate(queries):
            results = (response["data"].get(f"anime{i}") or {}).get("results") or []
            result[query] = results[0] if results else None
        return result

    def _build_multi_search_query(self, queries: list[str]) -> str:
        query_parts = []
        params = []
        for i, query in enumerate(queries):
            query_parts.append(self.Queries.ANIME_SEARCH_MULTI_PART.replace("{idx}", str(i)).strip())
            params.append(f"$search{i}: String")
        full_query = self.Queries.ANIME_SEARCH_MULTI \
            .replace('{parts}', "\n".join(query_parts)) \
            .replace('{params}', ", ".join(params)).strip()
        return full_query

    async def get_user_anime_list(self, username: str,
                                  fetch_full_anime_data: bool = False) -> list[dict]:
        if not self.user_token:
            raise ExternalServiceException("User token is required to access user anime lists.")
        self.logger.debug(f"Getting user anime list for {username}")
        query = self.Queries.USER_ANIME_LIST
        if fetch_full_anime_data:
            query = query.replace("{media_placeholder}", f"media {{ {self.Queries.FULL_MEDIA_FIELDS} }}")
        else:
            query = query.replace("{media_placeholder}", "")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(query),
                                           "variables": {"username": username,
                                                         "format": config.user_settings.user_score_format.value}
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        return self._process_response(response)["data"]["MediaListCollection"]["lists"]

    async def get_user_anime_list_entry(self, anilist_id: int, fetch_full_anime_data: bool = False) -> dict:
        if not self.user_token:
            raise ExternalServiceException("User token is required to access user anime list entries.")
        self.logger.debug(f"Getting user anime list entry for anime {anilist_id}")
        query = self.Queries.USER_ANIME_ENTRY
        if fetch_full_anime_data:
            query = query.replace("{media_placeholder}", f"media {{ {self.Queries.FULL_MEDIA_FIELDS} }}")
        else:
            query = query.replace("{media_placeholder}", "")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(query),
                                           "variables": {"mediaId": anilist_id,
                                                         "format": config.user_settings.user_score_format.value}
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        return self._process_response(response)["data"]["Media"]["mediaListEntry"]

    async def update_anime_list_entry(self,
                                      anilist_anime_id: int,
                                      status: AnilistAnimeUserStatus | None,
                                      progress: int | None,
                                      score: float | int | None,
                                      repeat: int | None = None,
                                      started_at: AnilistDate | None = None,
                                      completed_at: AnilistDate | None = None,
                                      private: bool | None = None,
                                      notes: str | None = UNSET) -> dict:
        if not self.user_token:
            raise ExternalServiceException("User token is required to update anime list entries.")
        self.logger.debug(f"Updating anime list entry for {anilist_anime_id}")
        update_body = dict()
        if status is not None:
            update_body["status"] = status.value
        if progress is not None:
            update_body["progress"] = progress
        if score is not None:
            update_body["score"] = score
        if repeat is not None:
            update_body["repeat"] = repeat
        if started_at is not None:
            update_body["startedAt"] = {
                "year": started_at.year,
                "month": started_at.month,
                "day": started_at.day
            }
        if completed_at is not None:
            update_body["completedAt"] = {
                "year": completed_at.year,
                "month": completed_at.month,
                "day": completed_at.day
            }
        if private is not None:
            update_body["private"] = private
        if notes is not UNSET:
            update_body["notes"] = notes
        update_body |= {"mediaId": anilist_anime_id,
                        "format": config.user_settings.user_score_format.value}

        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.UPDATE_ANIME_LIST_ENTRY),
                                           "variables": update_body
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        # id, mediaId, status, progress, score, repeat, startedAt, completedAt, private, notes
        return self._process_response(response)["data"]["SaveMediaListEntry"]

    async def batch_update_anime_list_entries(self,
                                              anilist_anime_ids: list[int],
                                              status: AnilistAnimeUserStatus | None = None,
                                              score: float | int | None = None,
                                              repeat: int | None = None,
                                              started_at: AnilistDate | datetime | None = None,
                                              completed_at: AnilistDate | datetime | None = None) -> list[dict]:
        if not self.user_token:
            raise ExternalServiceException("User token is required to update anime list entries.")
        self.logger.debug(f"Updating anime list entries for {anilist_anime_ids}")
        if not anilist_anime_ids:
            return []
        variables: dict = ({f"mediaId{i}": anilist_anime_id
                            for i, anilist_anime_id in enumerate(anilist_anime_ids)}
                           | {"format": config.user_settings.user_score_format.value})
        if status is not None:
            variables["status"] = status.value
        if score is not None:
            variables["score"] = score
        if repeat is not None:
            variables["repeat"] = repeat
        if started_at is not None:
            variables["startedAt"] = {
                "year": started_at.year,
                "month": started_at.month,
                "day": started_at.day
            }
        if completed_at is not None:
            variables["completedAt"] = {
                "year": completed_at.year,
                "month": completed_at.month,
                "day": completed_at.day
            }

        full_query = self._build_multi_update_query(len(anilist_anime_ids))
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(full_query),
                                           "variables": variables
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        response = self._process_response(response)
        return [response["data"][f"e{i}"] for i in range(len(anilist_anime_ids))]

    def _build_multi_update_query(self, count: int) -> str:
        query_parts = []
        params = []
        for i in range(count):
            query_parts.append(self.Queries.UPDATE_ANIME_LIST_ENTRY_MULTI_PART.replace("{idx}", str(i)))
            params.append(f"$mediaId{i}: Int")
        full_query = self.Queries.UPDATE_ANIME_LIST_ENTRY_MULTI \
            .replace('{parts}', "".join(query_parts)) \
            .replace('{params}', ", ".join(params))
        return full_query

    async def delete_anime_list_entry(self, list_entry_id: int) -> bool:
        if not self.user_token:
            raise ExternalServiceException("User token is required to delete anime list entries.")
        self.logger.debug(f"Deleting anime list entry for {list_entry_id}")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.DELETE_ANIME_LIST_ENTRY),
                                           "variables": {
                                               "id": list_entry_id
                                           }
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        return self._process_response(response)["data"]["DeleteMediaListEntry"]["deleted"]

    async def batch_delete_anime_list_entries(self, list_entry_ids: list[int]):
        if not self.user_token:
            raise ExternalServiceException("User token is required to delete anime list entries.")
        self.logger.debug(f"Deleting anime list entries for {list_entry_ids}")
        if not list_entry_ids:
            return []
        variables = {f"id{i}": list_entry_id for i, list_entry_id in enumerate(list_entry_ids)}
        full_query = self._build_multi_delete_query(len(list_entry_ids))
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(full_query),
                                           "variables": variables
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"})
        self._process_response(response)

    def _build_multi_delete_query(self, count: int) -> str:
        query_parts = []
        params = []
        for i in range(count):
            query_parts.append(self.Queries.DELETE_ANIME_LIST_ENTRY_MULTI_PART.replace("{idx}", str(i)))
            params.append(f"$id{i}: Int")
        full_query = self.Queries.DELETE_ANIME_LIST_ENTRY_MULTI \
            .replace('{parts}', "".join(query_parts)) \
            .replace('{params}', ", ".join(params))
        return full_query

    async def get_user_data(self, token: str | None = None) -> dict:
        if not self.user_token and not token:
            raise ExternalServiceException("User token is required to get username.")
        self.logger.debug("Getting user data")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.GET_USER_DATA),
                                       },
                                       headers={"Authorization": f"Bearer {token or self.user_token}"})
        return self._process_response(response)["data"]["Viewer"]

    async def get_genre_and_tag_collections(self) -> tuple[list[str], list[dict]]:
        self.logger.debug("Getting genre and tag collections")
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.GENRE_AND_TAG_COLLECTIONS),
                                       },
                                       headers={"Authorization": f"Bearer {self.user_token}"}
                                       if self.user_token else None)
        data = self._process_response(response)["data"]
        return data["GenreCollection"], data["MediaTagCollection"]

    async def healthcheck(self, with_auth: bool, token: str | None = None):
        headers = {"Authorization": f"Bearer {token or self.user_token}"} if with_auth else {}
        response = await self._request("POST", self.BASE_URL,
                                       json_={
                                           "query": self._minify_query(self.Queries.HEALTHCHECK),
                                       },
                                       headers=headers)
        if response.status_code not in range(200, 300):
            if response.status_code in range(400, 500):
                try:
                    error_message = " | ".join([error.get("message", "No message")
                                                for error in response.json["errors"]])
                except:
                    error_message = f"Non-JSON response: {response.text}"
            else:
                error_message = "Anilist is down"
            raise ExternalServiceException(detail=error_message,
                                           status_code=response.status_code)

    class Queries:
        FUTURE_AIRING_SCHEDULE = """
        query AiringSchedule($idIn: [Int]) {
          Page {
            media(id_in: $idIn) {
              airingSchedule(notYetAired: true, perPage: 25) {
                nodes {
                  airingAt
                  episode
                }
              }
              id
            }
          }
        }
        """
        AIRING_SCHEDULE = """
        query AiringSchedules(
          $mediaIdIn: [Int]
          $episodeLesser: Int
          $episodeGreater: Int
          $airingAtLesser: Int
          $airingAtGreater: Int
          $page: Int
        ) {
          Page(page: $page, perPage: 50) {
            airingSchedules(
              mediaId_in: $mediaIdIn
              episode_lesser: $episodeLesser
              episode_greater: $episodeGreater
              airingAt_lesser: $airingAtLesser
              airingAt_greater: $airingAtGreater
              sort: ID
            ) {
              episode
              airingAt
              mediaId
            }
          }
        }
        """

        FULL_MEDIA_FIELDS = """
              id
              title {
                english
                native
                romaji
              }
              description
              season
              seasonYear
              episodes
              duration
              source
              status
              averageScore
              meanScore
              popularity
              format
              countryOfOrigin
              hashtag
              synonyms
              idMal
              startDate {
                day
                month
                year
              }
              endDate {
                day
                month
                year
              }
              genres
              tags {
                name
                rank
                isMediaSpoiler
                isGeneralSpoiler
              }
              isAdult
              nextAiringEpisode {
                episode
                timeUntilAiring
                airingAt
              }
              studios {
                edges {
                  node {
                    name
                    siteUrl
                  }
                  isMain
                }
              }
              trailer {
                site
                id
              }
              bannerImage
              coverImage {
                extraLarge
                large
                medium
              }
              externalLinks {
                url
                site
              }
        """

        ANIME_DATA_BY_IDS = """
        query Media($idIn: [Int]) {
          Page {
            media(id_in: $idIn, type: ANIME) {
              {full_media_fields}
            }
          }
        }
        """.replace("{full_media_fields}", FULL_MEDIA_FIELDS)
        ANIME_SEARCH = """
        query Page(
          $search: String
          $statusIn: [MediaStatus]
          $season: MediaSeason
          $seasonYear: Int
          $formatIn: [MediaFormat]
          $sourceIn: [MediaSource]
          $genreIn: [String]
          $tagIn: [String]
          $genreNotIn: [String]
          $tagNotIn: [String]
          $onList: Boolean
          $page: Int
          $perPage: Int
          $sort: [MediaSort]
        ) {
          Page(page: $page, perPage: $perPage) {
            media(
              seasonYear: $seasonYear
              season: $season
              type: ANIME
              sort: $sort
              format_in: $formatIn
              status_in: $statusIn
              genre_in: $genreIn
              tag_in: $tagIn
              genre_not_in: $genreNotIn
              tag_not_in: $tagNotIn
              source_in: $sourceIn
              onList: $onList
              search: $search
              isAdult: false
            ) {
              {full_media_fields}
            }
          }
        }
        """
        ANIME_SEARCH_MULTI = """
        query SearchMultipleAnime ({params}) {
          {parts}
        }
        """
        ANIME_SEARCH_MULTI_PART = """
          anime{idx}: Page(perPage: 1) {
            results: media(search: $search{idx}, type: ANIME, isAdult: false) {
              id
              title {
                english
                romaji
                native
              }
            }
          }
        """
        ANIME_EXTRA_DATA = """
        query MediaExtras($mediaId: Int) {
          Media(id: $mediaId) {
            characters(sort: FAVOURITES_DESC) {
              edges {
                node {
                  image {
                    large
                  }
                  name {
                    full
                  }
                  siteUrl
                }
                role
                voiceActorRoles(language: JAPANESE, sort: RELEVANCE) {
                  voiceActor {
                    image {
                      large
                    }
                    name {
                      full
                    }
                    siteUrl
                  }
                }
              }
            }
            relations {
              edges {
                node {
                  id
                  coverImage {
                    large
                  }
                  title {
                    english
                    native
                    romaji
                  }
                  format
                }
                relationType
              }
            }
            staff(sort: RELEVANCE) {
              edges {
                role
                node {
                  image {
                    large
                  }
                  name {
                    full
                  }
                  siteUrl
                }
              }
            }
          }
        }
        """

        USER_ANIME_LIST = """
        query ($username: String, $format: ScoreFormat) {
          MediaListCollection(
            type: ANIME
            forceSingleCompletedList: true
            userName: $username
          ) {
            lists {
              entries {
                id
                mediaId
                progress
                score(format: $format)
                startedAt {
                  year
                  month
                  day
                }
                completedAt {
                  year
                  month
                  day
                }
                private
                repeat
                status
                notes
                {media_placeholder}
              }
              status
              isCustomList
            }
          }
        }
        """
        USER_ANIME_ENTRY = """
        query MediaListEntry($mediaId: Int, $format: ScoreFormat) {
          Media(id: $mediaId) {
            mediaListEntry {
              id
              mediaId
              progress
              score(format: $format)
              startedAt {
                year
                month
                day
              }
              completedAt {
                year
                month
                day
              }
              private
              repeat
              status
              notes
              {media_placeholder}
            }
          }
        }
        """
        UPDATE_ANIME_LIST_ENTRY = """
        mutation SaveMediaListEntry(
          $mediaId: Int
          $status: MediaListStatus
          $progress: Int
          $score: Float
          $repeat: Int
          $private: Boolean
          $notes: String
          $startedAt: FuzzyDateInput
          $completedAt: FuzzyDateInput
          $format: ScoreFormat
        ) {
          SaveMediaListEntry(
            mediaId: $mediaId
            status: $status
            progress: $progress
            score: $score
            repeat: $repeat
            private: $private
            notes: $notes
            startedAt: $startedAt
            completedAt: $completedAt
          ) {
            id
            mediaId
            status
            progress
            score(format: $format)
            startedAt {
              year
              month
              day
            }
            completedAt {
              year
              month
              day
            }
            private
            notes
            repeat
          }
        }
        """
        UPDATE_ANIME_LIST_ENTRY_MULTI = """
        fragment mediaListFragment on MediaList {
          id
          mediaId
          status
          progress
          score(format: $format)
          completedAt {
            year
            month
            day
          }
          startedAt {
            year
            month
            day
          }
          private
          notes
          repeat
        }
        mutation SaveMediaListEntry(
          {params}
          $status: MediaListStatus
          $score: Float
          $startedAt: FuzzyDateInput
          $completedAt: FuzzyDateInput
          $repeat: Int
          $format: ScoreFormat
        ) {
          {parts}
        }
        """
        UPDATE_ANIME_LIST_ENTRY_MULTI_PART = """
        e{idx}: SaveMediaListEntry( 
            mediaId: $mediaId{idx}
            status: $status
            score: $score
            startedAt: $startedAt
            completedAt: $completedAt
            repeat: $repeat
          ) {
            ...mediaListFragment
          }
        """
        DELETE_ANIME_LIST_ENTRY = """
        mutation DeleteMediaListEntry($id: Int) {
          DeleteMediaListEntry(id: $id) {
            deleted
          }
        }
        """
        DELETE_ANIME_LIST_ENTRY_MULTI = """
        mutation DeleteMediaListEntry({params}) {
        {parts}
        }
        """
        DELETE_ANIME_LIST_ENTRY_MULTI_PART = """
          e{idx}: DeleteMediaListEntry(id: $id{idx}) {
            deleted
          }
        """
        GET_USER_DATA = """
        query Viewer {
          Viewer {
            name
            options {
              titleLanguage
            }
            mediaListOptions {
              scoreFormat
            }
            avatar {
              medium
            }
            bannerImage
            statistics {
              anime {
                statuses {
                  count
                  status
                }
                meanScore
              }
            }
            siteUrl
            moderatorRoles
          }
        }
        """

        GENRE_AND_TAG_COLLECTIONS = """
        query GenreAndMediaTagCollections {
          MediaTagCollection {
            name
            category
          }
          GenreCollection
        }
        """
        HEALTHCHECK = """
        query Media {
          Media(id: 1) {
            id
          }
        }
        """

    @staticmethod
    def _minify_query(query: str) -> str:
        return re.sub(r"\s+", " ", query).strip()

    # noinspection PyMethodMayBeStatic
    def _process_response(self, response):
        if response.status == 404:
            raise ExternalServiceException("Not found",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status == 400:
            errors = ",".join([error["message"]
                               for error in (response.json.get("errors") or [])
                               if error and isinstance(error, dict) and error.get("message")])
            raise ExternalServiceException(f"Bad request: {errors}",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers,
                                           })
        elif response.status in [401, 403]:
            raise ExternalServiceException("Unauthorized",
                                           status_code=response.status)
        elif response.status == 429:
            raise ExternalServiceException("Rate limit exceeded, try again later",
                                           status_code=response.status)
        elif response.status >= 500:
            raise ExternalServiceException("AniList is down",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "status": response.status,
                                               "content": response.text,
                                               "headers": response.headers
                                           })
        elif response.status != 200:
            raise ExternalServiceException(f"Unhandled response from Anilist ({response.status}): {response.text}",
                                           status_code=response.status,
                                           debug_info={
                                               "url": response.url,
                                               "content": response.text,
                                               "headers": response.headers
                                           })

        return response.json
