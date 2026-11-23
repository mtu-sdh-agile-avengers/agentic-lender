"""Shared test setup.

Tests never call the ECB: the market agent is switched off here (it then
reports `available: false`), and tests/test_market.py feeds it recorded
responses through a fake transport instead.
"""

import os

os.environ["MARKET_DATA_ENABLED"] = "false"
