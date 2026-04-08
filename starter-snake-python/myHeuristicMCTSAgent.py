import random
import numpy as np
import typing

# region Battlesnake Game Initialisation
# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
       "apiversion":"1",
       "author":"heuristicAgent",  # Your Battlesnake Username
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

# For each possible move:
    # [0] = x vector, [1] = y vector, [2] = string direction
moves = [[0, 1, "up"], [0, -1, "down"], [-1, 0, "left"], [1, 0, "right"]]
depth = 2

deathScore = -10000
hazardHealthBarrier = 10 # The min. amount of health our snake wants
                         # to have after passing through a hazard

floodFillWeight = 1 # this is the number the floodFill score is multiplied by for scoring
foodDistancePenalty = 1 # 
hungryBounds = 40 # health at which snake searches for food
hazardAvoidBounds = 40 # snake will avoid hazards like plague if hazard damage is above this number

centreScoreWeight = 0.99 # this number represents what the score weight is for the tiles in the
                        # corners. E.g., 0.8 means that the tiles are each multiplied by a float between
                        # between 0.8 and 1 based on their distance from the centre of the board.
                        # Must be float between 0 and 1
centreScoreBalancer = 1 - centreScoreWeight

tailFollowWeight = 0.99 # demerit when chasing own tail. otherwise it does it repeatedly and is easily trapped
tailSideFloodFillWeight = 3 # multiplies score of floodFill by this
                            # number if the tail is on that side

hazardWeight = 0.975 # multiplies the score by this if passing through a hazard

chanceCollisionWeight = 0.5

# TODO: Implement below parameters (optional)
snakeDisWeight = 0.9
snakeDisScoreBalancer = snakeDisWeight - 1

nonLethalHazardWeight = .15 # the score for moving into a hazardous space is equal
                            # to the deathScore multiplied by this number.

def wallCollision(nextMove, boardWidth, boardHeight):
    if (nextMove['x'] == boardWidth or nextMove['x'] == -1 or
        nextMove['y'] == boardHeight or nextMove['y'] == -1):
        return True

def getHazardDamage(state):
    hazardDamage = int(len(state["board"]["hazards"]) * 2 / 3)
    return hazardDamage
    # endregion

def hazardKillCheck(state, hazardDamage):
    if hazardDamage > state["you"]["health"] - hazardHealthBarrier:
        return True
    else:
        return False

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
    if hazardKillCheck(state, getHazardDamage(state)) or hazardDamage > hazardAvoidBounds:
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

def potentialCollisions(state, myHead):
    pot = list()
    for snake in state["board"]["snakes"]:
        # If a snake is one of more tiles longer than us, avoid them like the plague
        if snake["length"] >= state["you"]["length"] - 1:
            head = snake["body"][0]
            for m in range (0, 4):
                coords = {'x': 0, 'y': 0}
                coords["x"] = (head["x"] + moves[m][0])
                coords["y"] = (head["y"] + moves[m][1])
                pot.append(coords)
    
    # Removes snake's own head's potential directions from pot list
    for m in range (0, 4):
            coords = {'x': 0, 'y': 0}
            coords["x"] = (myHead["x"] + moves[m][0])
            coords["y"] = (myHead["y"] + moves[m][1])
            if coords in pot:
                pot.remove(coords)
    return pot


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

    # ranges from 10 - 1 so like. it ranges from the average of the board's width and height
    centreScore = centreBoard["x"] - abs(point["x"] - centreBoard["x"])

    # centreDis ranges from 1 to 11.
    centreScore = centreDis / centreMaxDis
    centreScore = (centreScore * -1 + 1) * centreScoreBalancer + centreScoreWeight
    return centreScore


def move(game_state: typing.Dict) -> typing.Dict:
    print("=============================")
    print("=============================")
    print("TURN:", {game_state['turn']})

    # region Initialisation
    # Snake Head + Neck
    myHead = game_state["you"]["body"][0]
    global myHealth
    myHealth = game_state["you"]["health"]

    # Board dimensions
    global boardWidth
    boardWidth = game_state['board']['width']

    global boardHeight
    boardHeight = game_state['board']['height']
    
    # Scores of each direction initialise as 0
    global score
    score = [0, 0, 0, 0] # up, down, left, right

    # endregion
    # Check Collisions
    #for mainMove in moves:
    print("My head:", myHead)
    #nextMove = {"x": myHead["x"] + mainMove[0], "y": myHead["y"] + mainMove[0]}
    global n
    n = 0
    for mainMove in moves:
        evaluateState(game_state, myHead, n, moves.index(mainMove))
    """
    else:
        print("Main Move:", mainMove, "N:", n)
        n += 1
        # Simulates next move
        nextState = simulateMove(game_state, moves[m][2], myHead)
        score[mainMove[2]] += evaluateState(game_state, myHead)
    """

    print("All scores:", int(score[0]), int(score[1]), int(score[2]), int(score[3]))
    maxScore = max(score) # Maximum score found in the score array
    scoreValues = np.array([score[0], score[1], score[2], score[3]]) # We use numpy here so we can use ".where"
    bestMoves = np.where(scoreValues == maxScore)[0]
    print("The best possible moves are:", bestMoves)

    nextMove = random.choice(bestMoves)
    print("The next move is", moves[nextMove][2])
    return {"move": moves[nextMove][2]}

