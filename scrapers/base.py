from abc import ABC, abstractmethod
from typing import List
from models.result import SearchResult

class BaseScraper(ABC):
    def __init__(self, page):
        self.page = page

    @abstractmethod
    async def search(self, query: str) -> List[SearchResult]:
        pass
