import argparse,json,hashlib
from examples.demo import run_demo
from .wire import canonical


def main():
    parser=argparse.ArgumentParser(description='P14 isolated, no-render, scripted-input demo')
    parser.add_argument('--digest',action='store_true')
    args=parser.parse_args()
    core,out=run_demo()
    if args.digest:
        print(hashlib.sha256(canonical({'state':core.state().value,'result':core.result().value,
                                      'batches':[b.value for b in core.committed_batches()]})).hexdigest())
    else:
        print(json.dumps({'scope':out['scope'],'outcome':out['snapshot']['outcome'],
            'revision':out['snapshot']['revision'],'last_event_seq':out['snapshot']['last_event_seq'],
            'enemy_action_candidates_consumed':out['p16_calls'],'snapshot':out['snapshot'],
            'result':out['result'],'replay_sha256':out['replay']['sha256']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
