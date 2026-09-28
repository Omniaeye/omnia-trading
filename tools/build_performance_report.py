# Copyright 2026 OMNIA EYE Corporation.
# SPDX-License-Identifier: Apache-2.0
"""Compatibility entry point; prefer omnia-trading-report after installation."""
from omnia_trading.reporting import main

if __name__ == '__main__':
    main()
