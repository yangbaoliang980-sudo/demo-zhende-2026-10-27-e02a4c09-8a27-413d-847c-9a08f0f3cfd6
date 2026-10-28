"""Only a production preflight is exposed. This is not a daemon or IPC server."""
import argparse
import json
from pathlib import Path
import sys

from .types import byte_digest, strict_json


def preflight(root):
    receipt = strict_json((root/'source_input_receipt.json').read_bytes())
    failures = []
    for item in receipt['consumed_files']:
        path = root/item['relative_path']
        if (not path.is_file() or path.stat().st_size != item['size_bytes'] or
                byte_digest(path.read_bytes()) != item['sha256']):
            failures.append(item['relative_path'])
    if failures:
        return {'status':'FAIL','reason':'SOURCE_BYTES_CHANGED','files':failures}, 1
    p10 = strict_json((root/'sources/P10/QUARANTINED.json').read_bytes())
    p08 = strict_json((root/'sources/P08/policy_record.proposal.json').read_bytes())
    p09 = strict_json((root/'sources/P09/mapping_release_registry.json').read_bytes())
    blockers = strict_json((root/'formal_prerequisites.json').read_bytes())
    result = {'schema_version':'P11-PREFLIGHT/0.1.0','status':'BLOCKED',
              'production_adapters_implemented':False,'production_enable_switch':False,
              'real_review_samples_received':p10['real_review_sample_count'],
              'p10_identity':p10['review_event_identity'],
              'p08_policy_status':p08['policy_status'],
              'p09_active_production_version':p09['active_production_version'],
              'actual_path_mapping':None,'actual_production_awards':0,
              'missing_artifacts':blockers['checks'],
              'formal_contract':'NOT_RUN','target_runtime':'NOT_RUN','real_anki_e2e':'NOT_RUN',
              'p32_independent':'NOT_RUN','p35_independent':'NOT_RUN'}
    # Updating a bool in a proposal cannot turn this isolated package into a production adapter.
    return result, 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preflight'])
    parser.parse_args()
    value, exit_code = preflight(Path(__file__).resolve().parents[1])
    print(json.dumps(value,ensure_ascii=False,indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
