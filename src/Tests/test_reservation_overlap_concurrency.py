from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from threading import Barrier, Event, Lock

from mongomock import MongoClient
import pytest

from DAL import MongoDBConnectionFactory
from DAL.reservation_manager import (
    ReservationConflict,
    ReservationLockTimeout,
    ReservationManager,
)


class PausingReservationCollection:
    """Hold the first conflict read open so a second request can race it."""

    def __init__(self, collection):
        self.collection = collection
        self.first_read = Event()
        self.release_first_read = Event()
        self.second_read = Event()
        self._calls = 0
        self._calls_lock = Lock()

    def find_one(self, query):
        result = self.collection.find_one(query)
        with self._calls_lock:
            self._calls += 1
            call = self._calls
        if call == 1:
            self.first_read.set()
            if not self.release_first_read.wait(timeout=5):
                raise TimeoutError("test did not release the first reservation read")
        else:
            self.second_read.set()
        return result

    def insert_one(self, document):
        return self.collection.insert_one(document)


def test_overlapping_concurrent_reservations_are_serialized(monkeypatch):
    db = MongoClient()["reservation_overlap_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    manager.reservation_collection = PausingReservationCollection(db.reservations)
    start_together = Barrier(2)

    def reserve(event_id, start_hour):
        start_together.wait(timeout=2)
        try:
            manager.insert_reservation(
                "room-1",
                event_id,
                date(2031, 3, 2),
                time(start_hour, 0),
                time(start_hour + 3, 0),
            )
            return "created"
        except ReservationConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(reserve, "event-a", 10)
        second = pool.submit(reserve, "event-b", 11)
        assert manager.reservation_collection.first_read.wait(timeout=2)
        try:
            assert not manager.reservation_collection.second_read.wait(timeout=0.5), (
                "the second reservation reached its conflict read while the first "
                "request was still checking and inserting"
            )
        finally:
            manager.reservation_collection.release_first_read.set()

        outcomes = [first.result(timeout=2), second.result(timeout=2)]

    assert sorted(outcomes) == ["conflict", "created"]
    assert db.reservations.count_documents({"roomId": "room-1"}) == 1
    assert db.reservation_locks.count_documents({}) == 0


def test_unlocked_check_insert_control_reproduces_different_start_race(monkeypatch):
    """Negative control matching the pre-fix check-then-insert sequence."""
    db = MongoClient()["reservation_overlap_control_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    manager.reservation_collection = PausingReservationCollection(db.reservations)
    manager._acquire_reservation_lock = lambda room_id: ("room:room-1", "owner")
    manager._owns_reservation_lock = lambda lock_id, owner: True
    manager._release_reservation_lock = lambda lock_id, owner: None
    start_together = Barrier(2)

    def reserve(event_id, start_hour):
        start_together.wait(timeout=2)
        manager.insert_reservation(
            "room-1",
            event_id,
            date(2031, 3, 2),
            time(start_hour, 0),
            time(start_hour + 3, 0),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(reserve, "event-a", 10)
        second = pool.submit(reserve, "event-b", 11)
        assert manager.reservation_collection.first_read.wait(timeout=2)
        try:
            assert manager.reservation_collection.second_read.wait(timeout=2)
        finally:
            manager.reservation_collection.release_first_read.set()
        first.result(timeout=2)
        second.result(timeout=2)

    assert db.reservations.count_documents({"roomId": "room-1"}) == 2


def test_expired_room_reservation_lock_is_reclaimed(monkeypatch):
    db = MongoClient()["reservation_lock_recovery_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    lock_id = manager._reservation_lock_id("room-1")
    db.reservation_locks.insert_one(
        {
            "_id": lock_id,
            "owner": "stale-process",
            "leaseExpiresAt": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
    )

    claimed_lock_id, owner = manager._acquire_reservation_lock("room-1")

    assert claimed_lock_id == lock_id
    assert owner != "stale-process"
    assert manager._owns_reservation_lock(lock_id, owner)
    manager._release_reservation_lock(lock_id, owner)
    assert db.reservation_locks.count_documents({}) == 0


def test_adjacent_reservations_for_same_room_are_allowed(monkeypatch):
    db = MongoClient()["reservation_adjacent_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    day = date(2031, 3, 2)

    manager.insert_reservation("room-1", "event-a", day, time(10), time(13))
    manager.insert_reservation("room-1", "event-b", day, time(13), time(16))

    assert db.reservations.count_documents({"roomId": "room-1"}) == 2


def test_different_rooms_can_be_reserved_concurrently(monkeypatch):
    db = MongoClient()["reservation_different_rooms_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    manager.reservation_collection = PausingReservationCollection(db.reservations)
    start_together = Barrier(2)

    def reserve(room_id, event_id):
        start_together.wait(timeout=2)
        return manager.insert_reservation(
            room_id,
            event_id,
            date(2031, 3, 2),
            time(10),
            time(13),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(reserve, "room-1", "event-a"),
            pool.submit(reserve, "room-2", "event-b"),
        ]
        assert manager.reservation_collection.first_read.wait(timeout=2)
        try:
            assert manager.reservation_collection.second_read.wait(timeout=2), (
                "a reservation for another room waited on the first room lock"
            )
        finally:
            manager.reservation_collection.release_first_read.set()
        [result.result(timeout=2) for result in results]

    assert db.reservations.count_documents({}) == 2
    assert db.reservation_locks.count_documents({}) == 0


def test_contended_room_lock_times_out_without_creating_reservation(monkeypatch):
    db = MongoClient()["reservation_lock_timeout_test"]
    monkeypatch.setattr(MongoDBConnectionFactory, "get_db", staticmethod(lambda: db))
    manager = ReservationManager()
    manager._LOCK_WAIT_SECONDS = 0.01
    manager._LOCK_RETRY_SECONDS = 0.001
    lock_id = manager._reservation_lock_id("room-1")
    db.reservation_locks.insert_one(
        {
            "_id": lock_id,
            "owner": "active-process",
            "leaseExpiresAt": datetime.now(timezone.utc) + timedelta(minutes=2),
        }
    )

    with pytest.raises(ReservationLockTimeout):
        manager.insert_reservation(
            "room-1",
            "event-a",
            date(2031, 3, 2),
            time(10),
            time(13),
        )

    assert db.reservations.count_documents({}) == 0
    assert db.reservation_locks.count_documents({"_id": lock_id}) == 1
