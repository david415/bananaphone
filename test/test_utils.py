
from zope.interface import implementer
import collections

from twisted.trial.unittest import SynchronousTestCase, TestCase
from twisted.python.failure import Failure
from twisted.internet.interfaces import IStreamClientEndpoint, IStreamServerEndpoint, IAddress, IListeningPort, IProtocolFactory, ILoggingContext
from twisted.internet.protocol import Factory
from twisted.test import proto_helpers
from twisted.internet import defer, reactor
from twisted.internet.endpoints import clientFromString, serverFromString

from tubes.test.util import FakeFount, FakeDrain, fakeEndpointWithPorts, StringEndpoint
from tubes.tube import series
from tubes.protocol import flowFountFromEndpoint
from tubes.listening import Listener

from bananaphone import changeWordSize, parseEncodingSpec, toBytes, reverse_hash_proxy, reverse_hash_proxy_flows
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

    def create_reverse_hash_pipe(self, polarity):
        server_ff = FakeFount()
        server_fd = FakeDrain()
        serverFlow = collections.namedtuple('server_flow', 'drain fount')
        serverFlow.drain = server_fd
        serverFlow.fount = server_ff

        client_ff = FakeFount()
        client_fd = FakeDrain()
        clientFlow = collections.namedtuple('client_flow', 'drain fount')
        clientFlow.drain = client_fd
        clientFlow.fount = client_ff

        encodingSpec = "words,sha1,2"
        model = "markov"
        filename = "/usr/share/dict/words" # XXX
        args = [encodingSpec, model, filename]

        reverse_hash_proxy_flows(serverFlow, clientFlow, polarity, *args)
        return serverFlow, clientFlow

    def test_reverse_hash_pipe(self):
        a_server_flow, a_client_flow = self.create_reverse_hash_pipe("left")
        b_server_flow, b_client_flow = self.create_reverse_hash_pipe("right")

        a_server_flow.drain.fount.flowTo(b_client_flow.fount.drain)

        for item in ["crypto", "hash"]:
            a_client_flow.fount.drain.receive(item)

        self.assertEqual(b_server_flow.drain.received, ['c', 'r', 'y', 'p', 't', 'o', 'h', 'a', 's', 'h'])

@implementer(IStreamClientEndpoint)
class FakeClientEndpoint(object):

    def __init__(self, transport = None):
        self.transport = transport

    def connect(self, fac):
        self.factory = fac
        self.proto = fac.buildProtocol(None)
        if self.transport is None:
            self.transport = proto_helpers.StringTransport()
        self.proto.makeConnection(self.transport)
        return defer.succeed(self.proto)

