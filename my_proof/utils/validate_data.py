from utils.data_registry import DataRegistry
from models.cargo_data import CargoData, ChatData
from typing import List, Dict, Any

# Assuming the existence of these functions
from utils.feature_extraction import get_sentiment_data, get_keywords_keybert, get_keywords_lda

def get_registry_data(
        config: Dict[str, Any],
        cargo_data: CargoData
    ) -> List[ChatData]:

    # the following items should be stored system config...
    provider_url = config['dlp_url']         # "https://your-vana-node-url"
    contract_address = config['dlp_address'] # "0xYourDataRegistryContractAddress"
    contract_abi = None
    with open(config['dlp_abi_path']) as f:
      contract_abi = json.load(f)            # [Include ABI JSON here]

    # Create the client instance
    data_registry = DataRegistry(
        provider_url,
        contract_address,
        contract_abi
    )
    # Fetch data base on source & user_id
    registry_chat_data = data_registry.fetch_chat_data(
        cargo_data.source_id
    )
    return registry_chat_data

def score_data(registry_chat_list: List[ChatData], chat_id: int, content_length: int) -> float:
    if content_length == 0 or len(meta_data_list) == 0:
        return 0

    total_score = 0
    entry_count = 0

    for chat_data in registry_chat_list:
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

def validate_data(
    config: Dict[str, Any],
    cargo_data: CargoData
) -> float:
    source_data = cargo_data.source_data
    source_chats = source_data.chat_data

    score_threshold = 0.5
    number_of_keywords = 10

    total_score = 0
    chat_count = 0

    registry_chat_list = get_registry_data(
        config,
        cargo_data
    )
    # Loop through the chat_data_list
    for source_chat in source_chats:
        chat_count += 1  # Increment chat count
        source_contents = source_chat.get_chat_contents(
            source_data.source
        )
        contents_length = len(source_contents)

        chat_score = score_data(
            registry_chat_list,
            source_chat.chat_id,
            contents_length
        )
        total_score += chat_score

        # if chat data has meaningful data...
        if chat_score > score_threshold:
            # content is unique...
            chat_sentiment = get_sentiment_data(
                source_contents
            )
            chat_keywords_keybert = get_keywords_keybert(
                source_contents,
                max_keywords=number_of_keywords
            )
            chat_keywords_lda = get_keywords_lda(
                source_contents,
                max_keywords=number_of_keywords
            )

            # Create a ChatData instance and add it to the list
            chat_data = ChatData(
                chat_id=source_chat.chat_id,
                chat_length=contents_length,
                sentiment=chat_sentiment,
                keywords_keybert=chat_keywords_keybert,
                keywords_lda=chat_keywords_lda
            )
            cargo_data.chat_data_list.append(
                chat_data
            )

    # Calculate uniqueness if there are chats
    if chat_count > 0:
        return total_score / chat_count

    return 0
