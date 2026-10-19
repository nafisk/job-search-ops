"""Independent configured-source coverage tests; all identities and scopes fictional."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from contracts import ContractError
from coverage import SourceCheck, SourceGap, coverage_status


ROOT = Path(__file__).resolve().parents[1]
CUTOFF = '2026-10-06T12:00:00Z'
AS_OF = '2026-10-06T13:00:00Z'
CHECKED = '2026-10-06T12:30:00Z'
OLD = '2026-10-05T12:00:00Z'


def fp(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def configured(name='sam'):
    return json.loads((ROOT / 'examples' / (name + '.json')).read_text())


def approved_scopes(profile):
    # Full fictional scope includes the named direct context and older backlog,
    # not merely a time window or a connection-test label.
    declarations = {
        'mail': {'mailboxes': ['Inbox', 'Archive', 'Spam', 'Sent'], 'older_unresolved': ['thread:fictional']},
        'calendar': {'calendar_ids': ['calendar:fictional'], 'process_ids': ['process:fictional']},
        'messages': {'direct_context': 'verified-fictional-context', 'overlap_days': 3,
                     'missing_transcript_backlog': ['voice:fictional-older'], 'unresolved_date_windows': ['window:fictional']},
    }
    return {service: fp({'profile_id': profile['profile_id'], 'scope': declaration})
            for service, declaration in declarations.items()
            if profile['integrations'][service]['enabled']}


def receipt(profile, scopes, service, **changes):
    value = SourceCheck(profile['profile_id'], service,
                        profile['integrations'][service]['connection_ref'], scopes[service],
                        CHECKED, CUTOFF, OLD, 'checked', (), ('fictional:full-source-evidence',))
    return replace(value, **changes)


def gap(**changes):
    return replace(SourceGap('voice:fictional-older', 'Saved transcript unavailable; original content unknown',
                             OLD, CHECKED), **changes)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.profile = configured()
        self.scopes = approved_scopes(self.profile)
        self.checks = {s: receipt(self.profile, self.scopes, s) for s in self.scopes}

    def run_status(self, profile=None, scopes=None, checks=None, cutoff=CUTOFF, as_of=AS_OF):
        return coverage_status(self.profile if profile is None else profile,
                               self.scopes if scopes is None else scopes,
                               self.checks if checks is None else checks,
                               cutoff=cutoff, as_of=as_of)

    def test_all_enabled_checked_after_frozen_cutoff(self):
        result = self.run_status()
        self.assertTrue(result['required_complete'])
        self.assertTrue(result['all_enabled_complete'])
        self.assertFalse(result['operational_complete'])
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['cutoff'], CUTOFF)
        self.assertEqual(result['as_of'], AS_OF)
        for service in self.scopes:
            self.assertEqual(result['sources'][service]['status'], 'checked')
            self.assertEqual(result['sources'][service]['checked_at'], CHECKED)
            self.assertEqual(result['sources'][service]['covered_through'], CUTOFF)
            self.assertEqual(result['sources'][service]['last_successful_at'], OLD)

    def test_required_configured_sources_cannot_be_omitted_from_scope(self):
        for service in ('mail', 'messages'):
            with self.subTest(service=service):
                scopes = {s: v for s, v in self.scopes.items() if s != service}
                with self.assertRaises(ContractError):
                    self.run_status(scopes=scopes, checks={s: v for s, v in self.checks.items() if s != service})

    def test_enabled_optional_source_still_requires_declared_scope(self):
        with self.assertRaises(ContractError):
            self.run_status(scopes={s: v for s, v in self.scopes.items() if s != 'calendar'},
                            checks={s: v for s, v in self.checks.items() if s != 'calendar'})

    def test_missing_required_receipt_is_not_checked_and_blocks_completion(self):
        for service in ('mail', 'messages'):
            with self.subTest(service=service):
                checks = {s: v for s, v in self.checks.items() if s != service}
                result = self.run_status(checks=checks)
                item = result['sources'][service]
                self.assertEqual(item['status'], 'not_checked')
                self.assertIsNone(item['checked_at'])
                self.assertIsNone(item['last_successful_at'])
                self.assertFalse(result['required_complete'])
                self.assertFalse(result['all_enabled_complete'])
                self.assertTrue(any(g['service'] == service for g in result['gaps']))

    def test_missing_optional_receipt_is_gap_but_not_required_failure(self):
        result = self.run_status(checks={s: v for s, v in self.checks.items() if s != 'calendar'})
        self.assertTrue(result['required_complete'])
        self.assertFalse(result['all_enabled_complete'])
        self.assertEqual(result['sources']['calendar']['status'], 'not_checked')
        self.assertTrue(any(g['service'] == 'calendar' for g in result['gaps']))

    def test_provided_null_is_not_a_trusted_check(self):
        with self.assertRaises(ContractError):
            self.run_status(checks={**self.checks, 'messages': None})

    def test_required_integration_cannot_be_disabled_or_use_nonboolean_flags(self):
        for change in ({'enabled': False}, {'required': 1}, {'enabled': 'yes'}):
            profile = deepcopy(self.profile)
            profile['integrations']['messages'].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.run_status(profile=profile)

    def test_disabled_optional_is_not_configured_and_never_claims_checked(self):
        profile = configured('alex')
        scopes = approved_scopes(profile)
        result = self.run_status(profile, scopes, {'mail': receipt(profile, scopes, 'mail')})
        self.assertTrue(result['all_enabled_complete'])
        for service in ('calendar', 'messages'):
            item = result['sources'][service]
            self.assertEqual(item['status'], 'not_configured')
            self.assertIsNone(item['checked_at'])
            self.assertIsNone(item['covered_through'])
            self.assertEqual(item['gaps'], [])

    def test_disabled_or_unknown_source_cannot_be_invented_in_scope_or_checks(self):
        for service in ('messages', 'sheets', 'unknown'):
            profile = configured('alex')
            scopes = approved_scopes(profile)
            checks = {'mail': receipt(profile, scopes, 'mail')}
            with self.subTest(service=service), self.assertRaises(ContractError):
                self.run_status(profile, {**scopes, service: fp('fictional-extra')}, checks)
        with self.assertRaises(ContractError):
            self.run_status(checks={**self.checks, 'unknown': self.checks['mail']})

    def test_stale_required_check_keeps_actual_original_timestamps(self):
        old = receipt(self.profile, self.scopes, 'messages', checked_at=OLD, covered_through=OLD)
        result = self.run_status(checks={**self.checks, 'messages': old})
        item = result['sources']['messages']
        self.assertEqual(item['status'], 'stale')
        self.assertEqual(item['checked_at'], OLD)
        self.assertEqual(item['covered_through'], OLD)
        self.assertEqual(item['last_successful_at'], OLD)
        self.assertFalse(result['required_complete'])
        self.assertTrue(any(g['service'] == 'messages' for g in result['gaps']))

    def test_fresh_readback_of_old_coverage_is_stale(self):
        old = receipt(self.profile, self.scopes, 'mail', covered_through=OLD)
        result = self.run_status(checks={**self.checks, 'mail': old})
        self.assertEqual(result['sources']['mail']['status'], 'stale')
        self.assertEqual(result['sources']['mail']['checked_at'], CHECKED)
        self.assertFalse(result['required_complete'])

    def test_partial_missing_transcript_retains_exact_gap_history(self):
        missing = gap()
        partial = receipt(self.profile, self.scopes, 'messages', status='partial', gaps=(missing,))
        result = self.run_status(checks={**self.checks, 'messages': partial})
        item = result['sources']['messages']
        self.assertEqual(item['status'], 'partial')
        self.assertEqual(item['gaps'], [asdict(missing)])
        self.assertEqual(item['last_successful_at'], OLD)
        self.assertIn({'service': 'messages', **asdict(missing)}, result['gaps'])
        self.assertFalse(result['required_complete'])

    def test_blocked_source_preserves_previous_success_instead_of_advancing_it(self):
        failed = receipt(self.profile, self.scopes, 'mail', covered_through=None, status='blocked', gaps=(gap(),))
        result = self.run_status(checks={**self.checks, 'mail': failed})
        self.assertEqual(result['sources']['mail']['status'], 'blocked')
        self.assertEqual(result['sources']['mail']['last_successful_at'], OLD)
        self.assertIsNone(result['sources']['mail']['covered_through'])
        self.assertFalse(result['required_complete'])

    def test_known_absent_transcript_gap_times_can_remain_unknown(self):
        missing = gap(first_observed_at=None, last_attempt_at=None)
        partial = receipt(self.profile, self.scopes, 'messages', status='partial', gaps=(missing,))
        result = self.run_status(checks={**self.checks, 'messages': partial})
        self.assertEqual(result['sources']['messages']['gaps'], [asdict(missing)])

    def test_duplicate_gap_identity_or_evidence_reference_rejected(self):
        for changes in ({'status': 'partial', 'gaps': (gap(), gap())},
                        {'evidence_refs': ('fictional:same', 'fictional:same')}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'messages': replace(self.checks['messages'], **changes)})

    def test_incomplete_optional_source_affects_all_enabled_not_required(self):
        partial = receipt(self.profile, self.scopes, 'calendar', status='partial', gaps=(gap(),))
        result = self.run_status(checks={**self.checks, 'calendar': partial})
        self.assertTrue(result['required_complete'])
        self.assertFalse(result['all_enabled_complete'])

    def test_profile_connection_service_and_scope_receipts_cannot_cross_bind(self):
        good = self.checks['messages']
        for change in ({'profile_id': 'fictional-other'}, {'connection_ref': 'fictional-other-connection'},
                       {'service': 'mail'}, {'scope_digest': fp('unapproved-context')}, {'scope_digest': 'not-a-digest'}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'messages': replace(good, **change)})

    def test_named_context_and_transcript_backlog_cannot_be_dropped_under_old_receipt(self):
        scopes = {**self.scopes, 'messages': fp({'profile_id': self.profile['profile_id'],
                                                'scope': {'direct_context': 'different-fictional-context'}})}
        with self.assertRaises(ContractError):
            self.run_status(scopes=scopes)

    def test_dictionary_receipts_and_mutable_gap_lists_are_untrusted(self):
        good = self.checks['messages']
        for bad in (asdict(good), replace(good, gaps=[gap()]),
                    replace(good, status='partial', gaps=({'gap_id': 'fake'},)),
                    replace(good, evidence_refs=['fictional:mutable'])):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'messages': bad})

    def test_checked_requires_coverage_and_no_gaps(self):
        for changes in ({'covered_through': None}, {'gaps': (gap(),)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'mail': replace(self.checks['mail'], **changes)})

    def test_partial_and_blocked_require_real_gap_and_source_evidence(self):
        for changes in ({'status': 'partial'}, {'status': 'blocked'}, {'evidence_refs': ()},
                        {'status': 'partial', 'gaps': (gap(reason=''),)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'mail': replace(self.checks['mail'], **changes)})

    def test_future_or_regressing_source_and_gap_chronology_rejected(self):
        future = '2026-10-07T12:00:00Z'
        for changes in ({'checked_at': future}, {'covered_through': future}, {'last_successful_at': future},
                        {'checked_at': OLD, 'covered_through': CUTOFF},
                        {'status': 'partial', 'gaps': (gap(first_observed_at=CHECKED, last_attempt_at=OLD),)},
                        {'status': 'partial', 'gaps': (gap(last_attempt_at=future),)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'mail': replace(self.checks['mail'], **changes)})

    def test_timezone_required_for_all_known_source_times(self):
        naive = '2026-10-06T12:00:00'
        for field in ('checked_at', 'covered_through', 'last_successful_at'):
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.run_status(checks={**self.checks, 'mail': replace(self.checks['mail'], **{field: naive})})
        with self.assertRaises(ContractError):
            self.run_status(cutoff=naive)
        with self.assertRaises(ContractError):
            self.run_status(as_of=naive)

    def test_cutoff_cannot_follow_evaluation(self):
        with self.assertRaises(ContractError):
            self.run_status(cutoff='2026-10-06T14:00:00Z')

    def test_equivalent_timestamp_offsets_use_actual_instants(self):
        checks = {s: replace(v, covered_through='2026-10-06T08:00:00-04:00') for s, v in self.checks.items()}
        result = self.run_status(checks=checks)
        self.assertTrue(result['all_enabled_complete'])
        self.assertEqual(result['sources']['mail']['covered_through'], '2026-10-06T08:00:00-04:00')

    def test_fresh_coverage_beyond_cutoff_does_not_require_as_of_equality(self):
        checks = {s: replace(v, covered_through='2026-10-06T12:20:00Z') for s, v in self.checks.items()}
        self.assertTrue(self.run_status(checks=checks)['all_enabled_complete'])

    def test_bad_scope_digest_and_status_are_rejected(self):
        for value in ('', None, True, 'a'*63, 'g'*64):
            with self.subTest(value=value), self.assertRaises(ContractError):
                self.run_status(scopes={**self.scopes, 'mail': value})
        with self.assertRaises(ContractError):
            self.run_status(checks={**self.checks, 'mail': replace(self.checks['mail'], status='complete')})

    def test_replay_detached_inputs_immutable_and_no_effects(self):
        before = deepcopy((self.profile, self.scopes, self.checks))
        with patch('builtins.open') as files, patch('socket.socket') as network, patch('subprocess.run') as processes:
            first = self.run_status()
            again = self.run_status(checks=dict(reversed(list(self.checks.items()))))
            files.assert_not_called(); network.assert_not_called(); processes.assert_not_called()
        self.assertEqual(first, again)
        self.assertEqual((self.profile, self.scopes, self.checks), before)
        first['sources']['mail']['evidence_refs'].append('output-only')
        self.assertEqual((self.profile, self.scopes, self.checks), before)


if __name__ == '__main__':
    unittest.main()
