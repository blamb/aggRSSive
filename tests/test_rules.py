from datetime import datetime, timezone

from aggrssive.models import Item, Rule
from aggrssive.rules import item_passes, rule_matches


def item(**kw) -> Item:
    base = dict(source_id=1, guid="g", url="https://example.edu/post", title="", author="", text="", categories="", published_at=datetime.now(timezone.utc))
    base.update(kw)
    return Item(**base)


def rule(kind="include", field="any", pattern="", is_regex=False) -> Rule:
    return Rule(owner_type="bundle", owner_id=1, kind=kind, field=field, pattern=pattern, is_regex=is_regex)


def test_contains_is_case_insensitive():
    assert rule_matches(rule(pattern="Open Pedagogy"), item(title="notes on open pedagogy"))


def test_field_scoping():
    i = item(title="Assessment redesign", text="a webinar next week", author="Brian")
    assert rule_matches(rule(field="title", pattern="assessment"), i)
    assert not rule_matches(rule(field="title", pattern="webinar"), i)
    assert rule_matches(rule(field="author", pattern="brian"), i)


def test_regex():
    assert rule_matches(rule(pattern=r"\bAI\b", is_regex=True), item(title="AI in the classroom"))
    assert not rule_matches(rule(pattern=r"\bAI\b", is_regex=True), item(title="Detail oriented"))


def test_bad_regex_never_matches():
    assert not rule_matches(rule(pattern="(", is_regex=True), item(title="("))


def test_category_field():
    assert rule_matches(rule(field="category", pattern="oer"), item(categories="OER\nteaching"))


def test_exclude_wins():
    rules = [rule("include", pattern="assessment"), rule("exclude", pattern="webinar")]
    assert item_passes(item(title="Assessment ideas"), rules)
    assert not item_passes(item(title="Assessment webinar"), rules)


def test_no_include_rules_means_everything():
    assert item_passes(item(title="anything"), [rule("exclude", pattern="spam")])


def test_match_mode_all_vs_any():
    rules = [rule("include", pattern="open"), rule("include", pattern="pedagogy")]
    i = item(title="open education")
    assert item_passes(i, rules, "any")
    assert not item_passes(i, rules, "all")
    assert item_passes(item(title="open pedagogy"), rules, "all")
