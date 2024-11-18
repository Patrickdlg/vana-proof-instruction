import json
import logging
import os
from typing import Dict, Any

import requests

from my_proof.models.proof_response import ProofResponse
from utils.hashing_utils import salted_data, serialize_bloom_filter_base64, deserialize_bloom_filter_base64
from utils.feature_extraction import get_keywords, get_sentiment_data


class Proof:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.proof_response = ProofResponse(dlp_id=config['dlp_id'])

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
        keywords = []
        sentiment = {}
        if self.proof_response.valid:
            keywords = get_keywords(chats)
            sentiment = get_sentiment_data(chats)
        self.proof_response.attributes = {
            'proof_valid': is_data_authentic,
            'did_score_content': True,
            'source_user_hash_64': source_user_hash,
            'sentiment': sentiment,
            'keywords': keywords
        }
        self.proof_response.metadata = {
            'dlp_id': self.config['dlp_id'],
        }
        return self.proof_response


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

