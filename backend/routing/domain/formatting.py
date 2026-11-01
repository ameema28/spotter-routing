"""Text shown to the driver."""


def format_duration(seconds: float) -> str:
    """Readable time such as '14 h 48 min', rounded to the minute."""
    hours, minutes = divmod(round(seconds / 60), 60)
    return f'{hours} h {minutes} min' if hours else f'{minutes} min'
