"""
Market Data Ingestion System
Real-time and historical data pipeline with error recovery
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import ccxt
from ccxt import ExchangeError, NetworkError
from google.cloud import firestore

logger = logging.getLogger(__name__)

class MarketDataIngestor:
    """
    Robust market data ingestion with real-time streaming and historical backfill
    Features:
    - Multi-exchange support via CCXT
    - Real-time WebSocket streaming
    - Automatic error recovery
    - Data validation and cleansing
    - Firebase persistence
    """
    
    def __init__(self, exchange_id: str = 'binance'):
        self.exchange_id = exchange_id
        self.exchange = self._init_exchange()
        self.firebase = get_firebase().get_db()
        self.data_cache = {}
        
        # Exchange configuration
        self.supported_exchanges = ['binance', 'coinbase', 'kraken', 'bybit']
        self._validate_exchange()
        
        # Rate limiting
        self.last_request_time = 0
        self.request_interval = 0.2  # 5 requests per second
        
    def _init_exchange(self):
        """Initialize exchange with proper configuration"""
        exchange_class = getattr(ccxt, self.exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Exchange {self.exchange_id} not supported by CCXT")
        
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        
        logger.info(f"Initialized {self.exchange_id} exchange")
        return exchange
    
    def _validate_exchange(self):
        """Validate exchange support"""
        if self.exchange_id not in self.supported_exchanges:
            logger.warning(f"Exchange {self.exchange_id} not in optimized list")
    
    async def fetch_historical_data(
        self, 
        symbol: str, 
        timeframe: str = '1h',
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data with pagination
        """
        try:
            self._rate_limit()
            
            # Convert since to timestamp
            since_timestamp = int(since.timestamp() * 1000) if since else None
            
            # Fetch data
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                since=since_timestamp,
                limit=limit
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', '