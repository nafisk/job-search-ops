"""Pure accepted lifecycle and exact response projections; no account or file effects."""
from copy import deepcopy
from dataclasses import asdict, dataclass

from applications import MATCH_BASES, _past, _resolve, reconcile
from contracts import check, digest, keys, text, timestamp

STAGES = frozenset('ACTIVE INTERVIEWING REJECTED WITHDRAWN PAUSED OFFER HIRED REFERRED CLOSED'.split())
SUPPRESSED = frozenset('REJECTED WITHDRAWN PAUSED HIRED CLOSED'.split())
OWNERS = frozenset(('applicant', 'user', 'employer'))


@dataclass(frozen=True)
class EventAcceptance:
    """Construct only in trusted host code after full-source, exact-role review."""
    profile_id: str
    event_id: str
    source_event_id: str
    source_digest: str
    application_key: str
    kind: str
    effective_at: str | None
    reviewed_at: str
    evidence_ref: str
    match_basis: str
    full_source_read: bool
    data: dict


@dataclass(frozen=True)
class SentCoverage:
    """Host-verified complete relevant Sent retrieval, never a worker/source flag."""
    profile_id: str
    scope_digest: str
    request_keys: frozenset
    through: str
    checked_at: str
    evidence_ref: str
    complete: bool


def _validate(event, sources, profile, now):
    check(type(event) is EventAcceptance, 'event', 'trusted EventAcceptance required')
    for field in ('event_id', 'source_event_id', 'application_key', 'evidence_ref'):
        text(getattr(event, field), field)
    check(event.source_event_id in sources, 'event', 'unknown source event')
    source = sources[event.source_event_id]
    check((event.profile_id, event.source_digest) == (profile, digest(source)), 'event', 'profile/source content mismatch')
    text(event.kind, 'kind')
    text(event.match_basis, 'match_basis')
    check(event.match_basis in MATCH_BASES, 'match_basis', 'unsupported exact match basis')
    check(type(event.full_source_read) is bool and event.full_source_read, 'event', 'independent full-source read required')
    reviewed = _past(event.reviewed_at, now)
    check(reviewed is not None, 'reviewed_at', 'actual review time required')
    observed, effective = _past(source['observed_at'], now), _past(event.effective_at, now)
    check(observed is None or reviewed >= observed, 'reviewed_at', 'review precedes source capture')
    check(effective is None or effective <= reviewed, 'effective_at', 'event follows review')
    if event.kind in ('outcome', 'manual_status', 'reopen'):
        keys(event.data, 'stage', 'event.data')
        text(event.data['stage'], 'stage')
        allowed = STAGES | ({'APPLIED'} if event.kind == 'manual_status' else set())
        check(event.data['stage'] in allowed, 'stage', 'unsupported stage')
        if event.kind == 'manual_status':
            check(source['origin'] in ('sheet', 'manual_history'), 'manual_status', 'accepted current/manual source required')
        if event.kind == 'reopen':
            check(event.data['stage'] not in SUPPRESSED, 'reopen', 'active stage required')
            check(source['origin'] == 'manual_history', 'reopen', 'explicit scoped user instruction required')
    elif event.kind == 'request':
        keys(event.data, 'request_id response_owner deadline_at suggested_followup_at', 'event.data')
        text(event.data['request_id'], 'request_id')
        text(event.data['response_owner'], 'response_owner')
        check(event.data['response_owner'] in OWNERS, 'response_owner', 'expected applicant, user or employer')
        for field in ('deadline_at', 'suggested_followup_at'):
            if event.data[field] is not None:
                timestamp(event.data[field])  # Actual future deadlines/suggestions are permitted.
    elif event.kind == 'reply':
        keys(event.data, 'request_id', 'event.data')
        text(event.data['request_id'], 'request_id')
        check(source['origin'] == 'correspondence', 'reply', 'verified full Sent correspondence required')
    else:
        check(False, 'kind', 'unsupported event kind')
    digest(asdict(event))
    return source


def _matches(event, source, app, apps, profile):
    matches, reason = _resolve(source, apps, profile)
    basis = ((event.match_basis == 'exact_role' and source['role_id'] == app['role_id'])
             or (event.match_basis == 'exact_requisition' and source['requisition_id'] is not None
                 and source['requisition_id'] in app['requisition_ids'] and matches == [event.application_key] and reason is None)
             or (event.match_basis == 'exact_application_ref' and source['application_ref'] is not None
                 and source['application_ref'] in app['application_refs'] and matches == [event.application_key] and reason is None)
             or (event.match_basis == 'independent_exact_role' and source['role_id'] in (None, app['role_id'])))
    return (source['employer_id'] == app['employer_id'] and basis
            and (source['requisition_id'] is None or not app['requisition_ids']
                 or source['requisition_id'] in app['requisition_ids']))


