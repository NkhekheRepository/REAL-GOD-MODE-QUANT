"""
Sentiment Analysis Module for Trading Strategies
Implements sentiment analysis from news and social media to enhance trading decisions
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
import requests
from datetime import datetime, timedelta
import json

class SentimentAnalyzer:
    """
    A class for analyzing market sentiment from news and social media
    """
    
    def __init__(self):
        """Initialize the sentiment analyzer"""
        # Financial sentiment words (simplified lexicon)
        self.positive_words = {
            'bullish', 'buy', 'long', 'up', 'rise', 'gain', 'profit', 'positive', 
            'optimistic', 'confident', 'strong', 'growth', 'increase', 'upgrade',
            'outperform', 'beat', 'exceed', 'surge', 'rally', 'recover', 'rebound'
        }
        
        self.negative_words = {
            'bearish', 'sell', 'short', 'down', 'fall', 'loss', 'negative', 
            'pessimistic', 'weak', 'decline', 'decrease', 'downgrade', 'underperform',
            'miss', 'drop', 'crash', 'plunge', 'slump', 'dip', 'correct', 'correction'
        }
        
        # Amplifiers and diminishers
        self.amplifiers = {'very', 'extremely', 'highly', 'significantly', 'substantially'}
        self.diminishers = {'slightly', 'somewhat', 'moderately', 'a bit', 'a little'}
        
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for sentiment analysis
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of a single text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        # Preprocess text
        clean_text = self.preprocess_text(text)
        words = clean_text.split()
        
        if not words:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0, 'compound': 0.0}
        
        # Count sentiment words
        positive_count = 0
        negative_count = 0
        
        i = 0
        while i < len(words):
            word = words[i]
            
            # Check for amplifiers/diminishers
            multiplier = 1.0
            if i > 0 and words[i-1] in self.amplifiers:
                multiplier = 1.5
            elif i > 0 and words[i-1] in self.diminishers:
                multiplier = 0.5
            
            if word in self.positive_words:
                positive_count += multiplier
            elif word in self.negative_words:
                negative_count += multiplier
                
            i += 1
        
        # Calculate scores
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            positive_score = 0.0
            negative_score = 0.0
            neutral_score = 1.0
        else:
            positive_score = positive_count / total_sentiment_words
            negative_score = negative_count / total_sentiment_words
            neutral_score = 0.0  # Simplified
            
        # Compound score (-1 to 1)
        compound = (positive_score - negative_score) if (positive_score + negative_score) > 0 else 0.0
        
        return {
            'positive': positive_score,
            'negative': negative_score,
            'neutral': neutral_score,
            'compound': compound
        }
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, float]:
        """
        Analyze sentiment for a batch of texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Aggregated sentiment scores
        """
        if not texts:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0, 'compound': 0.0}
        
        sentiments = [self.analyze_sentiment(text) for text in texts]
        
        # Average the scores
        avg_positive = np.mean([s['positive'] for s in sentiments])
        avg_negative = np.mean([s['negative'] for s in sentiments])
        avg_neutral = np.mean([s['neutral'] for s in sentiments])
        avg_compound = np.mean([s['compound'] for s in sentiments])
        
        return {
            'positive': avg_positive,
            'negative': avg_negative,
            'neutral': avg_neutral,
            'compound': avg_compound
        }
    
    def get_market_signal(self, sentiment_score: float, 
                         threshold: float = 0.2) -> Tuple[int, str]:
        """
        Convert sentiment score to trading signal
        
        Args:
            sentiment_score: Compound sentiment score (-1 to 1)
            threshold: Threshold for signal generation
            
        Returns:
            Tuple of (signal, reasoning) where signal: 1=buy, -1=sell, 0=hold
        """
        if sentiment_score > threshold:
            return 1, f"Positive sentiment detected (score: {sentiment_score:.2f})"
        elif sentiment_score < -threshold:
            return -1, f"Negative sentiment detected (score: {sentiment_score:.2f})"
        else:
            return 0, f"Neutral sentiment (score: {sentiment_score:.2f})"

class NewsSentimentFetcher:
    """
    Class to fetch financial news for sentiment analysis
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize news fetcher
        
        Args:
            api_key: API key for news service (optional for demo)
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
    
    def fetch_financial_news(self, query: str = "Bitcoin OR cryptocurrency", 
                           hours_back: int = 24) -> List[Dict]:
        """
        Fetch financial news (simulated for demo purposes)
        
        Args:
            query: Search query
            hours_back: How many hours back to fetch news
            
        Returns:
            List of news articles
        """
        # For demo purposes, we'll return simulated news
        # In a real implementation, this would call NewsAPI or similar
        simulated_news = [
            {
                'title': 'Bitcoin Surges Past $60,000 as Institutional Adoption Grows',
                'description': 'Bitcoin prices rose significantly today following increased institutional investment',
                'publishedAt': datetime.now().isoformat(),
                'source': {'name': 'Financial Times'}
            },
            {
                'title': 'Crypto Market Faces Regulatory Concerns',
                'description': 'New regulations may impact cryptocurrency trading volumes',
                'publishedAt': (datetime.now() - timedelta(hours=5)).isoformat(),
                'source': {'name': 'Bloomberg'}
            },
            {
                'title': 'Ethereum Upgrade Expected to Reduce Transaction Fees',
                'description': 'The upcoming Ethereum upgrade aims to make transactions cheaper and faster',
                'publishedAt': (datetime.now() - timedelta(hours=10)).isoformat(),
                'source': {'name': 'CoinDesk'}
            },
            {
                'title': 'Major Bank Announces Crypto Trading Desk',
                'description': 'A major international bank has launched a cryptocurrency trading desk for clients',
                'publishedAt': (datetime.now() - timedelta(hours=15)).isoformat(),
                'source': {'name': 'Reuters'}
            },
            {
                'title': 'Market Volatility Increases Amid Economic Uncertainty',
                'description': 'Global markets showing increased volatility as investors assess economic outlook',
                'publishedAt': (datetime.now() - timedelta(hours=20)).isoformat(),
                'source': {'name': 'Wall Street Journal'}
            }
        ]
        
        # Filter by time
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        filtered_news = []
        for article in simulated_news:
            try:
                pub_time = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                if pub_time >= cutoff_time:
                    filtered_news.append(article)
            except:
                # If date parsing fails, include the article
                filtered_news.append(article)
                
        return filtered_news
    
    def get_news_for_sentiment(self, query: str = "Bitcoin OR cryptocurrency", 
                             hours_back: int = 24) -> List[str]:
        """
        Get news text for sentiment analysis
        
        Args:
            query: Search query
            hours_back: How many hours back to fetch news
            
        Returns:
            List of news text strings
        """
        news_articles = self.fetch_financial_news(query, hours_back)
        news_texts = []
        
        for article in news_articles:
            # Combine title and description
            text = f"{article.get('title', '')} {article.get('description', '')}"
            news_texts.append(text.strip())
            
        return news_texts

