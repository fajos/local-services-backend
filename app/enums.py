# app/enums.py

from enum import Enum


class PriceType(str, Enum):
    fixed = "Fixed"
    negotiable = "Negotiable"
    visit_required = "Visit Required"


class BookingStatus(str, Enum):
    pending = "Pending"
    accepted = "Accepted"
    declined = "Declined"
    completed = "Completed"


class QuoteStatus(str, Enum):
    pending = "Pending"
    accepted = "Accepted"
    declined = "Declined"


class VisitStatus(str, Enum):
    not_started = "Not_started"
    scheduled = "Scheduled"
    done = "Done"


class PaymentStatus(str, Enum):
    unpaid = "Unpaid"
    paid = "Paid"
    refunded = "Refunded"