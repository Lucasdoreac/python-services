"""Synthetic regression/characterization; no interpretation of legacy dates is assumed."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from mongomock import MongoClient

from DAL import MongoDBConnectionFactory
from DAL.reservation_manager import ReservationConflict, ReservationManager
from utils.enums import EventStatus


@pytest.fixture
def memory_db(monkeypatch):
    db = MongoClient()['timezone_synthetic']
    monkeypatch.setattr(MongoDBConnectionFactory, 'get_db', staticmethod(lambda: db))
    return db


@pytest.mark.parametrize('start,end', [
    ('2031-03-02T20:00:00.000Z', datetime(2031, 3, 2, 23)),
    ('2031-03-02T21:00:00.000Z', datetime(2031, 3, 3, 0)),
    ('2031-03-02T22:00:00.000Z', datetime(2031, 3, 3, 1)),
    ('2031-12-31T23:30:00.000Z', datetime(2032, 1, 1, 2, 30)),
])
def test_submit_reservation_keeps_end_date_and_three_hours(memory_db, start, end):
    from BLL import FlowController
    inserted = FlowController.reserve_for_event('event-a', 'room-a', start)
    assert inserted['endAt'] == end
    assert inserted['endAt'] - inserted['startAt'] == timedelta(hours=3)
    assert memory_db.reservations.find_one({'eventId': 'event-a'})['endAt'] == end


def test_json_reservation_keeps_end_date(client):
    from BLL import FlowController
    from DAL import MongoDBConnectionFactory
    response, status = FlowController.register_reservation_from_json({
        'eventId': 'midnight-json', 'roomId': 'midnight-room',
        'reservationDate': '2031-03-02T22:00:00.000Z',
    })
    assert status == 201
    stored = MongoDBConnectionFactory.get_db().reservations.find_one({'eventId': 'midnight-json'})
    assert stored['startAt'] == datetime(2031, 3, 2, 22)
    assert stored['endAt'] == datetime(2031, 3, 3, 1)


def test_overlap_after_midnight_and_adjacent_slot(memory_db):
    from BLL import FlowController
    FlowController.reserve_for_event('a', 'room', '2031-03-02T22:00:00.000Z')
    with pytest.raises(ReservationConflict):
        FlowController.reserve_for_event('b', 'room', '2031-03-03T00:00:00.000Z')
    FlowController.reserve_for_event('c', 'room', '2031-03-03T01:00:00.000Z')
    assert memory_db.reservations.count_documents({}) == 2


def test_existing_ambiguous_and_broken_legacy_is_not_rewritten_on_retry(memory_db):
    from BLL import FlowController
    doc = {'_id': 'legacy', 'roomId': 'room', 'eventId': 'old',
           'startAt': datetime(2031, 3, 2, 22), 'endAt': datetime(2031, 3, 2, 1),
           'status': EventStatus.WAITING.value}
    memory_db.reservations.insert_one(doc.copy())
    assert FlowController.reserve_for_event('old', 'room', '2031-03-02T22:00:00.000Z') is None
    assert memory_db.reservations.find_one({'_id': 'legacy'}) == doc


@pytest.mark.parametrize('zone,expected_iso,expected_query_date', [
    ('America/Sao_Paulo', '2031-03-02T11:00:00+00:00', '2031-03-02'),
    ('Asia/Tokyo', '2031-03-01T23:00:00+00:00', '2031-03-01'),
])
def test_characterizes_current_frontend_query_mismatch(memory_db, zone, expected_iso, expected_query_date):
    from BLL import FlowController
    # Models selectedDate.setHours(8), toISOString().split('T')[0], and literal 08:00 query.
    selected = datetime(2031, 3, 2, 8, tzinfo=ZoneInfo(zone))
    instant = selected.astimezone(timezone.utc)
    assert instant.isoformat() == expected_iso
    assert instant.date().isoformat() == expected_query_date
    FlowController.reserve_for_event('a', 'room', instant.strftime('%Y-%m-%dT%H:%M:%S.000Z'))
    manager = ReservationManager()
    # The actual API query does not exclude the occupied room at the UI's reported time.
    assert 'room' not in manager.find_unavailable_room_ids_by_date(expected_query_date, '08:00:00')
    assert 'room' in manager.find_unavailable_room_ids_by_date(instant.strftime('%Y-%m-%d'), instant.strftime('%H:%M:%S'))
