import copy
import hashlib
import os
from pathlib import Path
import socket
import struct
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
import time
import unittest
from mocks.anki_transport.support import Harness, submit, query, pairing, event, control, Q
from runtime.anki.transport.ipc_server_client.protocol import canonical, decode_response, digest, ProtocolError, MAX_FRAME_BYTES
from runtime.anki.transport.ipc_server_client.local import create_key,read_key,private_directory
from runtime.anki.transport.ipc_server_client.wire import (LoopbackAddress,LoopbackClient,LoopbackServer,WireError,
    MAGIC,read_exact,recv_frame,send_frame,mac)
from runtime.anki.transport.ipc_server_client.outbox import Outbox,ClientPump,QueueFull,check_reply

class WireOutboxTests(unittest.TestCase):
    def test_reject_all_nonliteral_loopback_bindings(self):
        for host in ['0.0.0.0','localhost','::','::1','192.168.0.1','127.0.0.2','example.org','']:
            with self.subTest(host=host),self.assertRaises(ValueError):LoopbackAddress(1234,host)

    def test_authenticated_socket_roundtrip_and_readonly_query(self):
        with Harness() as h:
            client=h.start();m=submit();r=client.exchange(canonical(m))
            self.assertEqual(h.server.address.host,'127.0.0.1');self.assertEqual(r['payload']['disposition'],'ACK_APPLIED')
            before=h.store.snapshot();client.exchange(canonical(query()))
            self.assertEqual(before,h.store.snapshot())

    def test_bad_key_closes_before_ledger(self):
        with Harness() as h:
            h.start();bad=LoopbackClient(h.server.address,pairing(bytes(reversed(range(32)))))
            with self.assertRaises(OSError):bad.exchange(canonical(submit()))
            self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_oversized_wire_header_closes_without_body_allocation(self):
        with Harness() as h:
            h.start()
            with socket.create_connection(h.server.address.tuple,timeout=2) as s:
                read_exact(s,len(MAGIC)+32,time.monotonic()+2)
                s.sendall(struct.pack('!I',MAX_FRAME_BYTES+1));self.assertEqual(s.recv(1),b'')
            self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_truncated_frame_does_not_reach_ledger(self):
        with Harness() as h:
            h.start()
            with socket.create_connection(h.server.address.tuple,timeout=2) as s:
                read_exact(s,len(MAGIC)+32,time.monotonic()+2);s.sendall(struct.pack('!I',20)+b'{}');s.shutdown(socket.SHUT_WR)
                self.assertEqual(s.recv(1),b'')
            self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_corrupt_mac_closes_before_parser(self):
        with Harness() as h:
            h.start();raw=canonical(submit())
            with socket.create_connection(h.server.address.tuple,timeout=2) as s:
                read_exact(s,len(MAGIC)+32,time.monotonic()+2)
                s.sendall(struct.pack('!I',len(raw))+raw+b'\x00'*32);self.assertEqual(s.recv(1),b'')
            self.assertEqual(h.store.snapshot().ledger['inbox'],{})

    def test_old_challenge_signature_rejected_on_new_connection(self):
        with Harness() as h:
            h.start();raw=canonical(submit())
            with socket.create_connection(h.server.address.tuple,timeout=2) as s:
                challenge=read_exact(s,len(MAGIC)+32,time.monotonic()+2)
            with socket.create_connection(h.server.address.tuple,timeout=2) as s:
                newer=read_exact(s,len(MAGIC)+32,time.monotonic()+2);self.assertNotEqual(newer,challenge)
                signature=mac(h.pair.secret,MAGIC+b':request:'+challenge[len(MAGIC):],raw)
                s.sendall(struct.pack('!I',len(raw))+raw+signature);self.assertEqual(s.recv(1),b'')
            self.assertEqual(h.balance,0)

    def test_authenticated_malformed_json_gets_rejected_not_silently_dropped(self):
        with Harness() as h:
            c=h.start();r=decode_response(c.exchange_raw(b'{"x":'))
            self.assertEqual(r['payload']['disposition'],'REJECTED');self.assertEqual(r['payload']['error_code'],'E_JSON_SYNTAX')

    def test_fragmented_receive_keeps_frame_boundaries(self):
        left,right=socket.socketpair();secret=bytes(range(32));context=b'test';raw=canonical({'x':123})
        blob=struct.pack('!I',len(raw))+raw+mac(secret,context,raw)
        def writer():
            with left:
                for b in blob:left.sendall(bytes([b]))
        t=Thread(target=writer);t.start()
        with right:self.assertEqual(recv_frame(right,secret,context,time.monotonic()+2),raw)
        t.join(2);self.assertFalse(t.is_alive())

    def test_response_authentication_failure(self):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);port=listener.getsockname()[1]
        def fake():
            with listener:
                c,_=listener.accept()
                with c:
                    nonce=b'n'*32;c.sendall(MAGIC+nonce)
                    raw=recv_frame(c,pairing().secret,MAGIC+b':request:'+nonce,time.monotonic()+2)
                    send_frame(c,b'z'*32,MAGIC+b':response:'+nonce+hashlib.sha256(raw).digest(),b'{}',time.monotonic()+2)
        t=Thread(target=fake);t.start()
        with self.assertRaises(OSError):LoopbackClient(LoopbackAddress(port),pairing()).exchange(canonical(submit()))
        t.join(2);self.assertFalse(t.is_alive())

    def test_parallel_duplicate_clients_award_once(self):
        with Harness() as h:
            h.start();messages=[canonical(submit()) for _ in range(8)]
            def send(raw):return LoopbackClient(h.server.address,h.pair).exchange(raw)
            with ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(send,messages))
            self.assertTrue(all(x['payload']['disposition']=='ACK_APPLIED' for x in r))
            self.assertEqual(h.balance,Q);self.assertEqual(h.store.snapshot().wallet['version'],1)

    def test_lost_ack_outbox_reopens_then_queries_without_reaward(self):
        dropped=[]
        def drop_once(_raw,_reply):
            if not dropped:dropped.append(True);raise WireError('TEST_REPLY_LOSS')
        with Harness() as h:
            c=h.start(before_send=drop_once);p=h.directory/'sender.p12-outbox.sqlite';box=Outbox(p,h.pair);m=submit();mid=box.enqueue(m)
            self.assertEqual(ClientPump(box,c).step(mid,0),'RETRY_WAIT');self.assertEqual(h.balance,Q)
            saved=box.get(mid);box=Outbox(p,h.pair)
            self.assertEqual(box.get(mid)['raw'],canonical(m));self.assertEqual(box.get(mid)['action'],'QUERY')
            self.assertEqual(ClientPump(box,c).step(mid,100000),'SETTLED');self.assertEqual(h.balance,Q)
            self.assertEqual(h.store.snapshot().wallet['version'],1);self.assertEqual(box.get(mid)['raw_sha'],saved['raw_sha'])

    def test_disconnect_before_send_reconnect_queries_then_submits(self):
        with Harness() as h:
            server=LoopbackServer(h.ingress);address=server.address;server.close()
            box=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);mid=box.enqueue(submit())
            c=LoopbackClient(address,h.pair);self.assertEqual(ClientPump(box,c).step(mid,0),'RETRY_WAIT')
            c=h.start();pump=ClientPump(box,c)
            self.assertEqual(pump.step(mid,100000),'RETRY_WAIT');self.assertEqual(box.get(mid)['action'],'SUBMIT')
            self.assertEqual(pump.step(mid,200000),'SETTLED');self.assertEqual(h.balance,Q)

    def test_quarantine_is_retained_and_watched_after_reopen(self):
        with Harness(closed=True) as h:
            c=h.start();path=h.directory/'sender.p12-outbox.sqlite';b=Outbox(path,h.pair);mid=b.enqueue(submit())
            self.assertEqual(ClientPump(b,c).step(mid,0),'WATCHING_QUARANTINE')
            b=Outbox(path,h.pair);row=b.get(mid);self.assertEqual(row['action'],'QUERY');self.assertGreaterEqual(row['due_ms'],30000)
            self.assertEqual(ClientPump(b,c).step(mid,100000),'WATCHING_QUARANTINE');self.assertEqual(h.balance,0)

    def test_outbox_quota_does_not_evict_unconfirmed(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair,max_rows=1);m=submit();mid=b.enqueue(m)
            with self.assertRaises(QueueFull):b.enqueue(submit(event('review-2',family_id='family-2')))
            self.assertEqual(b.get(mid)['raw'],canonical(m))

    def test_outbox_payload_conflict_preserves_first_bytes(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);m=submit();mid=b.enqueue(m)
            changed=copy.deepcopy(m);changed['payload']['event']['rating']='Easy'
            with self.assertRaises(ValueError):b.enqueue(changed)
            self.assertEqual(b.get(mid)['raw'],canonical(m))

    def test_outbox_semantic_duplicate_reuses_original_delivery_id(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);mid=b.enqueue(submit())
            self.assertEqual(b.enqueue(submit()),mid)

    def test_request_and_scope_binding_are_checked_before_settlement(self):
        with Harness() as h:
            m=submit();raw=canonical(m);reply=h.send(m)
            for mutate in ['id','hash','scope','inbox']:
                changed=copy.deepcopy(reply)
                if mutate=='id':changed['message_id']='0'*32
                if mutate=='hash':changed['request_sha256']='0'*64
                if mutate=='scope':changed['scope']['beneficiary_id']='fixture:other'
                if mutate=='inbox':changed['payload']['inbox_id']='0'*64
                with self.assertRaises(ProtocolError):check_reply(raw,changed,h.pair)

    def test_bad_response_leaves_unconfirmed_data(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);m=submit();mid=b.enqueue(m)
            class BadClient:
                def exchange(self,raw):
                    response=h.send(m);response['request_sha256']='0'*64;return response
            self.assertEqual(ClientPump(b,BadClient()).step(mid,0),'RETRY_WAIT')
            self.assertEqual(b.get(mid)['action'],'QUERY');self.assertEqual(b.get(mid)['raw'],canonical(m))

    def test_bounded_retry_budget_and_backoff_keep_data(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);mid=b.enqueue(submit())
            class Down:
                def exchange(self,raw):raise OSError('down')
            pump=ClientPump(b,Down(),request_budget=1);pump.step(mid,0)
            self.assertEqual(pump.step(mid,100000),'BUDGET_EXHAUSTED_DATA_RETAINED')
            self.assertEqual(b.get(mid)['state'],'RETRY_WAIT')
            for attempt in [1,2,10,1000000000]:self.assertTrue(250<=Outbox.delay(mid,attempt)<=60000)

    def test_lease_prevents_simultaneous_sender_attempts(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);mid=b.enqueue(submit());b.begin_attempt(mid,0)
            self.assertIsNone(b.begin_attempt(mid,1));self.assertIsNotNone(b.begin_attempt(mid,10001))

    def test_stale_attempt_cannot_overwrite_newer_result(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);m=submit();mid=b.enqueue(m)
            old=b.begin_attempt(mid,0);new=b.begin_attempt(mid,10001);reply=h.send(m)
            self.assertEqual(b.accept(new,canonical(m),reply,10001),'SETTLED')
            b.network_failed(old,20000);self.assertEqual(b.get(mid)['state'],'SETTLED')
            self.assertEqual(b.accept(old,canonical(m),reply,20000),'STALE_ATTEMPT_IGNORED')

    def test_outbox_corruption_is_not_silently_resubmitted(self):
        with Harness() as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);mid=b.enqueue(submit())
            with b.connect() as c:c.execute('UPDATE messages SET raw=? WHERE message_id=?',(b'corrupt',mid));c.commit()
            with self.assertRaises(ValueError):b.begin_attempt(mid,0)
            self.assertEqual(b.get(mid)['raw'],b'corrupt')

    def test_pairing_key_and_directory_permissions(self):
        with Harness() as h:
            path=create_key(h.directory);self.assertEqual(len(read_key(h.directory)),32)
            os.chmod(path,0o644)
            with self.assertRaises(PermissionError):read_key(h.directory)
            os.chmod(path,0o600);os.chmod(h.directory,0o755)
            try:
                with self.assertRaises(PermissionError):private_directory(h.directory)
            finally:os.chmod(h.directory,0o700)

    def test_symlink_outbox_and_key_are_rejected(self):
        with Harness() as h:
            target=h.directory/'target';target.write_bytes(b'x'*32);os.chmod(target,0o600)
            (h.directory/'pairing.key').symlink_to(target)
            with self.assertRaises(OSError):read_key(h.directory)
            linked=h.directory/'evil.p12-outbox.sqlite';linked.symlink_to(target)
            with self.assertRaises(PermissionError):Outbox(linked,h.pair)

    def test_authority_change_cannot_clear_watched_outbox(self):
        with Harness(closed=True) as h:
            b=Outbox(h.directory/'sender.p12-outbox.sqlite',h.pair);m=submit();mid=b.enqueue(m)
            first=b.begin_attempt(mid,0);reply=h.send(m);b.accept(first,canonical(m),reply,0)
            second=b.begin_attempt(mid,100000);changed=copy.deepcopy(reply)
            changed['payload']['receipt']['store_id_sha256']='0'*64
            with self.assertRaises(ValueError):b.accept(second,canonical(m),changed,100000)
            self.assertEqual(b.get(mid)['raw'],canonical(m))
            self.assertEqual(b.get(mid)['receipt_store'],reply['payload']['receipt']['store_id_sha256'])

    def test_source_scope_change_cannot_reopen_existing_outbox(self):
        from dataclasses import replace
        with Harness() as h:
            path=h.directory/'sender.p12-outbox.sqlite';b=Outbox(path,h.pair);b.enqueue(submit())
            with self.assertRaises(ValueError):Outbox(path,replace(h.pair,beneficiary_id='fixture:other'))

if __name__=='__main__':unittest.main(verbosity=2)
