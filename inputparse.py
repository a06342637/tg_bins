"""Extract only BIN prefixes from numbers at the start of pasted lines."""
import re

LEADING_NUMBER = re.compile(r"^([0-9]+(?:[ \t-]+[0-9]+)*)")


def extract_prefixes(text):
    """Accept plain BINs/cards and card-first records; deduplicate in input order.

    Preserve support for space/hyphen formatted cards. For short BINs followed
    by numeric metadata, retain the first field instead of appending a date.
    Never return complete card numbers or trailing fields.
    """
    prefixes = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        match = LEADING_NUMBER.match(line)
        if not match:
            continue
        groups = re.split(r"[ \t-]+", match.group(1))
        joined = "".join(groups)
        digits = joined if match.end() == len(line) or 13 <= len(joined) <= 19 else groups[0]
        if len(digits) < 4:
            continue
        prefix = digits[:6]
        if prefix not in seen:
            seen.add(prefix)
            prefixes.append(prefix)
    return prefixes
