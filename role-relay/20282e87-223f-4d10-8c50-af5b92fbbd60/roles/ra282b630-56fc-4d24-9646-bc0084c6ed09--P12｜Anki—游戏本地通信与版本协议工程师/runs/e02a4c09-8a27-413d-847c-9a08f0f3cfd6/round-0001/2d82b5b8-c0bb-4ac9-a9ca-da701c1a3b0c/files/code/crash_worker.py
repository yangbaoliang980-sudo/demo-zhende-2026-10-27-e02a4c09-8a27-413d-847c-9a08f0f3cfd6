"""Actual disposable child-process fault injection; never takes real data."""
import os
import sys
from ledger_runtime import StudyLedger
from ledger_runtime.types import canonical
from tests.support.simulated_ports import FixtureWallet, FixturePolicy, FixtureEvidence, event
from tests.support.sqlite_atomic_model import SQLiteAtomicModel


def main():
    database, point = sys.argv[1:]
    store = SQLiteAtomicModel(database, fault=point, hard_exit=True)
    service = StudyLedger(store, FixtureWallet(), FixtureEvidence(), FixturePolicy())
    if point == 'after_receive_commit':
        result = service.receive(canonical(event()))
        if result.ack != 'ACK_RECEIVED':
            raise RuntimeError(result.reason)
        os._exit(71)
    service.handle(canonical(event()))
    raise RuntimeError('Fault injection did not trigger')


if __name__ == '__main__':
    main()
