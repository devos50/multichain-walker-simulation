from database import Database
from node import Node
import random
import os

from scoring import get_ranking


class Simulation:
    def __init__(self, max_time, log_dir, verbose, persistent_walking, directed_walking, block_limit, alpha):
        self.max_time = max_time
        self.bootstrap = Node(0, self)
        self.nodes = []
        self.event_queue = []
        self.time = 0
        self.block_file = os.path.join(log_dir, 'blocks.dat')
        self.load_balance_file = os.path.join(log_dir, 'load.dat')
        self.ranking_deviation_file = os.path.join(log_dir, 'ranking.dat')
        self.verbose = verbose
        self.persistent_walking = persistent_walking
        self.directed_walking = directed_walking
        self.block_limit = block_limit
        self.alpha = alpha

        print "Reading multichain database.."
        database = Database("multichain.db", self.block_limit)
        public_keys = database.get_identities()
        for public_key in public_keys:
            node = Node(public_key, self, self.persistent_walking, self.directed_walking, self.alpha)
            node.add_blocks(database.get_blocks(public_key))
            node.receive_identity(self.bootstrap)
            node.send_identity(self.bootstrap)
            self.nodes.append(node)
            self.add_event(Simulation.initialisation_delay(), node.take_walk_step)
            self.add_event(Simulation.initialisation_delay(), node.update_ranking)

        print "Calculating rankings.."
        # Here rankings are calculated based on the full database, not the individual databases of the nodes
        self.rankings = {}
        for public_key in public_keys:
            self.rankings[str(public_key)] = get_ranking(database, public_key)


        print "Scheduling data gathering.."
        for time in range(0, self.max_time, 60000):
            self.add_event(time, self.log_data)

    def add_event(self, delta_time, function, arguments=[]):
        time = self.time + delta_time
        event = [time, function] + arguments
        self.event_queue.append(event)
        self.event_queue.sort(key=lambda x: x[0])

    @staticmethod
    def connection_delay():
        return random.randint(100, 500)

    @staticmethod
    def initialisation_delay():
        return random.randint(0, 5000)

    def start(self):
        print "Starting simulation.."
        while self.event_queue:
            if self.time < self.max_time:
                event = self.event_queue.pop(0)
                self.time = event[0]
                if self.verbose:
                    print "Time: " + str(self.time) + " | " + str(event[1:])
                else:
                    if self.time % 1000 == 0:
                        print self.time
                event[1](*event[2:])
            else:
                print "Time limit reached"
                break

        if not self.event_queue:
            print "No more events"
        self.final_log_data()
        return

    def log_data(self):
        with open(self.block_file, 'a') as f:
            f.write(str(self.time) + " ")
        for node in self.nodes:
            if node.public_key is not 0:
                node.log_blocks(self.block_file)
        with open(self.block_file, 'a') as f:
            f.write("\n")

        with open(self.ranking_deviation_file, 'a') as f:
            f.write(str(self.time) + " ")
        for node in self.nodes:
            if node.public_key is not 0:
                node.log_ranking(self.ranking_deviation_file)
        with open(self.ranking_deviation_file, 'a') as f:
            f.write("\n")

    def final_log_data(self):
        for node in self.nodes:
            if node.public_key is not 0:
                node.log_requests(self.load_balance_file)

    def send_message(self, sender, target, message):
        self.add_event(Simulation.connection_delay(), target.receive_message, [sender, message])

