import random
from typing import Union

import numpy as np
from matplotlib import pyplot as plt

SATURATION_WORKLOAD = 0
ALTERNATING_WORKLOAD = 1

SLOT_UNUSED = 0
SLOT_SUCCESSFUL = 1
SLOT_COLLISION = 2


class Packet:
    def __init__(self, source):
        assert isinstance(source, Node)
        self.source = source
        self.packet_duration = 1

    def __str__(self):
        return f'P[{self.source}]'


class Node:
    NodeCnt = 0

    def __init__(self):
        self.node_id = Node.NodeCnt
        Node.NodeCnt += 1
        self.queue = []

    def release_packet(self, slot):
        if len(self.queue) == 0:
            self.queue.append(Packet(self))

    def attempt_transmission(self, slot: int):
        raise Exception('Not implemented')

    def __str__(self):
        return f'N{self.node_id} Q={len(self.queue)}'

# Step 1
class AlohaNode(Node):
    def __init__(self, p_transmission: float):
        super().__init__()
        self.p_transmission = p_transmission

    def attempt_transmission(self, slot: int) -> Union[Packet, None]:
        # The node will only transmit if it has a pkt
        if len(self.queue) == 0:
            return None

        # Transmission Probability
        if random.random() < self.p_transmission:
            return self.queue[0]

        return None

    def ack(self, slot: int, success: bool):
        # Remove packet if transmission successful
        if success and len(self.queue) > 0:
            self.queue.pop(0)


# Step 4
class CSMANode(Node):
    def __init__(self):
        super().__init__()
        self.k = 0
        self.backoff_counter = None

    @staticmethod
    def contention_window(k, cw_min=31, cw_max=1023):
        """
        Compute the contention window (CW) for IEEE 802.11 DCF.

        Parameters:
        k (int): Backoff stage (number of retransmissions)
        cw_min (int): Minimum contention window (default 31 for 802.11b)
        cw_max (int): Maximum contention window (default 1023 for 802.11b)

        Returns:
        int: CW value in slots
        """
        cw = (2 ** k) * (cw_min + 1) - 1
        cw = cw // 2
        return min(cw, cw_max)

    def attempt_transmission(self, slot: int) -> Union[Packet, None]:
        if len(self.queue) == 0:
            return None

        if self.backoff_counter is None:
            self.backoff_counter = random.randint(0, self.contention_window(self.k))

        if self.backoff_counter > 0:
            self.backoff_counter -= 1
            return None
        else:
            # Counter has reached 0 so transmit packet
            return self.queue[0]

    def ack(self, slot: int, success: bool):
        if success:
            # For successful transmission
            self.queue.pop(0)
            self.k = 0
            self.backoff_counter = None
        else:
            # For collision, increment the backoff stage and pick a new counter
            self.k += 1
            self.backoff_counter = random.randint(0, self.contention_window(self.k))

    def __str__(self):
        return f'N{self.node_id} cnt={self.backoff_counter} k={self.k} Q={len(self.queue)}'


def saturation_workload(nodes, slot):
    """
    If a node has no packets, release one
    :param nodes:
    :param slot:
    :return:
    """
    for node in nodes:
        if len(node.queue) == 0:
            node.release_packet(slot)

# Step 7
def alternating_workload(nodes, slot):
    d = slot // 200
    if d % 2 == 1:
        saturation_workload(nodes, slot)
    else:
        N = 5
        saturation_workload(nodes[:N], slot)


def compute_nodes_with_packets(nodes):
    nodes_with_packets = []
    for node in nodes:
        if len(node.queue) > 0:
            nodes_with_packets.append(node)

    return nodes_with_packets


def simulate(node_constructor, n_nodes: int, workload_type: int, duration: int, plot: bool = False):
    Node.NodeCnt = 0
    nodes = [node_constructor() for _ in range(n_nodes)]
    status = np.zeros((n_nodes, duration))
    status[:] = SLOT_UNUSED
    random.seed(1234)

    successes = 0
    for slot in range(duration):
        """
        Update the workload of each node in the network
        """
        if workload_type == SATURATION_WORKLOAD:
            saturation_workload(nodes, slot)
        elif workload_type == ALTERNATING_WORKLOAD:
            alternating_workload(nodes, slot)
        else:
            raise Exception('Unknown workload type')

        # debug information
        nodes_with_packets = compute_nodes_with_packets(nodes)
        #print(f"{slot}: contenders {' '.join(str(n) for n in nodes_with_packets)}")
        #print(f'{slot}: contenders {' '.join([str(n) for n in nodes_with_packets])}')

        """
        Determine if a packet should be transmitted and record what nodes attempt transmission
        """
        nodes_with_transmissions = []
        for ix, node in enumerate(nodes):
            packet = node.attempt_transmission(slot)
            if packet is not None:
                #print(f'{slot}: {packet} attempted transmission')
                nodes_with_transmissions.append(node)

        """
        Determine if there are collisions
        """
        channel_collisions = len(nodes_with_transmissions) > 1

        #print(f"{slot}: channel is {'free' if not channel_collisions else 'busy'}")
        for node in nodes_with_transmissions:
            if not channel_collisions:
                successes += 1
                status[node.node_id, slot] = 1
            else:
                status[node.node_id, slot] = 2
            node.ack(slot, not channel_collisions)

        nodes_with_packets = compute_nodes_with_packets(nodes)
        #print(f"{slot}: contenders {' '.join([str(n) for n in nodes_with_packets])} POST")

    if plot:
        plt.pcolor(status)
        plt.colorbar()
        plt.xlabel('Time slot')
        plt.yticks(np.arange(n_nodes) + 0.5, np.arange(n_nodes))
        plt.ylabel('Node ID')
        plt.show()

    throughput = successes / duration
    print(f'Throughput: {throughput} Successes: {successes}')
    return throughput, status

