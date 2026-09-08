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
    phone_number: Optional[str] = None
    area: Optional[str] = None
    broker_type: Optional[str] = None
    images: Optional[str] = None

    def to_dict(self):
        return {
            'Source': self.source,
            'Title': self.title,
            'Price': self.price,
            'Area': self.area,
            'Phone Number': self.phone_number,
            'Location': self.location,
            'URL': self.url,
            'Description': self.description,
            'Broker Type': self.broker_type,
            'Images': self.images
        }
