"""Executable P13 wiring demonstration using inert, labelled canned DTOs."""
import json
from pathlib import Path
from .codec import FrozenMessage, fingerprint
from .contracts import validate
from .host import CommandMailbox
from .ports import PortRegistry, require_isolated
from .sequence import BattleStreamGuard

ROOT=Path(__file__).resolve().parents[3]


def fixture(name):
    return json.loads((ROOT/'contracts/internal/examples'/f'{name}.json').read_text())


class CannedPort:
    """No gameplay implementation: accepts exactly one known fixture's bytes."""
    def __init__(self):self.seen=[]
    def submit(self,message):
        self.seen.append(message.sha256)
        if message.raw!=validate(fixture('BattleCommand')).raw:
            raise ValueError('UNSCRIPTED_FIXTURE_INPUT')
        return validate(fixture('BattleReply'))


def main():
    require_isolated()
    command=validate(fixture('BattleCommand'))
    source_before=fingerprint(fixture('BattleSnapshot'))
    port=CannedPort();registry=PortRegistry();registry.bind('battle','P14',port);registry.freeze()
    host=CommandMailbox(registry.get('battle').submit,capacity=2)
    queued=host.post(command.raw); delivered=host.drain()
    response=delivered[0].response
    if response is None:raise RuntimeError(delivered[0].status)
    stream=BattleStreamGuard();stream.rebase(validate(fixture('BattleSnapshot')))
    result=stream.offer(validate(response.value['commit']))
    replay=stream.offer(validate(response.value['commit']))
    assert result.disposition=='ACCEPT' and replay.disposition=='DUPLICATE'
    assert source_before==fingerprint(fixture('BattleSnapshot'))
    print(json.dumps({'mode':'ISOLATED_CANNED_DTO_ONLY','queued':queued.status,
        'delivery':delivered[0].status,'stream':result.disposition,'replay':replay.disposition,
        'input_snapshot_unchanged':True,'battle_logic_executed':False,
        'wallet_business_executed':False,'rendering_executed':False,
        'real_anki_events':0,'production_integration':'NOT_RUN'},indent=2))


if __name__=='__main__':main()
