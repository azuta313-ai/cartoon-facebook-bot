"""Scene selection guardrails for distinct Bobo stories."""

# The spaceship-button plot is retired, and the Snowball champion is a visual
# quality benchmark only. Its snowman/snowball story and reference are forbidden.
FORBIDDEN_SCENE_IDS = frozenset({5, 6})
SCENE_CANDIDATE_ORDER = (7, 1, 2, 0, 3, 4)


def eligible_scene_order(day_ordinal, slot, recent_scene_ids=()):
    """Rotate only original scene references; never fall back to retired plots."""
    slot = int(slot)
    if slot not in (0, 1):
        raise ValueError("Bobo slot must be 0 (morning) or 1 (evening)")
    recent = {int(value) for value in recent_scene_ids if value is not None}
    offset = (int(day_ordinal) + slot) % len(SCENE_CANDIDATE_ORDER)
    rotated = SCENE_CANDIDATE_ORDER[offset:] + SCENE_CANDIDATE_ORDER[:offset]
    return [scene_id for scene_id in rotated
            if scene_id not in recent and scene_id not in FORBIDDEN_SCENE_IDS]