def _stage(history, conflicts, gap):
    states = [e for e in history if e['kind'] in ('outcome', 'manual_status', 'reopen')]
    if not states:
        return None, None, 'conflicted' if conflicts else 'unknown', []
    reopen_times = [timestamp(e['effective_at']) for e in states
                    if e['kind'] == 'reopen' and e['effective_at'] is not None]
    if reopen_times:
        # An explicit scoped reopening resolves earlier *known* lifecycle state,
        # while preserving history and holding any state that cannot be ordered.
        states = [e for e in states if e['effective_at'] is None
                  or timestamp(e['effective_at']) >= max(reopen_times)]
    unknown = [e for e in states if e['effective_at'] is None]
    for event in unknown:
        gap(event, 'Actual lifecycle event time is unknown')
    manuals = {e['data']['stage'] for e in states if e['kind'] == 'manual_status'}
    outcomes = {e['data']['stage'] for e in states if e['kind'] == 'outcome'}
    if manuals and outcomes and len(manuals | outcomes) > 1:
        conflicts.append('Accepted current/manual state conflicts with source lifecycle state')
    by_time = {}
    for event in states:
        if event['effective_at'] is not None:
            by_time.setdefault(timestamp(event['effective_at']), []).append(event)
    stage, at, support = None, None, []
    for instant in sorted(by_time):
        group = by_time[instant]
        if len({e['data']['stage'] for e in group}) > 1:
            conflicts.append('Simultaneous incompatible lifecycle outcomes')
            continue
        next_stage = group[0]['data']['stage']
        reopened = any(e['kind'] == 'reopen' for e in group)
        if stage in SUPPRESSED and next_stage not in SUPPRESSED and not reopened:
            conflicts.append('Suppressed process requires explicit chronological reopening')
            continue
        stage, at, support = next_stage, group[0]['effective_at'], [e['event_id'] for e in group]
    if unknown:
        if len({e['data']['stage'] for e in states}) > 1:
            conflicts.append('Unknown lifecycle chronology prevents ordering')
        if stage is None and len({e['data']['stage'] for e in unknown}) == 1:
            stage = unknown[0]['data']['stage']
        at = None
    return stage, at, 'conflicted' if conflicts else ('unknown' if unknown else 'known'), support


