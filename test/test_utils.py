
from zope.interface import implementer

from twisted.trial.unittest import SynchronousTestCase, TestCase
from twisted.python.failure import Failure
from twisted.internet.interfaces import IStreamClientEndpoint, IStreamServerEndpoint
from twisted.test import proto_helpers
from twisted.internet import defer

from tubes.test.util import FakeFount, FakeDrain
from tubes.tube import series

from bananaphone import changeWordSize, parseEncodingSpec, toBytes, reverse_hash_proxy
from tubes_utils import CoroutineDrain, CoroutineFount, TubesCoroutinePipeline


class CoCoTubeDrainTests(SynchronousTestCase):

    def test_drain_changeWordSize(self):

        ff = FakeFount()
        fd = FakeDrain()

        co = changeWordSize( 8, 1 )
        pipe = TubesCoroutinePipeline( co )

        ff.flowTo(pipe.drain)
        pipe.fount.flowTo(fd)

        for item in [255, 18]:
            ff.drain.receive(item)

        self.assertEqual(fd.received, [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0])

@implementer(IStreamClientEndpoint)
class FakeClientEndpoint(object):

    def __init__(self):
        self.transport = None

    def connect(self, fac):
        self.factory = fac
        self.proto = fac.buildProtocol(None)
        transport = proto_helpers.StringTransport()
        self.proto.makeConnection(transport)
        self.transport = transport
        return defer.succeed(self.proto)

@implementer(IStreamServerEndpoint)
class FakeServerEndpoint(object):

    def __init__(self):
        self.transport = None

    def listen(self, fac):
        self.factory = fac
        self.proto = fac.buildProtocol(None)
        transport = proto_helpers.StringTransport()
        self.proto.makeConnection(transport)
        self.transport = transport
        return defer.succeed(self.proto)

class TubeEndpointProxyTests(TestCase):
    def test_tube_proxy(self):
        clientEndpoint = FakeClientEndpoint()
        serverEndpoint = FakeServerEndpoint()

        polarity = "left"
        encodingSpec = [ "words", "sha1", 2 ]
        model = "markov"
        filename = "/usr/share/dict/words" # XXX

        args = [model, filename] + encodingSpec
        print "args"
        print args
        reverse_hash_proxy(serverEndpoint, clientEndpoint, polarity, *args)
