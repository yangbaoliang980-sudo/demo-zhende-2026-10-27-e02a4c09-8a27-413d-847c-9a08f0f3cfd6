#!/usr/bin/env python3
"""P22 read-only content CLI. All writes are new report directories."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from p22_content.io import ContentError,read_json,read_bytes,parse_tsv,json_bytes,publish_new_directory,sha256
from p22_content.pipeline import validate,output_files,REGISTRY_COLUMNS
from p22_content.schema import SchemaBank
from p22_content.assets import check_assets
from p22_content.migration import migrate_manifest,validate_id_map,compare_registry,MIGRATION_COLUMNS

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ['lint','preflight']:
        p=sub.add_parser(name);p.add_argument('--output',type=Path)
        if name=='lint':p.add_argument('--profile',choices=['candidate','production'],default='candidate')
    p=sub.add_parser('migrate-manifest');p.add_argument('--input',required=True);p.add_argument('--output',required=True,type=Path)
    p=sub.add_parser('assets');p.add_argument('--catalog',required=True);p.add_argument('--asset-root',type=Path);p.add_argument('--output',type=Path)
    p=sub.add_parser('id-map');p.add_argument('--map',default='content/manifest/id_migration_map.tsv');p.add_argument('--registry',default='content/manifest/content_id_registry.tsv');p.add_argument('--previous');p.add_argument('--output',type=Path)
    p=sub.add_parser('negative-samples');p.add_argument('--output',type=Path)
    args=parser.parse_args(argv);root=args.root.resolve()
    try:
        if args.command in ['lint','preflight']:
            profile='production' if args.command=='preflight' else args.profile
            report=validate(root,profile);files=output_files(report);rc=report['exit_code']
            summary={k:report[k] for k in ['validator_version','structural_status','reference_status','production_gate','summary','exit_code']}
            if report['summary']['errors']:summary['errors']=[e for e in report['issues'] if e['severity']=='ERROR']
        elif args.command=='migrate-manifest':
            bank=SchemaBank(root);original=read_bytes(root,args.input);data=read_json(root,args.input);migrated,audit=migrate_manifest(data,bank)
            audit['source_raw_sha256']=sha256(original);files={'original_manifest.json':original,'content_manifest.json':json_bytes(migrated),'migration_audit.json':json_bytes(audit)};summary=audit;rc=0
        elif args.command=='assets':
            bank=SchemaBank(root);report=check_assets(args.asset_root or root,read_json(root,args.catalog),bank);files={'asset_check_report.json':json_bytes(report)};summary=report;rc=0 if report['status']=='PASS' else 2
        elif args.command=='id-map':
            bank=SchemaBank(root)
            registry=parse_tsv(read_bytes(root,args.registry),{k:'boolean' if k=='production_allowed' else 'string' for k in REGISTRY_COLUMNS},args.registry)
            rows=parse_tsv(read_bytes(root,args.map),{k:'string' for k in MIGRATION_COLUMNS},args.map)
            report=validate_id_map(registry,rows,bank)
            if args.previous:
                previous=parse_tsv(read_bytes(root,args.previous),{k:'boolean' if k=='production_allowed' else 'string' for k in REGISTRY_COLUMNS},args.previous)
                previous_errors=bank.errors('schema/content/id_registry.schema.json',previous)
                report['evolution']={'status':'FAIL','issues':previous_errors,'applied':False} if previous_errors else compare_registry(previous,registry)
                if report['evolution']['status']=='FAIL':report['status']='FAIL'
            files={'id_migration_check.json':json_bytes(report)};summary=report;rc=0 if report['status']=='PASS' else 2
        else:
            from p22_content.samples import run_samples
            report=run_samples(root);files={'negative_samples_result.json':json_bytes(report)};summary=report;rc=0 if report['status']=='PASS' else 2
        if args.output:publish_new_directory(args.output,files,protected_root=root)
        print(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True));return rc
    except ContentError as e:
        print(json.dumps({'code':e.code,'file':e.path,'pointer':e.pointer,'message':e.message,'status':'BLOCKED' if e.code.startswith('B_') else 'FAIL'},ensure_ascii=False),file=sys.stderr)
        return 3 if e.code.startswith('B_') else 2
    except OSError as e:
        print(json.dumps({'code':'E_IO','status':'FAIL','message':str(e)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
