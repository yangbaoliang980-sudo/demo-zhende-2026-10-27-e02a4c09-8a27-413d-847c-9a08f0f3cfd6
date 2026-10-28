"""Re-execute committed inputs; recorded candidates are inputs, never results."""
from .core import BattleCore, ReplayBundle
from .model import Rules
from .ports import DependencyUnavailable
from .wire import FrozenMessage, checked


class RecordedInputs:
    def __init__(self):
        self.remaining=[]

    def select(self,port,basis):
        if not self.remaining:
            raise DependencyUnavailable('REPLAY_INPUT_MISSING')
        entry=self.remaining.pop(0)
        if entry['port']!=port or entry['basis_sha256']!=basis.sha256:
            raise ValueError('REPLAY_INPUT_BASIS_MISMATCH')
        return FrozenMessage.from_value(entry['candidate'])


class RecordedDeck:
    def __init__(self,inputs): self.inputs=inputs
    def propose(self,command,snapshot): return self.inputs.select('P15',snapshot)


class RecordedEnemy:
    def __init__(self,inputs): self.inputs=inputs
    def propose(self,snapshot): return self.inputs.select('P16',snapshot)


def replay(bundle):
    if isinstance(bundle,dict):
        if bundle.get('format')!='P14-REPLAY/0.1.0-isolated':
            raise ValueError('REPLAY_VERSION')
        value=bundle
        bundle=ReplayBundle(FrozenMessage.from_value(value['header']),
                            tuple(FrozenMessage.from_value(e) for e in value['entries']))
        if value['sha256']!=bundle.sha256: raise ValueError('REPLAY_DIGEST_MISMATCH')
    h=bundle.header.value; inputs=RecordedInputs()
    core=BattleCore(h['initial_state'],Rules.from_value(h['rules']),
                   stage_id=h['stage_id'],profile_scope=h['profile_scope'],
                   deck_planner=RecordedDeck(inputs),enemy_planner=RecordedEnemy(inputs))
    for entry in bundle.entries:
        e=entry.value
        if e['fault_code']=='INTERNAL_RESOLUTION_ERROR':
            raise DependencyUnavailable('EXTERNAL_EXCEPTION_REPLAY_REQUIRES_ORIGINAL_CAUSE')
        inputs.remaining=list(e['inputs'])
        call={'USER':core.submit,'SYSTEM':core.submit_system,'ABORT_CAPABILITY':core.abort}[e['channel']]
        reply=call(checked(e['command'],'BattleCommand')).value
        if reply['result']!='COMMITTED' or inputs.remaining:
            raise ValueError('REPLAY_DIVERGED')
        if core.export_replay().entries[-1].raw!=entry.raw:
            raise ValueError('REPLAY_ENTRY_DIVERGED')
    if core.export_replay().sha256!=bundle.sha256: raise ValueError('REPLAY_DIVERGED')
    return core
