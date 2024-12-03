from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import math
from typing import Union

from dataclasses import dataclass, field

# Enum for DataSource
class DataSource(Enum):
    telegram = 1

# Source Chat Data
@dataclass
class SourceChatData:
    chat_id: int
    participants: list[str] = field(default_factory=list)
    contents: list[str] = field(default_factory=list)
    total_content_length: int = 0
    total_content_value: int = 0

    def timeliness_value(self) -> float:
        if self.total_content_length == 0:
            return 0
        # tav = (𝛴 litsi) / (𝛴 li)
        time_avg = self.total_content_value / self.total_content_length
        # a = ln(2) / thl
        half_life = 60  # 60 minutes
        time_decay = math.log(2) / half_life
        # t = exp(-atav)
        return math.exp(- time_decay * time_avg)  # range 0 to 1

    def thoughtfulness_of_conversation(self) -> float:
        n = len(self.participants)  # n: number of participants
        u = 2  # 𝜇: optimal number of participants
        d = 1  # 𝜎: standard deviation of the curve

        # Formula: p = exp(-(n-𝜇) / (2𝜎^2))
        return math.exp(-(n - u) / (2 * d ** 2))  # range 0 to 1

    def contextualness_of_conversation(self)  -> float:
        c = self.total_content_length #total token length, c, of the text data
        m = 2 #midpoint
        k = 1 #key parameters.
        # l=1/(1+exp(-k(c-c0)))
        return 1/(1 + math.exp(-k*(c-m)))

    def quality_score(self) -> float :
        a = 1 # factor
        b = 1 # factor
        c = 1 # factor
        t = self.timeliness_value()
        p = self.thoughtfulness_of_conversation()
        l = self.contextualness_of_conversation()
        return round((a*t + b*t + c*l)/(a+b+c),2)


    def content_as_text(self) -> str:
        """Converts contents to a single string with each entry on a new line."""
        return "\r".join(self.contents)

    def add_content(self, content: str, submission_in_minutes: int) -> None:
        """Adds a new content string to the contents list if it's not empty."""
        if content:
            content_len = len(content)
            self.total_content_length += content_len
            content_value = submission_in_minutes * content_len
            self.total_content_value += content_value
            self.contents.append(content)

    def add_participant(self, participant: str) -> None:
        """Adds a new participant to the participants list if it's not already present."""
        if participant and participant not in self.participants:
            self.participants.append(participant)

    def to_dict(self) -> dict:
        """Converts the object to a dictionary representation."""
        return {
            "chat_id": self.chat_id,
            "contents": self.content_as_text()
        }

# SourceData with enum and chat data
@dataclass
class SourceData:
    source: DataSource         # "telegram"
    user: str
    source_chats: List[SourceChatData]  # List of SourceChatData instances

    def __init__(self, source, user, source_chats=None):
        self.source = source
        self.user = user
        self.source_chats = source_chats or []

    def to_dict(self):
        return {
            "source": self.source.name,  # Use .name to convert enum to string
            "user": self.user,
            "chats": [source_chat.to_dict() for source_chat in self.source_chats]
        }


# ChatData for Source (final destination data structure)
@dataclass
class ChatData:
    chat_id: int
    chat_length: int

    sentiment: Dict[str, Any] = field(default_factory=dict)
    keywords_keybert: Dict[str, Any] = field(default_factory=dict)
    keywords_lda: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "chat_length": self.chat_length,
            "sentiment": self.sentiment,                # No need to call .to_dict() for dicts
            "keywords_keybert": self.keywords_keybert,  # Same for other dict fields
            "keywords_lda": self.keywords_lda           # Same for other dict fields
        }

# CargoData for Source
@dataclass
class CargoData:
    source_data: SourceData
    source_id: str
    chat_list: List[ChatData] = field(default_factory=list)

    def to_dict(self):
        # Return a dictionary representation of the CargoData object
        return {
            "source_data": self.source_data,  # Assuming source_data can be serialized directly
            "source_id": self.source_id,
            "chat_list": [chat.to_dict() for chat in self.chat_list]  # Convert each ChatData in the list to a dict
        }

    @staticmethod
    def convert_to_serializable(obj: Any) -> Any:
        if isinstance(obj, np.float32):
            return float(obj)  # Convert float32 to float
        elif isinstance(obj, dict):
            return {k: CargoData.convert_to_serializable(v) for k, v in obj.items()}  # Recursively handle dictionary values
        elif isinstance(obj, list):
            return [CargoData.convert_to_serializable(item) for item in obj]  # Recursively handle list items
        return obj  # Return the object if it's already serializable

    def get_chat_list_data(self) -> Any:
        # Convert each ChatData to dict and make sure all nested objects are serializable
        chat_list_data = [self.convert_to_serializable(chat_data.to_dict()) for chat_data in self.chat_list]
        return chat_list_data


# MetaData for Source
@dataclass
class MetaData:
    source_id: str
    dlp_id: str

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "dlp_id": self.dlp_id
        }
