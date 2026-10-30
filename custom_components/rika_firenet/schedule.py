"""The stove's weekly heating schedule: 7 days, two time slots per day.

The bridge gives each slot as one integer, HHMMHHMM (start then end, leading zero dropped: 7001230 is 07:00 to
12:30), and 0 for a slot that is off. They are records 7 to 20 of `controls_pos` in /api/state, and are commanded
under the names below on /api/controls.

The main way to set it is a Home Assistant schedule (the "Schedule" helper, edited as a weekly grid): the button
"copy" sends its plan to the stove, see slots_from_ha_schedule(). The stove takes two slots per day.

A slot can also be edited as two times (entities disabled by default). A change is kept pending until the whole
schedule goes in one command.
"""

from __future__ import annotations

from datetime import time

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
SLOTS_PER_DAY = 2
SLOT_COUNT = len(DAYS) * SLOTS_PER_DAY
EDGES = ("start", "end")
FIRST_SLOT_POSITION = 7  # index of the first slot in controls_pos


def slot_index(day: int, slot: int) -> int:
    """0..13 from a day (0 = Monday) and a slot of that day (0 or 1)."""
    return day * SLOTS_PER_DAY + slot


def command_key(index: int) -> str:
    """Name of a slot in a command: heatTimeMon1 ... heatTimeSun2."""
    return f"heatTime{_DAY_NAMES[index // SLOTS_PER_DAY]}{index % SLOTS_PER_DAY + 1}"


def decode_slot(value: int) -> tuple[time, time] | None:
    """(start, end) of a slot value, (00:00, 00:00) for a slot that is off, None for a value that is no slot."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    start, end = divmod(value, 10000)
    if start // 100 > 23 or start % 100 > 59 or end // 100 > 24 or end % 100 > 59 or (end // 100 == 24 and end % 100):
        return None
    # The stove may give 24:00 as an end: a time entity cannot hold it, the last minute of the day stands for it.
    end_time = time(23, 59) if end // 100 == 24 else time(end // 100, end % 100)
    return time(start // 100, start % 100), end_time


def encode_slot(start: time, end: time) -> int:
    """Slot value of a start and an end. Start equal to end switches the slot off. Raises ValueError when the end
    is before the start."""
    if start == end:
        return 0
    if end < start:
        raise ValueError("the end of the slot is before its start")
    return (start.hour * 100 + start.minute) * 10000 + end.hour * 100 + end.minute


def slots_from_state(data: dict | None) -> list[int] | None:
    """The 14 slot values of an /api/state answer, None while the stove has not given them."""
    positions = (data or {}).get("controls_pos") or []
    if len(positions) < FIRST_SLOT_POSITION + SLOT_COUNT:
        return None
    values = positions[FIRST_SLOT_POSITION : FIRST_SLOT_POSITION + SLOT_COUNT]
    return [v if isinstance(v, int) and not isinstance(v, bool) else 0 for v in values]


HA_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class TooManySlots(ValueError):
    """A day of the Home Assistant schedule has more time ranges than the stove has slots."""

    def __init__(self, weekday: str, count: int) -> None:
        super().__init__(f"{weekday} has {count} time ranges, the stove takes {SLOTS_PER_DAY}")
        self.weekday = weekday
        self.count = count


def _as_time(value) -> time:
    """A time of a Home Assistant schedule: a time object, or a text such as '07:00:00'; its '24:00' (given as
    time.max or '24:00:00') becomes 23:59, the last minute a slot can end at here."""
    if isinstance(value, time):
        return time(23, 59) if value == time.max else value.replace(second=0, microsecond=0)
    parts = str(value).split(":")
    hour, minute = int(parts[0]), int(parts[1])
    return time(23, 59) if hour == 24 else time(hour, minute)


def slots_from_ha_schedule(plan: dict) -> list[int]:
    """The 14 slot values of a Home Assistant schedule ({"monday": [{"from": ..., "to": ...}, ...], ...}).

    A day without a range gets two slots that are off. Raises TooManySlots when a day has more than two ranges.
    """
    slots: list[int] = []
    for weekday in HA_WEEKDAYS:
        ranges = sorted(plan.get(weekday) or [], key=lambda r: _as_time(r["from"]))
        if len(ranges) > SLOTS_PER_DAY:
            raise TooManySlots(weekday, len(ranges))
        for i in range(SLOTS_PER_DAY):
            slots.append(encode_slot(_as_time(ranges[i]["from"]), _as_time(ranges[i]["to"])) if i < len(ranges) else 0)
    return slots
