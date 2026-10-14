"""Elapsed time between sampled phases; never compare raw clip offsets."""
import math

PHASE_ORDER = ('entry', 'main_action', 'peak', 'exit', 'finish')


def number(value, maximum=None):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum) else None


def aligned_timing(phases):
    paired = {p['name']: p for p in phases if p.get('first') and p.get('second')}
    entry = paired.get('entry')
    if not entry:
        return {'rows': [], 'starts': None, 'reason': 'Both clips need an estimated Entry frame. You can still set skill starts manually.'}
    starts = [number(entry[side].get('timestamp')) for side in ('first', 'second')]
    if None in starts:
        return {'rows': [], 'starts': None, 'reason': 'The saved Entry timestamps are invalid.'}
    rows = []
    previous = starts
    for name in PHASE_ORDER[1:]:
        phase = paired.get(name)
        if not phase:
            continue
        times = [number(phase[side].get('timestamp')) for side in ('first', 'second')]
        if None in times or any(t <= prev for t, prev in zip(times, previous)):
            return {'rows': [], 'starts': None, 'reason': 'Saved phase timestamps are out of order. Review the clips and run a fresh analysis.'}
        first, second = (t - start for t, start in zip(times, starts))
        delta = second - first
        rows.append({'phase': name, 'phase_label': phase['label'], 'first': round(first, 2),
                     'second': round(second, 2), 'delta': round(delta, 2), 'absolute_delta': round(abs(delta), 2),
                     'direction': 'later' if delta > 0 else 'earlier' if delta < 0 else 'same',
                     'first_timestamp': times[0], 'second_timestamp': times[1]})
        previous = times
    return {'rows': rows, 'starts': starts, 'reason': '' if rows else 'Another paired phase is needed to compare elapsed time.'}
