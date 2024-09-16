from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class Building:
    name: str
    address: str
    acronym: str
    closeAt: str
    openAt: str
    mapsLink: str

@dataclass
class Department:
    _id: str
    name: str
    emails: List[str]
    head: str

@dataclass
class Event:
    _id: str
    name: str
    organizer: dict  # Could further define this with another dataclass if more detail is needed
    eventTypeId: str
    odsTypeId: str
    subscriptionLink: str
    description: str
    graduationId: str
    targetPublic: str
    resources: str
    expectedSubscribers: str
    roomType: List[str]
    entrepreneuralPath: str
    extensionProject: str
    studentsMonitors: List[int]
    eventLogo: str

@dataclass
class Graduation:
    _id: str
    code: str
    name: str
    graduation: str
    departamentId: str

@dataclass
class Reservation:
    _id: str
    roomId: str
    courseId: str
    startAt: datetime
    endAt: datetime

@dataclass
class Room:
    _id: str
    id: int
    name: str
    studentCapacity: int
    buildingId: str
    roomNumber: int
    floor: int

@dataclass
class Type:
    _id: str
    types: List[dict]  # This could be further refined into a list of another data class if needed
    collection: str

