import os
import requests
from typing import Dict, List, Optional

BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')

class TokenUtils:
    @staticmethod
    async def get_token_price(token_address: str) -> Optional[float]:
        """Get token price from Birdeye API"""
        try:
            headers = {'X-API-KEY': BIRDEYE_API_KEY}
            response = requests.get(
                f'https://public-api.birdeye.so/public/price?address={token_address}',
                headers=headers
            )
            data = response.json()
            return float(data['data']['value'])
        except Exception as e:
            print(f"Error getting token price: {e}")
            return None

    @staticmethod
    async def search_tokens(query: str) -> List[Dict]:
        """Search for tokens using Birdeye API"""
        try:
            headers = {'X-API-KEY': BIRDEYE_API_KEY}
            response = requests.get(
                f'https://public-api.birdeye.so/public/tokenlist?sort_by=volume&sort_type=desc&offset=0&limit=20&query={query}',
                headers=headers
            )
            data = response.json()
            return data['data']['tokens']
        except Exception as e:
            print(f"Error searching tokens: {e}")
            return []

    @staticmethod
    async def get_top_gainers() -> List[Dict]:
        """Get top gaining tokens"""
        try:
            headers = {'X-API-KEY': BIRDEYE_API_KEY}
            response = requests.get(
                'https://public-api.birdeye.so/public/tokenlist?sort_by=price_change_24h&sort_type=desc&offset=0&limit=10',
                headers=headers
            )
            data = response.json()
            return data['data']['tokens']
        except Exception as e:
            print(f"Error getting top gainers: {e}")
            return []

    @staticmethod
    async def get_top_losers() -> List[Dict]:
        """Get top losing tokens"""
        try:
            headers = {'X-API-KEY': BIRDEYE_API_KEY}
            response = requests.get(
                'https://public-api.birdeye.so/public/tokenlist?sort_by=price_change_24h&sort_type=asc&offset=0&limit=10',
                headers=headers
            )
            data = response.json()
            return data['data']['tokens']
        except Exception as e:
            print(f"Error getting top losers: {e}")
            return []

    @staticmethod
    async def get_token_metadata(token_address: str) -> Optional[Dict]:
        """Get token metadata using Helius API"""
        try:
            headers = {'Authorization': f'Bearer {HELIUS_API_KEY}'}
            response = requests.get(
                f'https://api.helius.xyz/v0/tokens/metadata?api-key={HELIUS_API_KEY}&mintAccounts={token_address}',
                headers=headers
            )
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            print(f"Error getting token metadata: {e}")
            return None 