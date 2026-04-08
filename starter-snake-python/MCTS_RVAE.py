import random
import typing
import math
import time

# ================= CONFIG =================

rolloutDepth = 20
MCTSTimeLimit = 0.2
raveExploration = 1000

lowHealthThreshold = 40
foodDistancePenalty = 3
spaceWeight = 2

deadPenalty   = -1000
noMovePenalty = -200
hazardPenalty = 200  # increased significantly - rave seems to undervalue hazards otherwise

# ================= INFO =================

def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "RAVE",
        "color": "#ffc700",
        "head": "pixel-round",
        "tail": "pixel-round",
    }

def start(game_state: typing.Dict):
    print("GAME START")

def end(game_state: typing.Dict):
    print("GAME OVER\n")

# ================= HELPERS =================

def getHead(state):
    return state["you"]["body"][0]

def movePoint(point, move):
    directions = {
        "up":    (0,  1),
        "down":  (0, -1),
        "left":  (-1, 0),
        "right": (1,  0),
    }
    dx, dy = directions[move]
    return {"x": point["x"] + dx, "y": point["y"] + dy}

def occupiedPositions(state):
    occupied = set()
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            occupied.add((b["x"], b["y"]))
    return occupied

def willEat(state, nextPoint):
    for f in state["board"]["food"]:
        if f["x"] == nextPoint["x"] and f["y"] == nextPoint["y"]:
            return True
    return False

# ================= SAFE MOVES =================

def getSafeMoves(state):
    moves = ["up", "down", "left", "right"]
    safe = []

    head = getHead(state)
    occupied = occupiedPositions(state)
    hazards = {(h["x"], h["y"]) for h in state["board"].get("hazards", [])}

    width = state["board"]["width"]
    height = state["board"]["height"]

    tail = state["you"]["body"][-1]

    for move in moves:
        nextPoint = movePoint(head, move)
        x, y = nextPoint["x"], nextPoint["y"]

        # WALL
        if x < 0 or x >= width or y < 0 or y >= height:
            continue

        eating = willEat(state, nextPoint)

        # BODY (only allow tail if NOT eating)
        if (x, y) in occupied:
            if not ( (x, y) == (tail["x"], tail["y"]) and not eating ):
                continue

        # HAZARD (hard avoid if possible)
        if (x, y) in hazards and state["you"]["health"] < 80:
            continue

        # TRAP CHECK
        space = floodFill(nextPoint, state["board"], occupied)
        if space <= len(state["you"]["body"]):
            continue

        safe.append(move)

    return safe

# ================= FLOOD FILL =================

def floodFill(start, board, occupied):
    stack = [(start["x"], start["y"])]
    visited = set()
    count = 0

    while stack:
        x, y = stack.pop()

        if (x, y) in visited or (x, y) in occupied:
            continue

        visited.add((x, y))
        count += 1

        for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            if (0 <= nx < board["width"] and
                0 <= ny < board["height"]):
                stack.append((nx, ny))

    return count

# ================= SIMULATION =================

def applyMove(state, move):
    new_head = movePoint(getHead(state), move)
    old_body = state["you"]["body"]

    new_body = [new_head] + old_body[:-1]
    new_health = state["you"]["health"] - 1

    new_food = list(state["board"]["food"])

    for i, food in enumerate(new_food):
        if food["x"] == new_head["x"] and food["y"] == new_head["y"]:
            new_body.append(old_body[-1])
            new_health = 100
            new_food = new_food[:i] + new_food[i+1:]
            break

    new_snakes = []
    for s in state["board"]["snakes"]:
        if s["id"] == state["you"]["id"]:
            new_snakes.append({**s, "body": new_body})
        else:
            new_snakes.append(s)

    return {
        "you": {
            "id": state["you"]["id"],
            "body": new_body,
            "health": new_health,
        },
        "board": {
            **state["board"],
            "food": new_food,
            "snakes": new_snakes,
        }
    }

