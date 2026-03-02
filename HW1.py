import heapq
import csv
from typing import List, Union


class Node:
    """
    A generic class implementing the common functionality of nodes and switches.
    The node_id is used to represent the node.
    The routes is a dictionary that is used to forward a packet.
    The destination is stored as the key in the dictionary and the value is the
    next hop.
    Given a packet, you can retrieve the next by looking for its destination in
    routes.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.output_queue = []
        self.routing_table = {}

    def add_route(self, destination, next_hop):
        self.routing_table[destination] = next_hop


class Packet:
    """
    Represent a packet. Currently, a packet includes only the source and
    destination, which are usually included in the header of the packet. A unique packet id is given to
    each packet
    upon its creating.
    """
    cnt: int = 0

    def __init__(self, source: Node, destination: Node, next_hop: Union[Node, None] = None):
        self.packet_id = Packet.cnt
        Packet.cnt += 1
        self.source = source
        self.destination = destination
        if next_hop is None:
            self.next_hop = destination
        else:
            self.next_hop = next_hop

        # Fields to track times for CSV files
        self.enqueue_time_src = None
        self.transmit_time_src = None
        self.receive_time_c = None
        self.transmit_time_c = None
        self.receive_time_d = None
        self.propogate_time_a = None
        self.receive_time_b = None
        self.queue_time_src = None
        self.e2e_delay = None

    def __str__(self):
        return f'P[{self.packet_id}, {self.source.node_id}->{self.destination.node_id}] next={self.next_hop.node_id}'


class Host(Node):
    """
    A host includes a FIFO queue that stores the packets to be transmitted
    """

    def __init__(self, node_id):
        super().__init__(node_id)

    def __str__(self):
        return f'{self.node_id:2s} queue={[p.packet_id for p in self.output_queue]}'


class Router(Node):
    """
    The class emulate the behavior of a switch/router.
    Note that unlike a host, the switch has both an input and an output queue.
    """

    def __init__(self, node_id, processing_delay=0):
        super().__init__(node_id)
        self.input_queue: List[Packet] = []
        self.processing_delay = processing_delay

    def next_hop(self, destination):
        if self == destination:
            return self
        return self.routing_table[destination]

    def __str__(self):
        return f'{self.node_id:2s} in={[p.packet_id for p in self.input_queue]}' \
               f'out={[p.packet_id for p in self.output_queue]}'


class Event:
    """
    This class holds the information about the events that will be interpreted by
    the
    simulator. The event has the following state
    - target_node - the node that needs to handle the packet
    - event_type - it can be either ENQUEUE, TRANSMIT, PROPAGATE, RECEIVE
    - time - the time when the event will be executed
    - packet - the packet associated with the event (can be None)
    - event_id - the id of the event
    """

    ENQUEUE = 0
    TRANSMIT = 1
    PROPOGATE = 2
    RECEIVE = 3
    PROCESSING = 4

    cnt = 0

    def __init__(self, event_type: int, target_node: Node, packet: Packet = None, time: int = None):
        assert (0 <= event_type <= 3)
        self.target_node = target_node
        self.event_type = event_type
        self.time = time
        self.packet = packet
        self.event_id = Event.cnt
        Event.cnt += 1

    def type_to_str(self):
        if self.event_type == Event.ENQUEUE:
            return 'ENQUEUE'
        elif self.event_type == Event.TRANSMIT:
            return 'TRANSMIT'
        elif self.event_type == Event.PROPOGATE:
            return 'PROPOGATE'
        elif self.event_type == Event.RECEIVE:
            return "RECEIVE"
        elif self.event_type == Event.PROCESSING:
            return "PROCESSING"
        else:
            raise Exception('Unknown Event Type')

    def __str__(self):
        return f'{self.time:4d} {self.type_to_str():12s} {self.target_node.node_id} pkt={str(self.packet)}'


class Simulator:
    """
    The main simulator class.
    """

    def __init__(self, transmission_delay=10, propogation_delay=1):
        self.event_queue: List[Event] = []
        self.transmission_delay: int = transmission_delay
        self.propogation_delay: int = propogation_delay
        self.clock = 0
        self.nodes = {}
        self.all_packets = []

    def schedule_event_after(self, event: Event, delay: int):
        """
        Schedules an event to be executed in the future
        :param event:
        :param delay: the delay after which the event will be executed
        :return:
        """
        event.time = self.clock + delay

    def run(self):
        """
        Runs the simulator.
        :return:
        """

        print('Starting simulation')
        while len(self.event_queue) > 0:
            self.clock, _, event = heapq.heappop(self.event_queue)

            print(f'{str(event)}')
            self.handle_event(event)

    def handle_event(self, event):
        """
        Handles the execution of the events. You must implement this
        :param event:
        :return:
        """

        node = event.target_node
        pkt = event.packet

        if event.event_type == Event.ENQUEUE:
            pkt.enqueue_time_src = self.clock
            node.output_queue.append(pkt)

            if pkt not in self.all_packets:
                self.all_packets.append(pkt)

            # Start transmission if queue was empty
            if len(node.output_queue) == 1:
                new_event = Event(Event.TRANSMIT, node, pkt)
                self.schedule_event_after(new_event, self.transmission_delay)
                heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

        elif event.event_type == Event.TRANSMIT:
            if isinstance(node, Host):
                pkt.transmit_time_src = self.clock

            if isinstance(node, Router) or node.node_id == 'C':
                pkt.transmit_time_c = self.clock

            if node.output_queue and node.output_queue[0] == pkt:
                node.output_queue.pop(0)

            if pkt.next_hop is None:
                pkt.next_hop = node.next_hop(pkt.destination)

            # Schedule propagation
            new_event = Event(Event.PROPOGATE, pkt.next_hop, pkt)
            self.schedule_event_after(new_event, self.propogation_delay)
            heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

            # Schedule next transmission if queue not empty
            if node.output_queue:
                next_pkt = node.output_queue[0]
                next_transmit = Event(Event.TRANSMIT, node, next_pkt)
                self.schedule_event_after(next_transmit, self.transmission_delay)
                heapq.heappush(self.event_queue, (next_transmit.time, next_transmit.event_id, next_transmit))

        elif event.event_type == Event.PROPOGATE:
            # Track propagation time (single link)
            if isinstance(node, Host):
                pkt.propagate_time_a = self.clock

            new_event = Event(Event.RECEIVE, pkt.next_hop, pkt)
            self.schedule_event_after(new_event, 0)
            heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

        elif event.event_type == Event.RECEIVE:
            if isinstance(node, Router) or node.node_id == 'C':
                pkt.receive_time_c = self.clock
                pkt.next_hop = node.next_hop(pkt.destination)
                node.output_queue.append(pkt)

                # Start processing/transmission if queue was empty
                if len(node.output_queue) == 1:
                    new_event = Event(Event.TRANSMIT, node, pkt)
                    self.schedule_event_after(new_event, self.transmission_delay)
                    heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

            elif isinstance(node, Host):
                if node == pkt.destination:
                    pkt.receive_time_d = self.clock
                    if node.node_id == 'B':  # For single link experiment
                        pkt.receive_time_b = self.clock
                else:
                    node.output_queue.append(pkt)
                    if len(node.output_queue) == 1:
                        new_event = Event(Event.TRANSMIT, node, pkt)
                        self.schedule_event_after(new_event, self.transmission_delay)
                        heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

        elif event.event_type == Event.PROCESSING:
            node.output_queue.append(pkt)
            if len(node.output_queue) == 1:
                new_event = Event(Event.TRANSMIT, node, pkt)
                self.schedule_event_after(new_event, self.transmission_delay)
                heapq.heappush(self.event_queue, (new_event.time, new_event.event_id, new_event))

    def write_switch_file(self, filename: str):
        all_packets = self.all_packets
        all_packets.sort(key=lambda p: p.packet_id)

        fieldnames = ['Seq num', 'Source', 'Queue @src', 'Transmit @src', 'Receive @C', 'Transmit @C', 'Receive @D',
                      'End To End', 'Queueing Delay @src', 'Queueing Delay @C']
        # Note: keyword args are highlighted red, but the function still works correctly
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for pkt in all_packets:
                writer.writerow({
                    'Seq num': pkt.packet_id,
                    'Source': pkt.source.node_id,
                    'Queue @src': pkt.enqueue_time_src,
                    'Transmit @src': pkt.transmit_time_src,
                    'Receive @C': pkt.receive_time_c,
                    'Transmit @C': pkt.transmit_time_c,
                    'Receive @D': pkt.receive_time_d,
                    'End To End': pkt.receive_time_d - pkt.enqueue_time_src if pkt.receive_time_d is not None else None,
                    'Queueing Delay @src': pkt.transmit_time_src - pkt.enqueue_time_src,
                    'Queueing Delay @C': pkt.transmit_time_c - pkt.receive_time_c
                })

    def write_single_link_file(self, filename: str):
        all_packets = self.all_packets
        all_packets.sort(key=lambda p: p.packet_id)

        fieldnames = ['Seq num', 'Queue @A', 'Transmit @A', 'Propogate @A', 'Receive @B', 'End To End',
                      'Queueing Delay']
        # Note: keyword args are highlighted red but the function still works correctly
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for pkt in all_packets:
                writer.writerow({
                    'Seq num': pkt.packet_id,
                    'Queue @A': pkt.enqueue_time_src,
                    'Transmit @A': pkt.transmit_time_src,
                    'Propogate @A': pkt.propagate_time_a,
                    'Receive @B': pkt.receive_time_b,
                    'End To End': pkt.receive_time_b - pkt.enqueue_time_src if pkt.receive_time_b is not None else None,
                    'Queueing Delay': pkt.transmit_time_src - pkt.enqueue_time_src
                })

    def new_host(self, node_id: str) -> Host:
        if node_id in self.nodes:
            raise Exception('Node already added.')
        node = Host(node_id)
        self.nodes[node_id] = node
        return node

    def new_router(self, str_id, processing_delay) -> Router:
        if str_id in self.nodes:
            raise Exception('Node already added.')
        switch = Router(str_id, processing_delay)
        self.nodes[str_id] = switch
        return switch


def link_experiment():
    sim = Simulator()
    A, B = sim.new_host('A'), sim.new_host('B')

    # Create packets and events
    for _ in range(2):
        pkt = Packet(A, B)
        event = Event(Event.ENQUEUE, A, pkt)
        sim.schedule_event_after(event, 0)
        heapq.heappush(sim.event_queue, (event.time, event.event_id, event))

    sim.run()
    sim.write_single_link_file('single_link_2.csv') # single_link_2 has the extra columns


def switch_experiment():
    sim = Simulator();
    A, B, C, D = sim.new_host('A'), sim.new_host('B'), sim.new_router('C', 1), sim.new_host('D')
    C.add_route(D, D)
    sim_time = 10000

    # Node A with bursts of 5 every 1000 ticks
    for t in range(0, sim_time, 1000):
        for i in range(5):
            pkt = Packet(A, D)
            pkt.next_hop = C
            event = Event(Event.ENQUEUE, A, pkt)
            sim.schedule_event_after(event, t)
            heapq.heappush(sim.event_queue, (event.time, event.event_id, event))

    # Node B with bursts of 2 every 500 ticks
    for t in range(0, sim_time, 500):
        for i in range(2):
            pkt = Packet(B, D)
            pkt.next_hop = C
            event = Event(Event.ENQUEUE, B, pkt)
            sim.schedule_event_after(event, t)
            heapq.heappush(sim.event_queue, (event.time, event.event_id, event))

    sim.run()
    sim.write_switch_file('switch_2.csv')  # switch_2 has the extra columns


if __name__ == '__main__':
    # link_experiment()
    switch_experiment()
