from gevent import monkey; monkey.patch_all()
import gevent
from Queue import PriorityQueue
from abletonlink import Link
import functools
import time

from FoxDot.lib.ServerManager import DefaultServer
from FoxDot.lib.TimeVar import TimeVar
from FoxDot.lib.TempoClock import QueueBlock, SoloPlayer
from FoxDot.lib.Players import Player


class LinkClock(object):

    def __init__(self, bpm=120, meter=(4,4)):
        self.link = Link(bpm)
        self.link.enable(True)
        self.clock = self.link.clock()
        self.meter = meter
        self.quantum = self.bar_length()
        # self.heap_queue = []
        self.queue = PriorityQueue()
        self._scheduled_events = {}
        self.sleeping_time = 0.0001
        self.ticking = False
        self.server = DefaultServer
        self.solo = SoloPlayer()

    def get_server(self):
        return self.server

    def get_clock(self):
        return self

    @property
    def bpm(self):
        state = self.link.captureAppSessionState()
        return state.tempo()

    @property
    def time(self):
        return self.clock.micros()

    @property
    def beat(self):
        state = self.link.captureAppSessionState()
        return state.beatAtTime(self.time, self.quantum)

    def bar_length(self):
        """ Returns the length of a bar in terms of beats """
        return (float(self.meter[0]) / self.meter[1]) * 4

    def bars(self, n=1):
        """ Returns the number of beats in 'n' bars """
        return self.bar_length() * n

    def beat_dur(self, n=1):
        """ Returns the length of n beats in seconds """
        return 0 if n == 0 else (60.0 / self.get_bpm()) * n

    def beats_to_seconds(self, beats):
        return self.beat_dur(beats)

    def seconds_to_beats(self, seconds):
        """ Returns the number of beats that occur in a time period  """
        return (self.get_bpm() / 60.0) * seconds

    def get_bpm(self):
        """ Returns the current beats per minute as a floating point number """
        if isinstance(self.bpm, TimeVar):
            bpm_val = self.bpm.now(self.beat)
        else:
            bpm_val = self.bpm
        return float(bpm_val)

    def now(self):
        return self.beat

    def osc_message_time(self):
        """ Returns the true time that an osc message should be run i.e. now + latency """
        return self.time

    def start(self):
        return gevent.spawn(self._run)

    def _run(self):
        self.ticking = True
        while self.ticking:
            heap_queue = self.queue.queue
            if heap_queue:
                beat = heap_queue[0]
                current_beat = self.beat
                if current_beat >= beat:
                    block = self._scheduled_events[beat]
                    gevent.spawn(self.__run_block, block, beat)
                    # heapq.heappop(self.heap_queue)
                    self.queue.get()

            gevent.sleep(self.sleeping_time)

    def __run_block(self, block, time):
        """ Private method for calling all the items in the queue block.
            This means the clock can still 'tick' while a large number of
            events are activated  """
        # Set the time to "activate" messages on - adjust in case the block is activated late

        # block.time = self.osc_message_time() - self.beat_dur(float(time) - block.beat)

        for item in block:
            # The item might get called by another item in the queue block

            if not block.called(item):
                try:
                    block.call(item)
                except SystemExit:
                    sys.exit()

        # Send all the message to supercollider together
        block.send_osc_messages()

    def schedule(self, f, beat=None, *args, **kwargs):

        if not self.ticking:
            self.start()

        if beat is None:
            beat = self.next_bar()

        try:
            block = self._scheduled_events[beat]
            block.add(f, args, kwargs)
        except KeyError:
            # heapq.heappush(self.heap_queue, beat)
            self.queue.put(beat)
            block = QueueBlock(self, f, beat, args, kwargs)
            self._scheduled_events[beat] = block
        if isinstance(f, Player):

            f.set_queue_block(block)

    def next_bar(self):
        """ Returns the beat value for the start of the next bar """
        beat = self.now()
        return beat + (self.meter[0] - (beat % self.meter[0]))


class ScheduledBlock(object):

    def __init__(self, f, *args, **kwargs):
        self.f = functools.partial(f, *args, **kwargs)


if __name__ == '__main__':

    # ll = LinkClock()
    # print ll.bpm
    # ll.start()
    #
    # print ll.beat
    # time.sleep(2)
    # print ll.beat


    from FoxDot import *

    # metro = LinkClock()
    # Player.metro = metro
    p = Player()
    p >> pluck([[1, 2], (0, 2, 4)], dur=[1, (0.5, 0.25)], sus=2)
    while True:
        time.sleep(1)

    p = P[1, 2]