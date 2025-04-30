from enum import Enum

class EmailStep(Enum):
    COORDENACAO = 0
    REITORIA = 1

class EventStatus(Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    APPROVED_BY_COORDENACAO = "approved_by_coordenacao"
    REJECTED_BY_COORDENACAO = "rejected_by_coordenacao"
    APPROVED_BY_REITORIA = "approved_by_reitoria"
    REJECTED_BY_REITORIA = "rejected_by_reitoria"
    REQUESTED_CHANGE = "requested_change"
    DIRECT_APPROVAL = "direct_approval"