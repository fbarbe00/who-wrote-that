# Who Sent This S#it?

Welcome to "Who sent this s#it?", a fun game where you guess who sent random funny/weird messages from your group chat. Currently, only WhatsApp chat data works out of the box. Other chats must follow the same format: columns of the chat must be: `username, content, date, [score]`.

## Getting Started

Follow these steps to get started:

### Step 1: Export Your WhatsApp Chat Data

1. Export your WhatsApp chat data from an English-speaking phone.

### Step 2: Install Dependencies

1. Download and install [Ollama](https://ollama.com/download).
2. Install the necessary dependencies by running:
    ```bash
    pip install -r requirements.txt
    ```

### Step 3: Process Your Chat Data

Execute the following Python code to process your chat data:

```python
## Step 1: Read WhatsApp Chat
from whatstk import df_from_whatsapp
import re
DEBUG = False
OLLAMA_MODEL = 'qwen2:0.5b'
df = df_from_whatsapp("chat.txt")

df = df[~df['message'].str.contains('omitted')]
df = df[~df['message'].str.contains('live location shared')]
df['message'] = df['message'].str.replace(' <This message was edited>', '')
df is df.dropna(subset=['message'])

usernames = df['username'].unique()
phone_numbers = set(df['message'].str.extract(r'@(\d{11,})').dropna().values.flatten())
if phone_numbers:
    users_string = " - ".join([f"{name}: {i}" for i, name in enumerate(usernames)])
    for p in phone_numbers:
        try:
            i = int(input(f"Which username does {p} belong to? {users_string}"))
            df['message'] = df['message'].str.replace(f'@{p}', usernames[i])
        except:
            print(f"Invalid input for {p} - must be a number from 0 to {len(usernames)-1}")

for i, username in enumerate(usernames):
    df['username'] = df['username'].str.replace(username, f'Person {i+1}')
    df['message'] = df['message'].str.replace(username, f'<Person {i+1}>', flags=re.IGNORECASE)

    print(f'Person {i+1} -> {username}')

index_last = 0
try:
    index_last = df[df['score'].notnull()].index[-1] - 2
    print(f"Detected scores, restarting from index {index_last}...")
except:
    pass

## Step 2: Find Funny Messages
import ollama
from tqdm import tqdm
instructions = {'role': 'system', 'content': 'On a scale from 1 to 5, how weird is this conversation? [ONLY REPLY WITH A NUMBER - 1 is not weird, 5 is very weird]'}

# Iterate through all messages, three at a time
for i in tqdm(range(index_last, len(df)-2)):
    messages = f"{df.iloc[i]['username']}: {df.iloc[i]['message']}\n"
    messages += f"{df.iloc[i+1]['username']}: {df.iloc[i+1]['message']}\n"
    messages += f"{df.iloc[i+2]['username']}: {df.iloc[i+2]['message']}\n"
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[instructions, {'role': 'user', 'content': messages}],
        options={'num_predict': 2}
    )['message']['content']
    try:
        score = int(response[:2].replace(".", "").strip())
        df.loc[i+2, 'score'] = score
        if score > 3 and DEBUG:
            tqdm.write(messages)
    except Exception as e:
        tqdm.write(f"Error: {e} - {response}")

# Remove NaN values
df = df.dropna(subset=['message'])
df.to_csv("chat_scores.csv", index=False)
```

Once you have processed the chat data, you'll get a file with the funniest messages scored. Use this file to start playing the game!

## Running the Server

To run the server, simply run:

```bash
python server.py
```

## Requirements

All necessary dependencies are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```

Enjoy the game!

## TODOs
Things I'd like to add/improve:
- add multiplayer with sockets
- run the llm analysis in the background with qwen2:0.5b
- add job to remove old scripts
- add group picture
- find a proper name (and keep it consistent)
- better color palets