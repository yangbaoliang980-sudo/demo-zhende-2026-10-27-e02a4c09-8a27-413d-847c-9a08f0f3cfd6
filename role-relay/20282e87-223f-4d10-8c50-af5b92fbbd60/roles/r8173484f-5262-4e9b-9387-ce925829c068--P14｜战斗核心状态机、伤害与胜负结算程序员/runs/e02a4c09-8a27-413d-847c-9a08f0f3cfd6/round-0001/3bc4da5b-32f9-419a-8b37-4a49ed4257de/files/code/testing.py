"""Opt-in inert scripted endpoints for module-isolated tests; never production."""
from .codec import FrozenMessage


class ScriptedEndpoint:
    """Return predefined immutable replies for exact predefined inputs.

    This does not implement a domain state machine, wallet, storage or renderer.
    A next owner can bind call() to its injected read/propose/lookup seam. Any
    unlisted input fails instead of manufacturing a plausible gameplay result.
    """
    def __init__(self, scripts):
        self._scripts={}
        self._calls=[]
        for args,response in scripts:
            if not isinstance(response,FrozenMessage) or any(not isinstance(x,FrozenMessage) for x in args):
                raise TypeError('FROZEN_FIXTURE_REQUIRED')
            key=tuple(x.raw for x in args)
            if key in self._scripts:raise ValueError('DUPLICATE_SCRIPT_INPUT')
            self._scripts[key]=response

    @property
    def calls(self):return tuple(self._calls)

    def call(self,*messages):
        if any(not isinstance(x,FrozenMessage) for x in messages):raise TypeError('FROZEN_FIXTURE_REQUIRED')
        key=tuple(x.raw for x in messages)
        if key not in self._scripts:raise LookupError('UNSCRIPTED_FIXTURE_INPUT')
        self._calls.append(tuple(x.sha256 for x in messages))
        return self._scripts[key]
