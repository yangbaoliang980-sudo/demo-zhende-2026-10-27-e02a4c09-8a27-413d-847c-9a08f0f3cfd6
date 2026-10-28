"""Static owner/dependency/source rules. This is not P32 or P35 acceptance."""
import ast
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    errors=[]
    registry=json.loads((ROOT/'contracts/internal/internal_api_contracts.json').read_text())
    for ic,owner in {'IC-02':'P13','IC-05':'P14','IC-08':'P13','IC-19':'P21','IC-25':'P32'}.items():
        if registry['interface_owners'].get(ic)!=owner:errors.append('WRONG_CONTRACT_OWNER:'+ic)
    for state,owner in {'BattleState':'P14','BattleState.energy':'P14','BattleState.zones':'P14','Wallet_business':'P17','Game_physical_persistence':'P21','HUD_binding':'P19','Presentation_playback':'P29'}.items():
        if registry['state_writers'].get(state)!=owner:errors.append('WRONG_WRITER:'+state)
    mapping=json.loads((ROOT/'architecture/actual_path_mapping.json').read_text())
    if mapping['production_write_authorized'] or mapping['actual_game_commit'] is not None:errors.append('FALSE_PRODUCTION_MAPPING')
    for entry in mapping['mappings']:
        if entry['owner']!='P13' and (entry['write_allowed'] or entry['actual_production_path'] is not None):errors.append('OTHER_OWNER_WRITE_MAPPING')
    modules={};core=ROOT/'runtime/framework/yltt_framework'
    for p in core.glob('*.py'):
        name='runtime.framework.yltt_framework'+('' if p.name=='__init__.py' else '.'+p.stem)
        modules[name]=p
    edges={name:set() for name in modules}
    banned={'sqlite3','socket','aqt','anki','requests'}
    for name,path in modules.items():
        for node in ast.walk(ast.parse(path.read_text())):
            targets=[]
            if isinstance(node,ast.Import):targets=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                if node.level:
                    pkg=name if path.name=='__init__.py' else name.rsplit('.',1)[0]
                    base='.'.join(pkg.split('.')[:len(pkg.split('.'))-node.level+1])
                    targets=[base+('.'+node.module if node.module else '')]
                elif node.module:targets=[node.module]
            for target in targets:
                if target.split('.')[0] in banned or target.startswith(('runtime.battle.','runtime.meta.','runtime.persistence.','ui.')):
                    errors.append('FORBIDDEN_FRAMEWORK_IMPORT:'+name+':'+target)
                if target in modules:edges[name].add(target)
    visiting=set();done=set()
    def visit(n):
        if n in visiting:errors.append('DEPENDENCY_CYCLE:'+n);return
        if n in done:return
        visiting.add(n)
        for child in edges[n]:visit(child)
        visiting.remove(n);done.add(n)
    for n in edges:visit(n)
    receipt=json.loads((ROOT/'architecture/source_input_receipt.json').read_text())
    for s in receipt['sources']:
        p=ROOT/s['retained_relative_path']
        if p.stat().st_size!=s['size_bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=s['sha256']:errors.append('UPSTREAM_BYTES_CHANGED:'+s['source_id'])
    print(json.dumps({'status':'FAIL' if errors else 'PASS','scope':'AUTHOR_STATIC_ARCHITECTURE_ONLY','interface_owners_checked':5,'runtime_modules_checked':len(modules),'module_import_edges':{k:sorted(v) for k,v in edges.items()},'upstream_files_checked':len(receipt['sources']),'errors':errors,'independent_review':'NOT_RUN'},ensure_ascii=False,indent=2));return 1 if errors else 0

if __name__=='__main__':raise SystemExit(main())
