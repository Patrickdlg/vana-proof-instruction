from web3 import Web3
from typing import List
from models.cargo_data import ChatData  # Ensure the correct import of ChatData class

class DataRegistry:
    def __init__(self, provider_url, contract_address, contract_abi):
        # Connect to the Ethereum node (Vana network)
        self.web3 = Web3(Web3.HTTPProvider(provider_url))
        self.contract = self.web3.eth.contract(
            address=Web3.toChecksumAddress(contract_address),
            abi=contract_abi
        )

    def get_total_entries(self):
        """Get the total number of entries in the registry."""
        return self.contract.functions.getDataCount().call()

    def get_data_by_index(self, index):
        """Get the data ID at a specific index."""
        return self.contract.functions.getDataIdByIndex(index).call()

    def get_metadata(self, data_id):
        """Fetch metadata for a given data ID."""
        return self.contract.functions.getMetadata(data_id).call()

    def fetch_chat_data(self, source_id: str) -> List[ChatData]:
        """
        Fetch all data entries and filter them by a specific source_id.

        :param source_id: The source_id to filter by.
        :return: List of filtered ChatData.
        """
        try:
            total_entries = self.get_total_entries()
            chat_data = []
            for index in range(total_entries):
                data_id = self.get_data_by_index(index)
                metadata = self.get_metadata(data_id)

                entry_source_id = metadata.get("source_id")

                # Compare source_id from metadata with provided source_id
                if entry_source_id == source_id:
                    # Assuming chat data is available in metadata, populate accordingly
                    chats = metadata.get("chats", [])
                    for chat in chats:
                        chat_data.append(
                            ChatData(
                                chat_id=chat.get("chat_id"),
                                chat_length=chat.get("chat_length"),
                                sentiment=chat.get("sentiment", {}),
                                keywords_keybert=chat.get("keywords_keybert", {}),
                                keywords_lda=chat.get("keywords_lda", {})
                            )
                        )
            return chat_data
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []  # Return an empty list in case of error
