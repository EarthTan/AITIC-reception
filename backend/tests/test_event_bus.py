# backend/tests/test_event_bus.py
import asyncio

from app.core.event_bus import EventBus


async def test_subscriber_receives_published_payload():
    bus = EventBus()
    queue = bus.subscribe("visit.imported")

    await bus.publish("visit.imported", {"visit_ids": [1]})

    payload = await asyncio.wait_for(queue.get(), timeout=1)
    assert payload == {"visit_ids": [1]}


async def test_multiple_subscribers_each_receive_the_event():
    bus = EventBus()
    queue_a = bus.subscribe("welcome.generated")
    queue_b = bus.subscribe("welcome.generated")

    await bus.publish("welcome.generated", {"visit_id": 5})

    assert await asyncio.wait_for(queue_a.get(), timeout=1) == {"visit_id": 5}
    assert await asyncio.wait_for(queue_b.get(), timeout=1) == {"visit_id": 5}


async def test_events_delivered_in_publish_order():
    bus = EventBus()
    queue = bus.subscribe("card.verify.requested")

    await bus.publish("card.verify.requested", {"card_uid": "A"})
    await bus.publish("card.verify.requested", {"card_uid": "B"})
    await bus.publish("card.verify.requested", {"card_uid": "C"})

    received = [await queue.get() for _ in range(3)]
    assert [item["card_uid"] for item in received] == ["A", "B", "C"]


async def test_subscribe_to_multiple_topics_merges_into_one_queue():
    bus = EventBus()
    queue = bus.subscribe(["a.topic", "b.topic"])

    await bus.publish("a.topic", {"from": "a"})
    await bus.publish("b.topic", {"from": "b"})

    first = await asyncio.wait_for(queue.get(), timeout=1)
    second = await asyncio.wait_for(queue.get(), timeout=1)
    assert {first["from"], second["from"]} == {"a", "b"}


async def test_publish_with_no_subscribers_does_not_raise():
    bus = EventBus()
    await bus.publish("nobody.listens", {})
