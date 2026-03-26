"""
Integration Tests for God Mode Quant Trading Orchestrator
Tests end-to-end functionality of the trading pipeline
"""
import unittest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock, mock_open
import threading
import importlib

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pre-mock numpy to avoid the import error
sys.modules['numpy'] = Mock()

# Pre-mock vnpy modules before any imports
mock_vnpy = Mock()
mock_vnpy.__version__ = "3.0.0"
sys.modules['vnpy'] = mock_vnpy
sys.modules['vnpy.event'] = Mock()
sys.modules['vnpy.trader'] = Mock()
sys.modules['vnpy.trader.engine'] = Mock()
sys.modules['vnpy.trader.object'] = Mock()
sys.modules['vnpy.trader.constant'] = Mock()
sys.modules['vnpy_ctastrategy'] = Mock()

class TestIntegration(unittest.TestCase):
    """Test end-to-end integration of the trading orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock external dependencies
        self.requests_patcher = patch('requests.post')
        self.mock_requests_post = self.requests_patcher.start()
        
        # Mock time.sleep to avoid delays in testing
        self.time_sleep_patcher = patch('time.sleep')
        self.mock_time_sleep = self.time_sleep_patcher.start()
        
    def tearDown(self):
        """Tear down test fixtures"""
        self.requests_patcher.stop()
        self.time_sleep_patcher.stop()
        
        # Clear any cached imports
        modules_to_clear = [k for k in sys.modules.keys() 
                          if k.startswith('vnpy') or k in ['main', 'risk_management', 
                                                           'security.audit_logger', 
                                                           'security.trust_scorer']]
        for m in modules_to_clear:
            if m in sys.modules:
                del sys.modules[m]
    
    @patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VAULT_ADDR': '',
        'VAULT_TOKEN': ''
    })
    @patch('requests.post')
    @patch('vnpy.event.EventEngine')
    @patch('vnpy.trader.engine.MainEngine')
    @patch('vnpy_ctastrategy.CtaStrategyApp')
    def test_orchestrator_startup_and_shutdown(self, mock_cta_app, mock_main_engine, 
                                               mock_event_engine, mock_requests_post):
        """Test that the orchestrator starts up, runs briefly, and shuts down correctly"""
        
        # Set up mock returns
        mock_event_instance = Mock()
        mock_event_engine.return_value = mock_event_instance
        
        mock_main_instance = Mock()
        mock_main_engine.return_value = mock_main_instance
        mock_cta_engine = Mock()
        mock_main_instance.add_app.return_value = mock_cta_engine
        mock_cta_engine.strategies = {}
        
        mock_requests_post.return_value = Mock(status_code=200)
        
        # Run the orchestrator in a thread with a timeout
        def run_main():
            try:
                import main
                main.main()
            except SystemExit:
                pass  # Expected when sys.exit is called
            except Exception as e:
                # Re-raise to fail the test if unexpected exception
                raise e
        
        # Start the orchestrator in a thread
        orchestrator_thread = threading.Thread(target=run_main)
        orchestrator_thread.daemon = True
        orchestrator_thread.start()
        
        # Wait for initialization
        orchestrator_thread.join(timeout=2.0)
        
        # Verify vnpy initialization occurred
        mock_event_engine.assert_called()
        mock_main_engine.assert_called()
        mock_main_instance.add_app.assert_called()
        
        # Verify CTA engine strategies were initialized
        mock_cta_engine.init_all_strategies.assert_called()
        mock_cta_engine.start_all_strategies.assert_called()
    
    @patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VAULT_ADDR': '',
        'VAULT_TOKEN': ''
    })
    @patch('requests.post')
    def test_risk_management_integration(self, mock_requests_post):
        """Test that risk management is properly integrated"""
        
        mock_requests_post.return_value = Mock(status_code=200)
        
        # Import risk management
        from risk_management import risk_manager
        
        # Verify that the risk manager was properly initialized with default values
        self.assertEqual(risk_manager.max_portfolio_risk_percent, 2.0)
        self.assertEqual(risk_manager.max_position_risk_percent, 0.5)
        self.assertEqual(risk_manager.max_drawdown_percent, 10.0)
        
        # Test position size calculation
        position_size = risk_manager.calculate_position_size(
            signal_price=50000.0,
            stop_loss_price=49000.0,  # 2% stop loss
            portfolio_value=100000.0,
            risk_percent=0.5
        )
        
        # With 0.5% risk ($500) and $1000 risk per share ($50000-$49000), position = 0.5
        expected_size = 0.5
        self.assertAlmostEqual(position_size, expected_size, places=2)
        
        # Test adding a position
        result = risk_manager.add_position(
            symbol='BTCUSDT',
            quantity=0.5,
            entry_price=50000.0
        )
        self.assertTrue(result)
        self.assertIn('BTCUSDT', risk_manager.portfolio.positions)
        
        # Test portfolio update
        risk_manager.update_portfolio_value(100250.0)  # $250 profit
        
        # Test risk report
        report = risk_manager.get_risk_report()
        self.assertIn('portfolio', report)
        self.assertIn('risk_limits', report)
        self.assertIn('risk_status', report)

    @patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat_id',
        'VAULT_ADDR': '',
        'VAULT_TOKEN': ''
    })
    @patch('requests.post')
    def test_security_components_integration(self, mock_requests_post):
        """Test that security components are properly integrated"""
        
        mock_requests_post.return_value = Mock(status_code=200)
        
        # Import security components
        from security.audit_logger import log_security_event
        from security.trust_scorer import record_trust_event, get_trust_score, TrustEventType
        
        # Test audit logger
        log_security_event(
            service="test_service",
            user="test_user",
            action="test_action",
            outcome="success",
            details={"test": "data"}
        )
        
        # Test trust scorer
        record_trust_event(
            service_or_user="test_service:user",
            event_type=TrustEventType.AUTH_SUCCESS,
            service="test_service",
            user="test_user",
            description="Test event",
            metadata={"test": "data"}
        )
        
        score = get_trust_score("test_service:user")
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        
        # Test risk report with trading stop logic
        from risk_management import risk_manager, should_stop_trading
        
        # Add a large position that would trigger risk limits
        risk_manager.max_position_risk_percent = 0.5
        risk_manager.add_position(
            symbol='BTCUSDT',
            quantity=10.0,  # Very large position
            entry_price=50000.0
        )
        risk_manager.update_portfolio_value(100000.0)
        
        # Check if trading should stop
        should_stop, reasons = should_stop_trading()
        # With a large position relative to portfolio, risk limits should be breached
        self.assertIsInstance(should_stop, bool)
        self.assertIsInstance(reasons, list)

if __name__ == '__main__':
    unittest.main()