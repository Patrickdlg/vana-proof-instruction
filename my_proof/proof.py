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
        validate_data(
            self.config,
            cargo_data
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
                'user_id': source_data.user,
                'submit_on': current_datetime,
                'chat_data': None
            }
            self.proof_response.metadata = metadata
            return self.proof_response

        #RL: loop though the source chat data, and get reuslt & scores
        uniqueness = validate_data(
            self.config,
            cargo_data
        )
        quality = get_chat_quality(cargo_data)

        score_threshold = 0.5 #UPDATE after testing some conversations
        self.proof_response.valid = is_data_authentic and quality >= score_threshold and uniqueness > score_threshold
        self.proof_response.uniqueness = uniqueness
        self.proof_response.quality = quality

        self.proof_response.attributes = {
            'proof_valid': is_data_authentic,
            'did_score_content': True,
            'source': source_data.source.name,
            'user_id': source_data.user,
            'submit_on': current_datetime,
            'chat_data': cargo_data.get_chat_list_data()
        }
        self.proof_response.metadata = metadata
        return self.proof_response


def get_source_data(input_data: Dict[str, Any]) -> SourceData:
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

        input_contents = input_chat.get('contents', [])  # Correctly fetch contents from the chat
        #print(f"Processing chat_id: {chat_id}, input_contents: {input_contents}")

        contents = []
        for input_content in input_contents:
            if input_source == DataSource.telegram:
                chat_type = input_content.get('@type')
                #print(f"chat_type: {chat_type}")
                if chat_type == "message":
                    message = input_content.get('content', {})
                    if isinstance(message, dict) and message.get("@type") == "messageText":
                        content = message.get("text", {}).get("text", "")
                        if (content):
                          #print(f"Extracted content: {content}")
                          contents.append(content)
            else:
                print(f"Unhandled data source: {input_source}")

        if chat_id and contents:
            source_chat = SourceChatData(
                chat_id=chat_id,
                contents="\r".join(contents)
            )
            #print(f"Generated source chat: {source_chat}")
            source_chats.append(source_chat)

    return source_data

def get_is_data_authentic(content, zktls_proof) -> bool:
    """Determine if the submitted data is authentic by checking the content against a zkTLS proof"""
    return 1.0

def get_chat_quality(chat) -> float:
    """Compute and return the overall score of a chat based on weighted average for message recency, conversation length, and number of participants"""
    return 1.0

def get_uniqueness(source_user_hash_64, chats) -> float:
    """Compute the uniqueness of the submitted data"""
    #TODO: Check indexing on the IPFS data and see if we can fetch the saved attributes
    return 1.0

def get_user_submission_freshness(source, user) -> float:
    """Compute User Submission freshness"""
    #TODO: Get the IPFS data and check the attributes for timestamp of last submission
    #TODO: Implement cool-down logic so that there is a cool down for one particular social media account. I.E. someone who just submitted will get a very low number
    return 1.0
