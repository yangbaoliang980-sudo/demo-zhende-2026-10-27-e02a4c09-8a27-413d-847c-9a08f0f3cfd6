// Independent JavaScript canonicalization for fixed cross-language vectors.
// This is test tooling, not a game runtime or a general JSON canonicalizer.
const fs = require('fs');
const crypto = require('crypto');
const path = require('path');
function stable(v) {
  if (v === null || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'number') {
    if (!Number.isSafeInteger(v)) throw Error('NON_SAFE_INTEGER');
    return JSON.stringify(v);
  }
  if (typeof v === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '['+v.map(stable).join(',')+']';
  if (typeof v === 'object') return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';
  throw Error('UNSUPPORTED_VALUE');
}
const root=path.resolve(__dirname,'../..');
const vectors=JSON.parse(fs.readFileSync(path.join(root,'contracts/internal/canonical_vectors.json'),'utf8'));
const results=vectors.cases.map(c=>{const actual=stable(c.value);const sha256=crypto.createHash('sha256').update(actual,'utf8').digest('hex');return {id:c.id,pass:actual===c.canonical_utf8 && sha256===c.sha256,sha256};});
const result={status:results.every(r=>r.pass)?'PASS':'FAIL',scope:'AUTHOR_CROSS_LANGUAGE_CODEC_ONLY',node:process.version,cases:results};
process.stdout.write(JSON.stringify(result,null,2)+'\n');process.exitCode=result.status==='PASS'?0:1;
