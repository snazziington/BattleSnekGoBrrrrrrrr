import random
import typing
import math
import time

# ================= INFO =================

def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "MattXWay",
        "color": "#ffc700",
        "head": "sneaky",
        "tail": "duck",
    }

# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")

# ================= HELPERS =================

def get_head(state):
    return state["you"]["body"][0]


def move_point(point, move):
    if move == "up":
        return {"x": point["x"], "y": point["y"] + 1}
    if move == "down":
        return {"x": point["x"], "y": point["y"] - 1}
    if move == "left":
        return {"x": point["x"] - 1, "y": point["y"]}
    if move == "right":
        return {"x": point["x"] + 1, "y": point["y"]}


def occupied_positions(state):
    occ = set()
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            occ.add((b["x"], b["y"]))
    return occ

# ================= SAFE MOVES =================

def get_safe_moves(state):
    moves = ["up", "down", "left", "right"]
    safe = []

    head = get_head(state)
    body = state["you"]["body"]
    neck = body[1]

    for move in moves:
        # prevent backwards
        if move == "left" and neck["x"] < head["x"]:
            continue
        if move == "right" and neck["x"] > head["x"]:
            continue
        if move == "down" and neck["y"] < head["y"]:
            continue
        if move == "up" and neck["y"] > head["y"]:
            continue

        new = move_point(head, move)

        # walls
        if not (0 <= new["x"] < state["board"]["width"] and
                0 <= new["y"] < state["board"]["height"]):
            continue

        # self collision
        if (new["x"], new["y"]) in [(b["x"], b["y"]) for b in body]:
            continue

        safe.append(move)

    return safe

# ================= FLOOD FILL =================

def flood_fill(start, board, occupied):
    stack = [(start["x"], start["y"])]
    visited = set()
    count = 0

    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue

        visited.add((x, y))
        count += 1

        for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            if (0 <= nx < board["width"] and
                0 <= ny < board["height"] and
                (nx, ny) not in occupied):
                stack.append((nx, ny))

    return count

# ================= SIMULATION =================

def apply_move(state, move):
    new_state = {
        "you": {
            "body": list(state["you"]["body"]),
            "health": state["you"]["health"] - 1
        },
        "board": state["board"]
    }

    head = get_head(state)
    new_head = move_point(head, move)

    new_body = [new_head] + new_state["you"]["body"][:-1]

    # food
    for food in state["board"]["food"]:
        if food == new_head:
            new_body.append(new_body[-1])
            new_state["you"]["health"] = 100

    new_state["you"]["body"] = new_body
    return new_state


def dead(state):
    head = get_head(state)
    body = state["you"]["body"][1:]

    if (head["x"], head["y"]) in [(b["x"], b["y"]) for b in body]:
        return True

    if not (0 <= head["x"] < state["board"]["width"] and
            0 <= head["y"] < state["board"]["height"]):
        return True

    return False

# ================= MCTS =================

class Node:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.value = 0


def ucb1(node):
    if node.visits == 0:
        return float('inf')
    return node.value / node.visits + math.sqrt(2 * math.log(node.parent.visits) / node.visits)


def select(node):
    while node.children:
        node = max(node.children, key=ucb1)
    return node


def expand(node):
    moves = get_safe_moves(node.state)
    for m in moves:
        child_state = apply_move(node.state, m)
        child = Node(child_state, node, m)
        node.children.append(child)
    return random.choice(node.children) if node.children else node


def rollout(state, depth=15):
    for _ in range(depth):
        moves = get_safe_moves(state)
        if not moves:
            return -100

        # bias with flood fill
        best_move = None
        best_score = -1

        for m in moves:
            ns = apply_move(state, m)
            space = flood_fill(get_head(ns), ns["board"], occupied_positions(ns))
            if space > best_score:
                best_score = space
                best_move = m

        state = apply_move(state, best_move)

    return evaluate(state)


def backpropagate(node, result):
    while node:
        node.visits += 1
        node.value += result
        node = node.parent

# ================= EVALUATION =================

def evaluate(state):
    if dead(state):
        return -1000

    head = get_head(state)

    space = flood_fill(head, state["board"], occupied_positions(state))
    score = space * 2

    if state["you"]["health"] < 40 and state["board"]["food"]:
        dist = min(abs(head["x"]-f["x"]) + abs(head["y"]-f["y"]) for f in state["board"]["food"])
        score -= dist * 3

    return score

# ================= MAIN MOVE =================

def move(game_state: typing.Dict) -> typing.Dict:
    safe_moves = get_safe_moves(game_state)

    if not safe_moves:
        return {"move": "left"}

    # flood fill filter
    filtered = []
    for m in safe_moves:
        ns = apply_move(game_state, m)
        space = flood_fill(get_head(ns), ns["board"], occupied_positions(ns))
        if space > len(game_state["you"]["body"]):
            filtered.append(m)

    if filtered:
        safe_moves = filtered

    root = Node(game_state)

    start_time = time.time()
    while time.time() - start_time < 0.18:
        node = select(root)
        node = expand(node)
        result = rollout(node.state)
        backpropagate(node, result)

    if not root.children:
        return {"move": random.choice(safe_moves)}

    best = max(root.children, key=lambda c: c.visits)

    return {"move": best.move}

# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})