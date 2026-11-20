"""Scene selection guardrails for distinct Bobo stories."""

# Scene 5 (spaceship button) and scene 6 (snowball) are retired permanently.
# Scene 8 is the newly installed original pinwheel reference and is prioritized
# once before the remaining eligible original scenes rotate.
FORBIDDEN_SCENE_IDS = frozenset({5, 6})
SCENE_CANDIDATE_ORDER = (8, 7, 1, 2, 0, 3, 4)


def eligible_scene_order(day_ordinal, slot, recent_scene_ids=()):
    """Prioritize the unused pinwheel pilot, then rotate non-retired scenes."""
    slot = int(slot)
    if slot not in (0, 1):
        raise ValueError("Bobo slot must be 0 (morning) or 1 (evening)")
    recent = {int(value) for value in recent_scene_ids if value is not None}
    available = [scene_id for scene_id in SCENE_CANDIDATE_ORDER
                 if scene_id not in recent and scene_id not in FORBIDDEN_SCENE_IDS]
    if 8 in available:
        available.remove(8)
        return [8] + available
    if not available:
        return []
    offset = (int(day_ordinal) + slot) % len(available)
    return available[offset:] + available[:offset]
