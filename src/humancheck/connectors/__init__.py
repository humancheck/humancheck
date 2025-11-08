"""Communication channel connectors for review notifications."""
from .base import ReviewConnector
from .slack import SlackConnector

__all__ = ['ReviewConnector', 'SlackConnector']
