import json
import logging
import os
from typing import Dict, Any
import requests

from datetime import datetime
from models.proof_response import ProofResponse
from utils.hashing_utils import salted_data, serialize_bloom_filter_base64, deserialize_bloom_filter_base64
from utils.feature_extraction import get_keywords_keybert, get_sentiment_data, get_keywords_lda
from models.cargo_data import SourceChatData, CargoData, SourceData, DataSource, MetaData, DataSource
from utils.validate_data import validate_data


class Proof:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proof_response = ProofResponse(dlp_id=config['dlp_id'])

    #Patrck's original Code...
    def generate(self) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof generation")

        zktls_proof = None
        chats = None
        source = None
        user = None

        for input_filename in os.listdir(self.config['input_dir']):
            input_file = os.path.join(self.config['input_dir'], input_filename)
            if os.path.splitext(input_file)[1].lower() == '.json':
                with open(input_file, 'r') as f:
                    input_data = json.load(f)

                    if input_filename == 'zktls_proof.json':
                        zktls_proof = input_data.get('zktls_proof', None)
                        continue

                    elif input_filename == 'chats.json':
                        chats = input_data.get('chats', None)
                        user = input_data.get('user', None)
                        source = input_data.get('source', None)
                        continue

        salt = self.config['salt']
        source_user_hash_64 = salted_data((source, user), salt)
        is_data_authentic = get_is_data_authentic(chats, zktls_proof)
        self.proof_response.ownership = 1.0 if is_data_authentic else 0.0 #TODO: What can we do to check the account is owned by submitter even if the TLS is valid
        self.proof_response.authenticity = 1.0 if is_data_authentic else 0.0
        if not is_data_authentic: #short circuit so we don't waste analysis
            self.proof_response.score = 0.0
            self.proof_response.uniqueness = 0.0
            self.proof_response.quality = 0.0
            self.proof_response.valid = False
            self.proof_response.attributes = {
                'proof_valid': False,
                'did_score_content': False,
                'source_user_hash_64': source_user_hash_64
            }
            self.proof_response.metadata = {
                'dlp_id': self.config['dlp_id'],
            }
            return self.proof_response

        uniqueness = get_uniqueness(source_user_hash_64, chats)
        score_threshold = 0.5 #UPDATE after testing some conversations
        self.proof_response.valid = is_data_authentic and quality >= score_threshold
        keywords_keybert = []
        keywords_lda = []
        sentiment = {}
        max_keywords = 10
        if self.proof_response.valid:
            sentiment = get_sentiment_data(chats)
            keywords_keybert = get_keywords_keybert(chats, max_keywords)
            keywords_lda = get_keywords_lda(chats, max_keywords)
        self.proof_response.attributes = {
            'proof_valid': is_data_authentic,
            'did_score_content': True,
            'source_user_hash_64': source_user_hash,
            'sentiment': sentiment,
            'keywords_keybert': keywords_keybert,
            'keywords_lda': keywords_lda
        }
        self.proof_response.metadata = {
            'dlp_id': self.config['dlp_id'],
        }
        return self.proof_response

    #RL: Proof Data...
    def proof_data(self) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof data")

        zktls_proof = None
        source_data = None

        for input_filename in os.listdir(self.config['input_dir']):
            input_file = os.path.join(self.config['input_dir'], input_filename)
            if os.path.splitext(input_file)[1].lower() == '.json':
                with open(input_file, 'r') as f:
                    input_data = json.load(f)
                    #print(f"Input Data: {input_data}")

                    if input_filename == 'zktls_proof.json':
                        zktls_proof = input_data.get('zktls_proof', None)
                        continue

                    elif input_filename == 'chats.json':
                        source_data = get_source_data(
                            input_data
                        )
                        continue

        salt = self.config['salt']
        source_user_hash_64 = salted_data(
            (source_data.source, source_data.user),
            salt
        )
        is_data_authentic = get_is_data_authentic(
            source_data,
            zktls_proof
        )
        cargo_data = CargoData(
            source_data = source_data,
            source_id = source_user_hash_64
        )

        metadata = MetaData(
          source_id = source_user_hash_64,
          dlp_id = self.config['dlp_id']
        )

        self.proof_response.ownership = 1.0 if is_data_authentic else 0.0
        self.proof_response.authenticity = 1.0 if is_data_authentic else 0.0

        current_datetime = datetime.now().isoformat()
        if not is_data_authentic: #short circuit so we don't waste analysis
            self.proof_response.score = 0.0
            self.proof_response.uniqueness = 0.0
            self.proof_response.quality = 0.0
            self.proof_response.valid = False
            self.proof_response.attributes = {
                'proof_valid': False,
                'did_score_content': False,
                'source': source_data.Source.name,
                'submit_on': current_datetime,
                'chat_data': None
            }
            self.proof_response.metadata = metadata
            return self.proof_response

        #validate/proof data ...
        validate_data(
            self.config,
            cargo_data,
            self.proof_response
        )

        score_threshold = 0.5 #UPDATE after testing some conversations
        self.proof_response.valid = (
            is_data_authentic
            and self.proof_response.quality >= score_threshold
            and self.proof_response.uniqueness >= score_threshold
        )
        self.proof_response.score = (
            self.proof_response.authenticity * 0.25
            + self.proof_response.ownership * 0.25
            + self.proof_response.quality * 0.25
            + self.proof_response.uniqueness * 0.25
        )

        self.proof_response.attributes = {
            'proof_valid': is_data_authentic,
            'did_score_content': True,
            'source': source_data.source.name,
            'submit_on': current_datetime,
            'chat_data': cargo_data.get_chat_list_data()
        }
        self.proof_response.metadata = metadata
        return self.proof_response

