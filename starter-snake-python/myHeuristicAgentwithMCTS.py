import random
import numpy as np
import typing
import math
import time

# region Battlesnake Game Initialisation
# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
       "apiversion":"1",
       "author":"Snazziington",  # Your Battlesnake Username
       "color":"#6B57E0",  # Choose color
       "head":"beluga",  # Choose head
       "tail":"do-sammy",  # Choose tail
    }

# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")

# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")
    snakeLength = game_state["you"]["length"]
    turnsSurvived = game_state['turn']
    print("Final score:", snakeLength  * 0.2 + turnsSurvived * 0.8)

# endregion

# ================= CONFIGURABLE PARAMETERS =================
# These values can be tweaked to change behavior easily

# THESE 3 PARAMETERS CONTROL THE MCTS ALGORITHM
# Rollout depth for the default policy simulation. Higher means more foresight but more computation time.
rolloutDepth = 20
# Time limit for MCTS loop in seconds. Battlesnake has a 500ms move time limit, so we want to stay well under that to be safe.
MCTSTimeLimit = 0.2
# A higher value encourages more exploration, while a lower value favors exploitation of known good moves
UCB1Exploration = 2

# For each possible move:
    # [0] = x vector, [1] = y vector, [2] = string direction
moves = [[0, 1, "up"], [0, -1, "down"], [-1, 0, "left"], [1, 0, "right"]]

deathScore = -10000
hazardHealthBarrier = 10 # The min. amount of health our snake wants
                         # to have after passing through a hazard

floodFillWeight = 3 # this is the number the floodFill score is multiplied by for scoring
foodDistancePenalty = 1
lowHealthThreshold = 40 # health at which snake searches for food
hazardAvoidBounds = 40 # snake will avoid hazards like plague if hazard damage is above this number

centreScoreWeight = 0.99 # this number represents what the score weight is for the tiles in the
                        # corners. E.g., 0.8 means that the tiles are each multiplied by a float between
                        # between 0.8 and 1 based on their distance from the centre of the board.
                        # Must be float between 0 and 1
centreScoreBalancer = 1 - centreScoreWeight

tailFollowWeight = 0.99 # demerit when chasing own tail. otherwise it does it repeatedly and is easily trapped
tailSideFloodFillWeight = 6 # multiplies score of floodFill by this
                            # number if the tail is on that side

hazardWeight = 0.975 # multiplies the score by this if passing through a hazard

chanceCollisionWeight = 0.5

nonLethalHazardWeight = .15 # the score for moving into a hazardous space is equal
                            # to the deathScore multiplied by this number.

# TODO: Implement below parameters (optional)
snakeDisWeight = 0.9
snakeDisScoreBalancer = snakeDisWeight - 1

def wallCollision(nextMove, boardWidth, boardHeight):
    if (nextMove['x'] == boardWidth or nextMove['x'] == -1 or
        nextMove['y'] == boardHeight or nextMove['y'] == -1):
        return True

def getHead(state):
    return state["you"]["body"][0]

def getTail(state):
    return state["you"]["body"][len(state["you"]["body"]) - 1]

def hazardKillCheck(state, hazardDamage):
    if hazardDamage > state["you"]["health"] - hazardHealthBarrier:
        return True
    else:
        return False

def getHazardDamage(state):
    # region Calc Hazard Damage
    hazardDamage = int(len(state["board"]["hazards"]) * 2 / 3)
    return hazardDamage

def checkSnakeTiles(game_state: typing.Dict):
    snakeBodyTiles = list()

    for snake in game_state["board"]["snakes"]:
        snakeBody = snake["body"]
        for xy in snakeBody:
            snakeBodyTiles.append(xy)
    return snakeBodyTiles

def foodLocations(state):
    foodSet = list()
    for f in state["board"]["food"]:
        foodSet.append(f)
    return foodSet

