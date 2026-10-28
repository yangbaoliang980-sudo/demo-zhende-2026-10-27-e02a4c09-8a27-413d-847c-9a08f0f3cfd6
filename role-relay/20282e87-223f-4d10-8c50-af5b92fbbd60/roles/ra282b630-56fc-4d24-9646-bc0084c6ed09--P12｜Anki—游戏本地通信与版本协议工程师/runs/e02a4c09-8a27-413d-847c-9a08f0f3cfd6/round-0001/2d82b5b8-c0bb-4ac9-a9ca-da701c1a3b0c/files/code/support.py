"""Only synthetic test wiring. Original P11 bytes live in sources/P11/."""
from pathlib import Path
import sys
import tempfile
import uuid
import os
from threading import Event as StopEvent, Thread
ROOT = Path(__file__).resolve().parents[2]
P11_ROOT = ROOT / 'sources/P11'
sys.path.insert(0, str(P11_ROOT))
from ledger_runtime.service import StudyLedger
from tests.support.sqlite_atomic_model import SQLiteAtomicModel
from tests.support.simulated_ports import (FixtureEvidence, FixturePolicy, FixtureWallet,
                                           event, control, UNIT, Q)
from runtime.anki.transport.ipc_server_client.protocol import canonical, digest, request
from runtime.anki.transport.ipc_server_client.bridge import Pairing, P11Bridge, GameIngress
from runtime.anki.transport.ipc_server_client.wire import LoopbackServer, LoopbackClient

SCOPE = {'source_id':'fixture:source','collection_lineage':'fixture:lineage','beneficiary_id':'fixture:player'}
# Public test fixture only; process demo instead creates a random private key.
TEST_KEY = bytes(range(32))

def pairing(secret=TEST_KEY):
    return Pairing('fixture:plugin', **SCOPE, secret=secret)


def submit(e=None, mid=None):
    return request('SUBMIT_EVENT', {'event':event() if e is None else e},
                   message_id=mid or uuid.uuid4().hex, producer_id='fixture:plugin', scope=dict(SCOPE))


def query(e=None, inbox=None):
    return request('QUERY_STATUS', {'inbox_id':inbox or digest(event() if e is None else e)},
                   message_id=uuid.uuid4().hex, producer_id='fixture:plugin', scope=dict(SCOPE))


class Harness:
    def __init__(self, directory=None, *, closed=False, fault=None, hard_exit=False, secret=TEST_KEY):
        self.temp = tempfile.TemporaryDirectory(prefix='p12-test-') if directory is None else None
        self.directory = Path(self.temp.name if self.temp else directory)
        os.chmod(self.directory, 0o700)
        (self.directory/'.P11_SIMULATION_ONLY').touch()
        self.store = SQLiteAtomicModel(self.directory/'game.p11-sim.sqlite', fault=fault, hard_exit=hard_exit)
        self.wallet, self.policy, self.evidence = FixtureWallet(), FixturePolicy(), FixtureEvidence()
        self.ledger = StudyLedger(self.store, self.wallet, None if closed else self.evidence,
                                 None if closed else self.policy)
        self.pair = pairing(secret)
        self.bridge = P11Bridge(self.ledger, self.store, SCOPE)
        self.ingress = GameIngress(self.pair, self.bridge)
        self.server, self.stop, self.thread = None, None, None

    def send(self, message):
        import json
        return json.loads(self.ingress.handle(canonical(message)))

    @property
    def balance(self):
        return self.store.snapshot().wallet['balances'].get(UNIT, 0)

    def start(self, **kwargs):
        self.server = LoopbackServer(self.ingress, **kwargs)
        self.stop = StopEvent()
        self.thread = Thread(target=self.server.serve, args=(self.stop,), daemon=True)
        self.thread.start()
        return LoopbackClient(self.server.address, self.pair)

    def close(self):
        if self.server:
            self.stop.set(); self.server.close(); self.thread.join(3)
            if self.thread.is_alive():
                raise RuntimeError('SERVER_THREAD_DID_NOT_STOP')
        if self.temp:
            self.temp.cleanup()

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
