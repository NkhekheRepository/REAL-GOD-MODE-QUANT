"""
MLOps Infrastructure for GodMode Quant Trading
MLflow integration for experiment tracking, model registry, and drift detection
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.sklearn
    import mlflow.keras
    import mlflow.pytorch
    from mlflow.models import infer_signature
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow not available. Install with: pip install mlflow")


class MLOpsManager:
    """
    Central MLOps manager for experiment tracking and model management
    """
    
    def __init__(
        self,
        tracking_uri: str = None,
        experiment_name: str = "godmode-quant-trading",
        registry_uri: str = None
    ):
        """
        Initialize MLOps manager
        
        Args:
            tracking_uri: MLflow tracking server URI
            experiment_name: Name of the experiment
            registry_uri: MLflow model registry URI
        """
        if not MLFLOW_AVAILABLE:
            logger.error("MLflow is not available.")
            self.enabled = False
            return
        
        self.enabled = True
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI",
            "file:///home/ubuntu/godmode-quant-orchestrator/mlruns"
        )
        self.experiment_name = experiment_name
        self.registry_uri = registry_uri or os.getenv("MLFLOW_REGISTRY_URI")
        
        # Set tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        if self.registry_uri:
            mlflow.set_registry_uri(self.registry_uri)
        
        # Get or create experiment
        self.experiment = self._get_or_create_experiment(experiment_name)
        
        # MLflow client
        self.client = MlflowClient()
        
        logger.info(f"MLOps Manager initialized: {experiment_name}")
        logger.info(f"Tracking URI: {self.tracking_uri}")
    
    def _get_or_create_experiment(self, name: str):
        """Get or create MLflow experiment"""
        try:
            experiment = mlflow.get_experiment_by_name(name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(name)
                logger.info(f"Created new experiment: {name} (ID: {experiment_id})")
                return mlflow.get_experiment(experiment_id)
            else:
                logger.info(f"Using existing experiment: {name}")
                return experiment
        except Exception as e:
            logger.error(f"Failed to get/create experiment: {e}")
            return None
    
    def start_run(
        self,
        run_name: str = None,
        tags: Dict = None
    ) -> mlflow.ActiveRun:
        """
        Start a new MLflow run
        
        Args:
            run_name: Name of the run
            tags: Dictionary of tags
            
        Returns:
            Active run
        """
        if not self.enabled:
            return None
        
        run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if tags:
            mlflow.set_tags(tags)
        
        run = mlflow.start_run(experiment_id=self.experiment.experiment_id, run_name=run_name)
        logger.info(f"Started run: {run_name}")
        
        return run
    
    def log_params(self, params: Dict[str, Any]):
        """Log parameters"""
        if not self.enabled:
            return
        mlflow.log_params(params)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = None):
        """Log metrics"""
        if not self.enabled:
            return
        mlflow.log_metrics(metrics, step=step)
    
    def log_model(
        self,
        model: Any,
        model_type: str,
        artifact_path: str = "model",
        input_example = None
    ):
        """
        Log model to MLflow
        
        Args:
            model: Model object
            model_type: Type of model ('sklearn', 'keras', 'pytorch')
            artifact_path: Path within artifact directory
            input_example: Input example for signature
        """
        if not self.enabled:
            return
        
        logger.info(f"Logging {model_type} model...")
        
        try:
            if model_type == 'sklearn':
                mlflow.sklearn.log_model(
                    model,
                    artifact_path=artifact_path,
                    input_example=input_example
                )
            elif model_type == 'keras':
                mlflow.keras.log_model(
                    model,
                    artifact_path=artifact_path
                )
            elif model_type == 'pytorch':
                mlflow.pytorch.log_model(
                    model,
                    artifact_path=artifact_path
                )
            else:
                logger.warning(f"Unsupported model type: {model_type}")
        
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
    
    def register_model(
        self,
        model_name: str,
        artifact_path: str = "model"
    ) -> str:
        """
        Register model in MLflow Model Registry
        
        Args:
            model_name: Name for the registered model
            artifact_path: Path to model artifacts
            
        Returns:
            Model version
        """
        if not self.enabled:
            return None
        
        try:
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/{artifact_path}"
            model_version = mlflow.register_model(model_uri, model_name)
            logger.info(f"Registered model: {model_name} (Version: {model_version.version})")
            return model_version.version
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return None
    
    def end_run(self, status: str = "FINISHED"):
        """End current run"""
        if not self.enabled:
            return
        mlflow.end_run(status)
        logger.info(f"Run ended with status: {status}")


class ModelPerformanceTracker:
    """
    Track model performance and detect concept drift
    """
    
    def __init__(
        self,
        window_size: int = 100,
        drift_threshold: float = 0.2
    ):
        """
        Initialize performance tracker
        
        Args:
            window_size: Size of rolling window for metrics
            drift_threshold: Threshold for drift detection
        """
        self.window_size = window_size
        self.drift_threshold = drift_threshold
        
        self.predictions_history: List[float] = []
        self.actuals_history: List[float] = []
        self.metrics_history: List[Dict] = []
        
        self.baseline_metrics = None
        self.drift_detected = False
    
    def add_prediction(
        self,
        prediction: float,
        actual: float,
        timestamp: datetime = None
    ):
        """
        Add a new prediction-actual pair
        
        Args:
            prediction: Predicted value
            actual: Actual value
            timestamp: Timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self.predictions_history.append(prediction)
        self.actuals_history.append(actual)
        
        # Maintain window size
        if len(self.predictions_history) > self.window_size:
            self.predictions_history.pop(0)
            self.actuals_history.pop(0)
            self.metrics_history.pop(0) if self.metrics_history else None
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        metrics['timestamp'] = timestamp.isoformat()
        self.metrics_history.append(metrics)
        
        # Check for drift
        self._check_drift()
    
    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate current metrics"""
        if len(self.predictions_history) < 2:
            return {}
        
        predictions = np.array(self.predictions_history)
        actuals = np.array(self.actuals_history)
        
        errors = predictions - actuals
        
        metrics = {
            'mae': np.mean(np.abs(errors)),
            'mse': np.mean(errors ** 2),
            'rmse': np.sqrt(np.mean(errors ** 2)),
        }
        
        if np.any(actuals != 0):
            metrics['mape'] = np.mean(np.abs(errors / actuals)) * 100
        
        # Directional accuracy
        direction_pred = np.sign(np.diff(predictions))
        direction_actual = np.sign(np.diff(actuals))
        if len(direction_pred) > 0:
            metrics['directional_accuracy'] = np.mean(direction_pred == direction_actual)
        
        return metrics
    
    def _check_drift(self):
        """Check for concept drift"""
        if len(self.metrics_history) < self.window_size:
            return
        
        # If no baseline, set it
        if self.baseline_metrics is None:
            self.baseline_metrics = self._calculate_metrics()
            return
        
        current_metrics = self._calculate_metrics()
        
        # Compare with baseline
        for key in ['mae', 'rmse', 'mape']:
            if key not in current_metrics or key not in self.baseline_metrics:
                continue
            
            baseline = self.baseline_metrics[key]
            current = current_metrics[key]
            
            if baseline > 0:
                drift_ratio = abs(current - baseline) / baseline
                
                if drift_ratio > self.drift_threshold:
                    self.drift_detected = True
                    logger.warning(
                        f"Concept drift detected! {key}: {current:.4f} "
                        f"(baseline: {baseline:.4f}, drift: {drift_ratio:.2%})"
                    )
                    return
        
        self.drift_detected = False
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current metrics"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return {}
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Get average metrics over history"""
        if not self.metrics_history:
            return {}
        
        avg_metrics = {}
        for key in self.metrics_history[0].keys():
            if key == 'timestamp':
                continue
            values = [m.get(key, 0) for m in self.metrics_history if key in m]
            if values:
                avg_metrics[key] = np.mean(values)
        
        return avg_metrics


