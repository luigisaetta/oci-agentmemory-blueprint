"""
Author: L. Saetta
Date last modified: 2026-07-28
License: MIT
Description: Builds the fixed user-scoped customer-support messages for Example 05.
"""

from datetime import datetime, timedelta

from oracleagentmemory.apis import Message

USER1_ENTRIES = [
    ("user", "My delivery for order 1001 is delayed. I need a tracking update."),
    (
        "assistant",
        "I am sorry about the delivery delay for order 1001. I will check the tracking status.",
    ),
    ("user", "Please confirm when the delayed package will arrive."),
    (
        "assistant",
        "The tracking update shows the package for order 1001 is expected tomorrow.",
    ),
    ("user", "Thank you. Please notify me if the delivery date changes."),
    ("assistant", "Yes, sure. Have a nice day."),
]
USER2_ENTRIES = [
    ("user", "My order 2002 delivery is delayed and I need a tracking update."),
    (
        "assistant",
        "I will investigate the delivery delay for order 2002 and review the shipment tracking.",
    ),
    ("user", "The tracking page has not changed since yesterday."),
    (
        "assistant",
        "The carrier reported a weather delay. The package should arrive Friday.",
    ),
    ("user", "Please send another update if the delivery is delayed again."),
    ("assistant", "Yes, sure. Have a nice day."),
]


def build_messages(
    entries: list[tuple[str, str]], timestamp: str, start_offset_seconds: int = 0
) -> list[Message]:
    """Build timestamped messages with one-second chronological increments.

    Args:
        entries: Ordered pairs of message roles and contents.
        timestamp: UTC timestamp assigned to the first message before any offset.
        start_offset_seconds: Seconds to add before assigning the first message.

    Returns:
        Ordered messages with distinct UTC timestamps one second apart.
    """
    start_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return [
        Message(
            role=role,
            content=content,
            timestamp=(start_time + timedelta(seconds=start_offset_seconds + index))
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        )
        for index, (role, content) in enumerate(entries)
    ]


def build_user1_messages(timestamp: str) -> list[Message]:
    """Build the first customer's delivery-delay conversation.

    Args:
        timestamp: UTC timestamp assigned to the first message.

    Returns:
        Six ordered messages for the first customer-support thread.
    """
    return build_messages(USER1_ENTRIES, timestamp)


def build_user2_messages(
    timestamp: str, start_offset_seconds: int = 0
) -> list[Message]:
    """Build the second customer's overlapping delivery-delay conversation.

    Args:
        timestamp: UTC timestamp assigned to the first message before any offset.
        start_offset_seconds: Seconds to add before assigning the first message.

    Returns:
        Six ordered messages for the second customer-support thread.
    """
    return build_messages(USER2_ENTRIES, timestamp, start_offset_seconds)
