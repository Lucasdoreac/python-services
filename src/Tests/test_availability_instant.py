"""Contrato opt-in: dados sintéticos, Mongo em memória e catálogo simulado."""
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytest
from DAL import MongoDBConnectionFactory
from DAL.reservation_manager import ACTIVE_RESERVATION_STATUSES
from Tests.helpers import headers, OWNER
from utils.enums import EventStatus


def query(client, **params):
    return client.get('/rooms/available-rooms?' + urlencode(params), headers=headers(OWNER))


@pytest.fixture
def catalog(monkeypatch):
    from BLL.index import FlowController
    calls = []
    def rooms(self, page, size, name):
        calls.append((page, size, name))
        return ([{'id': x, 'name': x, 'campus': 'campus'} for x in ['busy', 'adjacent', 'rejected', 'unknown', 'free']], {'page': page, 'total_pages': 4})
    monkeypatch.setattr(FlowController, 'find_all_rooms', rooms)
    monkeypatch.setattr(FlowController, 'find_all_campus', staticmethod(lambda strict=False: [{'id': 'campus', 'name': 'Campus'}]))
    return calls


def test_availability_instant_overlap_status_pagination_and_offsets(client, catalog):
    db = MongoDBConnectionFactory.get_db()
    start = datetime(2031, 3, 3, 0)
    def add(room, begin, end, status):
        db.reservations.insert_one({'roomId': room, 'startAt': begin, 'endAt': end, 'status': status})
    add('busy', start-timedelta(hours=2), start+timedelta(minutes=1), ACTIVE_RESERVATION_STATUSES[0])
    add('adjacent', start-timedelta(hours=3), start, ACTIVE_RESERVATION_STATUSES[0])
    add('rejected', start, start+timedelta(hours=3), EventStatus.REJECTED_BY_REITORIA.value)
    add('unknown', start, start+timedelta(hours=3), 'unknown')
    for iso in ['2031-03-03T00:00:00Z', '2031-03-02T21:00:00-03:00', '2031-03-03T09:00:00+09:00']:
        r = query(client, start_at=iso, page=2, page_size=5, room_name='a')
        assert r.status_code == 200
        assert [x['id'] for x in r.json['data']] == ['adjacent', 'rejected', 'free']
        assert r.json['pagination'] == {'page': 2, 'total_pages': 4}
    assert catalog == [(2, 5, 'a')]*3


@pytest.mark.parametrize('status', ACTIVE_RESERVATION_STATUSES + [EventStatus.REJECTED_BY_COORDENACAO.value, EventStatus.REJECTED_BY_REITORIA.value, 'other'])
def test_statuses(client, catalog, status):
    db = MongoDBConnectionFactory.get_db()
    db.reservations.insert_one({'roomId': 'busy', 'startAt': datetime(2031, 3, 2, 22), 'endAt': datetime(2031, 3, 3, 1), 'status': status})
    r = query(client, start_at='2031-03-03T00:00:00Z')
    ids = [room['id'] for room in r.json['data']]
    assert ('busy' in ids) == (status in [EventStatus.REJECTED_BY_REITORIA.value, EventStatus.REJECTED_BY_COORDENACAO.value])


def test_other_adjacent_boundary_and_fraction(client, catalog):
    db = MongoDBConnectionFactory.get_db()
    db.reservations.insert_one({'roomId':'busy', 'startAt':datetime(2031,3,3,3), 'endAt':datetime(2031,3,3,6), 'status':'requested'})
    assert 'busy' in [x['id'] for x in query(client, start_at='2031-03-03T00:00:00Z').json['data']]
    assert 'busy' not in [x['id'] for x in query(client, start_at='2031-03-03T00:00:00.001Z').json['data']]


@pytest.mark.parametrize('value', ['', '2031-03-03', '2031-03-03T00:00:00', '2031-02-30T00:00:00Z', '2031-03-03T00:00:00+03:60', '2031-03-03T00:00:00+24:00', '2031-03-03T00:00:00.0001Z', '9999-12-31T23:59:59Z', 'garbage'])
def test_bad_start_is_400(client, catalog, value):
    assert query(client, start_at=value).status_code == 400
    assert catalog == []


def test_mixed_or_duplicate_parameters(client, catalog):
    assert query(client, start_at='2031-03-03T00:00:00Z', date='2031-03-03', time='00:00:00').status_code == 400
    assert client.get('/rooms/available-rooms?start_at=2031-03-03T00:00:00Z&start_at=2031-03-03T00:00:00Z', headers=headers(OWNER)).status_code == 400


def test_db_exception_returns_500(client, catalog, monkeypatch):
    from DAL.reservation_manager import ReservationManager
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic database error')
    monkeypatch.setattr(ReservationManager, 'find_unavailable_room_ids_at', fail)
    assert query(client, start_at='2031-03-03T00:00:00Z').status_code == 500
    assert query(client, date='2031-03-03', time='00:00:00').status_code == 500


def test_catalog_exception_returns_500(client, catalog, monkeypatch):
    from BLL.index import FlowController
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic catalog error')
    monkeypatch.setattr(FlowController, 'find_all_rooms', fail)
    assert query(client, start_at='2031-03-03T00:00:00Z').status_code == 500
    monkeypatch.setattr(FlowController, 'find_all_rooms', lambda *args: ([], {}))
    monkeypatch.setattr(FlowController, 'find_all_campus', fail)
    assert query(client, start_at='2031-03-03T00:00:00Z').status_code == 500


def test_legacy_date_time_is_unchanged(client, catalog):
    db = MongoDBConnectionFactory.get_db()
    db.reservations.insert_one({'roomId':'busy', 'startAt':datetime(2031,3,2,8), 'endAt':datetime(2031,3,2,11), 'status':'requested'})
    r = query(client, date='2031-03-02', time='08:00:00')
    assert r.status_code == 200 and 'busy' not in [x['id'] for x in r.json['data']]
    assert query(client, date='nonsense', time='08:00:00').status_code == 400
