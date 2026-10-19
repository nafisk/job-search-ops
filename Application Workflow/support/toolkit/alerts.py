"""Read-only alert collection and extraction. No account SDK or browser dependency."""
import base64
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urlsplit
import zlib
from contracts import check, digest, text, texts, timestamp
from sheet_values import safe_url

UUID = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
NAV = re.compile(r"^(?:view (?:all |more )?(?:top )?(?:job )?matches!?|see all jobs|manage.*|edit alert|unsubscribe|help|daily|weekly|never|linkedin|twitter|instagram|reddit|simplify|learn why.*)$", re.I)


def posting(url):
    """Known URL identities only; decode observed Simplify transport locally with limits."""
    url = unescape(url.strip())
    safe_url(url)
    parsed = urlsplit(url)
    if parsed.hostname == "email.matches.simplify.jobs" and parsed.path.startswith("/c/"):
        token = parsed.path[3:].split(".")[0]
        check(len(token) <= 8192, "redirect", "tracking token exceeds supported size")
        packed = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(packed, 65537)
        check(len(decoded) <= 65536 and decoder.eof and not decoder.unused_data, "redirect", "incomplete or oversized tracking payload")
        targets = parse_qs(decoded.decode("utf-8"), keep_blank_values=True).get("l", [])
        check(len(targets) == 1, "redirect", "one observed destination required")
        url = targets[0]
        safe_url(url)
        parsed = urlsplit(url)
        check(parsed.hostname != "email.matches.simplify.jobs", "redirect", "nested tracking unsupported")
    if parsed.hostname in ("linkedin.com", "www.linkedin.com"):
        match = re.fullmatch(r"/(?:comm/)?jobs/view/(\d+)/?", parsed.path)
        if match:
            return "linkedin:" + match[1], "https://www.linkedin.com/jobs/view/" + match[1] + "/"
        check(not re.search(r"/(?:comm/)?jobs/view/", parsed.path), "job URL", "unrecognized LinkedIn posting identity")
    if parsed.hostname in ("simplify.jobs", "www.simplify.jobs"):
        query = parse_qs(parsed.query, keep_blank_values=True)
        match = re.fullmatch(r"/p/(" + UUID + r")(?:/[^?#]*)?", parsed.path)
        if parsed.path.rstrip("/") == "/matches" and "viewMatch" in query:
            check(len(query["viewMatch"]) == 1 and re.fullmatch(UUID, query["viewMatch"][0]), "job URL", "invalid Simplify match identity")
            key = query["viewMatch"][0].lower()
            return "simplify:" + key, "https://simplify.jobs/matches?viewMatch=" + key
        if match:
            return "simplify:" + match[1].lower(), url.split("?")[0].split("#")[0]
        check(not parsed.path.startswith("/p/") and "viewMatch" not in query, "job URL", "unrecognized Simplify posting identity")
    return None


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors, self.visible, self.active, self.hidden = [], [], None, 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("head", "style", "script"):
            self.hidden += 1
        if tag == "a":
            if self.active is not None:
                self.anchors.append(self.active)
            self.active = [attrs.get("href", ""), ""]
        if tag == "img" and self.active is not None:
            self.active[1] += " " + attrs.get("alt", "")

    def handle_endtag(self, tag):
        if tag in ("head", "style", "script"):
            self.hidden = max(0, self.hidden - 1)
        if tag == "a" and self.active is not None:
            self.anchors.append(self.active)
            self.active = None

    def handle_data(self, data):
        if not self.hidden:
            self.visible.append(data)
            if self.active is not None:
                self.active[1] += data


def message_parts(raw):
    """Support full connector snake_case and native Gmail camelCase MIME trees."""
    parts, gaps = [], []
    def walk(node):
        mime = node.get("mime_type", node.get("mimeType", ""))
        body = node.get("body") or {}
        children = node.get("parts") or []
        if mime in ("text/plain", "text/html"):
            content = body.get("content")
            if content is None:
                encoded = body.get("base64_url_content") or body.get("data")
                if encoded is not None:
                    try:
                        content = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True).decode("utf-8")
                    except (ValueError, UnicodeError):
                        gaps.append("Undecodable text MIME body")
                elif body.get("attachment_id", body.get("attachmentId")):
                    gaps.append("Text MIME body requires attachment retrieval")
            if type(content) is str and content:
                if "size" in body and (type(body["size"]) is not int or body["size"] != len(content.encode("utf-8"))):
                    gaps.append("Text MIME byte length differs from declared size")
                if mime == "text/html" and "</html>" not in content.lower():
                    gaps.append("HTML document lacks a closing boundary")
                if any(x in content.lower() for x in ("[message clipped]", "[content truncated]", "[message truncated]")):
                    gaps.append("Body reports truncation")
                parts.append((mime, content))
            else:
                gaps.append("Missing text MIME body")
        for child in children:
            walk(child)
    walk(raw.get("payload") or {})
    if not parts:
        gaps.append("No complete text MIME parts")
    if raw.get("truncated") or raw.get("format") in ("minimal", "metadata"):
        gaps.append("Transport body is incomplete")
    return parts, gaps


