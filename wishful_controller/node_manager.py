import logging
import time
import sys
import wishful_framework as msgs

__author__ = "Piotr Gawlowicz"
__copyright__ = "Copyright (c) 2015, Technische Universitat Berlin"
__version__ = "0.1.0"
__email__ = "gawlowicz@tkn.tu-berlin.de"


class Group(object):
    def __init__(self, name):
        self.name = name
        self.uuid = str(uuid.uuid4())
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def remove_node(self,node):
        self.nodes.remove(node)


class Node(object):
    def __init__(self,msg):
        self.id = str(msg.agent_uuid)
        self.ip = str(msg.ip)
        self.name = str(msg.name)
        self.info = str(msg.info)
        self.modules = {}
        self.functions = {}
        self.interfaces = {}
        self.iface_to_modules = {}

        for module in msg.modules:
            self.modules[module.id] = str(module.name)
            for func in module.functions:
                if module.id not in self.functions:
                    self.functions[module.id] = [str(func.name)]
                else:
                    self.functions[module.id].append(str(func.name))

        for iface in msg.interfaces:
            self.interfaces[iface.id] = str(iface.name)
            for module in iface.modules:
                if iface.id in self.iface_to_modules:
                    self.iface_to_modules[iface.id].append(str(module.id))
                else:
                    self.iface_to_modules[iface.id] = [str(module.id)]

    def __str__(self):
        print "ID:", self.id
        print "IP:", self.ip
        print "Name:", self.name
        print "Info:", self.info
        print "Modules", self.modules
        print "Module_Functions", self.functions
        print "Interfaces", self.interfaces
        print "Iface_Modules", self.iface_to_modules
        return ""


class NodeManager(object):
    def __init__(self, controller):
        self.log = logging.getLogger("{module}.{name}".format(
            module=self.__class__.__module__, name=self.__class__.__name__))

        self.controller = controller
        self.nodes = []
        self.groups = []

        self.newNodeCallback = None
        self.nodeExitCallback = None

        self.helloMsgInterval = 3
        self.helloTimeout = 3*self.helloMsgInterval


    def get_node_by_id(self, nid):
        node = None
        for n in self.nodes:
            if n.id == nid:
                node = n;
                break
        return node 


    def get_node_by_ip(self, ip):
        node = None
        for n in self.nodes:
            if n.ip == ip:
                node = n;
                break
        return node


    def get_node_by_str(self, string):
        node = None
        node = self.get_node_by_ip(string)
        if node:
            return node

        node = self.get_node_by_id(string)
        return node


    def add_node(self, msgContainer):
        topic = msgContainer[0]
        cmdDesc = msgContainer[1]
        msg = msgs.NewNodeMsg()
        msg.ParseFromString(msgContainer[2])
        agentId = str(msg.agent_uuid)
        agentName = msg.name
        agentInfo = msg.info
        
        for n in self.nodes:
            if agentId == n.id:
                self.log.debug("Already known Node UUID: {}, Name: {}, Info: {}".format(agentId,agentName,agentInfo))
                return

        node = Node(msg)
        self.nodes.append(node)
        self.log.debug("New node with UUID: {}, Name: {}, Info: {}".format(agentId,agentName,agentInfo))
        self.controller.transport.subscribe_to(agentId)

        if node and self.newNodeCallback:
            self.newNodeCallback(node)

        dest = agentId
        cmdDesc.Clear()
        cmdDesc.type = msgs.get_msg_type(msgs.NewNodeAck)
        cmdDesc.func_name = msgs.get_msg_type(msgs.NewNodeAck)
        msg = msgs.NewNodeAck()
        msg.status = True
        msg.controller_uuid = self.controller.uuid
        msg.agent_uuid = agentId
        msg.topics.append("ALL")

        msgContainer = [dest, cmdDesc, msg.SerializeToString()]

        time.sleep(1) # TODO: why?
        self.controller.transport.send_downlink_msg(msgContainer)
        return node


    def remove_node(self, msgContainer):
        topic = msgContainer[0]
        cmdDesc = msgContainer[1]
        msg = msgs.NodeExitMsg()
        msg.ParseFromString(msgContainer[2])
        agentId = str(msg.agent_uuid)
        reason = msg.reason

        node = self.get_node_by_id(agentId)

        if not node:
            return [None,None]

        self.log.debug("Controller removes node with UUID: {}, Reason: {}".format(agentId, reason))

        self.nodes.remove(node)

        if node and self.nodeExitCallback:
            self.nodeExitCallback(node, reason)

        return [node, reason]


    def send_hello_msg_to_node(self, nodeId):
        self.log.debug("Controller sends HelloMsg to agent")
        dest = nodeId
        cmdDesc = msgs.CmdDesc()
        cmdDesc.type = msgs.get_msg_type(msgs.HelloMsg)
        cmdDesc.func_name = msgs.get_msg_type(msgs.HelloMsg)
        msg = msgs.HelloMsg()
        msg.uuid = str(self.controller.uuid)
        msg.timeout = self.helloTimeout
        msgContainer = [dest, cmdDesc, msg.SerializeToString()]
        self.controller.transport.send_downlink_msg(msgContainer)


    def serve_hello_msg(self, msgContainer):
        self.log.debug("Controller received HELLO MESSAGE from agent".format())
        dest = msgContainer[0]
        cmdDesc = msgContainer[1]
        msg = msgs.HelloMsg()
        msg.ParseFromString(msgContainer[2])

        self.send_hello_msg_to_node(str(msg.uuid))
        #TODO: reschedule agent delete function in scheduler, support aspscheduler first
        pass