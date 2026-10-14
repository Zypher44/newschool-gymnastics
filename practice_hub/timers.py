"""Persisted countdowns. Stopping freezes time; starting resumes it."""
import math
from datetime import timedelta


def remaining(deadline, now):
    return max(0, math.ceil((deadline - now).total_seconds()))


def group_deadline(session):
    return session.rotation_deadline or session.rotation_started_at + timedelta(minutes=session.rotation_minutes)


def stop_group(session, now):
    if session.rotation_paused_seconds is None:
        session.rotation_paused_seconds = remaining(group_deadline(session), now)


def start_group(session, now):
    if session.rotation_paused_seconds is not None:
        seconds = session.rotation_paused_seconds or session.rotation_minutes * 60
        session.rotation_deadline = now + timedelta(seconds=seconds)
        session.rotation_paused_seconds = None


def clock_values(deadline, seconds, now):
    seconds = remaining(deadline, now) if deadline else seconds
    return {'deadline': deadline.isoformat() if deadline else '', 'seconds': seconds,
            'display': f'{seconds // 60:02d}:{seconds % 60:02d}', 'running': bool(deadline),
            'server_now': now.isoformat()}
