"""Shared parsing utilities for game data strings."""


def parse_kda(kda_str: str) -> tuple[int, int, int]:
    """Parse K/D/A string like '5/3/12' into (kills, deaths, assists)."""
    if not kda_str:
        return (0, 0, 0)
    parts = kda_str.replace(" ", "").split("/")
    if len(parts) == 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return (0, 0, 0)
    return (0, 0, 0)


def parse_int(s: str) -> int:
    """Parse integer from string, default 0."""
    try:
        return int(s.replace(",", "").replace(" ", ""))
    except (ValueError, AttributeError):
        return 0


def parse_time(time_str: str) -> float:
    """Convert MM:SS to seconds."""
    if not time_str:
        return 0.0
    parts = time_str.split(":")
    if len(parts) == 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return 0.0
    return 0.0