def reconcile_lifecycle(payload, submission_acceptances=None, events=None, sent_coverage=None,
                        excluded_application_keys=None, *, sent_cutoff=None):
    """Layer exact accepted events over union; return detached proposals only."""
    base = reconcile(payload, submission_acceptances)
    profile, now = payload['profile_id'], timestamp(payload['as_of'])
    sent_cutoff = payload['as_of'] if sent_cutoff is None else sent_cutoff
    cutoff = timestamp(sent_cutoff)
    check(cutoff <= now, 'sent_cutoff', 'cannot follow evaluation time')
    apps = {a['application_key']: a for a in base['applications']}
    sources = {s['event_id']: s for s in base['source_events']}
    events = [] if events is None else events
    check(type(events) is list, 'events', 'expected trusted event list')
    excluded = frozenset() if excluded_application_keys is None else excluded_application_keys
    check(type(excluded) is frozenset, 'exclusions', 'expected frozen registered application keys')
    for key in excluded:
        text(key, 'exclusion key')
    check(excluded <= apps.keys(), 'exclusions', 'unknown registered application key')
    accepted, native, gaps = {}, {}, []

    def gap(event, reason):
        item = {'application_key': event['application_key'], 'event_id': event['event_id'], 'reason': reason}
        if item not in gaps:
            gaps.append(item)

    for event in events:
        source = _validate(event, sources, profile, now)
        record = asdict(event)
        check(event.event_id not in accepted or accepted[event.event_id] == record, 'event_id', 'immutable interpretation collision')
        native_key = digest([event.source_event_id, event.application_key, event.kind, event.effective_at, event.data])
        check(native_key not in native or native[native_key] == event.event_id, 'event_id', 'same native interpretation under another ID')
        native[native_key] = event.event_id
        accepted[event.event_id] = record
        app = apps.get(event.application_key)
        if app is None or not _matches(event, source, app, apps, profile):
            gap(record, 'Accepted target is unregistered or conflicts with exact source identity')
    valid = [accepted[k] for k in sorted(accepted)
             if not any(g['event_id'] == k for g in gaps)]
    request_keys = frozenset(digest([e['application_key'], e['data']['request_id']])
                             for e in valid if e['kind'] == 'request')
    covered = False
    if sent_coverage is not None:
        coverage = sent_coverage
        check(type(coverage) is SentCoverage, 'Sent', 'trusted SentCoverage required')
        check(type(coverage.request_keys) is frozenset and coverage.request_keys == request_keys,
              'Sent', 'exact complete declared request scope required')
        expected_scope = digest({'profile_id': profile, 'request_keys': sorted(request_keys)})
        check((coverage.profile_id, coverage.scope_digest) == (profile, expected_scope), 'Sent', 'profile/scope mismatch')
        text(coverage.evidence_ref, 'Sent evidence')
        check(type(coverage.complete) is bool, 'Sent complete', 'expected bool')
        through, checked = _past(coverage.through, now), _past(coverage.checked_at, now)
        check(through is not None and checked is not None and checked >= through, 'Sent', 'invalid coverage chronology')
        covered = coverage.complete and through == cutoff

    results, proposals = [], []
    for key, app in sorted(apps.items()):
        history = [e for e in valid if e['application_key'] == key]
        conflicts = list(app['conflicts'])
        stage, at, status, support = _stage(history, conflicts, gap)
        requests = {}
        for event in history:
            if event['kind'] == 'request':
                requests.setdefault(event['data']['request_id'], []).append(event)
            elif event['kind'] == 'reply' and not any(e['kind'] == 'request' and e['data']['request_id'] == event['data']['request_id'] for e in history):
                gap(event, 'No exact declared request for this reply')
        suppressed = stage in SUPPRESSED or key in excluded
        request_output = []
        for request_id, definitions in sorted(requests.items()):
            event = definitions[0]
            data = event['data']
            replies = [e for e in history if e['kind'] == 'reply' and e['data']['request_id'] == request_id]
            good = [e['event_id'] for e in replies if event['effective_at'] is not None and e['effective_at'] is not None
                    and timestamp(e['effective_at']) >= timestamp(event['effective_at'])]
            ambiguous = len({digest([e['effective_at'], e['data']]) for e in definitions}) > 1
            unknown = event['effective_at'] is None or any(e['effective_at'] is None for e in replies)
            for reply_event in replies:
                if reply_event['event_id'] not in good:
                    gap(reply_event, 'Reply/request chronology is unknown or reply precedes request')
            if suppressed:
                response = 'suppressed'
            elif conflicts or ambiguous or unknown or (status == 'unknown' and any(
                    e['kind'] in ('outcome', 'manual_status', 'reopen') for e in history)):
                response = 'held'
                gap(event, 'Request has conflicting state/definition or unknown chronology')
            elif good or data['response_owner'] == 'employer':
                response = 'waiting_on_employer'
            elif covered and timestamp(event['effective_at']) <= cutoff:
                response = 'reply_due'
            else:
                response = 'status_unchecked'
                gap(event, 'Complete relevant Sent coverage through request/evaluation cutoff is missing')
            deadline = data['deadline_at']
            request_output.append({'request_key': digest([key, request_id]), 'request_id': request_id,
                                   'event_id': event['event_id'], 'response_owner': data['response_owner'],
                                   'requested_at': event['effective_at'], 'deadline_at': deadline,
                                   'suggested_followup_at': data['suggested_followup_at'], 'status': response,
                                   'due_as_of': sent_cutoff if response == 'reply_due' else None,
                                   'reply_event_ids': sorted(good), 'deadline_state': 'unknown' if deadline is None
                                   else ('overdue' if timestamp(deadline) < now else 'upcoming')})
        conflicts = sorted(set(conflicts))
        results.append({'application_key': key, 'submission_confirmed': bool(app['submission_facts']),
                        'submission_facts': deepcopy(app['submission_facts']), 'current_stage': stage,
                        'effective_at': at, 'status': status, 'manual_status_events': [e for e in history if e['kind'] == 'manual_status'],
                        'history': history, 'requests': request_output, 'conflicts': conflicts})
        if status == 'known' and stage != 'APPLIED':
            proposals.append({'application_key': key, 'stage': stage, 'effective_at': at, 'event_ids': sorted(support)})
    return deepcopy({'reconciliation': base, 'applications': results, 'sent_cutoff': sent_cutoff,
                     'gaps': sorted(gaps, key=lambda g: (g['application_key'], g['event_id'], g['reason'])),
                     'lifecycle_proposals': proposals, 'operational_complete': False})
