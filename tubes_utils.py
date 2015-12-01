
from zope.interface import Interface, implementer
from twisted.internet.defer import Deferred, inlineCallbacks
from tubes.itube import IDrain, IFount
from tubes.kit import Pauser, beginFlowingTo, beginFlowingFrom

from cocotools import coroutine, composable
from bananaphone import changeWordSize


@implementer(IFount)
class CoroutineFount():

    drain = None
    outputType = None

    flowIsPaused = False
    flowIsStopped = False

    def __init__(self, upstreamPauser, outputType=None):

        self._receivedWhilePaused = []
        self._paused = False

        def actuallyPause():
            print "coroutine fount actually pause"
            self._myPause = upstreamPauser.pause()

        def actuallyUnpause():
            print "coroutine fount actually unpause"
            aPause = self._myPause
            self._myPause = None
            if self._receivedWhilePaused:
                for item in self._receivedWhilePaused:
                    self.drain.receive(item)
            aPause.unpause()

        self._pauser = Pauser(actuallyPause, actuallyUnpause)
        self.outputType = outputType

    def flowTo(self, drain):
        print "coroutine fount flow to"
        beginFlowingTo(self, drain)

    def pauseFlow():
        print "coroutine fount pause flow"
        return self._pauser.pause()

    def stopFlow(self):
        print "coroutine fount stop flow"
        self.flowIsStopped = True
        #self.drain.fount.stopFlow()


@implementer(IDrain)
class CoroutineDrain():
    inputType = None
    fount = None

    def __init__(self, coroutine=None, inputType = None):
        self.coroutine = coroutine
        self.inputType = inputType

        self._receivedWhilePaused = []
        self._pause = None
        self._paused = False

        def _actuallyPause():
            print "coroutine drain actually pause"
            if self._paused:
                raise NotImplementedError()
            self._paused = True
            if self.fount is not None:
                self._pause = self.fount.pauseFlow()

        def _actuallyResume():
            print "coroutine drain actually resume"
            p = self._pause
            self._pause = None
            self._paused = False
            if self._receivedWhilePaused:
                for item in self._receivedWhilePaused:
                    self.coroutine.send(item)
            if p is not None:
                p.unpause()

        self._pauser = Pauser(_actuallyPause, _actuallyResume)

    def flowingFrom(self, fount):
        print "coroutine drain flowing from"
        beginFlowingFrom(self, fount)

    def receive(self, item):
        if self.fount is None:
            raise RuntimeError(
                "Invalid state: can't call receive on a drain "
                "when it's got no fount.")

        if self._paused:
            print "receive paused!"
            self._receivedWhilePaused.append(item)
            return
        self.coroutine.send(item)

    def flowStopped(self, reason):
        print "coroutine drain flow stopped"
        #self.fount.drain.flowStopped()


class TubesCoroutinePipeline(object):

    def __init__( self, co ):
        self.coroutine = co > self.sendOutput
        self.drain = CoroutineDrain( coroutine = self.coroutine )
        self.fount = CoroutineFount( self.drain._pauser )
        #self.fount = CoroutineFount()
    def sendOutput(self, item):
        self.fount.drain.receive(item)
