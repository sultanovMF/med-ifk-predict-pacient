from enum import Flag, auto


class Event(Flag):
    NONE = auto()
    ENTERED_NAME = auto()
    ENTERED_BOOL = auto()
    ENTERED_DIAGNOSIS = auto()
    END_FORM = auto()
