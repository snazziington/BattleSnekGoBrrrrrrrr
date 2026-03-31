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
       "author":"Snazziington",  # TODO: Your Battlesnake Username
       "color":"#6B57E0",  # TODO: Choose color
       "head":"beluga",  # TODO: Choose head
       "tail":"do-sammy",  # TODO: Choose tail
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

collisionScore = -1000

floodFillWeight = 1
chanceCollisionWeight = .75
tailFollowWeight = .8

def wallCollision(nextMove, boardWidth, boardHeight):
    if nextMove['x'] == boardWidth or nextMove['x'] == -1 or nextMove['y'] == boardHeight or nextMove['y'] == -1:
        return True
    
def checkSnakeTiles(game_state: typing.Dict):
    snakeBodyTiles = list()

    for snake in game_state["board"]["snakes"]:
        snakeBody = snake["body"]
        for xy in snakeBody:
            snakeBodyTiles.append(xy)
    return snakeBodyTiles

def floodFill(start, board, occupied): # floodEvalPosition, boardState, occupiedTiles
    # Flood fill score for moving into wall is 0
    if start["x"] in {0, board["width"]} or start["y"] in {0, board["height"]}:
        return 0

    else:
        stack = [(start["x"], start["y"])]
        visited = set()
        count = 0

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue

            visited.add((x, y))
            count += 1

            for nx, ny in [(x + 1, y),(x - 1, y),(x, y + 1),(x, y - 1)]:
                if (0 <= nx < board["width"] and
                    0 <= ny < board["height"] and
                    (nx, ny) not in occupied):
                    stack.append((nx, ny))
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
    
def simulateMove(state, move):
    newState = {
        "you": {
            "body": list(state["you"]["body"]),
            "health": state["you"]["health"] - 1
        },
        "board": state["board"]
    }

    head = state["you"]["body"][0] # TODO: use def getHead(state)
    newHead = movePoint(head, move)

    newBody = [newHead] + newState["you"]["body"][:-1]

    # food
    for food in state["board"]["food"]:
        if food == newHead:
            newBody.append(newBody[-1])
            newState["you"]["health"] = 100

    newState["you"]["body"] = newBody
    return newState

def occupiedPositions(state):
    occ = list()
    # Adds current state of all snakes to the occ array
    for s in state["board"]["snakes"]:
        for b in s["body"]:
            bodyCoords = {'x': 0, 'y': 0}
            bodyCoords["x"] = b["x"]
            bodyCoords["y"] = b["y"]
            occ.append(bodyCoords)
        
    # Adds potential moves of other snakes to potPositions array
    
    for snake in state["board"]["snakes"]:
        if len(snake["body"]) > len(state["you"]): # TODO: Add a "+ 1" on the right side so our snake only
                                                   # ignores collisions with a snake *two* points smaller?
            head = snake["body"][0]
            for m in range (0, 4):
                coords = (head["x"] + moves[m][0], head["y"] + moves[m][1])
                occ.append(coords)
    print("occc:", occ)
    return occ

    # TODO: Exclude our snake from this^^ code block; our snake should not avoid its own potential moves lol

def potentialCollisions(state):
    pot = list()
    print("youuuu", state["you"])
    
    for snake in state["board"]["snakes"]:
        print("themmmm", snake["length"])
        if snake["length"] >= state["you"]["length"]:
            # TODO: Add a "+ 1" on the right side so our snake only ignores collisions with a
            # snake *two* points smaller?
            head = snake["body"][0]
            for m in range (0, 4):
                coords = {'x': 0, 'y': 0}
                coords["x"] = (head["x"] + moves[m][0])
                coords["y"] = (head["y"] + moves[m][1])
                pot.append(coords)
    return pot

def move(game_state: typing.Dict) -> typing.Dict:
    print("============")
    print("MOVE:", {game_state['turn']})
    print("Check Snake Tiles:", checkSnakeTiles(game_state))

    # region Initialisation
    # Snake Head + Neck
    myHead = game_state["you"]["body"][0]
    myTail = game_state["you"]["body"][len(game_state["you"]["body"]) - 1]

    # Board dimensions
    boardWidth = game_state['board']['width']
    boardHeight = game_state['board']['height']

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
        print("If moving", moves[m][2], ", head will be at:", nextMove)

        # Simulates next move
        print("Moooves: ", moves[m][2])
        simGameState = simulateMove(game_state, moves[m][2])
        occupiedTiles = occupiedPositions(simGameState)
        floodFillScore = floodFillWeight * floodFill(simGameState["you"]["body"][0], simGameState["board"], occupiedTiles)
        score[m] += floodFillScore

        print("floodFillScore:", floodFillScore)
        print("Next move:", nextMove)
        print("Potential Collisions:", potentialCollisions(game_state))

        if wallCollision(nextMove, boardWidth, boardHeight):
                score[m] += collisionScore
                print("Cannot move", moves[m][2], ", will collide with wall")

        # Avoid Snake Collisions
        elif nextMove in checkSnakeTiles(game_state):
            if nextMove == myTail:
                print("Chasing own tail")
                score[m] *= tailFollowWeight
            else:
                print("Check Snake Tiles:", checkSnakeTiles(game_state))
                score[m] += collisionScore
                print("Cannot move", moves[m][2], ", will collide with a body")

        elif nextMove in potentialCollisions(game_state):
            print("Cannot move", moves[m][2], ", may collide with a snake")
            score[m] *= chanceCollisionWeight
        
        print("Score for moving", moves[m][2], "is:", score[m])

    # Flood Fill
    # for possible moves above -100, check which place has more area

    # Food
    # For possible moves above -100, check nearest food source
    
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