def floodFill(start, board, occupied, myTail): # floodEvalPosition, boardState, occupiedTiles

    stack = [(start["x"], start["y"])]
    visited = set()
    count = 0
    floodArray = list()
    barriersFound = list()

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
        for nx, ny in [(x + 1, y),(x - 1, y),(x, y + 1),(x, y - 1)]:
            floodingCoords = {'x': nx, 'y': ny}
            barriersFound.append(floodingCoords)

            if (0 <= nx < board["width"] and
                0 <= ny < board["height"] and
                floodingCoords not in occupied):
                stack.append((nx, ny))

                if (nx, ny) not in floodArray:
                        floodArray.append((nx, ny))

                if floodingCoords in barriersFound:
                    barriersFound.pop(barriersFound.index(floodingCoords))

    #print("Flood Fill Arrayyyy:", floodArray)
    #print("barriersFound:", barriersFound)
    # The snake favours moving to the enclosed area that contains its tail, because it can follow it.

    if myTail in barriersFound:
        count *= tailSideFloodFillWeight
        print("Multiplying flood fill value bcs tail is on this side")
    
    elif myTail == start:
        count *= tailSideFloodFillWeight
        print("Multiplying flood fill value bcs next move is tail")
    return count


def movePoint(point, move):
    if move == "up":
        return {"x": point["x"], "y": point["y"] + 1}
    if move == "down":
        return {"x": point["x"], "y": point["y"] - 1}
    if move == "left":
        return {"x": point["x"] - 1, "y": point["y"]}
    if move == "right":
        return {"x": point["x"] + 1, "y": point["y"]}
    
def simulateMove(state, move, myHead):

    newState = state
    newState["you"]["health"] = myHealth - 1

    newHead = movePoint(myHead, move) # new head position = old head position moved
                                    # to the direction we're moving
    newBody = state["you"]["body"]
    newBody.insert(0, newHead)

    # need to print simulate game state to ensure it is correctly applying the new head and such stuff
    # food
    ateFood = False
        # If no food was eaten, body shrinks by 1. If food was eaten, body will remain lengthened

    for food in state["board"]["food"]:
        if food == newHead:
            newState["you"]["health"] = 100
            ateFood = True
        
    if ateFood == False:
        newBody.pop()
    return newState

def occupiedPositions(state, hazardDamage):
    occ = list()
    # Adds current body tiles of all snakes to the occ array
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            bodyCoords = {'x': 0, 'y': 0}
            bodyCoords["x"] = b["x"]
            bodyCoords["y"] = b["y"]
            occ.append(bodyCoords)
        
    # If hazards would kill us or hazard Damage is above 40, and there is no food on
    # the hazard, add them to the occupied tiles list
    if hazardKillCheck(state, hazardDamage) or hazardDamage > hazardAvoidBounds:
        for hazard in hazardLocations(state):
            if hazard not in foodLocations(state):
                occ.append(hazard)

    for x in range (-1, state["board"]["width"]):
        occ.append({"x": x, "y": -1})
        occ.append({"x": x, "y": state["board"]["height"]})

    for y in range (-1, state["board"]["height"]):
        occ.append({"x": -1, "y": y})
        occ.append({"x": state["board"]["width"], "y": y})        
    return occ

def hazardLocations(state):
    hazardSet = list()
    for f in state["board"]["hazards"]:
        hazardSet.append(f)
    return hazardSet

def preferCenterOfMap(point, state):
    # We prefer our snake being nearer to the middle.
    # Therefore, we will give a bonus to a move's score if it is near the centre of the board
    centreBoard = {"x": state["board"]["width"] / 2, "y": state["board"]["height"] / 2}
    centreBoard["x"] = state["board"]["width"] / 2
    centreMaxDis = (state["board"]["width"] + state["board"]["height"]) / 2
    
    centreDis = abs(point["x"] - centreBoard["x"]) + abs(point["y"] - centreBoard["y"])
    print("centreDis: ", centreDis)

    # ranges from 10 - 1 so like. it ranges from the average of the board's width and height
    centreScore = centreBoard["x"] - abs(point["x"] - centreBoard["x"])

    # centreDis ranges from 1 to 11.
    centreScore = centreDis / centreMaxDis
    centreScore = (centreScore * -1 + 1) * centreScoreBalancer + centreScoreWeight
    return centreScore

