"""Map utility functions — shared across feature_engine and hero_memory."""


def classify_lane(x_norm: float, y_norm: float) -> str:
    """Classify a minimap position into lane using diagonal distance.

    LOL minimap is diagonal: top-left → bot-right.
    Mid lane runs along the main diagonal.

    Args:
        x_norm: Normalized X position (0=left, 1=right).
        y_norm: Normalized Y position (0=top, 1=bottom).

    Returns:
        "top", "mid", "bot", or "jungle".
    """
    # Mid lane: close to the main diagonal (top-left to bot-right)
    diag_dist = abs(x_norm - y_norm)
    if diag_dist < 0.2:
        return "mid"
    # Top lane: upper-left quadrant
    if y_norm < 0.4 and x_norm < 0.6:
        return "top"
    # Bot lane: lower-right quadrant
    if y_norm > 0.6 and x_norm > 0.4:
        return "bot"
    return "jungle"
