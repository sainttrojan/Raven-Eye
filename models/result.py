from dataclasses import dataclass
from typing import Optional

@dataclass
class SearchResult:
    source: str
    title: str
    url: str
    price: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None

    def to_dict(self):
        return {
            'Source': self.source,
            'Title': self.title,
            'Price': self.price,
            'Location': self.location,
            'URL': self.url,
            'Description': self.description
        }
