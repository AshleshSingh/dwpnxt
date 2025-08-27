import collections
import yaml


def validate_rules(path: str = "analytics/rules.yaml"):
    """Validate keyword rules for empties and duplicates.

    Returns a list of warning strings.
    """
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    rules = data.get("rules", [])
    warnings = []

    seen_keywords = set()
    for rule in rules:
        name = rule.get("name", "<unnamed>")
        keywords = rule.get("keywords") or []
        if not keywords:
            warnings.append(f"Rule '{name}' has no keywords")
            continue
        # check duplicates within a rule
        counts = collections.Counter(k.lower() for k in keywords)
        dups = [k for k, c in counts.items() if c > 1]
        if dups:
            warnings.append(
                f"Rule '{name}' has duplicate keywords: {', '.join(sorted(dups))}"
            )
        # check duplicates across rules
        overlap = [k for k in (k.lower() for k in keywords) if k in seen_keywords]
        if overlap:
            warnings.append(
                f"Rule '{name}' shares keywords with other rules: {', '.join(sorted(set(overlap)))}"
            )
        seen_keywords.update(k.lower() for k in keywords)
    # check for identical keyword sets
    sets = {}
    for rule in rules:
        name = rule.get("name", "<unnamed>")
        key = tuple(sorted(k.lower() for k in (rule.get("keywords") or [])))
        if key in sets:
            warnings.append(
                f"Rule '{name}' has the same keywords as rule '{sets[key]}'"
            )
        else:
            sets[key] = name
    return warnings


if __name__ == "__main__":
    for w in validate_rules():
        print("WARNING:", w)
