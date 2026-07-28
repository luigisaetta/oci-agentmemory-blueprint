"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Builds the fixed user-scoped customer-support messages for Example 05.
"""

from oracleagentmemory.apis import Message


def build_user1_messages(timestamp: str) -> list[Message]:
    """Build the first customer's delivery-delay conversation.

    Args:
        timestamp: UTC timestamp assigned to every message in this insertion.

    Returns:
        Five ordered messages for the first customer-support thread.
    """
    entries = [
        ("user", "My delivery for order 1001 is delayed. I need a tracking update."),
        (
            "assistant",
            "I am sorry about the delivery delay. I will check the tracking status.",
        ),
        ("user", "Please confirm when the delayed package will arrive."),
        (
            "assistant",
            "The tracking update shows the package is expected tomorrow.",
        ),
        ("user", "Thank you. Please notify me if the delivery date changes."),
    ]
    return [
        Message(role=role, content=content, timestamp=timestamp)
        for role, content in entries
    ]


def build_user2_messages(timestamp: str) -> list[Message]:
    """Build the second customer's overlapping delivery-delay conversation.

    Args:
        timestamp: UTC timestamp assigned to every message in this insertion.

    Returns:
        Five ordered messages for the second customer-support thread.
    """
    entries = [
        ("user", "My order 2002 delivery is delayed and I need a tracking update."),
        (
            "assistant",
            "I will investigate the delivery delay and review the shipment tracking.",
        ),
        ("user", "The tracking page has not changed since yesterday."),
        (
            "assistant",
            "The carrier reported a weather delay. The package should arrive Friday.",
        ),
        ("user", "Please send another update if the delivery is delayed again."),
    ]
    return [
        Message(role=role, content=content, timestamp=timestamp)
        for role, content in entries
    ]