def evaluateMove(game_state, m):
    print("==========================================================")
    print("==========================================================")
    print("TURN:", game_state["turn"])
    print("gameState", game_state)
    # region Initialisation
    # Snake Head + Neck
    myHead = getHead(game_state)
    myTail = game_state["you"]["body"][len(game_state["you"]["body"]) - 1]
    global myHealth
    myHealth = game_state["you"]["health"]

    # Board dimensions
    boardWidth = game_state['board']['width']
    boardHeight = game_state['board']['height']

    # region Calc Hazard Damage
    hazardRound = game_state["turn"] % 175
    # R 0 - 24
    if hazardRound < 25:
        hazardDamage = 0
    
    # R 25 - 49
    elif hazardRound < 50:
        hazardDamage = 14
    
    # R 50 - 74
    elif hazardRound < 75:
        hazardDamage = 28
    
    # R 75 - 99
    elif hazardRound < 100:
        hazardDamage = 42
    
    # R 100 - 175
    else:
        hazardDamage = 56

    print("Hazardddddd Damage:", hazardDamage)
    # endregion
    
    # Scores of each direction initialise as 0
    global score
    score = [0, 0, 0, 0] # up, down, left, right

    # endregion
    # Check Collisions
    print("...")
    nextMove = {'x': myHead["x"], 'y': myHead["y"]}
    print("nextMove", nextMove)
    # New coords of head if doing this move
    print("If moving", moves[m][2], ", head will go to", nextMove)

    # occupiedTiles 
    occupiedTiles = occupiedPositions(game_state, hazardDamage)
    print("Hazard Damage", hazardDamage)
    print("Next move:", nextMove)

    # Avoid Wall/Snake Collisions (and Hazard collisions if it would kill)
    if wallCollision(nextMove, boardWidth, boardHeight):
            score[m] += deathScore
            print("Cannot move", moves[m][2], ", will collide with wall")
            print("Score changed by:", deathScore, "New score: ", score[m])
    
    floodFillValue = floodFill(nextMove, game_state["board"], occupiedTiles, myTail)

    # Check if there's food on a hazard (if yes, tis safe)
    if hazardKillCheck(game_state, hazardDamage) and nextMove not in foodLocations(game_state) and nextMove in hazardLocations(game_state):
        print("Checking if hazards will kill us")

        score[m] += deathScore * nonLethalHazardWeight
        print("Lets avoid hazard. Add", deathScore * nonLethalHazardWeight, "to score")
        print("Score changed by:", deathScore * nonLethalHazardWeight, "New score: ", score[m])

    # Only for moves that will not cause death
    if score[m] > -5000:
        # Increase score based on freedom of movement in new tile
        floodFillScore = floodFillWeight * floodFillValue
        score[m] += floodFillScore
        print("floodFillScore:", floodFillScore)
        print("Score changed by:", floodFillScore, "New score: ", score[m])

        # Decrease score if food is far
        foodScore = 0
        totalFoodDist = 0
        print("Heeeeealth", game_state["you"]["health"])

        for food in foodLocations(game_state):
            foodDist = min(abs(nextMove["x"]-food["x"]) + abs(nextMove["y"]-f["y"]) for f in game_state["board"]["food"])
            if game_state["you"]["health"] < lowHealthThreshold:
                foodScore -= foodDist * foodDistancePenalty
                totalFoodDist -= foodDist
                if game_state["you"]["health"] < 5:
                    totalFoodDist *= 10 
        score[m] += foodScore
        print("TotalFoodDist:", totalFoodDist)
        print("Score changed by:", foodScore, "New score: ", score[m])
        
        
        # Reduce score if hazard will damage you
        if nextMove in hazardLocations(game_state):
            # TODO: I feel like the weighting of the hazard 
            # should depend on how much damage it does... Not necessary though
            print("Hazard Damage", hazardDamage)
            score[m] *= hazardWeight
            print("hazardDamage:", hazardDamage)
            print("Score multiplied by:", hazardWeight, "New score: ", score[m])

       
        if nextMove in checkSnakeTiles(game_state):
            # Check if chasing own tail + did not just eat food
            if nextMove == myTail and game_state["you"]["health"] < 97 and game_state['turn'] > 2:
                print("Chasing own tail", game_state["you"]["health"])
                score[m] *= tailFollowWeight
                print("Score multiplied by", tailFollowWeight, "New score:", score[m])
            
            else:
                score[m] += deathScore
                print("Cannot move", moves[m][2], ", will collide with a body")
                print("Score changed by:", deathScore, "New score: ", score[m])

    score[m] *= round(preferCenterOfMap(nextMove, game_state), 2)
    print("Score multiplied by", round(preferCenterOfMap(nextMove, game_state), 2), "New score:", score[m])

    print("Score for moving", moves[m][2], "is:", score[m])
    
    print("All scores:", score)
    maxScore = max(score) # Maximum score found in the score array
    scoreValues = np.array([score[0], score[1], score[2], score[3]]) # We use numpy here so we can use ".where"
    bestMoves = np.where(scoreValues == maxScore)[0]
    print("The best possible moves are:", bestMoves)

    nextMove = random.choice(bestMoves)
    print("The next move is", moves[nextMove][2])
    return score[nextMove]

