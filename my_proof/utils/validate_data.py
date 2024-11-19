from utils.data_registry import DataRegistry
from models.cargo_data import CargoData, ChatData
from typing import List

# Assuming the existence of these functions
from utils.feature_extraction import get_sentiment_data, get_keywords_keybert, get_keywords_lda

def get_registry_data(cargo_data: CargoData) -> List[ChatData]:
    provider_url = "https://your-vana-node-url"
    contract_address = "0xYourDataRegistryContractAddress"
    contract_abi = [
        # Include ABI JSON here
    ]

    # Create the client instance
    client = DataRegistry(
        provider_url,
        contract_address,
        contract_abi
    )

    # Fetch and filter data
    registry_chat_data = client.fetch_data(
        cargo_data.source_data.source,  # Assuming source_data contains source
        cargo_data.source_data.user
    )
    return registry_chat_data

def score_data(meta_data_list: List[ChatData], chat_id: int, content_length: int) -> float:
    if content_length == 0 or len(meta_data_list) == 0:
        return 0

    total_score = 0
    entry_count = 0

    for chat_data in meta_data_list:
        matched = chat_data.chat_id == chat_id
        if matched:
            entry_count += 1
            entry_len = chat_data.chat_length
            # Calculate score if content_length is greater than zero
            score = (content_length - entry_len) / content_length
            total_score += score

    if entry_count > 0:
        return total_score / entry_count

    return 1

def validate_data(cargo_data: CargoData) -> float:
    source_data = cargo_data.source_data
    source_chats = cargo_data.chat_data

    chat_list = []  # Initialize as a standard list
    total_score = 0
    chat_count = 0

    registry_chat_data = get_registry_data(cargo_data)
    # Loop through the chat_data_list
    for source_chat in source_chats:
        chat_count += 1  # Increment chat count
        source_contents = source_chat.get_chat_contents(
            source_data.source  # Assuming source_data has the 'source' field
        )
        contents_length = len(source_contents)

        chat_score = score_data(
            registry_chat_data,
            source_chat.chat_id,
            contents_length
        )

        if chat_score > 0.5:
            # content is unique...
            sentiment = get_sentiment_data(source_chat)  # Assuming source_chat contains the data
            keywords_keybert = get_keywords_keybert(source_chat, max_keywords=5)
            keywords_lda = get_keywords_lda(source_chat, max_keywords=5)

            # Create a ChatData instance and add it to the list
            chat_data = ChatData(
                chat_id=source_chat.chat_id,
                chat_length=contents_length,
                sentiment=sentiment,
                keywords_keybert=keywords_keybert,
                keywords_lda=keywords_lda
            )
            chat_list.append(chat_data)

    # Calculate uniqueness if there are chats
    if chat_count > 0:
        total_score = sum(chat.chat_length for chat in chat_list)  # Example of scoring logic
        return total_score / chat_count

    return 0