class ExperimentTracker:
    """
    Track trading experiments with different strategies
    """
    
    def __init__(self, mlflow_manager: MLOpsManager):
        """
        Initialize experiment tracker
        
        Args:
            mlflow_manager: MLOpsManager instance
        """
        self.mlflow = mlflow_manager
        self.current_run = None
    
    def start_experiment(
        self,
        strategy_name: str,
        symbol: str,
        parameters: Dict
    ):
        """
        Start a new experiment
        
        Args:
            strategy_name: Name of the trading strategy
            symbol: Trading symbol
            parameters: Strategy parameters
        """
        run_name = f"{strategy_name}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        tags = {
            'strategy': strategy_name,
            'symbol': symbol,
            'experiment_type': 'trading'
        }
        
        self.current_run = self.mlflow.start_run(run_name=run_name, tags=tags)
        self.mlflow.log_params(parameters)
        
        logger.info(f"Started experiment: {run_name}")
    
    def log_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pnl: float = None
    ):
        """Log a trade"""
        if not self.current_run:
            return
        
        trade = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'pnl': pnl,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log as artifact
        trade_file = f"/tmp/trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        Path(trade_file).parent.mkdir(exist_ok=True)
        
        with open(trade_file, 'w') as f:
            json.dump(trade, f)
        
        mlflow.log_artifact(trade_file)
        os.remove(trade_file)
    
    def log_metrics_summary(
        self,
        total_trades: int,
        win_rate: float,
        total_pnl: float,
        sharpe_ratio: float = None,
        max_drawdown: float = None
    ):
        """Log experiment metrics summary"""
        metrics = {
            'total_trades': total_trades,
            'win_rate': win_rate * 100,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / 10000) * 100  # Assuming 10k starting capital
        }
        
        if sharpe_ratio is not None:
            metrics['sharpe_ratio'] = sharpe_ratio
        
        if max_drawdown is not None:
            metrics['max_drawdown'] = max_drawdown * 100
        
        self.mlflow.log_metrics(metrics)
    
    def end_experiment(self):
        """End current experiment"""
        if self.current_run:
            self.mlflow.end_run()
            self.current_run = None
            logger.info("Experiment ended")


