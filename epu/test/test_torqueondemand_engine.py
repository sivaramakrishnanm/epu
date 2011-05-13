from ion.test import iontest

import ion.util.ionlog

import time

from twisted.internet import defer

from epu.decisionengine.test.mockcontroller import DeeControl
from epu.decisionengine.test.mockcontroller import DeeState
from epu.decisionengine import EngineLoader

import epu.states as InstanceStates
BAD_STATES = [InstanceStates.TERMINATING, InstanceStates.TERMINATED, InstanceStates.FAILED]

log = ion.util.ionlog.getLogger(__name__)

ENGINE="epu.decisionengine.impls.TorqueOnDemandEngine"

class TorqueOnDemandEngineTestCase(iontest.IonTestCase):

    def setUp(self):
        self.engine = EngineLoader().load(ENGINE)
        self.state = DeeState()
        self.control = DeeControl(self.state)

    def tearDown(self):
        pass


    # -----------------------------------------------------------------------
    # Basics
    # -----------------------------------------------------------------------
    
    @defer.inlineCallbacks
    def test_no_launch(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(0)
        self._new_workerstatus("localhost:down")
        yield self.engine.initialize(self.control, self.state, conf)
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 0

    @defer.inlineCallbacks
    def test_launch_1(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(1)
        self._new_workerstatus("localhost:down")
        yield self.engine.initialize(self.control, self.state, conf)
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 1

    @defer.inlineCallbacks
    def test_terminate_1(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self.state.new_launch("instanceid1", public_ip="fakehost")
        self.engine.workers.append("fakehost")
        self._new_workerstatus("localhost:down;fakehost:offline")
        yield self.engine.initialize(self.control, self.state, conf)
        self.engine.free_worker_times['fakehost'] = 0
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_killed == 1
        assert self.control.total_launched == 0

    @defer.inlineCallbacks
    def test_launch_10(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(10)
        self._new_workerstatus("localhost:down")
        yield self.engine.initialize(self.control, self.state, conf)
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 10

    @defer.inlineCallbacks
    def test_launch_1_and_terminate_1(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(1)
        self.state.new_launch("instanceid1", public_ip="fakehost")
        self.engine.workers.append("fakehost")
        self._new_workerstatus("localhost:down;fakehost:offline")
        yield self.engine.initialize(self.control, self.state, conf)
        self.engine.free_worker_times['fakehost'] = 0
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 1
        assert self.control.total_killed == 1

    @defer.inlineCallbacks
    def test_launch_0_and_terminate_1(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(1)
        self.state.new_launch("instanceid1", public_ip="fakehost")
        self.engine.workers.append("fakehost")
        self._new_workerstatus("localhost:down;fakehost:offline;fakefree:free")
        yield self.engine.initialize(self.control, self.state, conf)
        self.engine.num_torque_workers = 1
        self.engine.free_worker_times['fakehost'] = 0
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 0
        assert self.control.total_killed == 1

    @defer.inlineCallbacks
    def test_empty_status_message(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(0)
        self._new_workerstatus("")
        yield self.engine.initialize(self.control, self.state, conf)
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 0
        assert self.control.total_killed == 0

    @defer.inlineCallbacks
    def test_skip_terminate_new_workers(self):
        torque = FakeTorqueManagerClient()
        conf = {'torque': torque}
        self._new_qlen(0)
        self._new_workerstatus("localhost:down;fakehost:offline")
        yield self.engine.initialize(self.control, self.state, conf)
        self.engine.free_worker_times['fakehost'] = time.time()
        yield self.engine.decide(self.control, self.state)
        assert self.control.total_launched == 0
        assert self.control.total_killed == 0

    def _new_qlen(self, qlen):
        self.state.new_sensor("queue-length", {"queue_name" : "fakequeue",
                                               "queue_length" : qlen})

    def _new_workerstatus(self, status):
        self.state.new_sensor("worker-status", {"queue_name" : "fakequeue",
                                               "worker_status" : status})

class FakeTorqueManagerClient(object):
    def __init__(self, proc=None, **kwargs):
        pass

    @defer.inlineCallbacks
    def watch_queue(self, subscriber, op="sensor_info", queue_name="default"):
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def unwatch_queue(self, subscriber, op="sensor_info", queue_name="default"):
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def add_node(self, hostname):
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def remove_node(self, hostname):
        yield defer.succeed(None)

    @defer.inlineCallbacks
    def offline_node(self, hostname):
        yield defer.succeed(None)