
from twisted.trial.unittest import SynchronousTestCase
from twisted.python.failure import Failure
from tubes.test.util import FakeFount, FakeDrain
from tubes.tube import series

from bananaphone import changeWordSize, parseEncodingSpec, toBytes
from tubes_utils import CoroutineDrain, CoroutineFount, fount2Coroutine2Fount


class CoCoTubeDrainTests(SynchronousTestCase):

    def test_drain_changeWordSize(self):
        res = []
        co = changeWordSize( 8, 1 ) > res.append
        coDrain = CoroutineDrain( co )
        ff = FakeFount()
        ff.flowTo(coDrain)
        for item in [255, 18]:
            ff.drain.receive(item)
        self.assertEqual(res, [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0])

    def test_drain_toBytes(self):
        res = []
        ff = FakeFount()
        co = toBytes > res.append
        coDrain = CoroutineDrain( co )
        ff.flowTo(coDrain)
        ff.drain.receive("hello")
        self.assertEqual(res, ['h', 'e', 'l', 'l', 'o'])

    def test_fount_coroutine_pipeline(self):
    
        fount = FakeFount()
        drain = FakeDrain()

        co = changeWordSize( 8, 1 )
        tube_series = fount.flowTo(series(co.toTube(), drain))

        for item in [255, 18]:
            fount.drain.receive(item)

        self.assertEqual(drain.received, [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0])