# ==================== MCTS IMPLEMENTATION ====================
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

    occupied = occupiedPositions(state, getHazardDamage(state))

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

def applyMove(state, move):
    """
    Features we're trying to simulate:
    - Moving the head
    - Updating the body
    - Eating food
    - Decreasing health
    """

    new_state = state
    new_state["you"]["health"] -= 1

    head = state["you"]["body"][0]
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
            return -200
        # initializing variables to track best move and score
        best_move = None
        best_score = -1
        # for each move
        for move in moves:
            # apply the move to get the new state
            ns = applyMove(state, move)
            score[moves.index(move)] = evaluateMove(ns, moves.index(move))
            # then use flood fill to evaluate how much space we have
            #space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns))
            #scoreMoves[moves.index(move)] = space
            #print("----Applied floodFill score to move----")
            #print(scoreMoves)
            # if this move gives us more space than our current best, we update our best move and score
            
            print("testing", score[moves.index(move)], best_score)
            if score[moves.index(move)] > best_score:
                best_score = score[moves.index(move)]
                best_move = move
        # after evaluating, apply best move
        state = applyMove(state, best_move)
    # 
    return best_score

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

    # filtered is here to improve performance by reducing the number of moves we consider in the MCTS loop by filtering out moves that lead to states with very little space, which are likely to be bad moves
    filtered = []
    for m in safe_moves:
        ns = applyMove(game_state, m)
        space = floodFill(getHead(ns), ns["board"], occupiedPositions(ns, getHazardDamage(ns)), getTail(ns))

        if space > len(game_state["you"]["body"]):
            filtered.append(m)

    if filtered:
        safe_moves = filtered

    # we create the root of our MCTS tree with the current game state, and then we run the MCTS loop until we hit our time limit
    root = Node(game_state)
    start_time = time.time()

    # MCTS loop
    while time.time() - start_time < MCTSTimeLimit:
        leaf = tree_policy(root)                 # Selection + Expansion
        simulation = default_policy(leaf.state)  # Rollout
        backpropagate(leaf, simulation)          # Backpropagation

    if not root.children:
        return {"move": random.choice(safe_moves)}

    print("----All safe moves----")
    print(safe_moves)

    # After the MCTS loop, we select the child of the root with the most visits, which represents the move that was explored the most and is likely the best move based on our simulations. We return this move as our decision for this turn.
    # alternatively we could select the child with the highest average value (value/visits) to prioritize moves that had better outcomes in the simulations, but selecting by visits is a common approach that tends to work well in practice.
    # we do this by using the max function with a key that looks at the visits of each child node, and we return the move associated with that child node as our chosen move for this turn.
    best_child = max(root.children, key=lambda c: c.value / c.visits if c.visits > 0 else float('-inf'))
    # best_child = max(root.children, key=lambda c: c.visits)
    print("----Scores of all moves----")
    print(scoreMoves)

    print("----Next move----")
    print("move", best_child.move)
    return {"move": best_child.move}

# Backpropagation of the simulation result up the tree
def backpropagate(node, result):
    # while there is still a node to update (going up to the root)
    while node:
        # we increment the visit count and add the result to the value of this node, which will help guide future selections. 
        node.visits += 1
        node.value += result
        # Then we move up to the parent node and repeat until we reach the root.
        node = node.parent
        
# ================= SERVER =================

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})