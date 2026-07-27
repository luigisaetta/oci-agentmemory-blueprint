"""
Author: L. Saetta
Date last modified: 2026-07-27
License: MIT
Description: Builds the fixed customer-support messages for Example 02.
"""

from oracleagentmemory.apis import Message

CONVERSATION = (
    ("user", "My package was due yesterday, but it has not arrived. Can you help?"),
    (
        "assistant",
        "I am sorry your package is late. I can check its delivery status for you.",
    ),
    ("user", "The order number is ORD-2048. Is there an updated delivery date?"),
    (
        "assistant",
        "The carrier reports a weather delay. Your package is now expected tomorrow.",
    ),
    ("user", "Will I receive a notification when it is out for delivery?"),
    (
        "assistant",
        "Yes. We will send an email with tracking details when the package is "
        "out for delivery.",
    ),
    (
        "user",
        "I need the item for an event. What happens if it does not arrive tomorrow?",
    ),
    (
        "assistant",
        "If it misses the updated date, contact us and we will review delivery "
        "options or a refund.",
    ),
    ("user", "Thank you. Please keep the order open while I wait for the update."),
    (
        "assistant",
        "You are welcome. Your order remains open, and we will continue monitoring the delivery.",
    ),
)


def build_customer_support_messages(timestamp: str) -> list[Message]:
    """Build the fixed customer-support conversation for persistence.

    Args:
        timestamp: UTC timestamp assigned to every message in this insertion.

    Returns:
        Ten ordered customer-support messages.
    """
    return [
        Message(role=role, content=content, timestamp=timestamp)
        for role, content in CONVERSATION
    ]
