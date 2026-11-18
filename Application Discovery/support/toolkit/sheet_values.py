"""Configured column mapping and literal native Sheets values; no Google access."""
import re
import math
from urllib.parse import urlsplit
from contracts import check, text

FIELDS = "first_seen last_seen company title job_link status source location level referral_contact target_fit fit_reason seen_count notes".split()


def safe_url(url):
    text(url, "job_link")
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None
                 and parsed.password is None and not any(ord(c) <= 32 or ord(c) == 127 for c in url))
    except ValueError:
        valid = False
    check(valid, "job_link", "expected observed HTTPS destination without credentials")
    return url


def hyperlink(url, label="Open job"):
    safe_url(url)
    text(label, "link label")
    return '=HYPERLINK("' + url.replace('"', '""') + '","' + label.replace('"', '""') + '")'


def formula_url(formula, label="Open job"):
    text(label, "link label")
    check(type(formula) is str, "job_link", "expected hyperlink formula")
    match = re.fullmatch(r'=HYPERLINK\("((?:[^"]|"")*)","' + re.escape(label.replace('"', '""')) + r'"\)', formula)
    check(match is not None, "job_link", "formula/label does not match configured presentation")
    return safe_url(match[1].replace('""', '"'))


def validate_mapping(columns):
    check(type(columns) is dict and bool(columns), "columns", "nonempty mapping required")
    indexes, headers = [], []
    for name, spec in columns.items():
        text(name, "logical field")
        check(type(spec) is dict and set(spec) == {"index", "header"}, "columns", "index/header required")
        check(type(spec["index"]) is int and spec["index"] > 0, "columns.index", "expected one-based integer")
        text(spec["header"], "columns.header")
        indexes.append(spec["index"])
        headers.append(spec["header"])
    check(len(indexes) == len(set(indexes)), "columns", "duplicate column index")
    check(len(headers) == len(set(headers)), "columns", "duplicate column header")


def decode_row(values, columns, *, link_label="Open job"):
    validate_mapping(columns)
    check(type(values) is list, "values", "expected row list")
    result = {name: values[spec["index"]-1] if spec["index"] <= len(values) else "" for name, spec in columns.items()}
    if result.get("job_link"):
        result["job_link"] = formula_url(result["job_link"], link_label)
    return result


def native_value(field, value, *, link_label="Open job"):
    if field == "job_link":
        return {"formulaValue": hyperlink(value, link_label)}
    if type(value) is str:
        return {"stringValue": value}  # Formula-looking source titles stay literal.
    if type(value) is bool:
        return {"boolValue": value}
    if type(value) in (int, float):
        check(math.isfinite(value), "value", "finite native number required")
        return {"numberValue": value}
    raise ValueError("Unsupported native cell value")


def mapped_changes(before, after, columns, *, link_label="Open job"):
    """Map changed configured fields only; unmapped fields remain in the private ledger."""
    validate_mapping(columns)
    return [{"field": field, "column": columns[field]["index"],
             "value": native_value(field, after[field], link_label=link_label)}
            for field in columns if field in after and (before is None or before.get(field) != after[field])]