# Step 2
def run_aloha_experiment(n_nodes, p, duration=10_000, plot=False):
    aloha_constructor = lambda: AlohaNode(p)
    throughput, M = simulate(aloha_constructor, n_nodes, SATURATION_WORKLOAD, duration=duration, plot=plot)
    print(f'Throughput: {throughput}')
    print(np.mean((M != SLOT_UNUSED), axis=1))


def aloha_bestp_experiment(n_nodes, step=0.01):
    xs = np.arange(0, .5, step)
    ys = []
    for p in xs:
        aloha_constructor = lambda: AlohaNode(p)
        throughput, _ = simulate(aloha_constructor, n_nodes, SATURATION_WORKLOAD, duration=10_000)
        ys.append(throughput)

    ys = np.array(ys)

    best_p = xs[np.argmax(ys)]
    best_throughput = np.max(ys)
    print(xs[np.argmax(ys)], np.max(ys))

    plt.plot(xs, ys, 's-')
    plt.axvline(best_p, color='red')
    plt.title(f'Best p={best_p:.2f} throughput={best_throughput:.2f}')
    plt.xlabel('Transmission probability')
    plt.ylabel('Throughput (packets per slot)')
    plt.show()

    aloha_constructor = lambda: AlohaNode(best_p)
    throughput, M = simulate(aloha_constructor, n_nodes, SATURATION_WORKLOAD, duration=1_000_000)
    S = np.mean(M == SLOT_SUCCESSFUL, axis=1)
    S = S / np.sum(S)
    print(S)

    plt.bar(np.arange(S.shape[0]), S)
    plt.title('Mistery graph')
    plt.show()

# Step 5 and 6
def csma_experiment(n_nodes, duration=10_000, plot=False):
    throughput, M = simulate(CSMANode, n_nodes, SATURATION_WORKLOAD, duration=duration, plot=plot)
    S = np.mean(M == SLOT_SUCCESSFUL, axis=1)
    S = S / np.sum(S)
    print(S)

    plt.bar(np.arange(S.shape[0]), S)
    plt.show()

# Step 8
def csma_variableload_experiment(n_nodes, duration=10_000, plot=False):
    throughput, M = simulate(CSMANode, n_nodes, ALTERNATING_WORKLOAD, duration=duration, plot=plot)


def aloha_variableload_experiment(n_nodes, duration=300, plot=True):
    """
    Variable load experiment for ALOHA
    Step 8, Question B
    """
    arrival_rates = np.concatenate([
        np.linspace(0.01, 0.20, duration // 2),
        np.linspace(0.20, 0.80, duration - duration // 2)
    ])

    # Buffers per node
    queues = [0] * n_nodes

    output = np.zeros((n_nodes, duration))

    # ALOHA transmission probability
    p = 1 / n_nodes

    for t in range(duration):
        lam = arrival_rates[t]

        # Arrivals
        for n in range(n_nodes):
            if np.random.rand() < lam:
                queues[n] += 1

        # Transmission Attempts
        attempts = [n for n in range(n_nodes) if queues[n] > 0 and np.random.rand() < p]

        if len(attempts) == 1:
            winner = attempts[0]
            queues[winner] -= 1
            output[winner, t] = 1

    if plot:
        plt.figure(figsize=(8, 5))
        plt.imshow(output, aspect='auto', origin='lower', cmap='viridis')
        plt.colorbar(label="Successful transmission (1 = success)")
        plt.xlabel("Time Slot")
        plt.ylabel("Node ID")
        plt.title("Slotted ALOHA Variable Load Experiment")
        plt.show()

    return output


if __name__ == '__main__':
    # run_aloha_experiment(5, 0.5, 25000, plot=False)
    # run_aloha_experiment(5, 0.5, 2500, plot=False)
    # aloha_bestp_experiment(25)
    # csma_experiment(5, duration=25, plot=True)
    # csma_experiment(25, duration=1_000_000)
    # csma_variableload_experiment(15, duration=300, plot=True)
     aloha_variableload_experiment(15, duration=300, plot=True)