def isDead(state):
    head = getHead(state)

    if not (0 <= head["x"] < state["board"]["width"] and
            0 <= head["y"] < state["board"]["height"]):
        return True

    body = {(b["x"], b["y"]) for b in state["you"]["body"][1:]}
    return (head["x"], head["y"]) in body

# ================= EVALUATION =================

def evaluate(state):
    if isDead(state):
        return deadPenalty

    head = getHead(state)
    space = floodFill(head, state["board"], occupiedPositions(state))
    score = space * spaceWeight

    # STRONG hazard penalty
    for h in state["board"].get("hazards", []):
        if head["x"] == h["x"] and head["y"] == h["y"]:
            score -= 500  # 🔥 MUCH stronger

    if state["you"]["health"] < lowHealthThreshold and state["board"]["food"]:
        dist = min(abs(head["x"] - f["x"]) + abs(head["y"] - f["y"])
                   for f in state["board"]["food"])
        score -= dist * foodDistancePenalty

    return score

# ================= NODE =================

class Node:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []

        self.visits = 0
        self.value = 0.0

        self.rave_value = {}
        self.rave_visits = {}

    def uct_score(self, parent_visits, c=1.4):
        if self.visits == 0:
            return float("inf")
        return (self.value / self.visits) + c * math.sqrt(math.log(parent_visits) / self.visits)

    def rave_score(self, action):
        v = self.rave_visits.get(action, 0)
        return self.rave_value.get(action, 0.0) / v if v > 0 else 0.0

    def update(self, result):
        self.visits += 1
        self.value += result

    def update_rave(self, action, result):
        self.rave_visits[action] = self.rave_visits.get(action, 0) + 1
        self.rave_value[action] = self.rave_value.get(action, 0.0) + result

# ================= MC-RAVE =================

def mc_rave_score(parent, child):
    uct = child.uct_score(parent.visits)
    rave = parent.rave_score(child.move)

    beta = math.sqrt(raveExploration / (3 * parent.visits + raveExploration))
    return (1 - beta) * uct + beta * rave

# ================= TREE POLICY =================

def tree_policy(node):
    while True:
        moves = getSafeMoves(node.state)

        if not moves:
            return node

        existing = {c.move for c in node.children}
        unexplored = [m for m in moves if m not in existing]

        if unexplored:
            m = random.choice(unexplored)
            new_state = applyMove(node.state, m)

            if isDead(new_state):
                continue

            child = Node(new_state, node, m)
            node.children.append(child)
            return child

        node = max(node.children, key=lambda c: mc_rave_score(node, c))

# ================= ROLLOUT =================

def default_policy(state):
    actions = []

    for _ in range(rolloutDepth):
        moves = getSafeMoves(state)

        if not moves:
            return deadPenalty, actions

        best_move = random.choice(moves)  # 🔥 less bias, avoids loops
        actions.append(best_move)
        state = applyMove(state, best_move)

        if isDead(state):
            return deadPenalty, actions

    return evaluate(state), actions

# ================= BACKPROP =================

def backpropagate(node, result, actions):
    depth = 0

    while node:
        node.update(result)

        for i, a in enumerate(actions):
            if i > 5:
                break
            weight = 1 / (1 + depth + i)
            node.update_rave(a, result * weight)

        node = node.parent
        depth += 1

# ================= MAIN =================

def move(game_state):
    safe_moves = getSafeMoves(game_state)

    if not safe_moves:
        return {"move": "up"}

    root = Node(game_state)

    start = time.time()
    while time.time() - start < MCTSTimeLimit:
        leaf = tree_policy(root)
        result, actions = default_policy(leaf.state)
        backpropagate(leaf, result, actions)

    if not root.children:
        return {"move": random.choice(safe_moves)}

    best = max(root.children, key=lambda c: c.visits)

    return {"move": best.move}

# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})