from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import pandas as pd
import uuid
import json
import os
import time

# Use environment variable to determine the data directory
DATA_DIR = os.getenv("DATA_DIR", ".")
GAMES_FILE = os.path.join(DATA_DIR, "games.json")
CHAT_DATA_DIR = os.path.join(DATA_DIR, "chat_data")

# Ensure directories exist
os.makedirs(CHAT_DATA_DIR, exist_ok=True)

templates = Jinja2Templates(directory="templates")

app = FastAPI()

# Load games data from the volume
if os.path.exists(GAMES_FILE):
    with open(GAMES_FILE, "r") as f:
        games = json.load(f)
else:
    games = {}

def get_next_round(game_id: str) -> Dict[str, Any]:
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game["last_played"] = time.time()

    if not os.path.exists(game["filename"]):
        raise HTTPException(status_code=404, detail="Game data file not found")

    df = pd.read_csv(game["filename"])

    required_columns = {'username', 'message', 'date', 'score'}
    if not required_columns.issubset(df.columns):
        raise HTTPException(status_code=400, detail="CSV file is missing required columns")

    sampled_index = df[df['score'] > 3].sample(1).index.item()

    played_indices = game.setdefault("played_indices", [])
    played_indices.append(sampled_index)
    played_indices = list(set(played_indices))
    game["played_indices"] = played_indices

    with open(GAMES_FILE, "w") as f:
        json.dump(games, f)

    return_data = {
        "group": game["group"],
        "game_id": game_id,
        "solution": [],
        "messages": []
    }

    seen_authors = []
    for offset in range(game["message_num"], 0, -1):
        message_data = df.loc[sampled_index - offset]
        member_index = int(message_data["username"].split(" ")[1]) - 1

        if message_data["username"] not in seen_authors:
            return_data["solution"].append(game["group"]["members"].split(",")[member_index])
            seen_authors.append(message_data["username"])
        anonymized_index = seen_authors.index(message_data["username"])

        return_data["messages"].append({
            "content": message_data["message"],
            "date": message_data["date"].split(" ")[0],
            "time": message_data["date"].split(" ")[1][:-3],
            "author": game["members_nickname"] + " " + str(anonymized_index + 1)
        })

    return_data["unique_authors"] = []
    for m in return_data["messages"]:
        if m["author"] not in return_data["unique_authors"]:
            return_data["unique_authors"].append(m["author"])
    return_data["members"] = game["group"]["members"].split(",")

    for message in return_data["messages"]:
        for j, author in enumerate(game["group"]["members"].split(",")):
            person_placeholder = f"Person {j+1}"
            if person_placeholder in seen_authors:
                message["content"] = message["content"].replace(person_placeholder, game["members_nickname"] + " " + str(seen_authors.index(person_placeholder) + 1))
            else:
                message["content"] = message["content"].replace(person_placeholder, game["members_nickname"] + " ?")

    return return_data

@app.get("/create_game", response_class=HTMLResponse)
async def render_create_game(request: Request):
    return templates.TemplateResponse("create_game.html", {"request": request})

@app.post("/create_game", response_class=HTMLResponse)
async def create_game(request: Request, chat_scores: UploadFile = File(...), group_name: str = Form(...), members: str = Form(...), members_nickname: str = Form(...), message_num: int = Form(...)):
    game_id = str(uuid.uuid4())
    cvs_path = os.path.join(CHAT_DATA_DIR, f"{game_id}.csv")
    try:
        with open(cvs_path, "wb") as f:
            f.write(await chat_scores.read())
    except Exception as e:
        error_message = f"Failed to save file: {e}"
        return templates.TemplateResponse("create_game.html", {"request": request, "error_message": error_message})

    try:
        df = pd.read_csv(cvs_path)
    except Exception as e:
        os.remove(cvs_path)
        error_message = f"Failed to read CSV file: {e}"
        return templates.TemplateResponse("create_game.html", {"request": request, "error_message": error_message})

    required_columns = {'username', 'message', 'date', 'score'}
    if not required_columns.issubset(df.columns):
        os.remove(cvs_path)
        error_message = "CSV file is missing required columns"
        return templates.TemplateResponse("create_game.html", {"request": request, "error_message": error_message})

    df = df.dropna(subset=['message'])

    if len(members.split(",")) < df['username'].nunique():
        os.remove(cvs_path)
        error_message = "Number of members must be greater or equal to the number of unique authors in the chat"
        return templates.TemplateResponse("create_game.html", {"request": request, "error_message": error_message, "num_members": df['username'].nunique()})

    if len(df) < int(message_num):
        os.remove(cvs_path)
        error_message = f"CSV file must have at least {message_num} messages"
        return templates.TemplateResponse("create_game.html", {"request": request, "error_message": error_message})
    
    df.to_csv(cvs_path, index=False)
    games[game_id] = {
        "filename": cvs_path,
        "group": {"name": group_name, "members": members},
        "message_num": int(message_num),
        "members_nickname": members_nickname.strip(),
        "created_at": time.time(),
    }

    with open(GAMES_FILE, "w") as f:
        json.dump(games, f)

    response = RedirectResponse(url=f"/game/{game_id}", status_code=303)
    return response


@app.get("/game/{game_id}", response_class=HTMLResponse)
async def render_game(request: Request, game_id: str):
    if game_id not in games:
        return RedirectResponse(url="/")
    try:
        data = get_next_round(game_id)
    except HTTPException as e:
        return HTMLResponse(status_code=e.status_code, content=e.detail)
    data["request"] = request
    return templates.TemplateResponse("game.html", data)

def delete_game(game_id):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    filename = games[game_id]["filename"]
    if os.path.exists(filename):
        os.remove(filename)
    games.pop(game_id, None)
    with open(GAMES_FILE, "w") as f:
        json.dump(games, f)

@app.get("/game/{game_id}/delete")
async def delete_game_endpoint(game_id: str):
    try:
        delete_game(game_id)
    except HTTPException as e:
        return HTMLResponse(status_code=e.status_code, content=e.detail)
    return RedirectResponse(url="/")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)