# Global MLOps instances
mlops_manager = None
experiment_tracker = None


def initialize_mlops(
    tracking_uri: str = None,
    experiment_name: str = "godmode-quant-trading"
):
    """Initialize global MLOps instances"""
    global mlops_manager, experiment_tracker
    
    mlops_manager = MLOpsManager(
        tracking_uri=tracking_uri,
        experiment_name=experiment_name
    )
    
    experiment_tracker = ExperimentTracker(mlops_manager) if mlops_manager.enabled else None
    
    return mlops_manager, experiment_tracker


if __name__ == "__main__":
    # Example usage
    if MLFLOW_AVAILABLE:
        print("MLOps Infrastructure Example")
        print("=" * 50)
        
        # Initialize MLOps
        mlops, tracker = initialize_mlops()
        
        # Start experiment
        tracker.start_experiment(
            strategy_name="test_strategy",
            symbol="BTCUSDT",
            parameters={
                'lookback': 20,
                'threshold': 0.02,
                'stop_loss': 0.05
            }
        )
        
        # Simulate some trades
        for i in range(10):
            tracker.log_trade(
                symbol="BTCUSDT",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=0.1,
                price=50000 + i * 100,
                pnl=50 if i % 2 == 0 else -30
            )
        
        # Log metrics
        tracker.log_metrics_summary(
            total_trades=10,
            win_rate=0.6,
            total_pnl=120.5,
            sharpe_ratio=1.8,
            max_drawdown=-0.05
        )
        
        # End experiment
        tracker.end_experiment()
        
        print("\nExperiment tracked successfully!")
        print(f"View at: {mlops.tracking_uri}")
    else:
        print("MLflow is not available. Install with: pip install mlflow")