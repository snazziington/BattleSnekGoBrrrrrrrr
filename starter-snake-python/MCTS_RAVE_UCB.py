import random
import typing
import math
import time

# ================= CONFIG =================

rolloutDepth = 20
MCTSTimeLimit = 0.2

UCB1Exploration = 2
raveWeight = 0.5   # MAIN CONTROL (0=UCB, 1=RAVE)

lowHealthThreshold = 40
foodDistancePenalty = 3
spaceWeight = 2

deadPenalty = -1000
noMovePenalty = -200
hazardPenalty = 20

# ================= INFO =================

def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "HybridMCTS",
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
        "up": (0, 1),
        "down": (0, -1),
        "left": (-1, 0),
        "right": (1, 0),
    }
    dx, dy = directions[move]
    return {"x": point["x"] + dx, "y": point["y"] + dy}

def occupiedPositions(state):
    occupied = set()
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            occupied.add((b["x"], b["y"]))
    return occupied

# ================= SAFE MOVES =================

def getSafeMoves(state):
    moves = ["up", "down", "left", "right"]
    safe = []

    head = getHead(state)
    body = state["you"]["body"]
    occupied = occupiedPositions(state)

    for move in moves:
        nextPoint = movePoint(head, move)

        if not (0 <= nextPoint["x"] < state["board"]["width"] and
                0 <= nextPoint["y"] < state["board"]["height"]):
            continue

        if (nextPoint["x"], nextPoint["y"]) in occupied:
            continue

        if (nextPoint["x"], nextPoint["y"]) in [(b["x"], b["y"]) for b in body]:
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
    new_state = {
        "you": {
            "body": list(state["you"]["body"]),
            "health": state["you"]["health"] - 1
        },
        "board": state["board"]
    }

    head = getHead(state)
    new_head = movePoint(head, move)

    new_body = [new_head] + new_state["you"]["body"][:-1]

    for food in state["board"]["food"]:
        if food == new_head:
            new_body.append(new_body[-1])
            new_state["you"]["health"] = 100

    new_state["you"]["body"] = new_body
    return new_state

def isDead(state):
    head = getHead(state)
    body = state["you"]["body"][1:]

    if (head["x"], head["y"]) in [(b["x"], b["y"]) for b in body]:
        return True

    if not (0 <= head["x"] < state["board"]["width"] and
            0 <= head["y"] < state["board"]["height"]):
        return True

    return False

# ================= EVALUATION =================

def evaluate(state):
    if isDead(state):
        return deadPenalty

    head = getHead(state)
    space = floodFill(head, state["board"], occupiedPositions(state))
    score = space * spaceWeight

    if state["you"]["health"] < lowHealthThreshold and state["board"]["food"]:
        dist = min(abs(head["x"]-f["x"]) + abs(head["y"]-f["y"])
                   for f in state["board"]["food"])
        score -= dist * foodDistancePenalty

    for h in state["board"].get("hazards", []):
        if (head["x"], head["y"]) == (h["x"], h["y"]):
            score -= hazardPenalty * (100 - state["you"]["health"])

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

    def ucb_score(self):
        if self.visits == 0:
            return float('inf')

        exploitation = self.value / self.visits
        exploration = math.sqrt(
            UCB1Exploration * math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration

    def rave_score(self):
        v = self.parent.rave_visits.get(self.move, 0)
        if v == 0:
            return 0
        return self.parent.rave_value.get(self.move, 0) / v

    def combined_score(self):
        ucb = self.ucb_score()
        rave = self.rave_score()

        # 🔥 Dynamic decay (RAVE → UCB over time)
        alpha = raveWeight * (1 / (1 + self.visits))

        return (1 - alpha) * ucb + alpha * rave

    def update(self, result):
        self.visits += 1
        self.value += result

    def update_rave(self, action, result):
        self.rave_visits[action] = self.rave_visits.get(action, 0) + 1
        self.rave_value[action] = self.rave_value.get(action, 0.0) + result

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

        node = max(node.children, key=lambda c: c.combined_score())

# ================= ROLLOUT =================

def default_policy(state):
    actions = []

    for _ in range(rolloutDepth):
        moves = getSafeMoves(state)

        if not moves:
            return noMovePenalty, actions

        move = random.choice(moves)
        actions.append(move)

        state = applyMove(state, move)

        if isDead(state):
            return deadPenalty, actions

    return evaluate(state), actions

# ================= BACKPROP =================

def backpropagate(node, result, actions):
    while node:
        node.update(result)

        for a in actions:
            node.update_rave(a, result)

        node = node.parent

# ================= MAIN =================

def move(game_state: typing.Dict) -> typing.Dict:
    safe_moves = getSafeMoves(game_state)

    if not safe_moves:
        return {"move": "left"}

    root = Node(game_state)

    start_time = time.time()

    while time.time() - start_time < MCTSTimeLimit:
        leaf = tree_policy(root)
        result, actions = default_policy(leaf.state)
        backpropagate(leaf, result, actions)

    if not root.children:
        return {"move": random.choice(safe_moves)}

    best_child = max(root.children, key=lambda c: c.visits)

    return {"move": best_child.move}

# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})