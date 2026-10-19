"""Pure exact interview facts, preserving source and legacy history; no actions."""
from copy import deepcopy
from dataclasses import asdict, dataclass

from applications import MATCH_BASES, _past, reconcile
from contracts import check, digest, keys, text, texts, timestamp
from lifecycle import SUPPRESSED, _matches, _stage
from portals import json_data

EVIDENCE = frozenset(('employer_email', 'calendar', 'user_confirmation', 'user_voice_transcript', 'advice'))
USER = frozenset(('user_confirmation', 'user_voice_transcript'))
PROCESS_KINDS = frozenset(('outcome', 'user_process', 'reopen', 'outline', 'advice'))


@dataclass(frozen=True)
class InterviewAcceptance:
    """Trusted full-source/native-identity interpretation, never worker JSON."""
    profile_id: str
    event_id: str
    source_event_id: str
    source_digest: str
    application_key: str
    process_id: str
    stage_id: str | None
    kind: str
    effective_at: str | None
    reviewed_at: str
    evidence_ref: str
    match_basis: str
    full_source_read: bool
    evidence_kind: str
    data: dict


def process_key(application_key, process_id):
    text(application_key, 'application_key')
    text(process_id, 'process_id')
    return digest([application_key, process_id])


def stage_key(process_key, stage_id):
    text(process_key, 'process_key')
    text(stage_id, 'stage_id')
    return digest([process_key, stage_id])


def _validate(event, sources, profile, now):
    check(type(event) is InterviewAcceptance, 'event', 'trusted InterviewAcceptance required')
    for field in ('event_id', 'source_event_id', 'application_key', 'process_id', 'kind', 'match_basis', 'evidence_kind', 'evidence_ref'):
        text(getattr(event, field), field)
    check(event.source_event_id in sources, 'event', 'unknown source event')
    source = sources[event.source_event_id]
    check((event.profile_id, event.source_digest) == (profile, digest(source)), 'event', 'profile/source content mismatch')
    check(event.match_basis in MATCH_BASES and event.evidence_kind in EVIDENCE, 'event', 'unsupported evidence/match basis')
    check(type(event.full_source_read) is bool and event.full_source_read, 'event', 'full-source host review required')
    reviewed, effective = _past(event.reviewed_at, now), _past(event.effective_at, now)
    observed = _past(source['observed_at'], now)
    check(reviewed is not None and (observed is None or observed <= reviewed), 'reviewed_at', 'review precedes source capture')
    check(effective is None or effective <= reviewed, 'effective_at', 'event follows review')
    if event.stage_id is not None:
        text(event.stage_id, 'stage_id')
    check(event.stage_id is not None or event.kind in PROCESS_KINDS, 'stage_id', 'exact stage required')
    if event.evidence_kind in USER:
        check(source['origin'] == 'manual_history', 'user evidence', 'actual reviewed user history required')
    if event.evidence_kind in ('employer_email', 'calendar'):
        check(source['origin'] in ('correspondence', 'unresolved_association'), 'source', 'original external evidence required')
    if event.evidence_kind == 'advice':
        check(event.kind == 'advice', 'advice', 'cannot establish employer/user facts')
    if event.evidence_kind == 'calendar':
        check(event.kind in ('invitation', 'booking', 'rsvp', 'cancellation'), 'calendar', 'cannot prove attendance/outcome')
    if event.kind == 'invitation':
        keys(event.data, 'label', 'event.data')
        text(event.data['label'], 'label')
    elif event.kind == 'booking':
        keys(event.data, 'booking_id starts_at ends_at timezone', 'event.data')
        text(event.data['booking_id'], 'booking_id')
        text(event.data['timezone'], 'timezone')
        start, end = event.data['starts_at'], event.data['ends_at']
        if start is not None:
            timestamp(start)
        if end is not None:
            check(start is not None and timestamp(start) < timestamp(end), 'booking', 'end requires earlier start')
    elif event.kind in ('rsvp', 'cancellation'):
        keys(event.data, 'booking_id response' if event.kind == 'rsvp' else 'booking_id', 'event.data')
        text(event.data['booking_id'], 'booking_id')
        if event.kind == 'rsvp':
            text(event.data['response'], 'response')
            check(event.data['response'] in ('accepted', 'tentative', 'declined', 'needs_action'), 'response', 'unsupported RSVP')
    elif event.kind == 'attendance':
        keys(event.data, 'attended', 'event.data')
        check(type(event.data['attended']) is bool, 'attended', 'explicit attendance bool required')
    elif event.kind == 'outcome':
        keys(event.data, 'status', 'event.data')
        text(event.data['status'], 'status')
        check(event.data['status'] in ('ACTIVE', 'REJECTED', 'PAUSED', 'WITHDRAWN', 'OFFER', 'HIRED', 'CLOSED'), 'status', 'unsupported process outcome')
    elif event.kind in ('user_process', 'reopen'):
        keys(event.data, '', 'event.data')
        check(event.evidence_kind in USER, 'user process', 'explicit exact user confirmation required')
    elif event.kind in ('availability_sent', 'registration', 'reschedule'):
        keys(event.data, 'request_id', 'event.data')
        text(event.data['request_id'], 'request_id')
    elif event.kind == 'outline':
        keys(event.data, 'stages total_stages', 'event.data')
        texts(event.data['stages'], 'outline stages')
        total = event.data['total_stages']
        check(total is None or (type(total) is int and total > 0 and total >= len(event.data['stages'])), 'total_stages', 'explicit valid denominator required')
    elif event.kind == 'advice':
        keys(event.data, 'note', 'event.data')
        text(event.data['note'], 'note')
        check(event.evidence_kind == 'advice', 'advice', 'preserve advice separately')
    else:
        check(False, 'kind', 'unsupported interview fact')
    digest(asdict(event))
    return source


