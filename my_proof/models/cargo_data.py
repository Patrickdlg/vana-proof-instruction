from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np

# Enum for DataSource
class DataSource(Enum):
    telegram = 1

# ChatData for Source
@dataclass
class SourceChatData:
    chat_id: int
    contents: str

    def __init__(self, chat_id, contents=None):
        self.chat_id = chat_id
        self.contents = contents

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "contents": self.contents
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