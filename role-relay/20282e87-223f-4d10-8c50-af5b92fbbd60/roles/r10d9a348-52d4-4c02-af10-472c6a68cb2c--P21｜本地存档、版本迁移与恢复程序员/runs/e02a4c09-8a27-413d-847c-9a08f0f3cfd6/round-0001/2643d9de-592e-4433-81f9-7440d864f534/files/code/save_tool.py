"""P21 operator tool. No lossy restore or reward replay command is exposed."""
import bootstrap  # noqa: F401
import argparse
import json
from p21_persistence import Store,SaveError
from p21_persistence.recovery import inspect_backup,compare_backup,stage_restore,rehearse_migration


def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='action',required=True)
    for name in ['status','verify','lookup','backup','compare','recover-exact','migrate']:
        s=subs.add_parser(name);s.add_argument('--store',required=True);s.add_argument('--anchor',required=True)
        s.add_argument('--instance',required=True)
        if name=='lookup':s.add_argument('--tx',required=True);s.add_argument('--request-sha')
        if name in ('backup','migrate'):s.add_argument('--destination',required=True)
        if name in ('compare','recover-exact'):s.add_argument('--backup',required=True)
    for name in ['inspect-backup','stage-restore','rehearse-migration']:
        s=subs.add_parser(name);s.add_argument('--backup',required=True)
        if name!='inspect-backup':s.add_argument('--destination',required=True)
    a=p.parse_args()
    try:
        if a.action=='inspect-backup':
            manifest,snapshot,_=inspect_backup(a.backup)
            result={'status':'VALID_BACKUP_NOT_AUTHORITY','manifest':manifest,'records':[x.head() for x in snapshot.records.values()]}
        elif a.action=='stage-restore':result=stage_restore(a.backup,a.destination)
        elif a.action=='rehearse-migration':result=rehearse_migration(a.backup,a.destination)
        else:
            store=Store(a.store,a.anchor,expected_store_instance=a.instance)
            if a.action=='status':result=store.status()
            elif a.action=='verify':
                snapshot=store.snapshot();result={'status':'VERIFIED','head':snapshot.anchor(),'records':[r.head() for r in snapshot.records.values()]}
            elif a.action=='lookup':result=store.lookup(a.tx,a.request_sha)
            elif a.action=='backup':result=store.backup(a.destination)
            elif a.action=='compare':result=compare_backup(store,a.backup)
            elif a.action=='recover-exact':result=store.recover_exact(a.backup)
            elif a.action=='migrate':result=store.migrate(a.destination)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 3 if result.get('status') in ('UNKNOWN','STAGED_READ_ONLY') or result.get('state')=='RECOVERY_REQUIRED' else 0
    except SaveError as e:
        print(json.dumps({'status':'BLOCKED' if e.code in ('E_PLATFORM_NOT_PROBED','E_DATA_LOSS_OR_FOREIGN_RESTORE_BLOCKED','E_READER_TOO_OLD','E_MIGRATION_REQUIRED') else 'ERROR','error':e.as_dict()},ensure_ascii=False,indent=2))
        return 3 if e.code in ('E_PLATFORM_NOT_PROBED','E_DATA_LOSS_OR_FOREIGN_RESTORE_BLOCKED','E_READER_TOO_OLD','E_MIGRATION_REQUIRED') else 4


if __name__=='__main__':raise SystemExit(main())