def _stage_facts(key, sid, history, gap):
    conflicts = []

    def latest(kind, eligible=None):
        facts = [e for e in history if e['kind'] == kind and (eligible is None or eligible(e))]
        if not facts:
            return None
        if any(e['effective_at'] is None for e in facts):
            conflicts.append('Unknown chronology for ' + kind)
            return None
        last = max(timestamp(e['effective_at']) for e in facts)
        tied = [e for e in facts if timestamp(e['effective_at']) == last]
        if len({digest(e['data']) for e in tied}) > 1:
            conflicts.append('Simultaneous incompatible ' + kind + ' facts')
            for event in tied:
                gap(event, conflicts[-1])
            return None
        return tied[0]

    invitation, booked, attendance = latest('invitation'), latest('booking'), latest('attendance')
    availability = latest('availability_sent')
    bid = booked['data']['booking_id'] if booked else None
    rsvp = latest('rsvp', lambda e: e['data']['booking_id'] == bid)
    canceled = latest('cancellation', lambda e: e['data']['booking_id'] == bid)
    reschedule = latest('reschedule')
    if attendance and booked and timestamp(attendance['effective_at']) < timestamp(booked['effective_at']):
        attendance = None  # Historical attendance cannot complete a replacement booking.
    if (attendance and booked and booked['data']['starts_at'] is not None
            and timestamp(attendance['effective_at']) < timestamp(booked['data']['starts_at'])):
        gap(attendance, 'Attendance precedes the current scheduled start; retained as history')
        attendance = None
    if booked and canceled and timestamp(canceled['effective_at']) < timestamp(booked['effective_at']):
        gap(canceled, 'Cancellation precedes the matching booking confirmation')
        canceled = None
    known_bookings = {e['data']['booking_id'] for e in history if e['kind'] == 'booking'}
    for event in history:
        if event['kind'] in ('rsvp', 'cancellation') and event['data']['booking_id'] not in known_bookings:
            gap(event, 'Booking-specific fact has no known booking in the exact stage')
    if booked and booked['data']['starts_at'] is None:
        gap(booked, 'Actual booking start is unknown')
        conflicts.append('Booking time is unknown')
    state = 'not_invited'
    if invitation:
        state = 'pending_schedule'
    if availability and (not invitation or timestamp(availability['effective_at']) >= timestamp(invitation['effective_at'])):
        state = 'availability_sent'
    if booked:
        state = 'invite_accepted' if rsvp and rsvp['data']['response'] == 'accepted' else 'booked'
    if canceled:
        state = 'canceled'
    if reschedule and (not booked or timestamp(reschedule['effective_at']) > timestamp(booked['effective_at'])):
        state = 'reschedule_requested'
        if (availability and availability['data']['request_id'] == reschedule['data']['request_id']
                and timestamp(availability['effective_at']) >= timestamp(reschedule['effective_at'])):
            state = 'availability_sent'
    if attendance:
        state = 'completed' if attendance['data']['attended'] else 'not_attended'
    if conflicts or any(e['effective_at'] is None for e in history if e['kind'] not in PROCESS_KINDS):
        state = 'unknown'
    booking = None if booked is None else {'event_id': booked['event_id'], **booked['data']}
    return {'stage_key': stage_key(key, sid), 'stage_id': sid, 'label': invitation['data']['label'] if invitation else None,
            'invited': any(e['kind'] == 'invitation' for e in history), 'booking': booking,
            'rsvp': rsvp['data']['response'] if rsvp else None,
            'attendance': attendance['data']['attended'] if attendance else None, 'canceled': canceled is not None,
            'availability_sent': sorted({e['data']['request_id'] for e in history if e['kind'] == 'availability_sent'}),
            'registrations': sorted({e['data']['request_id'] for e in history if e['kind'] == 'registration'}),
            'reschedule_requested': reschedule is not None, 'status': state, 'history': history,
            'conflicts': sorted(set(conflicts)), 'action_required': None}


