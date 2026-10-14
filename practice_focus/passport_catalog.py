"""The Practice Passport's fixed stamp families and coach recognition rules."""


BADGES = [
    ('first_practice', '🚀', 'My First Practice', [('earned', 'First stamp', 'Complete your first practice with coach-approved tracker results.', 'practice_days', 1)]),
    ('goal_getter', '🎯', 'Goal Getter', [(level, level.title(), f'Complete {target} coach-assigned skill or routine targets.', 'goals', target) for level, target in [('bronze', 3), ('silver', 10), ('gold', 25)]]),
    ('correction_detective', '🔍', 'Correction Detective', [('earned', 'First stamp', 'Show your coach that you applied a correction.', '', 0)]),
    ('wow_moment', '🌟', 'My Wow Moment', [('earned', 'First stamp', 'Earn your first coach-approved Wow.', 'wow', 1)]),
    ('personal_best', '📈', 'Better Than Before', [('earned', 'First stamp', 'Reach a personal improvement milestone confirmed by your coach.', '', 0)]),
    ('routine_builder', '🧩', 'Routine Builder', [('earned', 'First stamp', 'Complete a planned routine target in three different practices.', 'routine_days', 3)]),
    ('ask_learn', '🙋', 'Ask & Learn', [('earned', 'First stamp', 'Ask for help and show your coach what you learned.', '', 0)]),
    ('teammate', '🤝', 'Great Teammate', [('earned', 'First stamp', 'Encourage or help a teammate, recognized by your coach.', '', 0)]),
    ('event_explorer', '🗺️', 'Event Explorer', [(event, label, f'Complete a coach-assigned target on {label}. Collect all four event stamps!', 'event:' + event, 1) for event, label in [('vault', 'Vault'), ('bars', 'Bars'), ('beam', 'Beam'), ('floor', 'Floor')]]),
    ('weekly_growth', '📅', 'Growing Every Week', [('earned', 'First stamp', 'Meet your individual weekly goals in three training weeks. Your coach accounts for your schedule and planned breaks.', '', 0)]),
    ('attendance', '📍', 'Practice Pal', [(level, level.title(), f'Attend {target} practices. Present and Late count; breaks never reset your progress.', 'attendance', target) for level, target in [('bronze', 5), ('silver', 15), ('gold', 30)]]),
]

STAMPS = {}
SLOT_CHOICES = []
for code, icon, name, variants in BADGES:
    options = []
    for variant, label, rule, metric, target in variants:
        slot = code + ':' + variant
        title = name if variant == 'earned' else name + ' · ' + label
        STAMPS[slot] = {'slot': slot, 'code': code, 'variant': variant, 'icon': icon,
                        'name': name, 'label': label, 'title': title, 'rule': rule,
                        'metric': metric, 'target': target, 'manual': not metric}
        options.append((slot, title))
    SLOT_CHOICES.append((name, options))

BADGE_CHOICES = [(code, name) for code, _, name, _ in BADGES]
