from dataclasses import dataclass


@dataclass
class EpisodeCoverageStats:
    latest_known_episode_number: int | None
    processed_episode_count: int
    downloading_episode_count: int
    failed_episode_count: int

    total_episode_count: int | None
    covered_episodes: set[int]

    def has_unprocessed(self):  # includes missing, downloading, failed
        return self.total_episode_count is not None and self.total_episode_count > self.processed_episode_count

    @property
    def missing_episode_count(self):
        if self.total_episode_count is None:
            return 0
        return max(0,
                   self.total_episode_count
                   - self.processed_episode_count
                   - self.downloading_episode_count
                   - self.failed_episode_count)