@dataclass(frozen=True)
class CardReview:
    """Coordinator's independent full-message card inventory, not parser-generated truth."""
    message_id: str
    body_digest: str
    expected_job_ids: frozenset
    unresolved_cards: int
    non_alert: bool
    evidence_ref: str


def extract(raw, review=None):
    text(raw["id"], "message ID")
    parts, gaps = message_parts(raw)
    jobs, variants = {}, []
    for index, (mime, content) in enumerate(parts):
        if mime == "text/html":
            parser = Markup()
            parser.feed(content)
            anchors = parser.anchors
            if parser.active is not None:
                gaps.append("Unclosed HTML link")
            visible = " ".join(parser.visible)
        else:
            anchors = [(u.rstrip(".,);"), line.strip()) for line in content.splitlines()
                       for u in re.findall(r"https?://[^\s<>\"]+", line)]
            visible = content
            if any(not line.split(":", 1)[1].strip().startswith("https://") for line in content.splitlines()
                   if re.match(r"\s*view job:", line, re.I)):
                gaps.append("Apparent job card lacks a readable URL")
        lower = visible.lower()
        recognized = (("job alert" in lower or "jobs you may be interested" in lower or "jobs we think" in lower)
                      and "linkedin" in lower) or ("job matches" in lower and "simplify" in lower)
        if not recognized:
            gaps.append("Unrecognized alert layout")
        if "unsubscribe" not in lower:
            gaps.append("Alert footer not accounted for")
        seen = set()
        for url, label in anchors:
            label = " ".join(label.split())
            if not url.startswith(("https://", "http://")):
                if label and not NAV.fullmatch(label) and not url.startswith(("mailto:", "#")):
                    gaps.append("Unreadable link in apparent card")
                continue
            try:
                job = posting(url)
            except (ValueError, zlib.error):
                gaps.append("Unresolved or invalid posting/tracking URL")
                continue
            if job:
                key, destination = job
                seen.add(key)
                item = jobs.setdefault(key, {"job_id": key, "job_url": destination, "occurrences": 0, "parts": []})
                item["occurrences"] += 1
                if index not in item["parts"]:
                    item["parts"].append(index)
            elif re.search(r"\b(?:view job|apply(?: now)?)\b", label, re.I):
                gaps.append("Job-like link has an unsupported destination")
        variants.append(seen)
    if len({frozenset(v) for v in variants}) > 1:
        gaps.append("MIME representations disagree on job identities")
    if not jobs:
        gaps.append("No posting identities extracted")
    reviewed = (type(review) is CardReview and review.message_id == raw["id"] and review.body_digest == digest(raw))
    if reviewed:
        text(review.evidence_ref, "card review evidence")
        check(type(review.expected_job_ids) is frozenset and type(review.unresolved_cards) is int and review.unresolved_cards >= 0
              and type(review.non_alert) is bool, "review", "invalid card review")
        for key in review.expected_job_ids:
            text(key, "reviewed job ID")
        if review.non_alert and not review.expected_job_ids and not jobs and review.unresolved_cards == 0 and not message_parts(raw)[1]:
            return {"message_id": raw["id"], "status": "non_alert", "jobs": [], "gaps": [], "review_ref": review.evidence_ref}
        if review.non_alert or review.expected_job_ids != frozenset(jobs) or review.unresolved_cards:
            gaps.append("Independent card inventory is unresolved or disagrees")
    else:
        gaps.append("Independent full-message card inventory required")
    return {"message_id": raw["id"], "status": "incomplete" if gaps else "complete", "jobs": list(jobs.values()),
            "gaps": sorted(set(gaps)), "review_ref": review.evidence_ref if reviewed else None}


