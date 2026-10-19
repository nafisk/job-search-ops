"""Independent source-bound lifecycle and exact response tests."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from applications import SubmissionAcceptance
from contracts import ContractError
from lifecycle import EventAcceptance, SentCoverage, reconcile_lifecycle

PROFILE = 'fictional-lifecycle'
NOW = '2026-10-06T14:00:00Z'
SEEN = '2026-10-06T12:00:00Z'
REVIEWED = '2026-10-06T13:00:00Z'
OLD = '2026-10-01T10:00:00Z'
REQUESTED = '2026-10-02T10:00:00Z'
REPLIED = '2026-10-03T10:00:00Z'
OUTCOME = '2026-10-04T10:00:00Z'


def fp(value):
    # Independent contract digests and expectations, not implementation-produced truth.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def app_key(role='ats:1', employer='example-co', profile=PROFILE):
    return fp([profile, employer, role])


def source(event_id, origin='correspondence', role='ats:1', employer='example-co', payload=None):
    return {'event_id': event_id, 'origin': origin, 'source_item_id': 'message:' + event_id,
            'observed_at': SEEN, 'employer_id': employer, 'role_id': role,
            'requisition_id': 'REQ-' + role.split(':')[-1] if role else None,
            'application_ref': None, 'evidence_refs': ['fictional:' + event_id],
            'payload': deepcopy(payload) if payload is not None else {'full_body': 'complete fictional message'}}


def packet(*messages, two_roles=False, profile=PROFILE):
    baseline = source('registered-1', 'sheet', payload={'manual_status': 'Applied', 'note': 'keep', 'raw_date': '2026-09-20'})
    sources = [baseline, *messages]
    if two_roles:
        sources.append(source('registered-2', 'manual_history', role='ats:2', payload={'old_status': 'Rejected', 'notes': 'history'}))
    return {'schema_version': 1, 'profile_id': profile, 'as_of': NOW, 'sources': sources}


def event(message, kind='outcome', at=OUTCOME, stage='REJECTED', data=None, role='ats:1', employer='example-co', event_id=None):
    if data is None:
        data = {'stage': stage}
    return EventAcceptance(PROFILE, event_id or ('accepted:' + message['event_id']), message['event_id'], fp(message),
                           app_key(role, employer), kind, at, REVIEWED, 'fictional-full-source-exact-proof',
                           'exact_role', True, deepcopy(data))


def request(message, request_id='request:1', at=REQUESTED, owner='applicant', deadline=None, followup=None, role='ats:1'):
    return event(message, 'request', at, data={'request_id': request_id, 'response_owner': owner,
                    'deadline_at': deadline, 'suggested_followup_at': followup}, role=role)


def reply(message, request_id='request:1', at=REPLIED, role='ats:1'):
    return event(message, 'reply', at, data={'request_id': request_id}, role=role)


def coverage(*bindings, through=NOW, complete=True, profile=PROFILE):
    keys = frozenset(fp([app_key(role), req]) for role, req in bindings)
    scope = fp({'profile_id': profile, 'request_keys': sorted(keys)})
    return SentCoverage(profile, scope, keys, through, NOW, 'fictional-all-relevant-Sent-pages', complete)


def current(result, key=None):
    key = app_key() if key is None else key
    return next(a for a in result['applications'] if a['application_key'] == key)


def request_state(result, key=None):
    return current(result, key)['requests'][0]


class LifecycleTests(unittest.TestCase):
    def test_submission_fact_separate_from_newer_rejection(self):
        receipt = source('old-receipt')
        rejection = source('new-rejection')
        accepted = SubmissionAcceptance(PROFILE, receipt['event_id'], fp(receipt), app_key(), 'exact_role',
                       'email_receipt', OLD, REVIEWED, 'fictional-submission-proof', True)
        result = reconcile_lifecycle(packet(receipt, rejection), {receipt['event_id']: accepted}, [event(rejection)])
        a = current(result)
        self.assertTrue(a['submission_confirmed'])
        self.assertEqual(a['current_stage'], 'REJECTED')
        self.assertEqual(a['effective_at'], OUTCOME)
        self.assertEqual(len(a['submission_facts']), 1)
        self.assertTrue(all(p['stage'] != 'APPLIED' for p in result['lifecycle_proposals']))

    def test_submission_fact_does_not_overwrite_interview_or_withdrawal(self):
        for stage in ['INTERVIEWING', 'WITHDRAWN']:
            with self.subTest(stage=stage):
                receipt, outcome = source('old-receipt'), source('outcome')
                accepted = SubmissionAcceptance(PROFILE, receipt['event_id'], fp(receipt), app_key(), 'exact_role',
                               'email_receipt', OLD, REVIEWED, 'fictional-proof', True)
                a = current(reconcile_lifecycle(packet(receipt, outcome), {'old-receipt': accepted}, [event(outcome, stage=stage)]))
                self.assertTrue(a['submission_confirmed'])
                self.assertEqual(a['current_stage'], stage)

    def test_no_events_or_silence_never_invents_rejection(self):
        result = reconcile_lifecycle(packet())
        a = current(result)
        self.assertFalse(a['submission_confirmed'])
        self.assertNotEqual(a['current_stage'], 'REJECTED')
        self.assertEqual(result['lifecycle_proposals'], [])

    def test_unknown_outcome_time_no_capture_fallback(self):
        message = source('unknown-time')
        result = reconcile_lifecycle(packet(message), events=[event(message, at=None)])
        a = current(result)
        self.assertIsNone(a['effective_at'])
        self.assertNotEqual(a['status'], 'known')
        self.assertEqual(result['lifecycle_proposals'], [])
        self.assertTrue(result['gaps'])

    def test_same_time_contradictory_outcomes_surface_and_hold(self):
        a, b = source('rejected'), source('interviewing')
        result = reconcile_lifecycle(packet(a, b), events=[event(a), event(b, stage='INTERVIEWING')])
        self.assertEqual(current(result)['status'], 'conflicted')
        self.assertTrue(current(result)['conflicts'])
        self.assertEqual(result['lifecycle_proposals'], [])

    def test_manual_status_conflict_is_retained_not_silently_downgraded(self):
        manual = source('manual', 'manual_history', payload={'status': 'Interviewing', 'note': 'user edited'})
        rejection = source('rejection')
        result = reconcile_lifecycle(packet(manual, rejection), events=[event(manual, 'manual_status', OUTCOME, 'INTERVIEWING'), event(rejection)])
        a = current(result)
        self.assertEqual(a['status'], 'conflicted')
        self.assertTrue(a['manual_status_events'])
        self.assertEqual(result['lifecycle_proposals'], [])
        self.assertIn(manual, result['reconciliation']['source_events'])

    def test_unknown_manual_chronology_remains_gap(self):
        manual, outcome = source('manual', 'manual_history'), source('outcome')
        result = reconcile_lifecycle(packet(manual, outcome), events=[event(manual, 'manual_status', None, 'INTERVIEWING'), event(outcome)])
        self.assertNotEqual(current(result)['status'], 'known')
        self.assertTrue(result['gaps'])
        self.assertEqual(result['lifecycle_proposals'], [])

    def test_manual_applied_label_is_not_submission_confirmation(self):
        manual = source('manual-applied', 'manual_history')
        result = reconcile_lifecycle(packet(manual), events=[event(manual, 'manual_status', OLD, 'APPLIED')])
        self.assertFalse(current(result)['submission_confirmed'])
        self.assertEqual(current(result)['submission_facts'], [])

    def test_full_sent_coverage_required_before_reply_due(self):
        message = source('request')
        result = reconcile_lifecycle(packet(message), events=[request(message)])
        self.assertEqual(request_state(result)['status'], 'status_unchecked')
        self.assertTrue(result['gaps'])
        checked = reconcile_lifecycle(packet(message), events=[request(message)], sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(request_state(checked)['status'], 'reply_due')

    def test_incomplete_sent_coverage_never_reply_due(self):
        message = source('request')
        result = reconcile_lifecycle(packet(message), events=[request(message)], sent_coverage=coverage(('ats:1', 'request:1'), complete=False))
        self.assertEqual(request_state(result)['status'], 'status_unchecked')
        self.assertTrue(result['gaps'])

    def test_request_owner_deadline_and_suggested_followup_are_separate(self):
        message = source('request')
        followup = '2026-10-08T10:00:00Z'
        result = reconcile_lifecycle(packet(message), events=[request(message, followup=followup)], sent_coverage=coverage(('ats:1', 'request:1')))
        state = request_state(result)
        self.assertEqual(state['response_owner'], 'applicant')
        self.assertIsNone(state['deadline_at'])
        self.assertEqual(state['suggested_followup_at'], followup)
        self.assertEqual(state['deadline_state'], 'unknown')

    def test_employer_owned_request_never_claims_user_reply_due(self):
        incoming = source('request')
        for sent in [None, coverage(('ats:1', 'request:1'))]:
            with self.subTest(sent=sent):
                result = reconcile_lifecycle(packet(incoming), events=[request(incoming, owner='employer')], sent_coverage=sent)
                self.assertNotEqual(request_state(result)['status'], 'reply_due')
                self.assertEqual(request_state(result)['response_owner'], 'employer')

    def test_real_deadline_overdue_is_not_followup(self):
        message = source('request')
        deadline = '2026-10-05T10:00:00Z'
        state = request_state(reconcile_lifecycle(packet(message), events=[request(message, deadline=deadline)],
                         sent_coverage=coverage(('ats:1', 'request:1'))))
        self.assertEqual(state['deadline_at'], deadline)
        self.assertIsNone(state['suggested_followup_at'])
        self.assertEqual(state['deadline_state'], 'overdue')

    def test_exact_later_reply_resolves_one_request(self):
        incoming, sent = source('request'), source('sent', payload={'mailbox': 'SENT', 'body': 'complete response'})
        result = reconcile_lifecycle(packet(incoming, sent), events=[request(incoming), reply(sent)], sent_coverage=coverage(('ats:1', 'request:1')))
        state = request_state(result)
        self.assertEqual(state['status'], 'waiting_on_employer')
        self.assertEqual(state['reply_event_ids'], ['accepted:sent'])

    def test_positive_exact_reply_does_not_need_negative_sent_coverage(self):
        incoming, sent = source('request'), source('sent')
        result = reconcile_lifecycle(packet(incoming, sent), events=[request(incoming), reply(sent)])
        self.assertEqual(request_state(result)['status'], 'waiting_on_employer')
        self.assertNotEqual(request_state(result)['status'], 'reply_due')

    def test_future_employer_deadline_and_suggested_followup_are_allowed(self):
        incoming = source('request')
        deadline, followup = '2026-10-07T10:00:00Z', '2026-10-08T10:00:00Z'
        result = reconcile_lifecycle(packet(incoming), events=[request(incoming, deadline=deadline, followup=followup)],
                                   sent_coverage=coverage(('ats:1', 'request:1')))
        state = request_state(result)
        self.assertEqual(state['deadline_at'], deadline)
        self.assertEqual(state['suggested_followup_at'], followup)
        self.assertEqual(state['deadline_state'], 'upcoming')

    def test_unrelated_same_company_sent_cannot_resolve_request(self):
        incoming, unrelated = source('request'), source('sent-other', role='ats:2')
        result = reconcile_lifecycle(packet(incoming, unrelated, two_roles=True), events=[request(incoming), reply(unrelated, role='ats:2')],
                                   sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(request_state(result)['status'], 'reply_due')
        self.assertEqual(request_state(result)['reply_event_ids'], [])

    def test_other_request_reply_does_not_resolve_requested_action(self):
        incoming, sent = source('request'), source('sent')
        result = reconcile_lifecycle(packet(incoming, sent), events=[request(incoming), reply(sent, request_id='request:other')],
                                   sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(request_state(result)['status'], 'reply_due')

    def test_two_obligations_in_one_message_remain_independent(self):
        incoming, sent = source('two-obligations'), source('registration-reply')
        registration = replace(request(incoming, request_id='registration:1'), event_id='accepted:registration')
        booking = replace(request(incoming, request_id='booking:1'), event_id='accepted:booking')
        result = reconcile_lifecycle(packet(incoming, sent), events=[registration, booking, reply(sent, request_id='registration:1')],
                    sent_coverage=coverage(('ats:1', 'registration:1'), ('ats:1', 'booking:1')))
        states = {r['request_id']: r for r in current(result)['requests']}
        self.assertEqual(len(states), 2)
        self.assertEqual(states['registration:1']['status'], 'waiting_on_employer')
        self.assertEqual(states['booking:1']['status'], 'reply_due')
        self.assertEqual(states['booking:1']['reply_event_ids'], [])

    def test_duplicate_native_obligation_under_new_event_id_rejected(self):
        incoming = source('request')
        accepted = request(incoming)
        duplicate = replace(accepted, event_id='different-interpretation-id')
        with self.assertRaises(ContractError):
            reconcile_lifecycle(packet(incoming), events=[accepted, duplicate])

    def test_prior_reply_does_not_resolve_new_request(self):
        incoming, sent = source('request'), source('sent')
        result = reconcile_lifecycle(packet(incoming, sent), events=[request(incoming), reply(sent, at=OLD)],
                                   sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertNotEqual(request_state(result)['status'], 'waiting_on_employer')
        self.assertEqual(request_state(result)['reply_event_ids'], [])

    def test_unknown_reply_or_request_chronology_holds(self):
        incoming, sent = source('request'), source('sent')
        for request_at, reply_at in [(None, REPLIED), (REQUESTED, None)]:
            with self.subTest(request_at=request_at, reply_at=reply_at):
                result = reconcile_lifecycle(packet(incoming, sent), events=[request(incoming, at=request_at), reply(sent, at=reply_at)],
                                           sent_coverage=coverage(('ats:1', 'request:1')))
                self.assertNotEqual(request_state(result)['status'], 'waiting_on_employer')
                self.assertNotEqual(request_state(result)['status'], 'reply_due')
                self.assertTrue(result['gaps'])

    def test_terminal_status_and_exclusion_suppress_request_without_reopen(self):
        incoming, terminal = source('request'), source('terminal')
        for stage in ['REJECTED', 'WITHDRAWN', 'PAUSED', 'HIRED', 'CLOSED']:
            with self.subTest(stage=stage):
                result = reconcile_lifecycle(packet(incoming, terminal), events=[event(terminal, at=OLD, stage=stage), request(incoming)],
                                           sent_coverage=coverage(('ats:1', 'request:1')))
                self.assertEqual(request_state(result)['status'], 'suppressed')
        result = reconcile_lifecycle(packet(incoming), events=[request(incoming)], sent_coverage=coverage(('ats:1', 'request:1')),
                                     excluded_application_keys=frozenset([app_key()]))
        self.assertEqual(request_state(result)['status'], 'suppressed')

    def test_generic_request_does_not_reopen_terminal_application(self):
        terminal, incoming = source('terminal'), source('request')
        result = reconcile_lifecycle(packet(terminal, incoming), events=[event(terminal, at=OLD), request(incoming)],
                                   sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(current(result)['current_stage'], 'REJECTED')
        self.assertEqual(request_state(result)['status'], 'suppressed')

    def test_explicit_reopen_after_terminal_restores_active_request(self):
        terminal, reopened, incoming = source('terminal'), source('reopen', 'manual_history'), source('request')
        result = reconcile_lifecycle(packet(terminal, reopened, incoming), events=[event(terminal, at=OLD),
                   event(reopened, 'reopen', '2026-10-02T09:00:00Z', 'ACTIVE'), request(incoming)],
                   sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(current(result)['current_stage'], 'ACTIVE')
        self.assertEqual(request_state(result)['status'], 'reply_due')

    def test_employer_reopen_cannot_clear_user_exclusion(self):
        reopened, incoming = source('reopen'), source('request')
        with self.assertRaises(ContractError):
            reconcile_lifecycle(packet(reopened, incoming), events=[event(reopened, 'reopen', OLD, 'ACTIVE'), request(incoming)],
                    sent_coverage=coverage(('ats:1', 'request:1')), excluded_application_keys=frozenset([app_key()]))

    def test_employer_correspondence_cannot_reopen_user_terminal_gate(self):
        terminal, reopened, incoming = source('terminal'), source('employer-reopen'), source('request')
        with self.assertRaises(ContractError):
            reconcile_lifecycle(packet(terminal, reopened, incoming),
                events=[event(terminal, at=OLD, stage='PAUSED'), event(reopened, 'reopen', REPLIED, 'ACTIVE'), request(incoming, at=OUTCOME)],
                sent_coverage=coverage(('ats:1', 'request:1')))

    def test_offer_alone_does_not_reopen_terminal_process(self):
        terminal, offer, incoming = source('terminal'), source('offer'), source('request')
        result = reconcile_lifecycle(packet(terminal, offer, incoming),
                events=[event(terminal, at=OLD), event(offer, at=REPLIED, stage='OFFER'), request(incoming, at=OUTCOME)],
                sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(current(result)['current_stage'], 'REJECTED')
        self.assertEqual(request_state(result)['status'], 'suppressed')
        self.assertEqual(result['lifecycle_proposals'], [])

    def test_conflicting_definitions_of_same_request_stay_held(self):
        a, b = source('request-a'), source('request-b')
        result = reconcile_lifecycle(packet(a, b), events=[request(a), request(b, owner='employer')],
                                     sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(request_state(result)['status'], 'held')
        self.assertTrue(result['gaps'])

    def test_old_manual_reopen_cannot_clear_current_user_exclusion(self):
        reopened = source('user-reopen', 'manual_history', payload={'user_instruction': 'reopen exact role'})
        incoming = source('request')
        result = reconcile_lifecycle(packet(reopened, incoming), events=[event(reopened, 'reopen', OLD, 'ACTIVE'), request(incoming)],
                    sent_coverage=coverage(('ats:1', 'request:1')), excluded_application_keys=frozenset([app_key()]))
        self.assertEqual(request_state(result)['status'], 'suppressed')
        self.assertEqual(len(current(result)['history']), 2)

    def test_explicit_later_reopen_resolves_known_historical_manual_conflict(self):
        manual = source('old-manual', 'manual_history')
        outcome, reopened, incoming = source('old-outcome'), source('reopen', 'manual_history'), source('request')
        events = [event(manual, 'manual_status', OLD, 'REJECTED'),
                  event(outcome, at=REQUESTED, stage='INTERVIEWING'),
                  event(reopened, 'reopen', REPLIED, 'ACTIVE'), request(incoming, at=OUTCOME)]
        result = reconcile_lifecycle(packet(manual, outcome, reopened, incoming), events=events,
                                     sent_coverage=coverage(('ats:1', 'request:1')))
        a = current(result)
        self.assertEqual(a['status'], 'known')
        self.assertEqual(a['current_stage'], 'ACTIVE')
        self.assertEqual(a['effective_at'], REPLIED)
        self.assertEqual(len(a['history']), 4)
        self.assertEqual(len(a['manual_status_events']), 1)
        self.assertEqual(request_state(result)['status'], 'reply_due')

    def test_reopen_cannot_order_prior_unknown_manual_time(self):
        manual, reopened, incoming = source('old-manual', 'manual_history'), source('reopen', 'manual_history'), source('request')
        result = reconcile_lifecycle(packet(manual, reopened, incoming),
                    events=[event(manual, 'manual_status', None, 'REJECTED'), event(reopened, 'reopen', REPLIED, 'ACTIVE'), request(incoming, at=OUTCOME)],
                    sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertNotEqual(current(result)['status'], 'known')
        self.assertNotEqual(request_state(result)['status'], 'reply_due')
        self.assertEqual(result['lifecycle_proposals'], [])
        self.assertTrue(result['gaps'])

    def test_unknown_source_or_application_cannot_gain_lifecycle(self):
        message = source('unregistered', role='ats:99')
        result = reconcile_lifecycle(packet(message), events=[event(message, role='ats:99')])
        self.assertEqual(len(result['applications']), 1)
        self.assertEqual(result['lifecycle_proposals'], [])
        self.assertTrue(result['gaps'])
        missing = replace(event(message), source_event_id='missing-source')
        with self.assertRaises(ContractError):
            reconcile_lifecycle(packet(message), events=[missing])

    def test_source_binding_profile_guard_and_untrusted_events(self):
        message = source('outcome')
        accepted = event(message)
        for bad in [replace(accepted, profile_id='other'), replace(accepted, source_digest='wrong'),
                    replace(accepted, full_source_read=False), accepted.__dict__]:
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                reconcile_lifecycle(packet(message), events=[bad])
        other_target = replace(accepted, application_key=app_key('ats:2'))
        result = reconcile_lifecycle(packet(message, two_roles=True), events=[other_target])
        self.assertTrue(result['gaps'])
        self.assertEqual(result['lifecycle_proposals'], [])

    def test_duplicate_event_replay_and_order_are_deterministic(self):
        outcome, incoming, sent = source('outcome'), source('request'), source('sent')
        events = [event(outcome, at=OLD, stage='ACTIVE'), request(incoming), reply(sent)]
        payload = packet(outcome, incoming, sent)
        result = reconcile_lifecycle(payload, events=events, sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(result, reconcile_lifecycle(payload, events=[events[2], events[0], events[1], events[0]],
                                                    sent_coverage=coverage(('ats:1', 'request:1'))))
        altered = replace(events[0], data={'stage': 'REJECTED'})
        with self.assertRaises(ContractError):
            reconcile_lifecycle(payload, events=[events[0], altered])

    def test_sent_coverage_scope_profile_and_asof_guard(self):
        incoming = source('request')
        good = coverage(('ats:1', 'request:1'))
        for bad in [replace(good, profile_id='other'), replace(good, scope_digest='wrong'),
                    coverage(('ats:2', 'request:1')), replace(good, through=REVIEWED),
                    replace(good, checked_at='2026-10-07T14:00:00Z')]:
            with self.subTest(bad=bad):
                try:
                    result = reconcile_lifecycle(packet(incoming), events=[request(incoming)], sent_coverage=bad)
                except ContractError:
                    continue
                self.assertNotEqual(request_state(result)['status'], 'reply_due')
                self.assertTrue(result['gaps'])

    def test_frozen_sent_horizon_can_be_checked_later_than_cutoff(self):
        incoming = source('request')
        cutoff = '2026-10-06T13:00:00Z'
        result = reconcile_lifecycle(packet(incoming), events=[request(incoming)],
                    sent_coverage=coverage(('ats:1', 'request:1'), through=cutoff), sent_cutoff=cutoff)
        state = request_state(result)
        self.assertEqual(state['status'], 'reply_due')
        self.assertEqual(state['due_as_of'], cutoff)
        self.assertEqual(result['sent_cutoff'], cutoff)

    def test_request_after_frozen_sent_cutoff_cannot_be_reply_due(self):
        incoming = source('request')
        cutoff = '2026-10-06T13:00:00Z'
        accepted = replace(request(incoming, at='2026-10-06T13:30:00Z'), reviewed_at=NOW)
        result = reconcile_lifecycle(packet(incoming), events=[accepted],
                    sent_coverage=coverage(('ats:1', 'request:1'), through=cutoff), sent_cutoff=cutoff)
        self.assertNotEqual(request_state(result)['status'], 'reply_due')
        self.assertTrue(result['gaps'])

    def test_equivalent_timezone_instants_are_used_for_ties_and_sent_scope(self):
        rejected, interviewing = source('rejected'), source('interviewing')
        result = reconcile_lifecycle(packet(rejected, interviewing), events=[event(rejected),
                    event(interviewing, at='2026-10-04T06:00:00-04:00', stage='INTERVIEWING')])
        self.assertEqual(current(result)['status'], 'conflicted')
        self.assertEqual(result['lifecycle_proposals'], [])
        incoming = source('request')
        checked = reconcile_lifecycle(packet(incoming), events=[request(incoming)],
                    sent_coverage=coverage(('ats:1', 'request:1'), through='2026-10-06T10:00:00-04:00'))
        self.assertEqual(request_state(checked)['status'], 'reply_due')

    def test_unknown_existing_lifecycle_holds_known_request_chronology(self):
        manual, incoming = source('manual', 'manual_history'), source('request')
        result = reconcile_lifecycle(packet(manual, incoming), events=[event(manual, 'manual_status', None, 'INTERVIEWING'), request(incoming)],
                    sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(request_state(result)['status'], 'held')
        self.assertTrue(result['gaps'])

    def test_unhashable_kind_stage_owner_and_match_basis_are_contract_errors(self):
        incoming = source('request')
        accepted = request(incoming)
        malformed = [replace(accepted, kind=[]), replace(accepted, match_basis={}),
                     replace(accepted, data={**accepted.data, 'response_owner': []}),
                     replace(event(incoming), data={'stage': []}), replace(accepted, data=[])]
        for bad in malformed:
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                reconcile_lifecycle(packet(incoming), events=[bad])

    def test_malformed_data_and_time_raise_without_effect(self):
        incoming = source('request')
        base = request(incoming)
        for bad in [replace(base, data={'request_id': 'r'}), replace(base, data={**base.data, 'deadline_at': 'tomorrow'}),
                    replace(base, effective_at='2026-10-07T10:00:00Z'), replace(base, reviewed_at='2026-10-01T10:00:00Z'),
                    replace(base, data={**base.data, 'response_owner': ''}), replace(base, kind='silence_rejected')]:
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                reconcile_lifecycle(packet(incoming), events=[bad])

    def test_history_and_inputs_detached_no_external_effects(self):
        incoming, outcome = source('request'), source('outcome')
        payload = packet(incoming, outcome)
        events = [event(outcome, at=OLD, stage='ACTIVE'), request(incoming)]
        before, event_before = deepcopy(payload), deepcopy(events)
        with patch('builtins.open', side_effect=AssertionError('file effect')), patch('socket.socket', side_effect=AssertionError('network effect')):
            result = reconcile_lifecycle(payload, events=events, sent_coverage=coverage(('ats:1', 'request:1')))
        self.assertEqual(payload, before)
        self.assertEqual(events, event_before)
        self.assertFalse(result['operational_complete'])
        self.assertEqual(len(current(result)['history']), 2)
        current(result)['requests'][0]['response_owner'] = 'changed'
        result['reconciliation']['source_events'][0]['payload']['changed'] = True
        self.assertEqual(payload, before)
        self.assertEqual(events, event_before)
        self.assertNotEqual(request_state(reconcile_lifecycle(payload, events=events, sent_coverage=coverage(('ats:1', 'request:1'))))['response_owner'], 'changed')


if __name__ == '__main__':
    unittest.main()
