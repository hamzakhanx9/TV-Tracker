from functools import lru_cache

from app.integrations.omdb import OmdbClient
from app.integrations.tmdb import TmdbClient
from app.integrations.tvmaze import TvmazeClient


@lru_cache
def get_tmdb_client() -> TmdbClient:
    return TmdbClient()


@lru_cache
def get_omdb_client() -> OmdbClient:
    return OmdbClient()


@lru_cache
def get_tvmaze_client() -> TvmazeClient:
    return TvmazeClient()