def received_at(raw):
    value = raw.get("internal_date", raw.get("internalDate"))
    check(type(value) in (str, int) and str(value).isdigit(), "internal_date", "Gmail receipt milliseconds required")
    return datetime.fromtimestamp(int(value) / 1000, timezone.utc)


def collect(adapter, scope, state=None, reviews=None):
    """Resumable read-only transport over frozen queries. Caller owns authorization/persistence."""
    text(scope["profile_id"], "profile_id")
    start, end = timestamp(scope["start"]), timestamp(scope["end"])
    check(start < end, "window", "nonempty frozen interval required")
    check(type(scope["max_attempts"]) is int and 1 <= scope["max_attempts"] <= 3,
          "attempts", "read limit must be between one and three")
    check(type(scope["queries"]) is list and bool(scope["queries"]), "queries", "explicit source queries required")
    texts([q["id"] for q in scope["queries"]], "query IDs")
    for query in scope["queries"]:
        text(query["query"], "query")
    texts([q["query"] for q in scope["queries"]], "query texts")
    binding = digest(scope)
    state = deepcopy(state) if state is not None else {"schema_version": 1, "scope_digest": binding, "pages": {}, "messages": {}, "attempts": {}, "errors": {}}
    check(type(state["schema_version"]) is int and state["schema_version"] == 1 and state["scope_digest"] == binding,
          "state", "different frozen scope or unsupported version")
    gaps, ids, cursors = [], set(), []
    def request(key, operation, validator):
        while state["attempts"].get(key, 0) < scope["max_attempts"]:
            state["attempts"][key] = state["attempts"].get(key, 0) + 1
            try:
                value = operation()
                validator(value)
                state["errors"].pop(key, None)
                return value
            except Exception as error:
                state["errors"][key] = type(error).__name__  # Do not copy potentially sensitive transport exception bodies.
        gaps.append({"item_id": key, "reason": "Read attempts exhausted: " + state["errors"].get(key, "unknown failure")})
        return None
    for query in scope["queries"]:
        token, visited = None, set()
        while True:
            key = "page:" + digest([query["id"], token])
            if key in visited:
                gaps.append({"item_id": query["id"], "reason": "Repeated pagination token"})
                cursors.append({"query_id": query["id"], "page_token": token, "reason": "Repeated pagination token"})
                break
            visited.add(key)
            page = state["pages"].get(key)
            if page is None:
                def validate_page(value):
                    check(value["complete"] is True, "page", "truncated page")
                    texts(value["message_ids"], "page message IDs")
                    text(value["evidence_ref"], "page evidence")
                    if value["next_page_token"] is not None:
                        text(value["next_page_token"], "next token")
                page = request(key, lambda: adapter.list_messages(query["query"], scope["start"], scope["end"], token), validate_page)
                if page is None:
                    cursors.append({"query_id": query["id"], "page_token": token, "reason": "Read attempts exhausted"})
                    break
                state["pages"][key] = deepcopy(page)
            ids.update(page["message_ids"])
            token = page["next_page_token"]
            if token is None:
                break
    results, sightings = [], []
    for mid in sorted(ids):
        raw = state["messages"].get(mid)
        if raw is None:
            def validate_message(value):
                check(value["id"] == mid, "message", "wrong ID returned")
                received_at(value)
                check(not message_parts(value)[1], "message", "body incomplete")
            raw = request("message:" + mid, lambda: adapter.read_message(mid), validate_message)
            if raw is None:
                continue
            state["messages"][mid] = deepcopy(raw)
        if not start <= received_at(raw) < end:
            results.append({"message_id": mid, "status": "outside_window", "jobs": [], "gaps": []})
            continue
        result = extract(raw, (reviews or {}).get(mid))
        results.append(result)
        gaps.extend({"item_id": mid, "reason": reason} for reason in result["gaps"])
        for job in result["jobs"]:
            sightings.append({"id": "email:" + mid + ":" + job["job_id"], "message_id": mid,
                              "source_item_id": mid + ":" + job["job_id"], "received_at": received_at(raw).isoformat(), **job})
    return {"status": "incomplete" if gaps else "complete", "next_state": state, "messages": results,
            "sightings": sightings, "gaps": gaps, "unresolved_cursors": cursors, "counts": {"message_ids": len(ids), "read_messages": len(results),
            "sightings": len(sightings), "unique_jobs": len({s["job_id"] for s in sightings})},
            "collection_window_proposed": scope["end"]}
