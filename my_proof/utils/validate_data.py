from models.cargo_data import CargoData, ChatData, SourceChatData, SourceData
from typing import List, Dict, Any

# Assuming the existence of these functions
from utils.feature_extraction import get_sentiment_data, get_keywords_keybert, get_keywords_lda

def get_user_submited_chat_data(
        config: Dict[str, Any],
        cargo_data: CargoData
    ) -> List[ChatData]:

    # Fetch old data from IPFS...
    # Patrick: Need to found out from Vana Team...

    return []

def score_data(previous_chat_list: List[ChatData], chat_id: int, content_length: int) -> float:
    if content_length == 0 :
        return 0

    total_score = 0
    entry_count = 0
    for chat_data in previous_chat_list:
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
    source_chats = source_data.source_chats

    score_threshold = 0.5
    number_of_keywords = 10

    total_score = 0
    chat_count = 0

    previous_chat_list = get_user_submited_chat_data(
        config,
        cargo_data
    )
    # Loop through the chat_data_list
    for source_chat in source_chats:

        #print(f"source_chat:{source_chat}")
        chat_count += 1  # Increment chat count
        source_contents = None
        contents_length = 0
        if source_chat.contents:  # Ensure chat_contents is not None
            source_contents = source_chat.content_as_text()
            print(f"source_contents: {source_contents}")
            contents_length = len(source_contents)

        chat_score = score_data(
            previous_chat_list,
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
                number_of_keywords
            )
            chat_keywords_lda = get_keywords_lda(
                source_contents,
                number_of_keywords
            )

            # Create a ChatData instance and add it to the list
            chat_data = ChatData(
                chat_id=source_chat.chat_id,
                chat_length=contents_length,
                sentiment=chat_sentiment,
                keywords_keybert=chat_keywords_keybert,
                keywords_lda=chat_keywords_lda
            )
            #print(f"chat_data: {chat_data}")
            cargo_data.chat_list.append(
                chat_data
            )

    # Calculate uniqueness if there are chats
    if chat_count > 0:
        return total_score / chat_count

    return 0