def reconcile_interviews(payload, events=None, legacy_records=None, *, submission_acceptances=None,
                         excluded_process_keys=None, excluded_application_keys=None, profile=None,
                         source_scopes=None, source_checks=None, cutoff=None):
    """Normalize reviewed facts only; never infer promotion from raw legacy state."""
    base = reconcile(payload, submission_acceptances)
    profile_id, now = payload['profile_id'], timestamp(payload['as_of'])
    cutoff = payload['as_of'] if cutoff is None else cutoff
    check(timestamp(cutoff) <= now, 'cutoff', 'cannot follow evaluation time')
    apps = {a['application_key']: a for a in base['applications']}
    sources = {s['event_id']: s for s in base['source_events']}
    legacy = [] if legacy_records is None else legacy_records
    check(type(legacy) is list and all(type(r) is dict for r in legacy), 'legacy_records', 'expected original JSON records')
    digest(legacy)
    json_data(legacy)
    exclusions = []
    for supplied in (excluded_process_keys, excluded_application_keys):
        supplied = frozenset() if supplied is None else supplied
        check(type(supplied) is frozenset, 'exclusions', 'expected frozen exact identities')
        for item in supplied:
            text(item, 'exclusion')
        exclusions.append(supplied)
    events = [] if events is None else events
    check(type(events) is list, 'events', 'expected trusted receipt list')
    accepted, native, groups, unresolved, gaps = {}, {}, {}, [], []

    def gap(event, reason):
        item = {'process_key': process_key(event['application_key'], event['process_id']), 'event_id': event['event_id'], 'reason': reason}
        if item not in gaps:
            gaps.append(item)

    for event in events:
        source = _validate(event, sources, profile_id, now)
        record = asdict(event)
        check(event.event_id not in accepted or accepted[event.event_id] == record, 'event_id', 'immutable interpretation collision')
        operation = digest([event.source_event_id, event.application_key, event.process_id, event.stage_id, event.kind, event.effective_at, event.data])
        check(operation not in native or native[operation] == event.event_id, 'event_id', 'same native interpretation under another ID')
        native[operation], accepted[event.event_id] = event.event_id, record
        app = apps.get(event.application_key)
        if app is None or not _matches(event, source, app, apps, profile_id) or app['conflicts']:
            gap(record, 'Unregistered/conflicting exact application identity')
            continue
        if event.effective_at is None:
            gap(record, 'Actual interview fact time is unknown')
    for eid in sorted(accepted):
        record = accepted[eid]
        if any(g['event_id'] == eid and g['reason'] == 'Unregistered/conflicting exact application identity' for g in gaps):
            unresolved.append(record)
        else:
            groups.setdefault(process_key(record['application_key'], record['process_id']), []).append(record)
    processes, proposals = [], []
    for key, history in sorted(groups.items()):
        establishment = [e for e in history if e['kind'] in ('invitation', 'booking', 'user_process')
                         or (e['kind'] == 'attendance' and e['data']['attended'])]
        if not establishment:
            for event in history:
                gap(event, 'No actual interview-process establishment evidence')
            unresolved.extend(history)
            continue
        first = history[0]
        state_events = [{**e, 'kind': 'reopen' if e['kind'] == 'reopen' else 'outcome',
                         'data': {'stage': e['data']['status'] if e['kind'] == 'outcome' else 'ACTIVE'}}
                        for e in history if e['kind'] in ('outcome', 'user_process', 'reopen')]
        conflicts = []
        status, at, confidence, _ = _stage(state_events, conflicts, gap)
        if status is None and not state_events:
            status = 'ACTIVE'
            confidence = 'unknown' if any(e['effective_at'] is None for e in history
                                           if e['kind'] not in ('outline', 'advice')) else 'known'
            if all(e['effective_at'] is not None for e in establishment):
                at = max(establishment, key=lambda e: timestamp(e['effective_at']))['effective_at']
        stages = [_stage_facts(key, sid, [e for e in history if e['stage_id'] == sid], gap)
                  for sid in sorted({e['stage_id'] for e in history if e['stage_id'] is not None})]
        if any(s['status'] == 'unknown' for s in stages):
            confidence = 'unknown' if not conflicts else 'conflicted'
        outlines = [e for e in history if e['kind'] == 'outline']
        totals = {e['data']['total_stages'] for e in outlines if e['data']['total_stages'] is not None}
        if len(totals) > 1:
            conflicts.append('Conflicting explicitly documented stage totals')
            confidence = 'conflicted'
            gap(outlines[0], conflicts[-1])
        excluded = key in exclusions[0] or first['application_key'] in exclusions[1]
        process = {'process_key': key, 'application_key': first['application_key'], 'process_id': first['process_id'],
                   'process_status': status, 'effective_at': at, 'status': confidence,
                   'status_basis': 'last_known_evidence', 'stages': stages,
                   'outlines': outlines, 'total_stages': next(iter(totals)) if len(totals) == 1 else None,
                   'history': history, 'excluded': excluded, 'suppressed': excluded or status in SUPPRESSED,
                   'conflicts': sorted(set(conflicts)), 'action_required': None}
        processes.append(process)
        if confidence == 'known' and not excluded:
            proposals.append({'process_key': key, 'application_key': first['application_key'], 'process_id': first['process_id'],
                              'process_status': status, 'stages': deepcopy(stages), 'excluded': excluded,
                              'effective_at': at, 'status_basis': 'last_known_evidence',
                              'suppressed': process['suppressed'], 'action_required': None,
                              'event_ids': [e['event_id'] for e in history]})
    coverage = None
    if profile is not None or source_scopes is not None or source_checks is not None:
        check(type(profile) is dict and profile.get('profile_id') == profile_id, 'profile', 'full matching coverage profile required')
        from coverage import coverage_status
        coverage = coverage_status(profile, {} if source_scopes is None else source_scopes,
                                   {} if source_checks is None else source_checks, cutoff=cutoff, as_of=payload['as_of'])
        for source_gap in coverage['gaps']:
            gaps.append({'process_key': None, 'event_id': None, 'reason': 'Source coverage gap', 'source_gap': deepcopy(source_gap)})
    else:
        gaps.append({'process_key': None, 'event_id': None, 'reason': 'Required source coverage was not supplied'})
    return deepcopy({'reconciliation': base, 'legacy_records': legacy, 'processes': processes,
                     'unresolved_events': sorted(unresolved, key=lambda e: e['event_id']),
                     'gaps': sorted(gaps, key=lambda g: (g['process_key'] or '', g['event_id'] or '', g['reason'], digest(g))),
                     'coverage': coverage,
                     'interview_proposals': proposals, 'operational_complete': False, 'delivered_baseline_changed': False})
