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

def getHead(state):
    return state["you"]["body"][0]


def movePoint(point, move):
    if move == "up":
        return {"x": point["x"], "y": point["y"] + 1}
    if move == "down":
        return {"x": point["x"], "y": point["y"] - 1}
    if move == "left":
        return {"x": point["x"] - 1, "y": point["y"]}
    if move == "right":
        return {"x": point["x"] + 1, "y": point["y"]}


def occupiedPositions(state):
    occ = set()
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            occ.add((b["x"], b["y"]))
    return occ

# ================= SAFE MOVES =================

def getSafeMoves(state):
    moves = ["up", "down", "left", "right"]
    safe = []

    head = getHead(state)
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

        new = movePoint(head, move)

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

def floodFill(start, board, occupied):
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

def applyMove(state, move):
    newState = {
        "you": {
            "body": list(state["you"]["body"]),
            "health": state["you"]["health"] - 1
        },
        "board": state["board"]
    }

    head = getHead(state)
    newHead = movePoint(head, move)

    newBody = [newHead] + newState["you"]["body"][:-1]

    # food
    for food in state["board"]["food"]:
        if food == newHead:
            newBody.append(newBody[-1])
            newState["you"]["health"] = 100

    newState["you"]["body"] = newBody
    return newState

def dead(state):
    head = getHead(state)
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
    moves = getSafeMoves(node.state)
    for m in moves:
        childState = applyMove(node.state, m)
        child = Node(childState, node, m)
        node.children.append(child)
    return random.choice(node.children) if node.children else node


def rollout(state, depth=15):
    for _ in range(depth):
        moves = getSafeMoves(state)
        if not moves:
            return -100

        # bias with flood fill
        bestMove = None
        bestScore = -1

        for m in moves:
            ns = applyMove(state, m)
            space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns))
            if space > bestScore:
                bestScore = space
                bestMove = m

        state = applyMove(state, bestMove)

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

    head = getHead(state)

    space = floodFill(head, state["board"], occupiedPositions(state))
    score = space * 2

    if state["you"]["health"] < 40 and state["board"]["food"]:
        dist = min(abs(head["x"]-f["x"]) + abs(head["y"]-f["y"]) for f in state["board"]["food"])
        score -= dist * 3

    return score

# ================= MAIN MOVE =================

def move(game_state: typing.Dict) -> typing.Dict:
    safeMoves = getSafeMoves(game_state)

    if not safeMoves:
        return {"move": "left"}

    # flood fill filter
    filtered = []
    for m in safeMoves:
        ns = applyMove(game_state, m)
        space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns))
        if space > len(game_state["you"]["body"]):
            filtered.append(m)

    if filtered:
        safeMoves = filtered

    root = Node(game_state)

    startTime = time.time()
    while time.time() - startTime < 0.18:
        node = select(root)
        node = expand(node)
        result = rollout(node.state)
        backpropagate(node, result)

    if not root.children:
        return {"move": random.choice(safeMoves)}

    best = max(root.children, key=lambda c: c.visits)

    return {"move": best.move}

# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})