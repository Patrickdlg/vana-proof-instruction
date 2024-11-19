from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Enum for DataSource
class DataSource(Enum):
    Telegram = 1

# ChatData for Source
@dataclass
class SourceChatData:
    chat_id: int
    content: List[Any]  # Assuming content is a list of messages (could be strings, dictionaries, etc.)

    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "content": self.content
        }

    def get_chat_contents(self, data_source: DataSource) -> str:
        if not isinstance(self.content, list):  # Validate content is a list
            raise ValueError("Content must be a list of messages.")

        if data_source == DataSource.Telegram:

            # Ensure the `content` is iterable and extract texts from messages
            contents = [
                message["content"]["text"]["text"]
                for message in self.content
                if isinstance(message, dict)  # Ensure each item is a dictionary
                and "content" in message
                and message["content"].get("@type") == "messageText"
                and "text" in message["content"]
            ]
            return " ".join(contents)  # Combine messages with a space separator

        raise Exception(f"get_chat_contents: Unhandled data_source({data_source.name})")


# SourceData with enum and chat data
@dataclass
class SourceData:
    source: DataSource         # "telegram"
    user: str
    chat_data: List[SourceChatData]  # List of SourceChatData instances

    def to_dict(self):
        return {
            "source": self.source.name,  # Use .name to convert enum to string
            "user": self.user,
            "chat_data": [chat_data.to_dict() for chat_data in self.chat_data]
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

# MetaData for Source
@dataclass
class MetaData:
    source_id: str
    dlp_id: str
    chat_data_list: List[ChatData]

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "dlp_id": self.dlp_id,
            "chats": [chat_data.to_dict() for chat_data in self.chat_data_list]
        }

# CargoData for Source
@dataclass
class CargoData:
    source_data: SourceData
    source_id: str
    chat_data_list: List[ChatData]
