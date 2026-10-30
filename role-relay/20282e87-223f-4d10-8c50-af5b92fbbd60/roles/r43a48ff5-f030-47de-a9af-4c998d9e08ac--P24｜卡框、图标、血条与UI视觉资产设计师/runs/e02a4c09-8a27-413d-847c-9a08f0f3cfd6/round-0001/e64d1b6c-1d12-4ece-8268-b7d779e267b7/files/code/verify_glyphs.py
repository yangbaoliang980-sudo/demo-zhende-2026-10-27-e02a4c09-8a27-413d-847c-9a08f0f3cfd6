#!/usr/bin/env python3
"""Optional author font cmap check, not a shaping or language quality test.

Dependency: fontTools[woff] with Brotli. Output must be outside the package.
"""
import argparse
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
import fontTools
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('output must be a new file outside package')
    files = sorted(p for p in (ROOT/'design/accessibility/fonts').iterdir() if p.suffix in {'.woff2','.ttf'})
    coverages, font_records = [], []
    for path in files:
        with TTFont(path) as font:
            codepoints = set(font.getBestCmap())
        coverages.append(codepoints)
        font_records.append({'path':str(path.relative_to(ROOT)), 'size_bytes':path.stat().st_size,
                             'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'cmap_codepoint_count':len(codepoints)})
    union = set().union(*coverages)
    fixtures = json.loads((ROOT/'design/accessibility/typography_test_strings.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT/'design/ux/wireframe_catalog.json').read_text(encoding='utf-8'))
    required = set()
    samples = []
    for item in fixtures['items']:
        missing = sorted({ord(c) for c in item['text'] if not c.isspace() and ord(c) not in union})
        samples.append({'id':item['id'], 'missing_codepoints':[f'U+{c:04X}' for c in missing]})
        if item['id'] != 'TXT-MISSING-01':
            required.update(ord(c) for c in item['text'] if not c.isspace())
    for board in catalog['items']:
        required.update(ord(c) for text in board['text_boxes'] for c in text['text'] if not c.isspace())
    unexpected = sorted(required-union)
    fixture_missing = next(s['missing_codepoints'] for s in samples if s['id']=='TXT-MISSING-01')
    expected = ['U+20BB7','U+F0000']
    report = {'layer':'AUTHOR_FONT_CMAP_ONLY','observed_utc':datetime.now(timezone.utc).isoformat(),
              'fontTools_version':fontTools.version,'unicode_version':unicodedata.unidata_version,
              'fonts':font_records,'required_distinct_nonspace_codepoints':len(required),
              'fixture_results':samples,'missing_fixture_codepoints':fixture_missing,
              'unexpected_missing_codepoints':[f'U+{c:04X}' for c in unexpected],
              'language_review':'NOT_RUN','shaping_test':'NOT_RUN','screen_reader':'NOT_RUN',
              'result':'PASS_EXPECTED_MISSING_FIXTURE_ONLY' if not unexpected and fixture_missing==expected else 'FAIL'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'missing_fixture':fixture_missing,'unexpected':report['unexpected_missing_codepoints']},ensure_ascii=False))
    return 0 if report['result'].startswith('PASS') else 1


if __name__=='__main__':
    raise SystemExit(main())
