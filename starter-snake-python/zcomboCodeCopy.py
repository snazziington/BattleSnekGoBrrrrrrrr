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

# endregion

# For each possible move:
    # [0] = x vector, [1] = y vector, [2] = string direction
moves = [[0, 1, "up"], [0, -1, "down"], [-1, 0, "left"], [1, 0, "right"]]

deathScore = -10000
hazardHealthBarrier = 10 # The min. amount of health our snake wants
                         # to have after passing through a hazard

floodFillWeight = 3 # this is the number the floodFill score is multiplied by for scoring
foodDistancePenalty = 1
hungryBounds = 40

# DIFF: below = 1
tailFollowWeight = 1 # demerit when chasing own tail. otherwise it does it repeatedly and is easily trapped
hazardWeight = 0.1 # multiplies the death score by this (adds a demerit to moving through hazards)
chanceCollisionWeight = 0.5
tailSideFloodFillWeight = 5 # multiplies score of floodFill by this
                            # number if the tail is on that side

nonLethalHazardWeight = .25 # the score for moving into a hazardous space is equal
                            # to the deathScore multiplied by this number.

def wallCollision(nextMove, boardWidth, boardHeight):
    if (nextMove['x'] == boardWidth or nextMove['x'] == -1 or
        nextMove['y'] == boardHeight or nextMove['y'] == -1):
        return True

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

    if myTail == start:
        count *= tailSideFloodFillWeight
        print("Multiplying flood fill value bcs next move is tail")

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
    newState["you"]["health"] -= 1

    newHead = movePoint(myHead, move) # new head position = old head position moved
                                    # to the direction we're moving
    newBody = state["you"]["body"]
    newBody.insert(0, newHead)

    # need to print simulate game state to ensure it is correctly applying the new head and such stuff
    # food
    ateFood = False
    for food in state["board"]["food"]:
        if food == newHead:
            newState["you"]["health"] = 100
            ateFood = True
        elif newState["you"]["health"] == 100:
            ateFood = True

    # If no food was eaten, body shrinks by 1. If food was eaten, body will remain lengthened
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
        
    # If hazards would kill us and there is no food on the hazard, add them to the occupied tiles list
    if hazardKillCheck(state, hazardDamage):
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
            pot.remove(coords)
    return pot

def hazardLocations(state):
    hazardSet = list()
    for f in state["board"]["hazards"]:
        hazardSet.append(f)
    return hazardSet

def preferCentreofMap(point, board):
    # We prefer our snake being nearer to the middle.
    # Therefore, we will give a bonus to a move's score if it is near the centre of the board
    centreBoard = {"x": board["width"] / 2, "y": board["height"] / 2}
    centreBoard["x"] = board["width"] / 2

    centreDis = abs(point["x"] - centreBoard["x"]) + abs(point["y"] - centreBoard["y"])
    return centreDis    

def move(game_state: typing.Dict) -> typing.Dict:
    print("=============================")
    print("=============================")
    print("TURN:", {game_state['turn']})

    # region Initialisation
    # Snake Head + Neck
    myHead = game_state["you"]["body"][0]
    myTail = game_state["you"]["body"][len(game_state["you"]["body"]) - 1]

    # Board dimensions
    boardWidth = game_state['board']['width']
    boardHeight = game_state['board']['height']

    # region Calc Hazard Damage
    hazardRound = game_state["turn"] % 175
    if hazardRound < 25:
        hazardDamage = 0
    
    elif hazardRound < 50:
        hazardDamage = 14
    
    elif hazardRound < 75:
        hazardDamage = 28
    
    elif hazardRound < 100:
        hazardDamage = 42
    
    elif hazardRound < 150:
        hazardDamage = 56

    else:
        hazardDamage = 0
    print("Hazardddddd Damage:", hazardDamage)
    # endregion
    
    # Scores of each direction initialise as 0
    score = [0, 0, 0, 0] # up, down, left, right

    # endregion
    # Check Collisions
    for m in range (0, 4): # For each possible move (up, down, left, right)
        print("...")
        nextMove = {'x': 0, 'y': 0}
        nextMove['x'] = myHead["x"] + moves[m][0]
        nextMove['y'] = myHead["y"] + moves[m][1]

        # New coords of head if doing this move
        print("If moving", moves[m][2], ", head will go from", myHead, "to", nextMove)

        # Simulates next move
        simGameState = simulateMove(game_state, moves[m][2], myHead)

        # occupiedTiles 
        occupiedTiles = occupiedPositions(game_state, hazardDamage)
        print("Hazard Locations:", hazardLocations(game_state))
        print("Hazard Damage", hazardDamage)
        print("Next move:", nextMove)
        #print("Potential Collisions:", potentialCollisions(game_state))

        # Avoid Wall/Snake Collisions (and Hazard collisions if it would kill)
        if wallCollision(nextMove, boardWidth, boardHeight):
                score[m] += deathScore
                print("Cannot move", moves[m][2], ", will collide with wall")
                print("Score changed by:", deathScore, "New score: ", score[m])
        
        floodFillValue = floodFill(nextMove, simGameState["board"], occupiedTiles, myTail)

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
            print("Heeeeealth", simGameState["you"]["health"])
            for food in foodLocations(game_state):
                foodDist = min(abs(nextMove["x"]-food["x"]) + abs(nextMove["y"]-f["y"]) for f in simGameState["board"]["food"])
                if game_state["you"]["health"] < hungryBounds:
                    foodScore -= foodDist * foodDistancePenalty
                    totalFoodDist -= foodDist
            score[m] += foodScore
            print("Hungry. TotalFoodDist:", totalFoodDist)
            print("Score changed by:", foodScore, "New score: ", score[m])
            
            
            # Reduce score if hazard will damage you
            if nextMove in hazardLocations(game_state):
                # TODO: I feel like the weighting of the hazard 
                # should depend on how much damage it does... Not necessary though
                print("Hazard Damage", hazardDamage)
                score[m] *= hazardWeight
                print("hazardDamage:", hazardDamage)
                print("Score multiplied by:", hazardWeight, "New score: ", score[m])

            # Reduce score by multiplier if collision with larger snake is possible
            if nextMove in potentialCollisions(game_state, myHead) and game_state['turn'] > 1:
                print("Preferably not moving", moves[m][2], ", may collide with a larger snake")
                score[m] *= chanceCollisionWeight
                print("Score multiplied by:", chanceCollisionWeight, "New score: ", score[m])
            
            if nextMove in checkSnakeTiles(game_state):
                # Check if chasing own tail + did not just eat food
                if nextMove == myTail and game_state["you"]["health"] != 100 and game_state['turn'] > 2:
                    print("Chasing own tail", game_state["you"]["health"])
                    score[m] *= tailFollowWeight
                    print("Score multiplied by", tailFollowWeight, "New score:", score[m])
                
                else:
                    score[m] += deathScore
                    print("Cannot move", moves[m][2], ", will collide with a body")
                    print("Score changed by:", deathScore, "New score: ", score[m])
        print("Score for moving", moves[m][2], "is:", score[m])
    
    print("All scores:", score)
    maxScore = max(score) # Maximum score found in the score array
    scoreValues = np.array([score[0], score[1], score[2], score[3]]) # We use numpy here so we can use ".where"
    bestMoves = np.where(scoreValues == maxScore)[0]
    print("The best possible moves are:", bestMoves)

    nextMove = random.choice(bestMoves)
    print("The next move is", moves[nextMove][2])
    return {"move": moves[nextMove][2]}

# Start server when `python main.py` is run
if __name__ =="__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
