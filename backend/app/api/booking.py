"""T03 — conversational booking: search, chat, select (state machine)."""

import json
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Booking, Bus, ChatMessage, PassengerProfile, User, WarningLog
from app.services import fare_advice, negotiator, vault
from app.services.detectors import (
    boarding_deviation,
    date_time_errors,
    deadline_buffer,
    passenger_mismatch,
)
from app.services.extractor import get_extractor
from app.services.passenger_ref import classify_passenger_ref

router = APIRouter(prefix="/api/booking", tags=["booking"])

REQUIRED_SLOTS = ["origin", "destination", "travel_date"]

_REPEAT_REQUEST = re.compile(
    r"\bsame as last\b|\bbook .*again\b|\brepeat\b|\bsame trip\b|\busual\b",
    re.IGNORECASE,
)
_COMPARE_REQUEST = re.compile(
    r"\bcheaper\b|\bcheapest\b|\bflexible\b|\bsave\b|\bwhich day\b|\bcompare\b",
    re.IGNORECASE,
)
_UNDO_REQUEST = re.compile(
    r"\bund(o|ne)\b|\bgo back\b|\bprevious\b|\brevert\b",
    re.IGNORECASE,
)


def _is_repeat_request(message: str) -> bool:
    return _REPEAT_REQUEST.search(message or "") is not None


def _is_undo_request(message: str) -> bool:
    return _UNDO_REQUEST.search(message or "") is not None


def _route_exists(db: Session, origin: str, destination: str) -> bool:
    return (
        db.query(Bus.id)
        .filter(
            func.lower(Bus.origin) == origin.lower(),
            func.lower(Bus.destination) == destination.lower(),
        )
        .first()
        is not None
    )


def _served_routes(db: Session) -> list[str]:
    pairs = db.query(Bus.origin, Bus.destination).distinct().all()
    undirected = sorted({tuple(sorted(pair)) for pair in pairs})
    return [f"{a} ↔ {b}" for a, b in undirected]


def _frequent_route(db: Session, user_id: int) -> tuple[str, str] | None:
    """Most-booked (origin, destination) for the user, real bookings only."""
    row = (
        db.query(Bus.origin, Bus.destination, func.count().label("trips"))
        .join(Booking, Booking.bus_id == Bus.id)
        .filter(Booking.user_id == user_id, Booking.is_synthetic.is_(False))
        .group_by(Bus.origin, Bus.destination)
        .order_by(func.count().desc())
        .first()
    )
    if row is None:
        return None
    return (row[0], row[1])


class SearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: str
    bus_type: str | None = None
    budget: int | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SelectRequest(BaseModel):
    session_id: str
    bus_id: int
    travel_date: str
    boarding_point: str
    passenger_profile_id: int | None = None
    manual_fields: int = 0


def _bus_card(bus: Bus, travel_date: date, db: Session) -> dict:
    booked = (
        db.query(func.count(Booking.id))
        .filter(Booking.bus_id == bus.id, Booking.travel_date == travel_date)
        .filter(Booking.status.in_(["PENDING_PAYMENT", "PAID"]))
        .scalar()
    ) or 0
    seats_left = max(0, bus.total_seats - booked)
    occupancy = round(1 - seats_left / bus.total_seats, 3)
    from app.services import analytics as analytics_service

    predicted = analytics_service.predict_occupancy(
        db, bus.origin, bus.destination, travel_date, bus.departure_time.hour
    )
    return {
        "id": bus.id,
        "operator": bus.operator,
        "bus_type": bus.bus_type,
        "origin": bus.origin,
        "destination": bus.destination,
        "departure": bus.departure_time.strftime("%H:%M"),
        "arrival": bus.arrival_time.strftime("%H:%M"),
        "arrival_day_offset": bus.arrival_day_offset,
        "duration_minutes": bus.duration_minutes,
        "fare": bus.base_fare,
        "total_seats": bus.total_seats,
        "seats_left": seats_left,
        "crowd_level": occupancy,
        "fare_indicator": analytics_service.fare_indicator(predicted),
    }


def _search(db: Session, origin: str, destination: str, travel: date, bus_type=None, budget=None):
    query = db.query(Bus).filter(
        func.lower(Bus.origin) == origin.lower(),
        func.lower(Bus.destination) == destination.lower(),
    )
    if bus_type:
        query = query.filter(Bus.bus_type == bus_type)
    if budget is not None:
        query = query.filter(Bus.base_fare <= budget)
    buses = query.order_by(Bus.departure_time).all()
    return [_bus_card(b, travel, db) for b in buses]


