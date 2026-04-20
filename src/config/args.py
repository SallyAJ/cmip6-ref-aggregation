import dataclasses


@dataclasses.dataclass
class DateUpdateArgs:
    year_start: int
    year_end: int
    month_start: int = 1
    month_end: int = 12
    day_start: int = 1
    day_end: int = 31