@implementer(IAddress)
class FakeAddress(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

@implementer(IListeningPort)
class FakeListeningPort(proto_helpers.StringTransport):
    def startListening(self):
        self.proto = self.factory.buildProtocol(None)
        self.proto.makeConnection(self)

    def stopListening(self):
        return defer.succeed(None)
    def getHost(self):
        return FakeAddress('myhost', 8899)

@implementer(IStreamServerEndpoint)
class FakeServerEndpoint(object):

    def __init__(self):
        self.transport = None

    def listen(self, fac):
        self.listening_port = FakeListeningPort()
        self.listening_port.factory = fac
        return defer.succeed(self.listening_port)

@implementer(IProtocolFactory, ILoggingContext)
class FakeFactory():
    protocol = None
    numPorts = 0
    noisy = True
    protocolConnectionMade = None

    def logPrefix(self):
        """
        Describe this factory for log messages.
        """
        return self.__class__.__name__


    def doStart(self):
        """Make sure startFactory is called.

        Users should not call this function themselves!
        """
        if not self.numPorts:
            if self.noisy:
                _logFor(self).info("Starting factory {factory!r}",
                                   factory=self)
            self.startFactory()
        self.numPorts = self.numPorts + 1

    def doStop(self):
        """Make sure stopFactory is called.

        Users should not call this function themselves!
        """
        if self.numPorts == 0:
            # this shouldn't happen, but does sometimes and this is better
            # than blowing up in assert as we did previously.
            return
        self.numPorts = self.numPorts - 1
        if not self.numPorts:
            if self.noisy:
                _logFor(self).info("Stopping factory {factory!r}",
                                   factory=self)
            self.stopFactory()

    def startFactory(self):
        """This will be called before I begin listening on a Port or Connector.

        It will only be called once, even if the factory is connected
        to multiple ports.

        This can be used to perform 'unserialization' tasks that
        are best put off until things are actually running, such
        as connecting to a database, opening files, etcetera.
        """
        print "fake factory startFactory"
        protocolConnectionMade = defer.succeed(None)

    def stopFactory(self):
        """This will be called before I stop listening on all Ports/Connectors.

        This can be overridden to perform 'shutdown' tasks such as disconnecting
        database connections, closing files, etc.

        It will be called, for example, before an application shuts down,
        if it was connected to a port. User code should not call this function
        directly.
        """
        print "fake factory stopFactory"

    def buildProtocol(self, addr):
        """
        Create an instance of a subclass of Protocol.

        The returned instance will handle input on an incoming server
        connection, and an attribute "factory" pointing to the creating
        factory.

        Alternatively, C{None} may be returned to immediately close the
        new connection.

        Override this method to alter how Protocol instances get created.

        @param addr: an object implementing L{twisted.internet.interfaces.IAddress}
        """
        p = self.protocol()
        p.factory = self
        return p


class FakeEndpointTests(TestCase):
    def test_all_the_fake_things(self):
        """
        Test that all of our fake objects actually work properly.
        """
        self.serverEndpoint = FakeServerEndpoint()
        self.server_factory = FakeFactory()
        self.server_factory.protocol = proto_helpers.AccumulatingProtocol
        self.server_factory.protocol.protocolConnectionMade = True

        d = self.serverEndpoint.listen(self.server_factory)
        self.listening_port = None
        def got_listener(port):
            self.listening_port = port
        d.addCallback(got_listener)
        def make_connection(result):
            self.clientEndpoint = FakeClientEndpoint( transport = self.listening_port )
            self.client_factory = FakeFactory()
            self.client_factory.protocol = proto_helpers.AccumulatingProtocol
            self.client_factory.protocol.protocolConnectionMade = True
            d2 = self.clientEndpoint.connect(self.client_factory)
        d.addCallback(make_connection)
        def client_send_some_data(result):
            self.client_factory.transport.write("hello")
        def check_received(result):
            self.assertEqual(self.client_factory.transport.value(), 'hello')
            self.assertEqual(self.server_factory.transport.value(), 'hello')
        return d

class FakeTubeTests(SynchronousTestCase):

    def test_tubes_server(self):
        endpoint, ports = fakeEndpointWithPorts()
        #self.serverEndpoint = FakeServerEndpoint()
        deferred = flowFountFromEndpoint(endpoint)
        deferred.callback(None)
        result = self.successResultOf(deferred)

        connected = []
        result.flowTo(Listener(connected.append))
        protocol = ports[0].factory.buildProtocol(None)

        self.assertEqual(len(connected), 0)
        protocol.makeConnection(proto_helpers.StringTransport())
        self.assertEqual(len(connected), 1)
        print connected[0]

        ff = FakeFount()
        fd = FakeDrain()

        ff.flowTo(connected[0].drain)
        connected[0].fount.flowTo(fd)

        for item in ["meow1", "meow2"]:
            ff.drain.receive(item)
        self.assertEqual(protocol.transport.value(), "meow1meow2")

        for item in ["meow3", "meow4"]:
            connected[0].fount.drain.receive(item)
        self.assertEqual(fd.received, ["meow3", "meow4"])

class TubeEndpointProxyTests(TestCase):
    """
    def test_tube_proxy1(self):
        test_server_endpoint = serverFromString(reactor, "tcp:interface=127.0.0.1:9977")
        factory = Factory()
        factory.protocolConnectionMade = None
        Factory.protocol = proto_helpers.AccumulatingProtocol
        d = test_server_endpoint.listen(factory)

        def setup_proxy(result):
            clientEndpoint = clientFromString(reactor, "tcp:127.0.0.1:9977")
            serverEndpoint = serverFromString(reactor, "tcp:interface=127.0.0.1:9988")
            polarity = "left"
            encodingSpec = [ "words", "sha1", 2 ]
            model = "markov"
            filename = "/usr/share/dict/words" # XXX
            args = [model, filename] + encodingSpec
            d2 = reverse_hash_proxy(serverEndpoint, clientEndpoint, polarity, *args)
            return d2
        d.addCallback(setup_proxy)

        def connect_to_proxy(result):
            test_client_endpoint = clientFromString(reactor, "tcp:127.0.0.1:9988")
            self.client_factory = Factory()
            self.client_factory.protocolConnectionMade = None
            self.client_factory.protocol = proto_helpers.AccumulatingProtocol
            d3 = test_client_endpoint.connect(self.client_factory)
            return d3
        d.addCallback(connect_to_proxy)
        def send_stuff(ignore):
            self.client_factory.protocol.transport.write("hello")
        d.addCallback(send_stuff)
        return d
    """
