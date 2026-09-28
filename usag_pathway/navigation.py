from django.urls import reverse


def pathway_navigation(names, current, route, athlete_id=None):
    """Build the progression and previous/next links for a single program."""
    names = list(names)
    steps = [
        {
            'label': f'Level {name}' if isinstance(name, int) else name.title(),
            'url': reverse(route, args=([athlete_id] if athlete_id is not None else []) + [name]),
            'current': name == current,
        }
        for name in names
    ]
    position = names.index(current)
    return {
        'steps': steps,
        'previous': steps[position - 1] if position else None,
        'next': steps[position + 1] if position < len(steps) - 1 else None,
    }
