from .cast_handstand import (
    CastHandstandRuleSet,
)


RULE_SETS = [
    CastHandstandRuleSet(),
]


def get_rule_set(
    skill_name,
):
    skill_name = (
        skill_name
        or ''
    )

    for rule_set in RULE_SETS:
        if rule_set.matches(
            skill_name
        ):
            return rule_set

    return None