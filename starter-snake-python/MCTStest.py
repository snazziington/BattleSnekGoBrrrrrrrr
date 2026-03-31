import random
import typing
import math
import time

# ================= CONFIGURABLE PARAMETERS =================
# These values can be tweaked to change behavior easily

# THESE 3 PARAMETERS CONTROL THE MCTS ALGORITHM
# Rollout depth for the default policy simulation. Higher means more foresight but more computation time.
rolloutDepth = 20
# Time limit for MCTS loop in seconds. Battlesnake has a 500ms move time limit, so we want to stay well under that to be safe.
MCTSTimeLimit = 0.2
# A higher value encourages more exploration, while a lower value favors exploitation of known good moves
UCB1Exploration = 2


# When health drops below this, the snake will prioritize getting food. Adjusting this can make the snake more or less aggressive in seeking food.
lowHealthThreshold = 40
# Penalty for being far from food when health is low. Higher means more aggressive food seeking.
foodDistancePenalty = 3
# Weight for available space in the evaluation function. Higher means the snake will prioritize moves that give it more room to maneuver.
spaceWeight = 2
# Penalty for dying. This should be a large negative number to strongly discourage moves that lead to death.
deadPenalty = -1000
# Penalty for having no safe moves in the default policy simulation. This helps the algorithm learn to avoid paths that lead to dead ends.
noMovePenalty = -200 


# ================= INFO =================

def info() -> typing.Dict:
    
    # Returns settings of the snake.
    # This is used by the Battlesnake engine to display your snake.
    
    return {
        "apiversion": "1",
        "author": "MattXWay",
        "color": "#ffc700",
        "head": "pixel-round",
        "tail": "pixel-round",
    }


def start(game_state: typing.Dict):
    #Called at the start of a game
    print("GAME START")


def end(game_state: typing.Dict):
    # Called at the end of a game
    print("GAME OVER\n")

# ================= HELPER FUNCTIONS =================

# get head position as a function since we use it a lot
def getHead(state):
    return state["you"]["body"][0]

# returns a new point after applying a theoretical move direction.
def movePoint(point, move):
    # directions are a list of coordinates based on how the snake moves
    directions = {
        "up": (0, 1),
        "down": (0, -1),
        "left": (-1, 0),
        "right": (1, 0),
    }
    # then accessed here based on which move is called and disected into dx/dy
    dx, dy = directions[move]
    return {"x": point["x"] + dx, "y": point["y"] + dy}

# returns a set of all occupied coordinates by all snakes, used for collision and flood fill
def occupiedPositions(state):
    # set here because it doesn't need to be an ordered list
    occupied = set()
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            occupied.add((b["x"], b["y"]))
    return occupied

# ================= SAFE MOVES =================

def getSafeMoves(state):
    """
    Returns a list of moves that:
    - Do not hit walls
    - Do not collide with our own body
    """
    moves = ["up", "down", "left", "right"]
    safe = []

    # get current thingy
    head = getHead(state)
    body = state["you"]["body"]

    occupied = occupiedPositions(state)
    print(f"Occupied positions: {occupied}")

    # for each move
    for move in moves:        
        nextPoint = movePoint(head, move)

        # Wall collision check
        if not (0 <= nextPoint["x"] < state["board"]["width"] and
                0 <= nextPoint["y"] < state["board"]["height"]):
            continue
        
        # Snake collision check (other snakes)
        for o in occupied:
            if (nextPoint["x"], nextPoint["y"]) == o:
                continue

        # Self collision check
        if (nextPoint["x"], nextPoint["y"]) in [(b["x"], b["y"]) for b in body]:
            continue
        
        # TODO: Other snake collision check
        safe.append(move)

    return safe

# ================= FLOOD FILL =================

