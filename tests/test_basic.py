import unittest
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.collector import MarketCollector
from scanner.scanner import MarketScanner
# from engine.decision import DecisionEngine 
# (DecisionEngine requires API keys, might fail init if not mocked)

class TestBotStructure(unittest.TestCase):
    def test_imports(self):
        self.assertIsNotNone(MarketCollector)
        self.assertIsNotNone(MarketScanner)

if __name__ == '__main__':
    unittest.main()
