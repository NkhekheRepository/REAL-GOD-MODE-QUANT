"""
Time Series Forecasting Module for Trading Strategies
Implements various forecasting models to enhance trading decisions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import warnings
warnings.filterwarnings('ignore')

class TimeSeriesForecaster:
    """
    A class for time series forecasting to enhance trading strategy decisions
    """
    
    def __init__(self, model_type: str = 'linear'):
        """
        Initialize the forecaster
        
        Args:
            model_type: Type of model ('linear', 'random_forest')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        if model_type == 'linear':
            self.model = LinearRegression()
        elif model_type == 'random_forest':
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def prepare_features(self, data: np.ndarray, lookback: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features for time series forecasting
        
        Args:
            data: Time series data
            lookback: Number of previous time steps to use as features
            
        Returns:
            X: Feature matrix
            y: Target vector
        """
        X, y = [], []
        for i in range(len(data) - lookback):
            X.append(data[i:i+lookback])
            y.append(data[i+lookback])
        return np.array(X), np.array(y)
    
    def fit(self, data: np.ndarray, lookback: int = 10) -> None:
        """
        Fit the forecasting model
        
        Args:
            data: Time series data to fit on
            lookback: Number of previous time steps to use as features
        """
        X, y = self.prepare_features(data, lookback)
        if len(X) > 0:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_fitted = True
    
    def predict(self, data: np.ndarray, lookback: int = 10) -> Optional[float]:
        """
        Make a prediction for the next time step
        
        Args:
            data: Recent time series data
            lookback: Number of previous time steps to use as features
            
        Returns:
            Predicted next value or None if model not fitted
        """
        if not self.is_fitted:
            return None
            
        if len(data) < lookback:
            return None
            
        # Get the last 'lookback' points
        recent_data = data[-lookback:]
        recent_data_scaled = self.scaler.transform([recent_data])
        prediction = self.model.predict(recent_data_scaled)[0]
        return prediction
    
    def predict_multiple(self, data: np.ndarray, steps: int = 5, lookback: int = 10) -> List[float]:
        """
        Predict multiple future steps
        
        Args:
            data: Historical time series data
            steps: Number of future steps to predict
            lookback: Number of previous time steps to use as features
            
        Returns:
            List of predicted values
        """
        if not self.is_fitted:
            return [None] * steps
            
        predictions = []
        current_data = data.copy()
        
        for _ in range(steps):
            pred = self.predict(current_data, lookback)
            if pred is None:
                break
            predictions.append(pred)
            # Append prediction to data for next step
            current_data = np.append(current_data, pred)
            
        return predictions

class EnhancedMaCrossoverStrategy:
    """
    Enhanced Moving Average Crossover Strategy with ML predictions
    """
    
    def __init__(self, 
                 fast_ma_length: int = 10,
                 slow_ma_length: int = 30,
                 prediction_lookback: int = 20,
                 confidence_threshold: float = 0.6):
        """
        Initialize the enhanced strategy
        
        Args:
            fast_ma_length: Fast moving average period
            slow_ma_length: Slow moving average period
            prediction_lookback: Lookback period for ML predictions
            confidence_threshold: Minimum confidence for ML signals
        """
        self.fast_ma_length = fast_ma_length
        self.slow_ma_length = slow_ma_length
        self.prediction_lookback = prediction_lookback
        self.confidence_threshold = confidence_threshold
        
        # Initialize forecasters for price prediction
        self.price_forecaster = TimeSeriesForecaster(model_type='random_forest')
        
        # Strategy state
        self.fast_ma_value = 0
        self.slow_ma_value = 0
        self.ma_trend = 0
        self.price_prediction = None
        self.prediction_confidence = 0
        
    def calculate_moving_averages(self, prices: np.ndarray) -> Tuple[float, float]:
        """Calculate fast and slow moving averages"""
        if len(prices) >= self.slow_ma_length:
            fast_ma = np.mean(prices[-self.fast_ma_length:])
            slow_ma = np.mean(prices[-self.slow_ma_length:])
            return fast_ma, slow_ma
        return 0, 0
    
    def update_prediction(self, prices: np.ndarray) -> None:
        """Update ML-based price prediction"""
        if len(prices) >= self.prediction_lookback:
            # Fit forecaster on recent data
            self.price_forecaster.fit(prices[-self.prediction_lookback*2:], 
                                    lookback=self.prediction_lookback//2)
            
            # Get prediction for next period
            self.price_prediction = self.price_forecaster.predict(prices, 
                                                                lookback=self.prediction_lookback//2)
            
            # Simple confidence calculation based on recent prediction accuracy
            if len(prices) >= self.prediction_lookback*2:
                recent_pred = self.price_forecaster.predict(
                    prices[:-1], lookback=self.prediction_lookback//2)
                if recent_pred is not None and len(prices) > 0:
                    error = abs(recent_pred - prices[-1])
                    # Normalize error by price level
                    self.prediction_confidence = max(0, 1 - error / prices[-1])
                else:
                    self.prediction_confidence = 0
            else:
                self.prediction_confidence = 0.5  # Default confidence
    
    def generate_signal(self, prices: np.ndarray) -> Dict:
        """
        Generate trading signal based on MA crossover and ML predictions
        
        Returns:
            Dictionary with signal information
        """
        # Update moving averages
        self.fast_ma_value, self.slow_ma_value = self.calculate_moving_averages(prices)
        
        # Update ML prediction
        self.update_prediction(prices)
        
        # Determine MA trend
        if self.fast_ma_value > self.slow_ma_value:
            ma_trend = 1  # Bullish
        elif self.fast_ma_value < self.slow_ma_value:
            ma_trend = -1  # Bearish
        else:
            ma_trend = 0  # Neutral
            
        # Generate signal
        signal = 0  # 0: hold, 1: buy, -1: sell
        reasoning = []
        
        # MA crossover signal
        if ma_trend > self.ma_trend:
            # Bullish crossover
            signal = 1
            reasoning.append("Bullish MA crossover")
        elif ma_trend < self.ma_trend:
            # Bearish crossover
            signal = -1
            reasoning.append("Bearish MA crossover")
            
        # ML enhancement
        if self.price_prediction is not None and self.prediction_confidence > self.confidence_threshold:
            current_price = prices[-1] if len(prices) > 0 else 0
            if self.price_prediction > current_price * 1.01:  # Predict 1% increase
                if signal <= 0:  # Only enhance buy signals or change hold to buy
                    signal = 1
                    reasoning.append(f"ML predicts price increase to {self.price_prediction:.2f}")
            elif self.price_prediction < current_price * 0.99:  # Predict 1% decrease
                if signal >= 0:  # Only enhance sell signals or change hold to sell
                    signal = -1
                    reasoning.append(f"ML predicts price decrease to {self.price_prediction:.2f}")
                    
        # Update state
        self.ma_trend = ma_trend
        
        return {
            'signal': signal,
            'reasoning': reasoning,
            'fast_ma': self.fast_ma_value,
            'slow_ma': self.slow_ma_value,
            'price_prediction': self.price_prediction,
            'prediction_confidence': self.prediction_confidence,
            'ma_trend': ma_trend
        }

# Example usage function
def demonstrate_ml_enhancement():
    """Demonstrate how ML enhancement works with sample data"""
    # Generate sample price data (simulating Bitcoin prices)
    np.random.seed(42)
    t = np.linspace(0, 100, 50)
    prices = 50000 + 10000 * np.sin(t/10) + np.random.normal(0, 1000, len(t))
    
    # Initialize enhanced strategy
    strategy = EnhancedMaCrossoverStrategy(
        fast_ma_length=5,
        slow_ma_length=15,
        prediction_lookback=20
    )
    
    # Generate signal
    result = strategy.generate_signal(prices)
    
    print("ML-Enhanced Trading Signal:")
    print(f"Signal: {result['signal']} (1=Buy, -1=Sell, 0=Hold)")
    print(f"Reasoning: {', '.join(result['reasoning'])}")
    print(f"Fast MA: {result['fast_ma']:.2f}")
    print(f"Slow MA: {result['slow_ma']:.2f}")
    print(f"MA Trend: {result['ma_trend']} (1=Bullish, -1=Bearish, 0=Neutral)")
    print(f"Price Prediction: {result['price_prediction']:.2f}")
    print(f"Prediction Confidence: {result['prediction_confidence']:.2f}")
    
    return result

if __name__ == "__main__":
    demonstrate_ml_enhancement()