def _session_state(db: Session, user_id: int, session_id: str) -> dict:
    row = (
        db.query(ChatMessage)
        .filter_by(user_id=user_id, session_id=session_id, role="state")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if row:
        return json.loads(row.content)
    return {"state": "NEW", "slots": {}}


def _push_version(prev_slots: dict, prev_versions: list, slots: dict) -> list:
    """Append the pre-turn slots when they changed (cap 10)."""
    if slots == prev_slots:
        return prev_versions
    return (prev_versions + [prev_slots])[-10:]


def _save_state(db: Session, user_id: int, session_id: str, state: dict) -> None:
    db.add(
        ChatMessage(
            user_id=user_id, session_id=session_id, role="state", content=json.dumps(state)
        )
    )


def _save_versioned(
    db: Session, user_id: int, session_id: str, new_state: str, slots: dict, versions: list
) -> None:
    _save_state(
        db, user_id, session_id, {"state": new_state, "slots": slots, "versions": versions}
    )


def _log(db: Session, user_id: int, session_id: str, role: str, content: str, meta=None) -> None:
    db.add(
        ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            meta=json.dumps(meta or {}),
        )
    )


@router.post("/search")
def search(req: SearchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    travel = date.fromisoformat(req.travel_date)
    if travel < date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "travel date cannot be in the past")
    return {
        "buses": _search(db, req.origin, req.destination, travel, req.bus_type, req.budget)
    }