def evaluateState(state, startPos, n, mainMove):
    countingScore = 0

    while n < depth:
        for m in range (0, 4): # For each possible move (up, down, left, right)
            print("M IS:", m)
            print("N IS:", n)
            if n == 0:
                scoringMove = moves[mainMove][2]
            
            else:
                scoringMove = mainMove

            myHead = startPos
            myTail = state["you"]["body"][len(state["you"]["body"]) - 1]
            print("...")
            nextMove = {'x': 0, 'y': 0}
            nextMove['x'] = myHead["x"] + moves[m][0]
            nextMove['y'] = myHead["y"] + moves[m][1]

            # New coords of head if doing this move
            print("If moving", moves[m][2], ", head will go from", myHead, "to", nextMove)

            # Simulates next move
            simGameState = simulateMove(state, moves[m][2], myHead)
            myTail = simGameState["you"]["body"][len(state["you"]["body"]) - 1]

            # occupiedTiles 
            occupiedTiles = occupiedPositions(state, getHazardDamage(state))
            print("Hazard Damage", getHazardDamage(state))
            print("Next move:", nextMove)

            # Avoid Wall/Snake Collisions (and Hazard collisions if it would kill)
            if wallCollision(nextMove, boardWidth, boardHeight) or nextMove in occupiedTiles:
                countingScore += deathScore
                print("Cannot move", moves[m][2], ", will collide with wall or occupied tile")
                print("Score changed by:", deathScore, "New score: ", int(countingScore), "Main:", moves[mainMove][2])
            
            if countingScore > -5000:
                floodFillValue = floodFill(nextMove, simGameState["board"], occupiedTiles, myTail)

                # Check if there's food on a hazard (if yes, tis safe)
                if hazardKillCheck(state, getHazardDamage(state)) and nextMove not in foodLocations(state) and nextMove in hazardLocations(state):
                    print("Checking if hazards will kill us")

                    countingScore += deathScore * nonLethalHazardWeight
                    print("Lets avoid hazard. Add", deathScore * nonLethalHazardWeight, "to score")
                    print("Score changed by:", deathScore * nonLethalHazardWeight, "New score: ", int(countingScore), "Main:", moves[mainMove][2])

                # Only for moves that will not cause death

                # Increase score based on freedom of movement in new tile
                floodFillScore = floodFillWeight * floodFillValue
                countingScore += floodFillScore
                print("floodFillScore:", floodFillScore)
                print("Score changed by:", floodFillScore, "New score: ", int(countingScore), "Main:", moves[mainMove][2])

                # Decrease score if food is far
                foodScore = 0
                totalFoodDist = 0
                print("Heeeeealth", simGameState["you"]["health"])

                for food in foodLocations(state):
                    foodDist = min(abs(nextMove["x"] - food["x"]) + abs(nextMove["y"] - f["y"]) for f in simGameState["board"]["food"])
                    if state["you"]["health"] < hungryBounds:
                        foodScore -= foodDist * foodDistancePenalty
                        totalFoodDist -= foodDist
                        if state["you"]["health"] < 5:
                            totalFoodDist *= 10 
                countingScore += foodScore
                print("TotalFoodDist:", totalFoodDist)
                print("Score changed by:", foodScore, "New score: ", int(countingScore), "Main:", moves[mainMove][2])
                
                # Reduce score if hazard will damage you
                if nextMove in hazardLocations(state):
                    # TODO: I feel like the weighting of the hazard 
                    # should depend on how much damage it does... Not necessary though
                    print("Hazard Damage", getHazardDamage(state))
                    countingScore *= hazardWeight
                    print("hazardDamage:", getHazardDamage(state))
                    print("[Hazard] Score multiplied by:", hazardWeight, "New score: ", int(countingScore), "Main:", moves[mainMove][2])

                # Reduce score by multiplier if collision with larger snake is possible
                if nextMove in potentialCollisions(state, myHead) and state['turn'] > 1:
                    print("Preferably not moving", moves[m][2], ", may collide with a larger snake")
                    countingScore *= chanceCollisionWeight
                    print("Score multiplied by:", chanceCollisionWeight, "New score: ", int(countingScore), "Main:", moves[mainMove][2])
                
                if nextMove in checkSnakeTiles(state):
                    # Check if chasing own tail + did not just eat food
                    if nextMove == myTail and state["you"]["health"] < 97 and state['turn'] > 2:
                        print("Chasing own tail", state["you"]["health"])
                        countingScore *= tailFollowWeight
                        print("Score multiplied by", tailFollowWeight, "New score:", int(countingScore), "Main:", moves[mainMove][2])
                    
                    else:
                        countingScore += deathScore
                        print("Cannot move", moves[m][2], ", will collide with a body")
                        print("Score changed by:", deathScore, "New score: ", int(countingScore), "Main:", moves[mainMove][2])
            
            # Ensures moves deeper in the tree weigh less heavily
            countingScore *= round(preferCenterOfMap(nextMove, state), 2)
            print("[Centre] Score multiplied by", round(preferCenterOfMap(nextMove, state), 2), "New score:", countingScore, "Main:", moves[mainMove][2])

            countingScore *= (depth - n + 1) / depth

            print("Score for this tree path is multiplied by", (depth - n + 1) / depth, "now it is", int(countingScore))
            score[mainMove] += countingScore
            
            print("Score for moving", moves[m][2], "was", int(score[mainMove] - countingScore), "and is now:", int(score[mainMove]))
                
        n += 1
        print("N and Depth", n, depth)
        if n == depth:
            return score

        else:
            print("N and Depth not equal", n, depth)
            evaluateState(simGameState, nextMove, n, mainMove)
    print("Score for move is", score)
    return score    

# Start server when `python main.py` is run
if __name__ =="__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
