from heapq import heappop, heappush
from math import hypot


CELL = 24
NEIGHBORS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def next_waypoint(actor, target, walls, width, height, intersects):
    start = (actor.x, actor.y)
    expanded = [
        (left - actor.radius, bottom - actor.radius, right + actor.radius, top + actor.radius)
        for left, bottom, right, top in walls
    ]

    def clear(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        return not any(intersects(wall, *a, dx, dy) for wall in expanded)

    def nearby(point):
        col, row = int(point[0] // CELL), int(point[1] // CELL)
        for y in range(row - 1, row + 2):
            for x in range(col - 1, col + 2):
                candidate = (x * CELL + CELL // 2, y * CELL + CELL // 2)
                if 0 < candidate[0] < width and 0 < candidate[1] < height and clear(point, candidate):
                    yield candidate

    # The exact endpoints share the graph with the grid; a clear direct edge
    # is already the shortest possible A* route.
    if clear(start, target):
        return target

    finish_nodes = set(nearby(target))
    if not finish_nodes:
        return None

    frontier = []
    costs = {start: 0.0}
    parents = {}
    for node in nearby(start):
        cost = hypot(node[0] - start[0], node[1] - start[1])
        costs[node] = cost
        parents[node] = start
        heappush(frontier, (cost + hypot(node[0] - target[0], node[1] - target[1]), cost, node))

    while frontier:
        _, cost, node = heappop(frontier)
        if cost != costs[node]:
            continue
        if node == target:
            while parents[node] != start:
                node = parents[node]
            return node
        candidates = [(node[0] + dx * CELL, node[1] + dy * CELL) for dx, dy in NEIGHBORS]
        if node in finish_nodes:
            candidates.append(target)
        for candidate in candidates:
            x, y = candidate
            if not (0 < x < width and 0 < y < height) or not clear(node, candidate):
                continue
            new_cost = cost + hypot(x - node[0], y - node[1])
            if new_cost < costs.get(candidate, float('inf')):
                costs[candidate] = new_cost
                parents[candidate] = node
                heappush(frontier, (new_cost + hypot(x - target[0], y - target[1]), new_cost, candidate))
    return None
