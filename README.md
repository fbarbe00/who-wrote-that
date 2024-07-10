# Who Sent This s#%t?

Welcome to "Who sent this s#%t?", a fun game where you guess who sent random funny/weird messages from your group chat. Currently, only WhatsApp chat data works out of the box. Other chats must follow the same format: columns of the chat must be: `username, content, date, [score]`.

## Getting Started

Follow these steps to get started:

### Step 1: Export Your WhatsApp Chat Data

1. Export your WhatsApp chat data from an English-speaking phone.

### Step 2: Install Dependencies

1. Download and install [Ollama](https://ollama.com/download).
2. Install the necessary dependencies by running:
    ```bash
    pip install whatstk ollama tqdm
    ```

### Step 3: Process Your Chat Data

Execute the python script `funnymessages.py`:

```sh
python funnymessages.py
```

Once you have processed the chat data, you'll get a file with the funniest messages scored. Use this file to start playing the game!

## Running the Server

To run the server, simply run:

```bash
python server.py
```

You can also run this with docker, simply use:

```bash
docker build -t who-wrote-that .
docker run -d -p 8000:8000 -v $(pwd):/app/data --name who-wrote-that --restart always who-wrote-that
```

(replace `$(pwd)` with the directory you want your data to be stored at)

## Requirements

All necessary dependencies are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```

Enjoy the game!

## TODOs
Things I'd like to add/improve:
- [ ] Turn this into a multiplayer game! Each client communicate with the server and has a limited amount of time to guess. Whoever has the most points wins. You can then get stats like "most guessed member", how many times each member appeared, and the leaderboard
- [ ] display most human-liked chats
- [ ] allow each chat to have a unique URL
- [ ] allow users to upload their chat export and run the llm server-side
- [ ] add job to remove old scripts
- [ ] add group picture
- [ ] find a proper name (and keep it consistent)
- [ ] fix issue with long member names on mobile