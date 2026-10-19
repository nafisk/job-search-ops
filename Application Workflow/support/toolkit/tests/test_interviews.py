"""Independent exact interview process/stage and evidence semantics."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from contracts import ContractError
from interviews import InterviewAcceptance, process_key, stage_key, reconcile_interviews

PROFILE = 'fictional-interviews'
NOW = '2026-10-06T14:00:00Z'
SEEN = '2026-10-06T12:00:00Z'
REVIEWED = '2026-10-06T13:00:00Z'
INVITED = '2026-10-01T10:00:00Z'
BOOKED = '2026-10-02T10:00:00Z'
ATTENDED = '2026-10-04T15:05:00Z'


def fp(value):
    # Independent identity contract and expected facts; no implementation output oracle.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def app_key(role='ats:1', employer='example-co', profile=PROFILE):
    return fp([profile, employer, role])


def pkey(role='ats:1', process='process:1', employer='example-co', profile=PROFILE):
    return fp([app_key(role, employer, profile), process])


def skey(stage='stage:1', role='ats:1', process='process:1'):
    return fp([pkey(role, process), stage])


def source(event_id, origin='correspondence', role='ats:1', employer='example-co', payload=None):
    return {'event_id': event_id, 'origin': origin, 'source_item_id': 'native:' + event_id,
            'observed_at': SEEN, 'employer_id': employer, 'role_id': role,
            'requisition_id': 'REQ-' + role.split(':')[-1] if role else None,
            'application_ref': None, 'evidence_refs': ['fictional:' + event_id],
            'payload': deepcopy(payload) if payload is not None else {'full_source': 'complete fictional evidence'}}


def packet(*messages, two_roles=False, profile=PROFILE):
    rows = [source('registered-1', 'sheet', payload={'status': 'Applied', 'note': 'keep', 'date': '2026-09-20'})]
    if two_roles:
        rows.append(source('registered-2', 'manual_history', role='ats:2'))
    return {'schema_version': 1, 'profile_id': profile, 'as_of': NOW, 'sources': rows + list(messages)}


def accepted(message, kind='invitation', data=None, at=INVITED, stage='stage:1', role='ats:1', process='process:1',
             evidence='employer_email', event_id=None, employer='example-co'):
    if data is None:
        data = {'label': 'Technical screen'}
    return InterviewAcceptance(PROFILE, event_id or ('accepted:' + message['event_id']), message['event_id'], fp(message),
             app_key(role, employer), process, stage, kind, at, REVIEWED, 'fictional-full-source-exact-proof',
             'exact_role', True, evidence, deepcopy(data))


def booking(message, stage='stage:1', role='ats:1', process='process:1', booking_id='booking:1', starts='2026-10-07T14:00:00Z',
            ends='2026-10-07T15:00:00Z', at=BOOKED):
    return accepted(message, 'booking', {'booking_id': booking_id, 'starts_at': starts, 'ends_at': ends, 'timezone': 'America/New_York'},
                    at=at, stage=stage, role=role, process=process, evidence='calendar')


def outcome(message, status='REJECTED', at=ATTENDED, evidence='employer_email'):
    return accepted(message, 'outcome', {'status': status}, at=at, stage=None, evidence=evidence)


def process(result, key=None):
    return next(p for p in result['processes'] if p['process_key'] == (pkey() if key is None else key))


def stage(result, stage_id='stage:1', process_key=None):
    return next(s for s in process(result, process_key)['stages'] if s['stage_id'] == stage_id)


class InterviewTests(unittest.TestCase):
    def test_exact_process_and_stage_keys_include_application_namespaces(self):
        self.assertEqual(process_key(app_key(), 'process:1'), pkey())
        self.assertEqual(stage_key(pkey(), 'stage:1'), skey())
        self.assertNotEqual(pkey(), pkey(role='ats:2'))
        self.assertNotEqual(pkey(), pkey(process='process:2'))
        self.assertNotEqual(pkey(), pkey(employer='other-co'))
        self.assertNotEqual(pkey(), pkey(profile='other-profile'))
        self.assertNotEqual(skey(), skey('stage:2'))

    def test_invitation_only_does_not_imply_booking_rsvp_or_attendance(self):
        message = source('invitation')
        result = reconcile_interviews(packet(message), events=[accepted(message)])
        s = stage(result)
        self.assertTrue(s['invited'])
        self.assertEqual(s['label'], 'Technical screen')
        self.assertIsNone(s['booking'])
        self.assertIsNone(s['rsvp'])
        self.assertIsNone(s['attendance'])
        self.assertFalse(s['canceled'])

    def test_calendar_booking_is_not_rsvp_or_attendance(self):
        message = source('calendar', payload={'calendar_event': 'actual fictional event', 'attendees': ['fictional@example.invalid']})
        result = reconcile_interviews(packet(message), events=[booking(message)])
        s = stage(result)
        self.assertEqual(s['booking']['starts_at'], '2026-10-07T14:00:00Z')
        self.assertEqual(s['booking']['timezone'], 'America/New_York')
        self.assertIsNone(s['rsvp'])
        self.assertIsNone(s['attendance'])
        self.assertEqual(s['status'], 'booked')

    def test_past_meeting_time_never_proves_attendance(self):
        message = source('calendar')
        result = reconcile_interviews(packet(message), events=[booking(message, starts='2026-10-04T14:00:00Z', ends='2026-10-04T15:00:00Z')])
        self.assertIsNone(stage(result)['attendance'])
        self.assertNotEqual(stage(result)['status'], 'completed')

    def test_attendance_before_scheduled_start_cannot_complete_future_booking(self):
        booked, attended = source('booked'), source('past-attendance', 'manual_history')
        result = reconcile_interviews(packet(booked, attended), events=[booking(booked),
                    accepted(attended, 'attendance', {'attended': True}, at=ATTENDED, evidence='user_confirmation')])
        s = stage(result)
        self.assertIsNone(s['attendance'])
        self.assertNotEqual(s['status'], 'completed')
        self.assertEqual(s['booking']['starts_at'], '2026-10-07T14:00:00Z')
        self.assertEqual(len(s['history']), 2)
        self.assertIn('accepted:past-attendance', [e['event_id'] for e in s['history']])

    def test_last_known_process_status_keeps_evidence_time_on_later_evaluation(self):
        invitation = source('invite')
        payload = packet(invitation)
        first = reconcile_interviews(payload, events=[accepted(invitation)])
        later_payload = deepcopy(payload)
        later_payload['as_of'] = '2026-10-07T14:00:00Z'
        later = reconcile_interviews(later_payload, events=[accepted(invitation)])
        for result in [first, later]:
            self.assertEqual(process(result)['status_basis'], 'last_known_evidence')
            self.assertEqual(process(result)['effective_at'], INVITED)
            self.assertEqual(result['interview_proposals'][0]['status_basis'], 'last_known_evidence')
            self.assertEqual(result['interview_proposals'][0]['effective_at'], INVITED)

    def test_accepted_rsvp_not_attendance(self):
        invitation, booked, rsvp = source('invitation'), source('booked'), source('rsvp')
        events = [accepted(invitation), booking(booked), accepted(rsvp, 'rsvp', {'booking_id': 'booking:1', 'response': 'accepted'},
                    at='2026-10-03T10:00:00Z', evidence='calendar')]
        result = reconcile_interviews(packet(invitation, booked, rsvp), events=events)
        self.assertEqual(stage(result)['rsvp'], 'accepted')
        self.assertIsNone(stage(result)['attendance'])
        self.assertNotEqual(stage(result)['status'], 'completed')

    def test_rsvp_alone_does_not_create_unknown_interview(self):
        message = source('rsvp')
        result = reconcile_interviews(packet(message), events=[accepted(message, 'rsvp', {'booking_id': 'booking:1', 'response': 'accepted'}, evidence='calendar')])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['unresolved_events'])

    def test_actual_attendance_proof_is_distinct_positive_fact(self):
        message = source('user-attendance', 'manual_history', payload={'user_report': 'I attended this exact technical screen'})
        result = reconcile_interviews(packet(message), events=[accepted(message, 'attendance', {'attended': True},
                    at=ATTENDED, evidence='user_confirmation')])
        self.assertIs(stage(result)['attendance'], True)
        self.assertEqual(stage(result)['status'], 'completed')
        self.assertIsNone(stage(result)['booking'])

    def test_explicit_nonattendance_not_rejection(self):
        message, invitation = source('not-attended', 'manual_history'), source('invitation')
        result = reconcile_interviews(packet(message, invitation), events=[accepted(invitation), accepted(message, 'attendance', {'attended': False},
                    at=ATTENDED, evidence='user_confirmation')])
        self.assertIs(stage(result)['attendance'], False)
        self.assertEqual(stage(result)['status'], 'not_attended')
        self.assertNotEqual(process(result)['process_status'], 'REJECTED')

    def test_cancellation_not_rejection_or_attendance(self):
        invitation, booked, canceled = source('invitation'), source('booked'), source('cancel')
        result = reconcile_interviews(packet(invitation, booked, canceled), events=[accepted(invitation), booking(booked),
                    accepted(canceled, 'cancellation', {'booking_id': 'booking:1'}, at='2026-10-03T10:00:00Z')])
        self.assertTrue(stage(result)['canceled'])
        self.assertEqual(stage(result)['status'], 'canceled')
        self.assertIsNone(stage(result)['attendance'])
        self.assertNotEqual(process(result)['process_status'], 'REJECTED')

    def test_old_rsvp_and_cancellation_do_not_apply_to_replacement_booking(self):
        old, new, rsvp, canceled = source('old-booking'), source('new-booking'), source('old-rsvp'), source('old-cancel')
        events = [booking(old), booking(new, booking_id='booking:2', at='2026-10-03T10:00:00Z',
                    starts='2026-10-08T14:00:00Z', ends='2026-10-08T15:00:00Z'),
                  accepted(rsvp, 'rsvp', {'booking_id': 'booking:1', 'response': 'accepted'}, at=ATTENDED, evidence='calendar'),
                  accepted(canceled, 'cancellation', {'booking_id': 'booking:1'}, at=ATTENDED)]
        result = reconcile_interviews(packet(old, new, rsvp, canceled), events=events)
        s = stage(result)
        self.assertEqual(s['booking']['booking_id'], 'booking:2')
        self.assertIsNone(s['rsvp'])
        self.assertFalse(s['canceled'])
        self.assertEqual(len(s['history']), 4)
        self.assertFalse(any(g['event_id'] in ('accepted:old-rsvp', 'accepted:old-cancel') for g in result['gaps']))

    def test_calendar_cannot_prove_attendance_or_interview_outcome(self):
        message = source('calendar')
        for e in [accepted(message, 'attendance', {'attended': True}, evidence='calendar'), outcome(message, evidence='calendar')]:
            with self.subTest(e=e), self.assertRaises(ContractError):
                reconcile_interviews(packet(message), events=[e])

    def test_user_confirmation_requires_actual_manual_history_source(self):
        message = source('mail-not-user')
        with self.assertRaises(ContractError):
            reconcile_interviews(packet(message), events=[accepted(message, 'user_process', {}, stage=None, evidence='user_confirmation')])

    def test_application_only_rejection_never_invents_interview_process(self):
        message = source('application-rejection', payload={'body': 'We will not move forward with your application'})
        result = reconcile_interviews(packet(message), events=[outcome(message)])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['unresolved_events'])
        self.assertEqual(result['interview_proposals'], [])

    def test_receipt_referral_and_interviewing_label_without_proof_create_no_process(self):
        messages = [source('receipt', payload={'body': 'Application received'}), source('referral', payload={'body': 'Your colleague referred you'}),
                    source('outline', payload={'status': 'INTERVIEWING', 'stages': ['screen', 'onsite']})]
        result = reconcile_interviews(packet(*messages))
        self.assertEqual(result['processes'], [])
        self.assertEqual(result['interview_proposals'], [])
        self.assertEqual(result['reconciliation']['source_events'], sorted(packet(*messages)['sources'], key=lambda x:x['event_id']))

    def test_outline_and_advice_never_establish_interview(self):
        outline, advice = source('outline'), source('advice', 'manual_history')
        events = [accepted(outline, 'outline', {'stages': ['screen', 'panel'], 'total_stages': 2}, stage=None),
                  accepted(advice, 'advice', {'note': 'Practice behavioral examples'}, stage=None, evidence='advice')]
        result = reconcile_interviews(packet(outline, advice), events=events)
        self.assertEqual(result['processes'], [])
        self.assertEqual(result['interview_proposals'], [])
        self.assertTrue(result['unresolved_events'])

    def test_advice_evidence_cannot_mint_invitation_booking_or_attendance(self):
        message = source('advice', 'manual_history')
        for e in [accepted(message, evidence='advice'), replace(booking(message), evidence_kind='advice'),
                  accepted(message, 'attendance', {'attended': True}, evidence='advice')]:
            with self.subTest(kind=e.kind), self.assertRaises(ContractError):
                reconcile_interviews(packet(message), events=[e])

    def test_user_confirmation_and_voice_can_establish_actual_process(self):
        for evidence in ['user_confirmation', 'user_voice_transcript']:
            with self.subTest(evidence=evidence):
                message = source('user-process', 'manual_history', payload={'user_confirmation': 'exact process occurred', 'legacy_date': '2026-09'})
                result = reconcile_interviews(packet(message), events=[accepted(message, 'user_process', {}, stage=None, evidence=evidence)])
                self.assertEqual(len(result['processes']), 1)
                self.assertEqual(process(result)['stages'], [])
                self.assertIn(message, result['reconciliation']['source_events'])

    def test_user_outcome_alone_cannot_establish_unproven_interview(self):
        message = source('user-outcome', 'manual_history')
        result = reconcile_interviews(packet(message), events=[outcome(message, evidence='user_confirmation')])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['unresolved_events'])

    def test_explicit_user_process_with_outcome_preserves_historical_fact(self):
        confirmed, message = source('user-process', 'manual_history'), source('user-outcome', 'manual_history')
        result = reconcile_interviews(packet(confirmed, message), events=[accepted(confirmed, 'user_process', {}, stage=None,
                    evidence='user_confirmation'), outcome(message, evidence='user_confirmation')])
        self.assertEqual(len(result['processes']), 1)
        self.assertEqual(process(result)['process_status'], 'REJECTED')
        self.assertEqual(process(result)['stages'], [])

    def test_nonattendance_alone_does_not_establish_interview(self):
        message = source('not-attended', 'manual_history')
        result = reconcile_interviews(packet(message), events=[accepted(message, 'attendance', {'attended': False},
                    at=ATTENDED, evidence='user_confirmation')])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['unresolved_events'])

    def test_invitation_does_not_claim_response_obligation_already_evaluated(self):
        message = source('invite')
        result = reconcile_interviews(packet(message), events=[accepted(message)])
        self.assertIsNone(stage(result).get('action_required'))

    def test_cyclic_legacy_payload_fails_with_contract_error(self):
        legacy = {}
        legacy['self'] = legacy
        with self.assertRaises(ContractError):
            reconcile_interviews(packet(), legacy_records=[legacy])

    def test_outcome_for_known_process_does_not_invent_attendance(self):
        invitation, rejection = source('invitation'), source('process-outcome')
        result = reconcile_interviews(packet(invitation, rejection), events=[accepted(invitation), outcome(rejection)])
        self.assertEqual(process(result)['process_status'], 'REJECTED')
        self.assertIsNone(stage(result)['attendance'])

    def test_same_company_different_roles_and_processes_stay_separate(self):
        first, second, other_process = source('first'), source('second', role='ats:2'), source('other-process')
        events = [accepted(first), accepted(second, role='ats:2'), accepted(other_process, process='process:2')]
        result = reconcile_interviews(packet(first, second, other_process, two_roles=True), events=events)
        self.assertEqual({p['process_key'] for p in result['processes']}, {pkey(), pkey(role='ats:2'), pkey(process='process:2')})
        self.assertTrue(all(len(p['stages']) == 1 for p in result['processes']))

    def test_other_stage_attendance_never_completes_first_stage(self):
        first, second = source('first'), source('second', 'manual_history')
        result = reconcile_interviews(packet(first, second), events=[accepted(first),
                    accepted(second, 'attendance', {'attended': True}, at=ATTENDED, stage='stage:2', evidence='user_confirmation')])
        self.assertIsNone(stage(result, 'stage:1')['attendance'])
        self.assertIs(stage(result, 'stage:2')['attendance'], True)
        self.assertNotEqual(stage(result, 'stage:1')['status'], 'completed')

    def test_outline_does_not_materialize_unobserved_stages(self):
        invitation, outline = source('invitation'), source('outline')
        result = reconcile_interviews(packet(invitation, outline), events=[accepted(invitation),
                    accepted(outline, 'outline', {'stages': ['screen', 'panel', 'offer'], 'total_stages': 3}, stage=None)])
        self.assertEqual(len(process(result)['stages']), 1)
        self.assertEqual(stage(result)['stage_id'], 'stage:1')
        self.assertEqual(len(process(result)['history']), 2)

    def test_availability_registration_and_reschedule_do_not_imply_booking(self):
        invitation, availability, registration, reschedule = source('invite'), source('availability'), source('registration'), source('reschedule')
        events = [accepted(invitation), accepted(availability, 'availability_sent', {'request_id': 'availability:1'}, at=BOOKED),
                  accepted(registration, 'registration', {'request_id': 'registration:1'}, at=BOOKED),
                  accepted(reschedule, 'reschedule', {'request_id': 'reschedule:1'}, at=BOOKED)]
        result = reconcile_interviews(packet(invitation, availability, registration, reschedule), events=events)
        s = stage(result)
        self.assertEqual(s['availability_sent'], ['availability:1'])
        self.assertEqual(s['registrations'], ['registration:1'])
        self.assertTrue(s['reschedule_requested'])
        self.assertIsNone(s['booking'])
        self.assertIsNone(s['attendance'])
        self.assertEqual(s['status'], 'reschedule_requested')

    def test_reopen_permission_alone_does_not_establish_interview(self):
        message = source('user-reopen', 'manual_history', payload={'user_instruction': 'resume this exact process'})
        result = reconcile_interviews(packet(message), events=[accepted(message, 'reopen', {}, stage=None, evidence='user_confirmation')])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['unresolved_events'])
        self.assertEqual(result['interview_proposals'], [])

    def test_explicit_user_reopen_can_reactivate_established_process(self):
        invitation, rejection, reopened = source('invite'), source('rejection'), source('reopen', 'manual_history')
        result = reconcile_interviews(packet(invitation, rejection, reopened), events=[accepted(invitation), outcome(rejection, at=BOOKED),
                    accepted(reopened, 'reopen', {}, at=ATTENDED, stage=None, evidence='user_confirmation')])
        self.assertEqual(process(result)['process_status'], 'ACTIVE')
        self.assertFalse(process(result)['suppressed'])
        self.assertEqual(len(process(result)['history']), 3)

    def test_required_source_gap_keeps_original_times_and_no_completion(self):
        from coverage import SourceCheck, SourceGap
        profile = json.loads((Path(__file__).resolve().parents[1] / 'examples' / 'sam.json').read_text())
        profile['profile_id'] = PROFILE
        cutoff = '2026-10-06T11:00:00Z'
        last_success = '2026-10-05T11:00:00Z'
        scopes = {service: fp({'profile': PROFILE, 'full_scope': service, 'pending': ['fictional:old-voice']})
                  for service in ['mail', 'calendar', 'messages']}
        checks = {service: SourceCheck(PROFILE, service, profile['integrations'][service]['connection_ref'], scopes[service],
                      SEEN, cutoff, last_success, 'checked', (), ('fictional:full-source-readback',)) for service in scopes}
        original_gap = SourceGap('fictional:old-voice', 'Saved transcript unavailable', None, SEEN)
        checks['messages'] = replace(checks['messages'], status='partial', gaps=(original_gap,))
        before = deepcopy(checks)
        invitation = source('invite')
        result = reconcile_interviews(packet(invitation), events=[accepted(invitation)], profile=profile,
                    source_scopes=scopes, source_checks=checks, cutoff=cutoff)
        coverage = result['coverage']
        self.assertFalse(coverage['required_complete'])
        self.assertEqual(coverage['sources']['messages']['checked_at'], SEEN)
        self.assertEqual(coverage['sources']['messages']['covered_through'], cutoff)
        self.assertEqual(coverage['sources']['messages']['last_successful_at'], last_success)
        flattened = [g['source_gap'] for g in result['gaps'] if g.get('source_gap', {}).get('gap_id') == 'fictional:old-voice']
        self.assertEqual(flattened, [{'service': 'messages', 'gap_id': 'fictional:old-voice', 'reason': 'Saved transcript unavailable',
                                     'first_observed_at': None, 'last_attempt_at': SEEN}])
        self.assertFalse(result['operational_complete'])
        self.assertFalse(result['delivered_baseline_changed'])
        self.assertEqual(len(result['interview_proposals']), 1)
        self.assertEqual(checks, before)
        with self.assertRaises(ContractError):
            reconcile_interviews(packet(invitation), events=[accepted(invitation)], profile={**profile, 'profile_id': 'other'},
                                 source_scopes=scopes, source_checks=checks, cutoff=cutoff)

    def test_ambiguous_process_outcomes_are_not_defaulted_to_active(self):
        invitation, rejected, active = source('invite'), source('rejected'), source('active')
        result = reconcile_interviews(packet(invitation, rejected, active), events=[accepted(invitation),
                    outcome(rejected), outcome(active, status='ACTIVE')])
        self.assertIsNone(process(result)['process_status'])
        self.assertEqual(process(result)['status'], 'conflicted')
        self.assertTrue(result['gaps'] or process(result)['conflicts'])
        self.assertEqual(result['interview_proposals'], [])

    def test_unknown_booking_reference_cannot_change_current_rsvp(self):
        booked, rsvp = source('booked'), source('rsvp')
        result = reconcile_interviews(packet(booked, rsvp), events=[booking(booked), accepted(rsvp, 'rsvp',
                    {'booking_id': 'unknown:booking', 'response': 'accepted'}, at=ATTENDED, evidence='calendar')])
        self.assertIsNone(stage(result)['rsvp'])
        self.assertTrue(any(g['event_id'] == 'accepted:rsvp' for g in result['gaps']))

    def test_legacy_records_preserved_without_promotion(self):
        legacy = [{'company': 'Example', 'role': 'Software Engineer', 'stage': 'interview', 'raw_date': '2026-09', 'notes': ['advice', 'keep unknown'],
                   'former_status': 'canceled', 'application_ref': 'old-unverified'}]
        before = deepcopy(legacy)
        result = reconcile_interviews(packet(), legacy_records=legacy)
        self.assertEqual(result['legacy_records'], before)
        self.assertEqual(result['processes'], [])
        result['legacy_records'][0]['notes'].append('changed')
        self.assertEqual(legacy, before)

    def test_unknown_effective_time_keeps_original_fact_and_gap(self):
        invitation = source('unknown-invite', payload={'legacy_date': '2026-09', 'body': 'exact invitation'})
        result = reconcile_interviews(packet(invitation), events=[accepted(invitation, at=None)])
        self.assertTrue(result['gaps'])
        self.assertEqual(result['interview_proposals'], [])
        self.assertIsNone(process(result)['history'][0]['effective_at'])
        self.assertIn(invitation, result['reconciliation']['source_events'])

    def test_tied_attendance_contradictions_hold_stage(self):
        attended, missed = source('attended', 'manual_history'), source('missed', 'manual_history')
        result = reconcile_interviews(packet(attended, missed), events=[accepted(attended, 'attendance', {'attended': True}, at=ATTENDED, evidence='user_confirmation'),
                    accepted(missed, 'attendance', {'attended': False}, at=ATTENDED, evidence='user_confirmation')])
        self.assertTrue(stage(result)['conflicts'])
        self.assertEqual(result['interview_proposals'], [])

    def test_current_application_and_process_exclusions_never_clear(self):
        invitation = source('invite')
        events = [accepted(invitation)]
        for kwargs in [{'excluded_application_keys': frozenset([app_key()])}, {'excluded_process_keys': frozenset([pkey()])}]:
            with self.subTest(kwargs=kwargs):
                result = reconcile_interviews(packet(invitation), events=events, **kwargs)
                self.assertTrue(process(result)['excluded'])
                self.assertEqual(result['interview_proposals'], [])
                self.assertEqual(len(process(result)['history']), 1)

    def test_source_binding_profile_and_full_read_guards(self):
        message = source('invitation')
        base = accepted(message)
        for e in [replace(base, profile_id='other'), replace(base, source_digest='wrong'), replace(base, full_source_read=False), base.__dict__]:
            with self.subTest(e=e), self.assertRaises(ContractError):
                reconcile_interviews(packet(message), events=[e])
        result = reconcile_interviews(packet(message, two_roles=True), events=[replace(base, application_key=app_key('ats:2'))])
        self.assertEqual(result['processes'], [])
        self.assertTrue(result['gaps'])

    def test_replay_native_collision_and_changed_event_content(self):
        invitation, booked = source('invitation'), source('booked')
        a, b = accepted(invitation), booking(booked)
        payload = packet(invitation, booked)
        result = reconcile_interviews(payload, events=[a, b])
        self.assertEqual(result, reconcile_interviews(payload, events=[b, a, a]))
        with self.assertRaises(ContractError):
            reconcile_interviews(payload, events=[a, replace(a, event_id='another-id')])
        with self.assertRaises(ContractError):
            reconcile_interviews(payload, events=[a, replace(a, data={'label': 'changed'})])

    def test_unknown_fact_gap_replay_is_deterministic_in_both_input_orders(self):
        first, second = source('unknown-first'), source('unknown-second')
        a = accepted(first, at=None)
        b = accepted(second, at=None, stage='stage:2')
        payload = packet(first, second)
        result = reconcile_interviews(payload, events=[a, b])
        self.assertEqual(result, reconcile_interviews(payload, events=[b, a]))
        self.assertEqual(result['interview_proposals'], [])
        self.assertEqual({g['event_id'] for g in result['gaps'] if g['event_id']}, {'accepted:unknown-first', 'accepted:unknown-second'})

    def test_malformed_proof_and_future_fact_times_rejected(self):
        message = source('invitation')
        base = accepted(message)
        for e in [replace(base, kind=[]), replace(base, data={'label': ''}), replace(base, stage_id=None),
                  replace(base, effective_at='2026-10-07T10:00:00Z'), replace(base, reviewed_at='2026-10-01T10:00:00Z'),
                  replace(base, evidence_kind='not_proof'), replace(base, data={'label': 'x', 'unknown': True})]:
            with self.subTest(e=e), self.assertRaises(ContractError):
                reconcile_interviews(packet(message), events=[e])

    def test_no_external_effects_inputs_and_histories_detached(self):
        invitation = source('invitation')
        payload = packet(invitation)
        events = [accepted(invitation)]
        before, events_before = deepcopy(payload), deepcopy(events)
        with patch('builtins.open', side_effect=AssertionError('file effect')), patch('socket.socket', side_effect=AssertionError('network effect')):
            result = reconcile_interviews(payload, events=events)
        self.assertFalse(result['operational_complete'])
        self.assertFalse(result['delivered_baseline_changed'])
        self.assertEqual(payload, before)
        self.assertEqual(events, events_before)
        process(result)['history'][0]['data']['label'] = 'changed'
        result['reconciliation']['source_events'][0]['payload']['changed'] = True
        self.assertEqual(payload, before)
        self.assertEqual(events, events_before)


if __name__ == '__main__':
    unittest.main()
