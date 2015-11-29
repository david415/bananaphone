#!/usr/bin/env python

from twisted.internet.endpoints import clientFromString, serverFromString
from twisted.internet.task import react
from twisted.internet.defer import Deferred, inlineCallbacks

from tubes.listening import Listener
from tubes.protocol import flowFountFromEndpoint, flowFromEndpoint
from tubes.kit import Pauser, beginFlowingFrom, beginFlowingTo, OncePause

import argparse
import sys


@inlineCallbacks
def main(reactor):

    servers = None
    clients = None
    num_servers = 0

    parser = argparse.ArgumentParser(description='tubes_cat.py - proxy between any two Twisted endpoints')
    parser.add_argument("-c", "--client", action='append', default=[], help="Twisted client endpoint descriptor string")
    parser.add_argument("-s", "--server", action='append', default=[], help="Twisted server endpoint descriptor string")
    args = parser.parse_args()

    if (len(args.server) + len(args.client)) != 2:
        parser.print_help()
        sys.exit(1)

    server_founts = []
    for endpointDescriptor in args.server:
        serverEndpoint = serverFromString(reactor, endpointDescriptor)
        flowFount = yield flowFountFromEndpoint(serverEndpoint)
        server_founts.append(flowFount)
    client_flows = []
    for endpointDescriptor in args.client:
        clientEndpoint = clientFromString(reactor, endpointDescriptor)
        flow = yield flowFromEndpoint(clientEndpoint)
        client_flows.append(flow)

    if len(server_founts) == 1:
        print "meow1"
        server_founts[0].fount.flowTo(client_flows[0].drain)
        client_flows[0].fount.flowTo(server_founts[0].drain)
    elif len(server_founts) == 2:
        print "meow2"
        a = server_founts[0]
        b = server_founts[1]
        a.flowTo(Listener(lambda x: x.fount.flowTo(b.drain)))
        b.flowTo(Listener(lambda y: y.fount.flowTo(a.drain)))
    else: # 2 client endpoints
        print "meow3"
        dl = defer.DeferredList(client_flows_d)
        def print_results(result):
            print "result"
            print result

    yield Deferred()

if __name__ == '__main__':
    react(main)
