"""
Author: L. Saetta
Date last modified: 2026-07-31
License: MIT
Description: Shared Oracle Agent Memory thread-discovery helpers for blueprint examples.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from oracleagentmemory.core import OracleAgentMemory


@dataclass(frozen=True)
class ThreadActivity:
    """One populated thread and its most recent message activity.

    Attributes:
        thread_id: Identifier of the persisted conversation thread.
        latest_message_timestamp: UTC timestamp supplied with its newest message.
        message_count: Number of persisted messages in the thread.
    """

    thread_id: str
    latest_message_timestamp: str
    message_count: int


def parse_timestamp(timestamp: object) -> datetime:
    """Parse a persisted message timestamp as a timezone-aware UTC value.

    Args:
        timestamp: ISO 8601 timestamp stored on a message record.

    Returns:
        The equivalent timezone-aware timestamp.

    Raises:
        ValueError: If the timestamp is not a timezone-aware ISO 8601 value.
    """
    if isinstance(timestamp, datetime):
        parsed_timestamp = timestamp
    elif isinstance(timestamp, str):
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    else:
        raise ValueError("Message timestamp must be an ISO 8601 value.")
    if parsed_timestamp.tzinfo is None:
        raise ValueError("Message timestamp must include a timezone.")
    return parsed_timestamp.astimezone(timezone.utc)


def list_populated_threads(
    client: OracleAgentMemory, user_id: str
) -> list[ThreadActivity]:
    """List a user's message-bearing threads by newest message first.

    This function uses a temporary private-store workaround because the SDK
    version used by the blueprint has no supported client thread-list API.

    Args:
        client: Configured Agent Memory client to query.
        user_id: Owner scope whose populated threads are requested.

    Returns:
        Thread activity entries ordered by latest message timestamp descending.

    Raises:
        ValueError: If a discovered message has an invalid timestamp.
    """
    # pylint: disable=protected-access
    messages = client._store.list(record_type="message", user_id=user_id, limit=None)
    thread_ids = {
        message.thread_id for message in messages if message.thread_id is not None
    }
    latest_messages: dict[object, tuple[datetime, str, int]] = {}
    for message in messages:
        if message.thread_id not in thread_ids:
            continue
        message_timestamp = parse_timestamp(message.timestamp)
        latest_for_thread = latest_messages.get(message.thread_id)
        message_count = 1 if latest_for_thread is None else latest_for_thread[2] + 1
        if latest_for_thread is None or message_timestamp > latest_for_thread[0]:
            latest_messages[message.thread_id] = (
                message_timestamp,
                message.timestamp,
                message_count,
            )
        else:
            latest_messages[message.thread_id] = (
                latest_for_thread[0],
                latest_for_thread[1],
                message_count,
            )
    activities = [
        ThreadActivity(str(thread_id), latest_timestamp, message_count)
        for thread_id, (_, latest_timestamp, message_count) in latest_messages.items()
    ]
    return sorted(
        activities,
        key=lambda activity: (
            -parse_timestamp(activity.latest_message_timestamp).timestamp(),
            activity.thread_id,
        ),
    )