@router.post("/chat")
def chat(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _session_state(db, user.id, req.session_id)
    prev_slots = dict(state.get("slots", {}))
    prev_versions = list(state.get("versions", []))
    slots = get_extractor().extract(req.message, state.get("slots", {}))
    restored = False
    # Booking Undo: restore the pre-turn slots instead of interpreting the
    # message as a new choice. The extractor output for this turn is dropped.
    if _is_undo_request(req.message):
        if not prev_versions:
            assistant_text = "Nothing to undo yet — tell me your trip and we'll pick it up from there."
            _save_versioned(db, user.id, req.session_id, "NEEDS_INFO", prev_slots, prev_versions)
            _log(db, user.id, req.session_id, "user", req.message)
            _log(db, user.id, req.session_id, "assistant", assistant_text, {"slots": prev_slots})
            db.commit()
            return {
                "state": "NEEDS_INFO",
                "slots": prev_slots,
                "buses": [],
                "assistant_text": assistant_text,
                "messages": [{"role": "assistant", "content": assistant_text}],
            }
        slots = dict(prev_versions[-1])
        prev_versions = prev_versions[:-1]
        restored = True
    # Trip Guardian MVP — "same as last time": refill the traveller's most
    # frequent route when they name no places. Explicit places always win,
    # and first-timers fall through to the normal missing-slot questions.
    if (
        _is_repeat_request(req.message)
        and not slots.get("origin")
        and not slots.get("destination")
    ):
        route = _frequent_route(db, user.id)
        if route is not None:
            slots["origin"], slots["destination"] = route
            if not slots.get("travel_date"):
                slots["travel_date"] = (date.today() + timedelta(days=1)).isoformat()
    # T04: the classifier is authoritative for WHO the ticket is for, but an
    # explicit earlier signal wins (e.g. deadline follow-ups must not reset it).
    # A restored undo keeps its saved passenger_ref untouched.
    try:
        if not restored and not state.get("slots", {}).get("passenger_ref"):
            slots["passenger_ref"] = classify_passenger_ref(req.message)
    except Exception:
        slots.setdefault("passenger_ref", slots.get("passenger_ref"))
    _log(db, user.id, req.session_id, "user", req.message)

    # Fare copilot: "which day is cheapest?" compares dated options for the
    # known route and continues booking on the cheapest date.
    if (
        _COMPARE_REQUEST.search(req.message or "")
        and slots.get("origin")
        and slots.get("destination")
    ):
        compare_days = fare_advice.mentioned_dates(req.message, date.today())
        if not compare_days:
            compare_days = [date.today() + timedelta(days=i + 1) for i in range(3)]
        comparison = fare_advice.compare_dates(
            db, slots["origin"], slots["destination"], compare_days, slots.get("bus_type")
        )
        if comparison.get("cheapest"):
            cheapest_date = comparison["cheapest"]["date"]
            slots["travel_date"] = cheapest_date
            travel = date.fromisoformat(cheapest_date)
            buses = _search(
                db, slots["origin"], slots["destination"], travel,
                slots.get("bus_type"), slots.get("budget"),
            )
            assistant_text = fare_advice.summarize(
                comparison["options"],
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
            )
            _save_versioned(
                db, user.id, req.session_id, "RESULTS", slots,
                _push_version(prev_slots, prev_versions, slots),
            )
            _log(db, user.id, req.session_id, "assistant", assistant_text, {"slots": slots})
            db.commit()
            return {
                "state": "RESULTS",
                "slots": slots,
                "buses": buses,
                "assistant_text": assistant_text,
                "messages": [{"role": "assistant", "content": assistant_text}],
                "fare_comparison": comparison,
            }
        assistant_text = fare_advice.template_summary(comparison)
        _save_versioned(
            db, user.id, req.session_id, "NEEDS_INFO", slots,
            _push_version(prev_slots, prev_versions, slots),
        )
        _log(db, user.id, req.session_id, "assistant", assistant_text, {"slots": slots})
        db.commit()
        return {
            "state": "NEEDS_INFO",
            "slots": slots,
            "buses": [],
            "assistant_text": assistant_text,
            "messages": [{"role": "assistant", "content": assistant_text}],
            "fare_comparison": comparison,
        }

    missing = [s for s in REQUIRED_SLOTS if not slots.get(s)]
    buses: list = []
    assistant_text = ""
    negotiation = None
    served_routes = None
    if slots.get("passenger_ref") == "ambiguous" and not missing and not restored:
        assistant_text = (
            "Just to confirm — is this ticket for you, or for someone else? "
            "Reply 'for me' or, e.g., 'for my mother'."
        )
        new_state = "NEEDS_INFO"
    elif missing:
        friendly = {"origin": "Where are you travelling from?", "destination": "Where to?", "travel_date": "Which date are you travelling?"}
        assistant_text = friendly[missing[0]]
        new_state = "NEEDS_INFO"
    else:
        travel = date.fromisoformat(slots["travel_date"])
        if travel < date.today():
            assistant_text = "That date is in the past — which date did you mean?"
            new_state = "NEEDS_INFO"
        else:
            buses = _search(
                db,
                slots["origin"],
                slots["destination"],
                travel,
                slots.get("bus_type"),
                slots.get("budget"),
            )
            new_state = "RESULTS"
            negotiation = None
            if not buses and (slots.get("bus_type") or slots.get("budget") is not None):
                # Requirement Negotiator: name the exact trade instead of
                # dead-ending on "Found 0 bus(es)". Relaxed slots are stored
                # so the suggested buses book with one tap.
                wanted_budget = slots.get("budget")
                wanted_type = slots.get("bus_type")
                plan = negotiator.relax_search(
                    db, slots["origin"], slots["destination"], travel,
                    wanted_type, wanted_budget,
                )
                if plan is not None:
                    slots["bus_type"] = plan["relaxed_slots"]["bus_type"]
                    slots["budget"] = plan["relaxed_slots"]["budget"]
                    buses = _search(
                        db, slots["origin"], slots["destination"], travel,
                        slots.get("bus_type"), slots.get("budget"),
                    )
                    cheapest = min(buses, key=lambda b: b["fare"])
                    negotiation = {
                        "dropped": plan["dropped"],
                        "relaxed_slots": plan["relaxed_slots"],
                    }
                    assistant_text = negotiator.compromise_text(
                        plan["dropped"], wanted_budget, wanted_type,
                        cheapest["fare"], f"{cheapest['operator']} {cheapest['bus_type']}",
                    )
            if negotiation is None:
                if slots.get("deadline_time"):
                    assistant_text = f"Found {len(buses)} bus(es). I will double-check arrivals against your {slots['deadline_time']} deadline before payment."
                else:
                    assistant_text = (
                        f"Found {len(buses)} bus(es). "
                        "Do you have an arrival deadline (exam, meeting) I should watch for?"
                    )
            served_routes = None
            if not buses and negotiation is None:
                if not _route_exists(db, slots["origin"], slots["destination"]):
                    # Unknown corridor: explain coverage instead of "Found 0".
                    origin, destination = slots.pop("origin"), slots.pop("destination")
                    served_routes = _served_routes(db)
                    assistant_text = (
                        f"No direct buses from {origin} to {destination} yet — "
                        f"we currently run: {', '.join(served_routes)}. "
                        "Which of these works for you?"
                    )
                    new_state = "NEEDS_INFO"
                else:
                    assistant_text = (
                        "Nothing matches those filters — try dropping the budget "
                        "or bus type, or pick another date."
                    )
                    new_state = "NEEDS_INFO"
    if restored:
        assistant_text = "Went back to your previous choice. " + assistant_text
        versions = prev_versions
    else:
        versions = _push_version(prev_slots, prev_versions, slots)
    _save_versioned(db, user.id, req.session_id, new_state, slots, versions)
    _log(db, user.id, req.session_id, "assistant", assistant_text, {"slots": slots})
    db.commit()
    response = {
        "state": new_state,
        "slots": slots,
        "buses": buses,
        "assistant_text": assistant_text,
        "messages": [
            {"role": "assistant", "content": assistant_text},
        ],
    }
    if negotiation is not None:
        response["negotiation"] = negotiation
    if served_routes is not None:
        response["served_routes"] = served_routes
    return response


@router.post("/select")
def select(req: SelectRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _session_state(db, user.id, req.session_id)
    slots = state.get("slots", {})
    bus = db.get(Bus, req.bus_id)
    if bus is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown bus")
    travel = date.fromisoformat(req.travel_date)
    pending_details = None
    if req.passenger_profile_id is not None:
        profile = (
            db.query(PassengerProfile)
            .filter_by(
                id=req.passenger_profile_id,
                owner_user_id=user.id,
                is_self=False,
            )
            .one_or_none()
        )
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown saved passenger")
    else:
        # T05: a just-captured use-once passenger (remember=false) lives in the
        # pending store until consent; use it directly for this booking.
        from app.api.passengers import _pop_pending

        pending_details = _pop_pending(db, user.id, req.session_id)
        if pending_details is not None:
            profile = None
        else:
            profile = (
                db.query(PassengerProfile)
                .filter_by(owner_user_id=user.id, is_self=True)
                .one_or_none()
            )
    if profile is None and pending_details is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "no self profile; register again")
    if pending_details is not None:
        details = pending_details
    else:
        details = vault.decrypt_for_user(user.id, profile.data_encrypted, db, profile.id, "POST /api/booking/select")
    booking = Booking(
        user_id=user.id,
        bus_id=bus.id,
        travel_date=travel,
        passenger_profile_id=profile.id if profile is not None else None,
        passenger_snapshot_encrypted=vault.encrypt_for_user(user.id, details),
        boarding_point=req.boarding_point,
        fare=bus.base_fare,
        deadline_time=None,
        manual_fields=int(req.manual_fields or 0),
    )
    if slots.get("deadline_time"):
        hh, mm = slots["deadline_time"].split(":")
        from datetime import time as dtime

        booking.deadline_time = dtime(int(hh), int(mm))
    db.add(booking)
    db.flush()
    warnings = _run_detectors(db, user, booking, bus, slots, req.boarding_point)
    _save_state(
        db,
        user.id,
        req.session_id,
        {
            "state": "PRE_PAYMENT",
            "slots": slots,
            "versions": state.get("versions", []),
            "bus_id": bus.id,
            "booking_ref": booking.booking_ref,
        },
    )
    db.commit()
    return {
        "booking_ref": booking.booking_ref,
        "status": booking.status,
        "bus": _bus_card(bus, travel, db),
        "passenger": details,
        "fare": booking.fare,
        "boarding_point": booking.boarding_point,
        "warnings": warnings,
    }


def _run_detectors(db, user, booking, bus, slots, boarding_point) -> list[dict]:
    """Run all four detectors, log FIRED rows, attach safer alternatives."""
    from datetime import time as dtime

    warnings: list[dict] = []
    deadline = booking.deadline_time
    if slots.get("deadline_time") and deadline is None:
        hh, mm = slots["deadline_time"].split(":")
        deadline = dtime(int(hh), int(mm))
    if deadline is not None:
        warning = deadline_buffer(deadline, bus, booking.travel_date)
        if warning:
            earlier = (
                db.query(Bus)
                .filter(
                    func.lower(Bus.origin) == bus.origin.lower(),
                    func.lower(Bus.destination) == bus.destination.lower(),
                )
                .order_by(Bus.arrival_time)
                .all()
            )
            # Only offer buses that actually clear the deadline (detector-clean).
            safe = [
                b
                for b in earlier
                if b.id != bus.id
                and b.arrival_time < bus.arrival_time
                and deadline_buffer(deadline, b, booking.travel_date) is None
            ]
            if safe:
                warning["alternative_bus_id"] = safe[0].id
            warnings.append(warning)

    past = (
        db.query(Booking.boarding_point)
        .filter(Booking.user_id == user.id, Booking.bus_id == bus.id)
        .filter(Booking.id != booking.id)  # exclude the booking being made now
        .all()
    )
    history = [row[0] for row in past if row[0]]
    deviation = boarding_deviation(
        chosen=boarding_point, history=history, route=(bus.origin, bus.destination)
    )
    if deviation:
        warnings.append(deviation)

    details = vault.decrypt_for_user(user.id, booking.passenger_snapshot_encrypted, db, booking.passenger_profile_id, "detectors")
    mismatch = passenger_mismatch(
        passenger=details,
        passenger_ref=slots.get("passenger_ref", "self"),
        bus_type=bus.bus_type,
    )
    if mismatch:
        warnings.append(mismatch)

    warnings.extend(
        date_time_errors(
            travel_date=booking.travel_date,
            raw_text=json.dumps(slots),
            bus=bus,
        )
    )
    for warning in warnings:
        db.add(
            WarningLog(
                user_id=user.id,
                booking_id=booking.id,
                detector=warning["code"],
                outcome="FIRED",
                detail=json.dumps(warning),
            )
        )
    return warnings


@router.get("/session/{session_id}")
def session_state(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = _session_state(db, user.id, session_id)
    return {"session_id": session_id, **state}