# This is used as a heuristic to evaluate how much room the snake has to survive.
def floodFill(start, board, occupied):
    # the way this works is by starting at the head and then exploring all 4 directions, then from those new points it explores all 4 directions again, and so on until there are no more valid points to explore. 
    # The count of all the valid points is returned as a measure of how much free space there is.
    stack = [(start["x"], start["y"])]
    visited = set()
    count = 0

    # while there are still points to explore
    while stack:
        # get the next point to explore
        x, y = stack.pop()
        # if we've already been here, skip
        if (x, y) in visited:
            continue
        # if this point is occupied, skip
        if (x, y) in occupied:
            continue
        # if we're still going, add this to the visited list
        visited.add((x, y))
        count += 1

        # Explore neighbors
        for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
            if (0 <= nx < board["width"] and
                0 <= ny < board["height"] and
                (nx, ny) not in occupied):
                stack.append((nx, ny))

    return count

# ================= SIMULATION =================
# Simulates applying a move and returns a new game state.
def applyMove(state, move):
    """
    Features we're trying to simulate:
    - Moving the head
    - Updating the body
    - Eating food
    - Decreasing health
    """

    new_state = {
        "you": {
            "body": list(state["you"]["body"]),
            "health": state["you"]["health"] - 1
        },
        "board": state["board"]
    }

    head = getHead(state)
    new_head = movePoint(head, move)

    # Move body forward
    new_body = [new_head] + new_state["you"]["body"][:-1]

    # Check food consumption
    for food in state["board"]["food"]:
        if food == new_head:
            new_body.append(new_body[-1])
            new_state["you"]["health"] = 100

    new_state["you"]["body"] = new_body
    return new_state


def isDead(state):
    """
    Checks if the snake is dead due to:
    - Self collision
    - Wall collision
    """
    head = getHead(state)
    body = state["you"]["body"][1:]

    if (head["x"], head["y"]) in [(b["x"], b["y"]) for b in body]:
        return True

    if not (0 <= head["x"] < state["board"]["width"] and
            0 <= head["y"] < state["board"]["height"]):
        return True

    return False

# ================= MCTS IMPLEMENTATION =================

class Node:
    """
    Each node represents a game state that contains:
    - parent => previous node
    - children => possible future states
    - visits => number of times explored
    - value => accumulated score
    """
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.value = 0

# Upper Confidence Bound formula (math I found online).
def ucb1(node):
    # Balances exploration vs exploitation.
    
    if node.visits == 0:
        return float('inf')

    # Exploitation is the average value of this node, while exploration encourages trying less visited nodes.
    exploitation = node.value / node.visits
    exploration = math.sqrt(UCB1Exploration * math.log(node.parent.visits) / node.visits)

    return exploitation + exploration

# SELECTION + EXPANSION combined (cleaner than recursion).
def tree_policy(node):
    """
    Walks down the tree selecting best nodes until:
    - A leaf is found
        - A leaf is a node with no children, meaning it hasn't been explored at all. We want to explore new nodes to discover new strategies.
    - Or a node that can be expanded
    """
    while True:
        if not node.children:
            return expand(node)

        # If not fully expanded, expand first
        if len(node.children) < len(getSafeMoves(node.state)):
            return expand(node)

        # Otherwise select best child based on UCB1
        node = max(node.children, key=ucb1)

# Expands a node by adding one new child
def expand(node):
    # To expand, we look at all possible moves from this state and add a child for the first move that hasn't been explored (yet)
    existing_moves = {child.move for child in node.children}
    possible_moves = getSafeMoves(node.state)

    # now for each move, if we haven't already explored it, we create a new child node with the resulting state and add it to the children of this node. We return the new child to be used for simulation.
    for move in possible_moves:
        if move not in existing_moves:
            new_state = applyMove(node.state, move)
            child = Node(new_state, node, move)
            node.children.append(child)
            return child
    
    return node