class SocialMediaSentimentFetcher:
    """
    Class to fetch social media sentiment (simplified for demo)
    """
    
    def __init__(self):
        """Initialize social media fetcher"""
        pass
    
    def fetch_twitter_sentiment(self, symbol: str = "BTC", 
                              hours_back: int = 24) -> List[str]:
        """
        Fetch Twitter sentiment (simulated for demo)
        
        Args:
            symbol: Trading symbol
            hours_back: How many hours back to fetch tweets
            
        Returns:
            List of tweet texts
        """
        # Simulated tweets
        simulated_tweets = [
            f"Just bought more {symbol}! Feeling bullish about the long term prospects 🚀",
            f"{symbol} looking weak today, might take profits and wait for better entry 📉",
            f"Great news about {symbol} adoption! This could be the start of a new bull run 💪",
            f"Worried about {symbol} volatility today, setting tight stop losses ⚠️",
            f"{symbol} breaking key resistance levels, momentum is building 📈",
            f"Taking a break from {symbol} trading, market too choppy right now ↔️",
            f"Just sold half my {symbol} position, locking in some profits 💰",
            f"Seeing accumulation patterns in {symbol}, smart money appears to be entering 👀",
            f"{symbol} rejection at support level, could see further downside 📉",
            f"Excited about the upcoming {symbol} developments, holding for the long haul 🔒"
        ]
        
        return simulated_tweets

