"""Private import queue and delivery bookkeeping. No account or network access."""
from __future__ import annotations

import contextlib
import base64
import datetime as dt
from email.header import decode_header, make_header
from email.utils import getaddresses
import fcntl
import hashlib
import html
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, urlsplit
from zoneinfo import ZoneInfo


class ProtocolError(ValueError):
    """An input, ownership condition, or reconciliation is unsafe."""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read(value):
    if isinstance(value, (str, Path)):
        return json.loads(Path(value).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ProtocolError("Non-finite JSON number")))
    return value


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            out.write(canonical(value) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def storage(root):
    root = Path(root).expanduser().resolve()
    if root.name == "state":
        raise ProtocolError("--root must be the installation folder, not its state subfolder")
    base = root / "state"
    preferences = base / "preferences-update.json"
    if preferences.is_symlink():
        raise ProtocolError("Managed preferences journal must not be a symlink")
    if preferences.exists() and read(preferences).get("status") == "applying":
        raise ProtocolError("Preferences update is applying; recover with preferences-apply before ordinary workflow operations")
    for part in ("queue/pending", "queue/done", "writer/claims", "writer/journals", "writer/receipts", "delivery"):
        folder = base / part
        # Never route managed state through an externally installed symlink.
        if any(p.is_symlink() for p in (base, *folder.parents, folder) if p != root and root in (p, *p.parents)):
            raise ProtocolError("Managed state contains a symlink")
        folder.mkdir(parents=True, exist_ok=True)
    return base


@contextlib.contextmanager
def locked(root):
    base = storage(root)
    # ponytail: one installation-wide local lock serializes small metadata changes.
    # The persistent workbook claim below survives process exits; there is no TTL.
    with (base / ".protocol.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield base
        fcntl.flock(stream, fcntl.LOCK_UN)


def text(value, field, limit=2000, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        raise ProtocolError(f"Invalid {field}")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ProtocolError(f"Control character in {field}")
    return value


def identifier(value, field="identifier"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", value):
        raise ProtocolError(f"Invalid {field}")
    return value


def timestamp(value, field="timestamp"):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ProtocolError(f"Invalid {field}") from exc
    if parsed.tzinfo is None:
        raise ProtocolError(f"{field} must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def url(value):
    text(value, "URL", 4000)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ProtocolError("Malformed URL") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ProtocolError("Only observed HTTP(S) URLs without credentials are allowed")
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ProtocolError("Whitespace in URL")
    if parsed.hostname in {"localhost", "localhost.localdomain"}:
        raise ProtocolError("Local URLs are not job evidence")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ProtocolError("Private network URL is not public job evidence")
    if any(k.lower() in {"access_token", "auth", "authorization", "token", "password", "session", "sessionid", "api_key"} for k, _ in parse_qsl(parsed.query)):
        raise ProtocolError("Credential-bearing URL")
    return value


def number(value, field, low=0, high=1_000_000, nullable=False):
    if nullable and value is None:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ProtocolError(f"Invalid {field}")
    return value


def validate_packet(value):
    p = read(value)
    if not isinstance(p, dict) or p.get("schema_version") != 1:
        raise ProtocolError("Packet schema_version must be 1")
    identifier(p.get("packet_id"), "packet_id")
    if p.get("source") not in {"email", "portal", "blind"}:
        raise ProtocolError("Unknown packet source")
    identifier(p.get("workbook_id"), "workbook_id")
    timestamp(p.get("observed_at"))
    policy = p.get("policy", {})
    if not isinstance(policy, dict):
        raise ProtocolError("Invalid policy object")
    identifier(policy.get("id"), "policy id")
    identifier(policy.get("version"), "policy version")
    if policy.get("source") != p["source"]:
        raise ProtocolError("Policy must bind the producing source")
    jobs = p.get("jobs")
    if not isinstance(jobs, list) or len(jobs) > 10000:
        raise ProtocolError("jobs must be a bounded list")
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ProtocolError("Invalid job")
        key = identifier(job.get("job_key"), "job_key")
        if key in seen:
            raise ProtocolError("Repeated job in one packet")
        seen.add(key)
        for field in ("company", "title", "location", "source_job_id", "fit_reason"):
            text(job.get(field), field)
        url(job.get("url"))
        if job.get("provider") not in {"LinkedIn", "Simplify", "Official ATS"}:
            raise ProtocolError("Unknown job provider")
        for field in ("level", "experience", "target_fit", "referral_contact", "notes"):
            text(job.get(field, ""), field, empty=True)
        if not isinstance(job.get("referral_hold", False), bool):
            raise ProtocolError("referral_hold must be boolean")
        q = job.get("qualification", {})
        if not isinstance(q, dict) or "required_years" not in q:
            raise ProtocolError("Qualification must declare required_years, including null when unstated")
        if q.get("decision") != "QUALIFY" or q.get("tier") not in {"core", "stretch", "senior_exception"}:
            raise ProtocolError("Only explicitly qualified proposals enter Jobs")
        timestamp(q.get("checked_at"))
        # These are source-backed agent judgments, never a claim that code verified fit.
        evidence = q.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ProtocolError("Invalid qualification evidence")
        for check in ("identity", "requirements", "location", "availability"):
            item = evidence.get(check, {})
            if not isinstance(item, dict):
                raise ProtocolError("Invalid evidence item")
            url(item.get("url"))
            text(item.get("quote"), f"{check} evidence quote", 12000)
        number(q.get("required_years"), "required_years", high=100, nullable=True)
        if p["source"] == "blind":
            number(job.get("rating"), "rating", high=5)
            text(job.get("rating_as_of"), "rating_as_of", 100)
            if job.get("rating_origin") != "user_supplied":
                raise ProtocolError("Blind rating provenance must identify the user-supplied list")
        sightings = job.get("sightings")
        if not isinstance(sightings, list) or not sightings or len(sightings) > 10000:
            raise ProtocolError("Every job requires bounded source sightings")
        ids = set()
        for event in sightings:
            if not isinstance(event, dict):
                raise ProtocolError("Invalid sighting")
            identifier(event.get("id"), "sighting id")
            timestamp(event.get("observed_at"))
            if event["id"] in ids:
                raise ProtocolError("Duplicate sighting in job")
            ids.add(event["id"])
        aliases = job.get("aliases", [])
        if not isinstance(aliases, list) or len(aliases) > 100:
            raise ProtocolError("Invalid alias list")
        for alias in aliases:
            if not isinstance(alias, dict):
                raise ProtocolError("Invalid alias evidence")
            identifier(alias.get("job_key"), "alias job_key")
            url(alias.get("evidence_url"))
            text(alias.get("quote"), "alias identity evidence", 12000)
    for collection in ("companies", "coverage"):
        if not isinstance(p.get(collection, []), list) or len(p.get(collection, [])) > 10000 or not all(isinstance(x, dict) for x in p.get(collection, [])):
            raise ProtocolError(f"Invalid {collection} list")
    for company in p.get("companies", []):
        identifier(company.get("company_key"), "company_key")
        text(company.get("company"), "company")
        number(company.get("rating"), "rating", high=5)
        timestamp(company.get("checked_at"))
        url(company.get("careers_url"))
        text(company.get("rating_as_of"), "rating_as_of", 100)
        if company.get("rating_origin") != "user_supplied":
            raise ProtocolError("Company rating needs user-supplied provenance")
    for coverage in p.get("coverage", []):
        identifier(coverage.get("company_key"), "coverage company_key")
        text(coverage.get("company"), "coverage company")
        text(coverage.get("scope"), "coverage scope")
        timestamp(coverage.get("checked_at"))
        if coverage.get("status") not in {"complete", "partial", "unavailable", "unknown"}:
            raise ProtocolError("Invalid source coverage")
        for field in ("observed_jobs", "qualified_jobs"):
            number(coverage.get(field), field, nullable=True)
    canonical(p)  # Reject NaN/Infinity anywhere, including optional source fields.
    return p


def enqueue(root, packet):
    p = validate_packet(packet)
    key = digest([p["source"], p["packet_id"], p["workbook_id"]])
    entry = {"packet_key": key, "packet_sha256": digest(p), "enqueued_at": now(), "packet": p}
    with locked(root) as base:
        validate_policy(base, p)
        for status in ("pending", "done"):
            path = base / "queue" / status / f"{key}.json"
            if path.exists():
                prior = read(path)
                if prior["packet_sha256"] != entry["packet_sha256"]:
                    raise ProtocolError("Packet ID reused with different bytes")
                return {"status": status, "packet_key": key, "receipt_id": prior.get("receipt_id")}
        atomic(base / "queue/pending" / f"{key}.json", entry)
    return {"status": "pending", "packet_key": key}


def configure_policies(root, workbook_id, sources, timezone="UTC"):
    """Setup-only binding from the human-reviewed profile, never worker output."""
    identifier(workbook_id, "workbook_id")
    ZoneInfo(timezone)
    if not isinstance(sources, dict) or not sources or not set(sources) <= {"email", "portal", "blind"}:
        raise ProtocolError("Invalid enabled policy sources")
    for source, policy in sources.items():
        identifier(policy.get("id"), "policy id")
        identifier(policy.get("version"), "policy version")
        number(policy.get("max_required_years"), "maximum years", high=100)
        if not isinstance(policy.get("allow_unstated_years"), bool):
            raise ProtocolError("State the unstated-years choice")
        tiers = policy.get("allowed_tiers")
        if not isinstance(tiers, list) or not tiers or not set(tiers) <= {"core", "stretch", "senior_exception"}:
            raise ProtocolError("Invalid allowed qualification tiers")
        for pattern in policy.get("forbidden_title_patterns", []):
            text(pattern, "title pattern", 500)
            re.compile(pattern)
        if source == "blind":
            number(policy.get("min_rating"), "minimum rating", high=5)
            number(policy.get("base_required_years"), "base required years", high=policy["max_required_years"])
    with locked(root) as base:
        if any(read(p)["status"] not in {"committed", "cancelled"} for p in (base / "writer/journals").glob("*.json")):
            raise ProtocolError("Cannot change policy while a write is unresolved")
        value = {"schema_version": 1, "workbook_id": workbook_id, "timezone": timezone, "sources": sources, "configured_at": now()}
        atomic(base / "approved-policies.json", value)
        return value


def validate_policy(base, packet):
    path = base / "approved-policies.json"
    if not path.exists():
        raise ProtocolError("Bind the reviewed installation policy before queueing")
    config = read(path)
    if config.get("schema_version") != 1 or config.get("workbook_id") != packet["workbook_id"]:
        raise ProtocolError("Packet workbook is not the approved shared tracker")
    policy = config.get("sources", {}).get(packet["source"])
    if not policy or any(policy.get(k) != packet["policy"].get(k) for k in ("id", "version")):
        raise ProtocolError("Packet does not match an enabled approved policy/version")
    for job in packet["jobs"]:
        qualification = job["qualification"]
        years = qualification["required_years"]
        if years is None and not policy["allow_unstated_years"]:
            raise ProtocolError("Approved policy does not allow unstated experience")
        if years is not None and years > policy["max_required_years"]:
            raise ProtocolError("Mandatory experience exceeds the source policy ceiling")
        if qualification["tier"] not in policy["allowed_tiers"]:
            raise ProtocolError("Qualification tier is outside source policy")
        if any(re.search(pattern, job["title"]) for pattern in policy.get("forbidden_title_patterns", [])):
            raise ProtocolError("Role title is excluded by the source policy")
        if packet["source"] == "blind":
            if job["rating"] < policy["min_rating"]:
                raise ProtocolError("Rating is below the configured threshold")
            base_years = number(policy.get("base_required_years"), "base required years", high=policy["max_required_years"])
            if qualification["tier"] == "core" and years is not None and years > base_years:
                raise ProtocolError("Blind core tier exceeds its base experience ceiling")
            if qualification["tier"] == "stretch" and (years is None or years <= base_years):
                raise ProtocolError("Blind stretch tier requires verified experience above its base ceiling")
    return policy


def pending(root, workbook_id=None):
    result = [read(p) for p in sorted((storage(root) / "queue/pending").glob("*.json"))]
    return [p for p in result if workbook_id is None or p["packet"]["workbook_id"] == workbook_id]


def claim_path(base, workbook_id):
    return base / "writer/claims" / f"{digest(workbook_id)}.json"


def acquire_claim(base, workbook_id, owner):
    identifier(owner, "owner")
    path = claim_path(base, workbook_id)
    if path.exists():
        current = read(path)
        if current["owner"] != owner:
            raise ProtocolError("Workbook has another persistent owner; no automatic takeover")
        return current
    claim = {"workbook_id": workbook_id, "owner": owner, "acquired_at": now()}
    atomic(path, claim)
    return claim


def release_claim(root, workbook_id, owner):
    with locked(root) as base:
        path = claim_path(base, workbook_id)
        if not path.exists():
            return {"status": "already_released"}
        if read(path)["owner"] != owner:
            raise ProtocolError("Only the recorded owner can release its claim")
        unresolved = [read(x) for folder in ("writer/journals", "writer/local-tracking", "writer/referrals") for x in (base / folder).glob("*.json")]
        if any(j["workbook_id"] == workbook_id and j["status"] not in {"committed", "cancelled"} for j in unresolved):
            raise ProtocolError("Reconcile or explicitly cancel the unattempted journal before release")
        path.unlink()
    return {"status": "released"}


def _saved_receipts(base):
    receipts = {read(path)["receipt_id"]: read(path) for path in sorted((base / "writer/receipts").glob("*.json"))}
    # Upgrade compatibility: pre-release local tracking receipts lived only in
    # their committed journals. Include them without manufacturing a new save.
    for path in sorted((base / "writer/local-tracking").glob("*.json")):
        record = read(path)
        if record.get("status") != "committed":
            continue
        receipt = record["receipt"]
        prior = receipts.setdefault(receipt["receipt_id"], receipt)
        if any(prior.get(key) != receipt.get(key) for key in ("workbook_id", "updates", "new_records")):
            raise ProtocolError("Conflicting tracking receipt copies")
    if any(r.get("status") != "saved" for r in receipts.values()):
        raise ProtocolError("Only verified saved receipts can enter a report")
    return list(receipts.values())


def tracking_summary(receipts, accepted_receipts=None):
    """Public facts only: never copy notes, contacts or evidence references."""
    identities = {}
    for receipt in accepted_receipts or receipts:
        for job in receipt.get("new_jobs", []) + receipt.get("new_records", []) + receipt.get("tracking_changes", []):
            identities[(receipt["workbook_id"], job["job_key"])] = {key: job[key] for key in ("company", "title", "url")}
    result = []
    for receipt in receipts:
        if receipt.get("operation") != "tracking":
            continue
        for change in receipt.get("tracking_changes", receipt.get("updates", [])):
            identity = ({key: change[key] for key in ("company", "title", "url")} if all(key in change for key in ("company", "title", "url")) else identities.get((receipt["workbook_id"], change["job_key"])))
            if identity is None:
                raise ProtocolError("Historical tracking receipt lacks role identity; rerun local-update with its original plan to review and adopt the receipt")
            label = change["field"] + " updated"
            if change["field"] == "Application Status":
                label = "Application Status: " + (change["old_value"] or "(blank)") + " → " + change["new_value"]
            result.append(dict(identity, change=label))
        for item in receipt.get("new_records", []):
            result.append({key: item[key] for key in ("company", "title", "url")} | {"change": "Tracked application: " + item["status"]})
    return result


def prepare_brief(root, brief_id):
    """Reserve undelivered saved receipts. This never sends or starts tracking."""
    identifier(brief_id, "brief_id")
    with locked(root) as base:
        path = base / "delivery" / f"{digest(brief_id)}.json"
        if path.exists():
            return read(path)
        briefs = [read(p) for p in (base / "delivery").glob("*.json")]
        if any(b["status"] != "delivered" for b in briefs):
            raise ProtocolError("An earlier brief is reserved/uncertain; reconcile it before another")
        delivered = {r for b in briefs for r in b["receipt_ids"]}
        receipts = _saved_receipts(base)
        selected = [r for r in receipts if r["receipt_id"] not in delivered]
        brief = {"brief_id": brief_id, "status": "prepared", "prepared_at": now(), "receipt_ids": [r["receipt_id"] for r in selected], "receipts": selected, "tracking_summary": tracking_summary(selected, receipts)}
        atomic(path, brief)
        return brief


def mark_brief_sending(root, brief_id, delivery):
    """Persist intent BEFORE invoking an explicitly authorized sender."""
    with locked(root) as base:
        path = base / "delivery" / f"{digest(identifier(brief_id))}.json"
        brief = read(path)
        if brief["status"] != "prepared":
            raise ProtocolError("Brief already attempted; reconcile delivery before retry")
        channel = delivery.get("channel", "email")
        if channel not in {"email", "chat"}:
            raise ProtocolError("Delivery channel must be email or chat")
        text(delivery.get("snapshot_path"), "snapshot_path")
        addresses = []
        if channel == "email":
            for key in ("recipient", "subject"):
                text(delivery.get(key), key)
            addresses = [address for _, address in getaddresses([delivery["recipient"]])]
            if len(addresses) != 1 or "@" not in addresses[0] or "\n" in delivery["recipient"] or "\r" in delivery["recipient"]:
                raise ProtocolError("A single authorized recipient is required")
        else:
            identifier(delivery.get("thread_id"), "thread_id")
        snapshot_bytes = Path(delivery["snapshot_path"]).read_bytes()
        public_snapshot = json.loads(snapshot_bytes)
        snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()
        if delivery.get("snapshot_sha256", snapshot_hash) != snapshot_hash:
            raise ProtocolError("Public snapshot digest mismatch")
        bodies = {}
        body_fields = (("text/plain", "plain_body_path"), ("text/html", "html_body_path")) if channel == "email" else (("text/markdown", "chat_body_path"),)
        for mime, field in body_fields:
            if delivery.get(field):
                bodies[mime] = Path(delivery[field]).read_text().replace("\r\n", "\n")
        if not bodies:
            raise ProtocolError("Freeze at least one actual rendered body before sending")
        visible = html.unescape("\n".join(bodies.values()))
        for receipt in brief["receipts"]:
            for job in receipt.get("new_jobs", []):
                if any(job[field] not in visible for field in ("company", "title", "url")):
                    raise ProtocolError("Rendered brief omits a newly saved role or its exact URL")
        tracked = brief["tracking_summary"] if "tracking_summary" in brief else tracking_summary(brief["receipts"])
        if tracked:
            if not isinstance(public_snapshot, dict) or public_snapshot.get("tracking_updates") != tracked:
                raise ProtocolError("Public snapshot tracking_updates must match the frozen tracking_summary")
            for item in tracked:
                if any(item[field] not in visible for field in ("company", "title", "url", "change")):
                    raise ProtocolError("Rendered brief omits a saved tracking change or its role identity")
        frozen = dict(delivery, channel=channel, snapshot_sha256=snapshot_hash, bodies=bodies)
        if addresses:
            frozen["recipient"] = addresses[0]
        brief.update(status="sending", delivery_intent=frozen, attempted_at=now())
        atomic(path, brief)
        return brief


def confirm_brief_delivery(root, brief_id, delivery_evidence):
    with locked(root) as base:
        path = base / "delivery" / f"{digest(identifier(brief_id))}.json"
        brief = read(path)
        if brief["status"] == "delivered":
            return brief
        if brief["status"] != "sending":
            raise ProtocolError("Record send intent before delivery acknowledgement")
        verified_at = timestamp(delivery_evidence.get("verified_at"))
        intent = brief["delivery_intent"]
        attempted_seconds = int(timestamp(brief["attempted_at"]).timestamp())
        used = {b["delivery_evidence"]["message_id"] for p in (base / "delivery").glob("*.json") if (b := read(p)).get("status") == "delivered"}
        def fresh(seconds):
            number(seconds, "native delivery time", high=1e12)
            # Native Codex/Gmail timestamps can have second-level precision.
            if seconds < attempted_seconds or seconds > verified_at.timestamp() + 1:
                raise ProtocolError("Native delivery predates this attempt or is after its verification")
        if intent.get("channel") == "chat":
            native = _native_delivery(delivery_evidence.get("native_chat_readback"))
            if native.get("thread", {}).get("id") != intent["thread_id"]:
                raise ProtocolError("Native chat readback belongs to another chat")
            matches = []
            def scan(value):
                if isinstance(value, dict):
                    if value.get("type") == "agentMessage" and value.get("phase") in {"final_answer", "final"} and value.get("text", "").replace("\r\n", "\n") == intent["bodies"]["text/markdown"]:
                        if value.get("id"):
                            matches.append(value["id"])
                    for child in value.values():
                        scan(child)
                elif isinstance(value, list):
                    for child in value:
                        scan(child)
            for turn in native.get("turns", []):
                if turn.get("status") != "completed" or turn.get("error"):
                    continue
                completed_at = turn.get("completedAt")
                if not isinstance(completed_at, (int, float)) or completed_at < attempted_seconds:
                    continue
                fresh(completed_at)
                scan(turn.get("items"))
            if len(set(matches)) != 1:
                raise ProtocolError("Expected one exact completed assistant report in native chat readback")
            if matches[0] in used:
                raise ProtocolError("Native message already acknowledged another brief")
            verified = {"channel": "chat", "thread_id": intent["thread_id"], "message_id": matches[0], "native_readback_sha256": digest(native), "snapshot_sha256": intent["snapshot_sha256"], "verified_at": delivery_evidence["verified_at"]}
            brief.update(status="delivered", delivery_evidence=verified, delivered_at=now())
            atomic(path, brief)
            return brief
        native = _native_delivery(delivery_evidence.get("native_sent_readback"))
        if not isinstance(native, dict) or "SENT" not in native.get("label_ids", native.get("labelIds", [])) or not native.get("id"):
            raise ProtocolError("Native message is not a verified Sent message")
        internal_date = native.get("internal_date", native.get("internalDate"))
        if not isinstance(internal_date, (str, int)) or not re.fullmatch(r"\d+", str(internal_date)):
            raise ProtocolError("Native Gmail internal timestamp is required")
        fresh(int(internal_date) / 1000)
        if native["id"] in used:
            raise ProtocolError("Native message already acknowledged another brief")
        payload = native.get("payload", {})
        headers = {}
        for header in payload.get("headers", []):
            headers.setdefault(header["name"].lower(), []).append(str(make_header(decode_header(header["value"]))))
        recipients = [address.casefold() for _, address in getaddresses(headers.get("to", []))]
        if recipients != [intent["recipient"].casefold()] or headers.get("subject") != [intent["subject"]] or headers.get("cc") or headers.get("bcc"):
            raise ProtocolError("Native recipient/subject does not match the frozen delivery intent")
        bodies = {}
        def collect(part):
            mime = part.get("mime_type", part.get("mimeType"))
            body = part.get("body") or {}
            if mime in {"text/plain", "text/html"} and not part.get("filename"):
                content = body.get("content")
                if content is None:
                    encoded = body.get("base64_url_content", body.get("data"))
                    if encoded is not None:
                        content = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
                if isinstance(content, str):
                    if mime in bodies:
                        raise ProtocolError("Ambiguous duplicate report body")
                    bodies[mime] = content.replace("\r\n", "\n")
            for child in part.get("parts") or []:
                collect(child)
        collect(payload)
        if bodies != intent["bodies"]:
            raise ProtocolError("Actual Sent bodies differ from the frozen rendered report")
        verified = {"message_id": native["id"], "native_readback_sha256": digest(native), "snapshot_sha256": intent["snapshot_sha256"], "verified_at": delivery_evidence["verified_at"]}
        brief.update(status="delivered", delivery_evidence=verified, delivered_at=now())
        atomic(path, brief)
        return brief


def _native_delivery(value):
    native = read(value)
    for _ in range(5):
        if not isinstance(native, dict) or native.get("isError") or native.get("error"):
            raise ProtocolError("Retain an actual successful native delivery readback")
        if isinstance(native.get("structuredContent"), dict):
            native = native["structuredContent"]
        elif "content" in native and not any(k in native for k in ("id", "thread", "payload")):
            blocks = [b["text"] for b in native["content"] if b.get("type") == "text"]
            if len(blocks) != 1:
                raise ProtocolError("Expected one native JSON delivery response")
            native = json.loads(blocks[0])
        else:
            return native
    raise ProtocolError("Too many native response wrappers")