def default_policy(state):
    """
    Simulates a random (but slightly biased) rollout.

    Uses flood fill to prefer moves with more space.
    """
    # for _ in range(rolloutDepth) means we will simulate a sequence of moves up to rolloutDepth steps into the future. This allows us to evaluate the potential long-term consequences of our current move, rather than just looking at the immediate next state.
    # Higher rollout depth means more foresight but also more computation time, so it needs to be balanced based on the time limit for battlesnake
    for _ in range(rolloutDepth):
        moves = getSafeMoves(state)
        # If there are no safe moves, we return a penalty score for dying, so we know that certain paths lead to death and should be avoided
        if not moves:
            return noMovePenalty
        # initializing variables to track best move and score
        best_move = None
        best_score = -1
        # for each move
        for move in moves:
            # apply the move to get the new state
            ns = applyMove(state, move)
            # then use flood fill to evaluate how much space we have
            space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns))
            scoreMoves[moves.index(move)] = space
            print("----Applied floodFill score to move----")
            print(scoreMoves)
            # if this move gives us more space than our current best, we update our best move and score
            if space > best_score:
                best_score = space
                best_move = move
        # after evaluating, apply best move
        state = applyMove(state, best_move)
    # 
    return evaluate(state)

# Backpropagation of the simulation result up the tree
def backpropagate(node, result):
    # while there is still a node to update (going up to the root)
    while node:
        # we increment the visit count and add the result to the value of this node, which will help guide future selections. 
        node.visits += 1
        node.value += result
        # Then we move up to the parent node and repeat until we reach the root.
        node = node.parent

# ================= EVALUATION =================

def evaluate(state):
    """
    Considers:
    - Survival (death penalty)
    - Available space
    - Distance to food when low health
    """
    # if the snake is dead, we return a large negative score to indicate this is a bad
    if isDead(state):
        return deadPenalty

    head = getHead(state)
    # we use flood fill again to evaluate how much space we have, and we multiply it by a weight to balance it against other factors
    space = floodFill(head, state["board"], occupiedPositions(state))
    score = space * spaceWeight

    # Food seeking when low health
    if state["you"]["health"] < lowHealthThreshold and state["board"]["food"]:
        dist = min(abs(head["x"]-f["x"]) + abs(head["y"]-f["y"]) for f in state["board"]["food"])
        # we subtract a penalty based on the distance to food, so that when health is low, we prioritize moves that get us closer to food. 
        # The FOOD_DISTANCE_PENALTY can be adjusted to make the snake more or less aggressive in seeking food when health is low
        score -= dist * foodDistancePenalty

    return score

# ================= MAIN MOVE =================
# Main decision function using MCTS. Basically where everything comes together
def move(game_state: typing.Dict) -> typing.Dict:
    """
    Steps:
    1. Filter safe moves
    2. Run MCTS loop
    3. Pick most visited child
    """
    safe_moves = getSafeMoves(game_state)
    global scoreMoves
    scoreMoves = [0, 0, 0, 0]
    # If there are no safe moves, we have to pick something, so we just return left (could be any move since we're doomed at this point)
    if not safe_moves:
        return {"move": "left"}

    # filtered is here to improve performance by reducing the number of moves we consider in the MCTS loop
    filtered = []
    for m in safe_moves:
        ns = applyMove(game_state, m)
        space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns))

        if space > len(game_state["you"]["body"]):
            filtered.append(m)

    if filtered:
        safe_moves = filtered

    # we create the root of our MCTS tree with the current game state, and then we run the MCTS loop until we hit our time limit
    root = Node(game_state)
    start_time = time.time()

    # MCTS loop
    while time.time() - start_time < MCTSTimeLimit:
        leaf = tree_policy(root)          # Selection + Expansion
        simulation = default_policy(leaf.state)  # Rollout
        backpropagate(leaf, simulation)          # Backpropagation

    if not root.children:
        return {"move": random.choice(safe_moves)}

    print("----All safe moves----")
    print(safe_moves)

    best_child = max(root.children, key=lambda c: c.visits)
    print("----Scores of all moves----")
    print(scoreMoves)

    print("----Next move----")
    print("move", best_child.move)
    return {"move": best_child.move}

# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
