import copy
import json
import unittest
from mocks.anki_transport.support import Harness, submit, event, query, SCOPE
from runtime.anki.transport.ipc_server_client.protocol import (canonical, decode_request,
    decode_response, strict_json, MAX_FRAME_BYTES, ProtocolError, VERSION, request)

class ParserContractTests(unittest.TestCase):
    def assert_rejected(self, raw, expected):
        with Harness() as h:
            response = decode_response(h.ingress.handle(raw))
            self.assertEqual(response['payload']['disposition'], 'REJECTED')
            self.assertEqual(response['payload']['error_code'], expected)
            self.assertEqual(h.store.snapshot().ledger['inbox'], {})
            self.assertEqual(h.balance, 0)

    def test_valid_event_roundtrip(self):
        value=submit();self.assertEqual(decode_request(canonical(value)),value)

    def test_duplicate_top_level_key(self):
        self.assert_rejected(b'{"protocol":1,"protocol":2}', 'E_JSON_DUPLICATE')

    def test_duplicate_nested_key(self):
        self.assert_rejected(b'{"a":{"x":1,"x":2}}', 'E_JSON_DUPLICATE')

    def test_nonfinite_and_float_and_unsafe_integer(self):
        for raw in [b'{"x":NaN}',b'{"x":Infinity}',b'{"x":1.5}',b'{"x":1e0}',b'{"x":9007199254740992}']:
            with self.subTest(raw=raw):self.assert_rejected(raw,'E_JSON_NUMBER')

    def test_invalid_utf8_bom_surrogate_and_trailing_data(self):
        for raw in [b'\xff',b'\xef\xbb\xbf{}',b'{"x":"\\ud800"}',b'{}{}']:
            with self.subTest(raw=raw):self.assert_rejected(raw,'E_JSON_SYNTAX')

    def test_size_limit(self):
        self.assert_rejected(b'x'*(MAX_FRAME_BYTES+1),'E_FRAME_LIMIT')

    def test_depth_limit_before_decoder(self):
        self.assert_rejected(b'['*13+b'0'+b']'*13,'E_JSON_DEPTH')

    def test_node_limit(self):
        self.assert_rejected(canonical([0]*513),'E_JSON_COMPLEXITY')

    def test_incompatible_versions_have_explicit_rejection(self):
        for version in ['0.0.9','0.1.1-isolated','0.2.0-isolated','1.0.0','0.1.0']:
            with self.subTest(version=version):
                m=submit();m['protocol_version']=version
                self.assert_rejected(canonical(m),'E_PROTOCOL_VERSION')

    def test_unknown_message_protocol_and_payload_version(self):
        for field,value,code in [('message_type','RUN_COMMAND','E_MESSAGE_TYPE'),('protocol','OTHER','E_PROTOCOL')]:
            m=submit();m[field]=value;self.assert_rejected(canonical(m),code)
        m=submit();m['payload']['event']['schema_version']='official';self.assert_rejected(canonical(m),'E_PAYLOAD_VERSION')

    def test_extra_fields_and_privacy_fields_are_closed(self):
        for where,field in [('top','admin'),('event','note_text'),('event','wallet_amount'),('event','raw_revlog_id'),('payload','trusted')]:
            with self.subTest(where=where,field=field):
                m=submit();target=m if where=='top' else m['payload'] if where=='payload' else m['payload']['event'];target[field]='injected'
                self.assert_rejected(canonical(m),'E_SCHEMA')

    def test_nonopaque_references_rejected(self):
        for value in ['../profile.db','C:\\Users\\profile','test\n',' spaced','テスト','a'*129]:
            m=submit();m['payload']['event']['card_reference']=value
            self.assert_rejected(canonical(m),'E_SCHEMA')

    def test_boolean_not_integer_revision(self):
        m=submit();m['payload']['event']['revision']=False
        self.assert_rejected(canonical(m),'E_SCHEMA')

    def test_review_and_control_shapes(self):
        for revision,predecessor,rating,kind in [(1,None,'Good','REVIEW'),(0,None,None,'UNDO'),(1,'review-1','Good','RESTORE')]:
            m=submit();m['payload']['event'].update(revision=revision,predecessor_event_id=predecessor,rating=rating,kind=kind)
            self.assert_rejected(canonical(m),'E_SCHEMA')

    def test_unproven_identity_not_generated_by_transport(self):
        with Harness() as h:
            e=event();e['event_id']=None;e['family_id']=None
            body=h.send(submit(e))['payload']
            self.assertEqual(body['disposition'],'ACK_QUARANTINED');self.assertEqual(h.balance,0)
            row=h.store.snapshot().ledger['inbox'][body['inbox_id']]
            self.assertIsNone(row['event']['event_id']);self.assertIsNone(row['event']['family_id'])

    def test_hello_without_supported_version_rejects(self):
        m=request('HELLO',{'supported_versions':[VERSION]},message_id='a'*32,producer_id='fixture:plugin',scope=SCOPE)
        m['payload']['supported_versions']=['1.0.0'];self.assert_rejected(canonical(m),'E_PROTOCOL_VERSION')

    def test_malformed_ack_missing_commit_rejected_by_client_schema(self):
        with Harness() as h:
            response=h.send(submit());response['payload']['receipt']=None
            with self.assertRaises(ProtocolError):decode_response(canonical(response))

    def test_quarantine_cannot_be_terminal_or_awarded(self):
        with Harness(closed=True) as h:
            r=h.send(submit())
            for field,value in [('delivery_terminal',True),('award_status','APPLIED')]:
                v=copy.deepcopy(r);v['payload'][field]=value
                with self.assertRaises(ProtocolError):decode_response(canonical(v))

if __name__=='__main__':unittest.main(verbosity=2)
