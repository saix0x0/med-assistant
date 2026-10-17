"""Picks the provider from config. The whole app calls get_provider()."""
from __future__ import annotations

from app import config


def get_provider():
    if config.is_mock():
        from app.providers.mock import MockProvider
        return MockProvider()
    from app.providers.sarvam import SarvamProvider
    return SarvamProvider()
