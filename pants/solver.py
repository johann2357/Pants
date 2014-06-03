"""
.. module:: solver
    :platform: Linux, Unix, Windows
    :synopsis: Provides functionality for finding a complete solution to a 
               world.

.. moduleauthor:: Robert Grant <rhgrant10@gmail.com>

"""

from .world import World
from .ant import Ant
import random


class Solver:
    """This class contains the functionality for solving a :class:`World`.  A
    :class:`World` can be solved using the :meth:`solve` or :meth:`solutions`.
    """
    def __init__(self, world, **kwargs):
        """Create a new :class:`Solver` with the given parameters.

        :param World world: the :class:`World` to solve
        :param float rho: percent evaporation of pheromone (0..1, default=0.8)
        :param float q: total pheromone deposited by each :class:`Ant` after
                        each interation is complete (>0, default=1)
        :param float t0: inital pheromone level along each :class:`Edge` of the
                         :class:`World` (>0, default=0.01)
        :param float alpha: relative importance of pheromone (default=1)
        :param float beta: relative importance of distance (default=3)
        :param float ant_count: how many :class:`Ants` will be used 
                                (default=10)
        :param float elite: multiplier of the pheromone deposited by the elite
                            :class:`Ant` (default=0.5)

        """
        self.world = world
        self.rho = kwargs.get('rho', 0.8)
        self.q = kwargs.get('Q', 1)
        self.t0 = kwargs.get('t0', .01)
        self.alpha = kwargs.get('alpha', 1)
        self.beta = kwargs.get('beta', 3)
        self.ant_count = kwargs.get('ant_count', 10)
        self.elite = kwargs.get('elite', .5)

    def reset_pheromone(self):
        """Reset the amount of pheromone on every edge to the initial default.
        """
        for edge in self.world.edges.values():
            edge.pheromone = self.t0
        
    def solve(self, limit=10):
        """Return the shortest path found after *limit* iterations.

        :param int limit: the number of iterations to perform (default=10)

        :returns: the single best solution found
        :rtype: :class:`Ant`

        """
        self.reset_pheromone()
        global_best = None
        for i in range(limit):
            # (Re-)Build the ant colony
            ants = self.round_robin_ants() if self.ant_count < 1 \
                    else self.random_ants()
            
            self.find_solutions(ants)
            self.update_scent(ants)
            local_best = self.get_best_ant(ants)
            if global_best is None or local_best < global_best:
                global_best = local_best.clone()
            if self.elite:
                self.trace_elite(global_best)
        return global_best
    
    def solutions(self, limit=10):
        """Return successively shorter paths until *limit* iterations have
        occured.

        Unlike :meth:`solve`, this method returns one solution for each 
        improvement of the best solution found thus far. Therefore it may 
        return a single solution (if the first one found was never improved) or
        it may return up to *limit* solutions (if every iteration improved the
        best solution found).

        :param int limit: the number of iterations to perform

        :returns: successively shorter solutions as :class:`Ant`s
        :rtype: list

        """
        self.reset_pheromone()
        global_best = None
        for i in range(limit):
            # (Re-)Build the ant colony
            ants = self.round_robin_ants() if self.ant_count < 1 \
                    else self.random_ants()
            self.find_solutions(ants)
            self.update_scent(ants)
            local_best = self.get_best_ant(ants)
            if global_best is None or local_best < global_best:
                global_best = local_best.clone()
                yield global_best
            if self.elite:
                self.trace_elite(global_best)
    
    def round_robin_ants(self):
        """Returns a list of :class:`Ant`s distributed to the nodes of the 
        world in a round-robin fashion.

        Note that this does not ensure at least one :class:`Ant` begins at each
        :class:`Node` unless there are exactly as many :class:`Ant`s as their 
        are :class:`Node`s. However, if *ant_count* is ``0`` then *ant_count*
        is set to the number of :class:`Node`s in the :class:`World` and this
        method is used to create the :class:`Ant`s before solving.

        :returns: the :class:`Ant`s initialized to :class:`Node`s in the 
                  :class:`World`
        :rtype: list

        """
        n = len(self.world.nodes)
        return [
            Ant(
                self.world, 
                self.alpha, 
                self.beta, 
                start=self.world.nodes[i % n]
            ) for i in range(self.ant_count)
        ]
        
    def random_ants(self):
        """Returns a list of :class:`Ant`s distributed to the nodes of the 
        world in a random fashion.

        Note that this does not ensure at least one :class:`Ant` begins at each
        :class:`Node` unless there are exactly as many :class:`Ant`s as their 
        are :class:`Node`s. This method is used to create the :class:`Ant`s 
        before solving if *ant_count* is **not** ``0``.

        TODO: Fix case where ant_count > len(world.nodes)

        :returns: the :class:`Ant`s initialized to :class:`Node`s in the 
                  :class:`World`
        :rtype: list

        """
        starts = self.world.nodes[:]
        ants = list()
        while self.ant_count > 0 and len(starts) > 0:
            r = random.randrange(len(starts))
            ants.append(
                Ant(self.world, self.alpha, self.beta, start=starts.pop(r))
            )
        return ants

    def find_solutions(self, ants):
        """Lets each ant find its own solution.

        TODO: Make the local pheromone update optional and configurable.

        :param list ants: the ants to use for solving

        """
        ants_done = 0
        while ants_done < len(ants):
            ants_done = 0
            for ant in ants:
                if ant.can_move():
                    m = ant.move()
                    self.world.edges[m].pheromone *= self.rho
                else:
                    ants_done += 1

    def update_scent(self, ants):
        """Update the amount of pheromone on each edge.

        This method represents the "global update" performed at the end of each
        iteration.

        :param list ants: the ants to use for solving

        """
        ants = sorted(ants)[:len(ants) // 2]
        for a in ants:
            p = self.q / a.distance
            for move in a.moves:
                edge = self.world.edges[move]
                edge.pheromone = max(
                    self.t0,
                    (1 - self.rho) * edge.pheromone + p)

    def get_best_ant(self, ants):
        """Return the :class:`Ant` with the shortest path.

        :param list ants: the :class:`Ant`s from which to choose
        :returns: the :class:`Ant` with the shortest path
        :rtype: :class:`Ant`

        """
        return sorted(ants)[0]

    def trace_elite(self, ant):
        """Deposit pheromone along the path of a particular ant.

        This method is used to deposit the pheromone of the elite :class:`Ant`
        at the end of each iteration.

        :param Ant ant: the elite :class:`Ant`

        """
        if self.elite:
            for m in ant.moves:
                self.world.edges[m].pheromone += \
                        self.elite * self.q / ant.distance
    