def get_telegram_data(
    current_timestamp: datetime,
    input_content: dict,
    source_chat_data: 'SourceChatData'
):
    chat_type = input_content.get('@type')
    if chat_type == "message":
        # Extract user ID
        chat_user_id = input_content.get("sender_id", {}).get("user_id", "")
        print(f"chat_user_id: {chat_user_id}")
        source_chat_data.add_participant(chat_user_id)

        # Extract and convert the Unix timestamp to a datetime object
        date_value = input_content.get("date", None)
        if date_value:
            message_date = datetime.utcfromtimestamp(date_value)  # Convert Unix timestamp to datetime
            #print(f"message_date: {message_date}")

            # Convert current_timestamp to datetime if it's a Unix timestamp
            if isinstance(current_timestamp, int):
                current_timestamp = datetime.utcfromtimestamp(current_timestamp)

            # Calculate the difference in minutes
            time_in_seconds = (current_timestamp - message_date).total_seconds()
            time_in_minutes = int(time_in_seconds // 60)
        else:
            time_in_minutes = 0  # Default to 0 if no date is provided
            print("No valid date found in the input content.")

        # Extract the message content
        message = input_content.get('content', {})
        if isinstance(message, dict) and message.get("@type") == "messageText":
            content = message.get("text", {}).get("text", "")
            #print(f"Extracted content: {content}")
            source_chat_data.add_content(
                content,
                time_in_minutes
            )


def get_source_data(input_data: Dict[str, Any]) -> SourceData:
    current_timestamp = int(datetime.now().timestamp())

    input_source_value = input_data.get('source', '').upper()
    input_source = None

    if input_source_value == 'TELEGRAM':
        input_source = DataSource.telegram
    else:
        print(f"Unmapped data source: {input_source_value}")

    input_user = input_data.get('user')
    #print(f"input_user: {input_user}")

    source_data = SourceData(
        source=input_source,
        user=input_user
    )

    input_chats = input_data.get('chats', [])
    #print(f"input_chats: {input_chats}")
    source_chats = source_data.source_chats

    for input_chat in input_chats:
        chat_id = input_chat.get('chat_id')
        input_contents = input_chat.get('contents', [])
        if chat_id and input_contents:
            source_chat = SourceChatData(
                chat_id=chat_id
            )
            for input_content in input_contents:
                if input_source == DataSource.telegram:
                    get_telegram_data(
                        current_timestamp,
                        input_content,
                        source_chat
                    )
                else:
                    print(f"Unhandled data source: {input_source}")
            source_chats.append(
                source_chat
            )
    return source_data


def get_is_data_authentic(content, zktls_proof) -> bool:
    """Determine if the submitted data is authentic by checking the content against a zkTLS proof"""
    return 1.0

def get_user_submission_freshness(source, user) -> float:
    """Compute User Submission freshness"""
    #TODO: Get the IPFS data and check the attributes for timestamp of last submission
    #TODO: Implement cool-down logic so that there is a cool down for one particular social media account. I.E. someone who just submitted will get a very low number
    return 1.0