class EnhancedSentimentStrategy:
    """
    Enhanced trading strategy that incorporates sentiment analysis
    """
    
    def __init__(self, 
                 ma_fast: int = 10,
                 ma_slow: int = 30,
                 sentiment_weight: float = 0.3,
                 sentiment_threshold: float = 0.2):
        """
        Initialize the sentiment-enhanced strategy
        
        Args:
            ma_fast: Fast moving average period
            ma_slow: Slow moving average period
            sentiment_weight: Weight given to sentiment signals (0-1)
            sentiment_threshold: Threshold for sentiment-based signals
        """
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.sentiment_weight = sentiment_weight
        self.sentiment_threshold = sentiment_threshold
        
        # Initialize components
        self.sentiment_analyzer = SentimentAnalyzer()
        self.news_fetcher = NewsSentimentFetcher()
        self.social_fetcher = SocialMediaSentimentFetcher()
        
        # Strategy state
        self.ma_trend = 0
        self.sentiment_signal = 0
        self.sentiment_score = 0.0
        self.combined_signal = 0
        
    def calculate_ma_signal(self, prices: np.ndarray) -> Tuple[int, Dict]:
        """
        Calculate signal based on moving average crossover
        
        Args:
            prices: Price data array
            
        Returns:
            Tuple of (signal, info_dict)
        """
        if len(prices) < self.ma_slow:
            return 0, {'ma_fast': 0, 'ma_slow': 0, 'trend': 0}
            
        ma_fast = np.mean(prices[-self.ma_fast:])
        ma_slow = np.mean(prices[-self.ma_slow:])
        
        if ma_fast > ma_slow:
            ma_trend = 1
        elif ma_fast < ma_slow:
            ma_trend = -1
        else:
            ma_trend = 0
            
        # Generate crossover signal
        signal = 0
        if ma_trend > self.ma_trend:
            signal = 1  # Bullish crossover
        elif ma_trend < self.ma_trend:
            signal = -1  # Bearish crossover
            
        info = {
            'ma_fast': ma_fast,
            'ma_slow': ma_slow,
            'trend': ma_trend,
            'ma_signal': signal
        }
        
        return signal, info
    
    def update_sentiment(self) -> Tuple[float, int, str]:
        """
        Update sentiment analysis from news and social media
        
        Returns:
            Tuple of (sentiment_score, sentiment_signal, reasoning)
        """
        # Fetch news and social media content
        news_texts = self.news_fetcher.get_news_for_sentiment(hours_back=6)  # Last 6 hours
        social_texts = self.social_fetcher.fetch_twitter_sentiment(hours_back=6)
        
        # Combine all texts
        all_texts = news_texts + social_texts
        
        if not all_texts:
            return 0.0, 0, "No sentiment data available"
        
        # Analyze sentiment
        news_sentiment = self.news_fetcher.get_news_for_sentiment(hours_back=6)
        if news_texts:
            news_result = self.sentiment_analyzer.analyze_batch(news_texts)
        else:
            news_result = {'compound': 0.0}
            
        if social_texts:
            social_result = self.sentiment_analyzer.analyze_batch(social_texts)
        else:
            social_result = {'compound': 0.0}
        
        # Weighted average (news gets higher weight)
        combined_compound = (news_result['compound'] * 0.7) + (social_result['compound'] * 0.3)
        
        # Get signal from sentiment
        sentiment_signal, reasoning = self.sentiment_analyzer.get_market_signal(
            combined_compound, self.sentiment_threshold)
        
        return combined_compound, sentiment_signal, reasoning
    
    def generate_signal(self, prices: np.ndarray) -> Dict:
        """
        Generate combined trading signal
        
        Args:
            prices: Price data array
            
        Returns:
            Dictionary with signal information
        """
        # Get MA signal
        ma_signal, ma_info = self.calculate_ma_signal(prices)
        
        # Get sentiment signal
        sentiment_score, sentiment_signal, sentiment_reasoning = self.update_sentiment()
        
        # Combine signals
        # Weighted combination: (1-sentiment_weight)*MA + sentiment_weight*Sentiment
        combined_raw = (1 - self.sentiment_weight) * ma_signal + self.sentiment_weight * sentiment_signal
        
        # Convert to discrete signal
        if combined_raw > 0.5:
            combined_signal = 1
        elif combined_raw < -0.5:
            combined_signal = -1
        else:
            combined_signal = 0
        
        # Update state
        self.ma_trend = ma_info['trend']
        self.sentiment_score = sentiment_score
        self.sentiment_signal = sentiment_signal
        self.combined_signal = combined_signal
        
        # Build reasoning
        reasoning = []
        if ma_info['ma_signal'] != 0:
            direction = "bullish" if ma_info['ma_signal'] > 0 else "bearish"
            reasoning.append(f"MA crossover: {direction}")
        
        if sentiment_signal != 0:
            direction = "positive" if sentiment_signal > 0 else "negative"
            reasoning.append(f"Sentiment: {direction} ({sentiment_reasoning})")
        
        if not reasoning:
            reasoning.append("No clear signals")
        
        return {
            'signal': combined_signal,
            'ma_signal': ma_signal,
            'ma_info': ma_info,
            'sentiment_score': sentiment_score,
            'sentiment_signal': sentiment_signal,
            'sentiment_reasoning': sentiment_reasoning,
            'combined_signal': combined_signal,
            'reasoning': reasoning
        }

# Example usage function
def demonstrate_sentiment_enhancement():
    """Demonstrate how sentiment enhancement works"""
    # Generate sample price data
    np.random.seed(42)
    prices = 50000 + np.cumsum(np.random.normal(0, 500, 100))  # Random walk
    
    # Initialize enhanced strategy
    strategy = EnhancedSentimentStrategy(
        ma_fast=10,
        ma_slow=30,
        sentiment_weight=0.3
    )
    
    # Generate signal
    result = strategy.generate_signal(prices)
    
    print("Sentiment-Enhanced Trading Signal:")
    print(f"Signal: {result['signal']} (1=Buy, -1=Sell, 0=Hold)")
    print(f"MA Signal: {result['ma_signal']}")
    print(f"Sentiment Score: {result['sentiment_score']:.3f}")
    print(f"Sentiment Signal: {result['sentiment_signal']}")
    print(f"Combined Signal: {result['combined_signal']}")
    print(f"Reasoning: {'; '.join(result['reasoning'])}")
    print(f"MA Fast: {result['ma_info']['ma_fast']:.2f}")
    print(f"MA Slow: {result['ma_info']['ma_slow']:.2f}")
    print(f"MA Trend: {result['ma_info']['trend']}")
    
    return result

if __name__ == "__main__":
    demonstrate_sentiment_enhancement()