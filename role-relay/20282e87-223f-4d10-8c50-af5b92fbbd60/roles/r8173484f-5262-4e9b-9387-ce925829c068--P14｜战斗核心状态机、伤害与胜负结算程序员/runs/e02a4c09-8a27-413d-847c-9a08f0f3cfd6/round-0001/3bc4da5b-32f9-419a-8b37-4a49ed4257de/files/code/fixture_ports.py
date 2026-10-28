"""Scripted P15/P16 stand-ins. Never use as a production rules/AI implementation.

Scripts specify exact moves and deltas. They contain no cost calculation,
shuffle, draw selection, target selection or enemy decision algorithm.
"""
from battle_core.ports import CandidateRejected, DependencyUnavailable
from battle_core.wire import FrozenMessage, message


class ScriptedDeck:
    def __init__(self,policy_version,scripts):
        self.policy_version=policy_version
        self.scripts=FrozenMessage.from_value(scripts)
        self.calls=0

    def propose(self,command,snapshot):
        self.calls+=1
        c=command.value; s=snapshot.value
        script=next((x for x in self.scripts.value if x['command_id']==c['command_id']),None)
        if script is None: raise DependencyUnavailable('NO_SCRIPTED_DECK_INPUT')
        if 'reject_code' in script: raise CandidateRejected(script['reject_code'])
        return message('DeckPatchCandidate',battle_id=s['battle_id'],command_id=c['command_id'],
            expected_revision=s['revision'],command_sha256=command.sha256,snapshot_sha256=snapshot.sha256,
            policy_version=self.policy_version,moves=script['moves'],energy_delta=script['energy_delta'],
            rng_before=s['rng'],rng_after=script.get('rng_after',s['rng']))


class ScriptedEnemy:
    def __init__(self,script):
        self.script=FrozenMessage.from_value(script); self.calls=0

    def propose(self,snapshot):
        self.calls+=1
        s=snapshot.value; p=self.script.value
        return message('EnemyIntent',battle_id=s['battle_id'],expected_revision=s['revision'],
            content_version=s['content_version'],**p)


def move(iid,src,dst,index):
    return {'instance_id':iid,'from_zone':src,'to_zone':dst,'to_index':index}
