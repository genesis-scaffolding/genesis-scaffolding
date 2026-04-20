from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from .base import BaseTool
from .schema import ToolResult


class ComputeDateRangeTool(BaseTool):
    name = "compute_date_range"
    description = (
        "Computes the starting and ending date of a time period (day, week, month, quarter, year) "
        "relative to today. The response will say 'this week starts on YYYY-MM-DD and ends on YYYY-MM-DD' "
        "— dates are always in YYYY-MM-DD format."
    )
    parameters = {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "enum": ["day", "week", "month", "quarter", "year"],
                "description": "The time period to compute.",
            },
            "offset": {
                "type": "integer",
                "description": (
                    "Integer offset from the current period. "
                    "0 = current, -1 = previous, +1 = next. "
                    "Example: offset=0 for 'this week', offset=-1 for 'last week', offset=+1 for 'next week'."
                ),
            },
        },
        "required": ["period", "offset"],
        "additionalProperties": False,
    }

    async def run(self, working_directory=None, **kwargs: int) -> ToolResult:
        period = kwargs.get("period")
        offset = kwargs.get("offset", 0)

        if period not in ("day", "week", "month", "quarter", "year"):
            return ToolResult(
                status="error",
                tool_response=(
                    f"Invalid period '{period}'. Supported: day, week, month, quarter, year. "
                    "Dates are returned in YYYY-MM-DD format."
                ),
            )

        today = date.today()

        try:
            result = _compute_date_range(period, offset, today)
            return ToolResult(status="success", tool_response=result)
        except Exception as e:
            return ToolResult(status="error", tool_response=f"Date computation failed: {e!s}")


def _compute_date_range(period: str, offset: int, today: date) -> str:
    if period == "day":
        return _compute_day_range(offset, today)
    elif period == "week":
        return _compute_week_range(offset, today)
    elif period == "month":
        return _compute_month_range(offset, today)
    elif period == "quarter":
        return _compute_quarter_range(offset, today)
    elif period == "year":
        return _compute_year_range(offset, today)
    else:
        return f"Unknown period type: {period}"


def _compute_day_range(offset: int, today: date) -> str:
    target = today + relativedelta(days=offset)
    if offset == 0:
        return f"today is {target.isoformat()}"
    elif offset == -1:
        return f"1 day ago was {target.isoformat()}"
    elif offset == 1:
        return f"in 1 day will be {target.isoformat()}"
    else:
        return f"{offset} days from today is {target.isoformat()}"


def _compute_week_range(offset: int, today: date) -> str:
    # ISO week starts on Monday (weekday 0)
    # Get Monday of current week, then apply offset
    current_week_monday = today - timedelta(days=today.weekday())
    target_week_start = current_week_monday + timedelta(weeks=offset)
    target_week_end = target_week_start + timedelta(days=6)

    prefix = _offset_prefix(offset, "week")
    return f"{prefix} starts on {target_week_start.isoformat()} and ends on {target_week_end.isoformat()}"


def _compute_month_range(offset: int, today: date) -> str:
    target_first = today + relativedelta(months=offset, day=1)
    # Last day of month: go to first of next month, then subtract 1 day
    next_month_first = target_first + relativedelta(months=1)
    target_last = next_month_first - timedelta(days=1)

    prefix = _offset_prefix(offset, "month")
    return f"{prefix} starts on {target_first.isoformat()} and ends on {target_last.isoformat()}"


def _compute_quarter_range(offset: int, today: date) -> str:
    current_quarter = (today.month - 1) // 3
    target_quarter = current_quarter + offset
    target_year = today.year + (target_quarter // 4)
    adjusted_quarter = target_quarter % 4

    # Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec
    quarter_start_month = adjusted_quarter * 3 + 1

    target_first = date(target_year, quarter_start_month, 1)
    next_quarter_first = target_first + relativedelta(months=3)
    target_last = next_quarter_first - timedelta(days=1)

    prefix = _offset_prefix(offset, "quarter")
    return f"{prefix} starts on {target_first.isoformat()} and ends on {target_last.isoformat()}"


def _compute_year_range(offset: int, today: date) -> str:
    target_year = today.year + offset
    target_first = date(target_year, 1, 1)
    target_last = date(target_year, 12, 31)

    prefix = _offset_prefix(offset, "year")
    return f"{prefix} starts on {target_first.isoformat()} and ends on {target_last.isoformat()}"


def _offset_prefix(offset: int, period: str) -> str:
    if offset == 0:
        return f"this {period}"
    elif offset == -1:
        return f"last {period}"
    elif offset == 1:
        return f"next {period}"
    else:
        return f"{offset} {period}s"
