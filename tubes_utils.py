
from zope.interface import Interface, implementer
from twisted.internet.defer import Deferred, inlineCallbacks
from tubes.itube import IDrain, IFount
from tubes.kit import Pauser, beginFlowingTo, beginFlowingFrom

from cocotools import coroutine, composable
from bananaphone import changeWordSize


## --> thanks to habnabit for these two higher order functions
def tubeFilter(pred):
    @receiver()
    def received(item):
        if pred(item):
            yield item
    return series(received)

def tubeMap(func):
    @receiver()
    def received(item):
        yield func(item)
    return series(received)
## <--

@implementer(IFount)
class CoroutineFount():

    drain = None
    outputType = None

    flowIsPaused = False
    flowIsStopped = False

    def __init__(self, outputType=None):
        self._pauser = Pauser(self._actuallyPause, self._actuallyResume)
        self.outputType = outputType

    def send_item(self, item):
        # XXX handle pause/resume here?
        self.drain.receive(item)

    def flowTo(self, drain):
        beginFlowingTo(self, drain)

    def pauseFlow():
        return self._pauser.pause()

    def _actuallyPause(self):
        self.flowIsPaused = True

    def _actuallyResume(self):
        self.flowIsPaused = False

    def stopFlow(self):
        self.flowIsStopped = True
        self.drain.fount.stopFlow()

@implementer(IDrain)
class CoroutineDrain():
    inputType = None
    fount = None

    def __init__(self, coroutine=None, inputType = None):
        self.coroutine = coroutine
        self.inputType = inputType

    def flowingFrom(self, fount):
        beginFlowingFrom(self, fount)

    def receive(self, item):
        if self.fount is None:
            raise RuntimeError(
                "Invalid state: can't call receive on a drain "
                "when it's got no fount.")
        self.coroutine.send(item)
        
    def flowStopped(reason):
        self.fount.drain.flowStopped(reason)

def fount2Coroutine2Fount(fount, co):
    drain = CoroutineDrain( co )
    coFount = CoroutineFount()
    co > coFount.send_item
    fount.flowTo(drain)
    return coFount
