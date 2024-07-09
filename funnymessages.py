## Step 1: read WhatsApp chat
from whatstk import df_from_whatsapp
import re
import sys
import os
import ollama
from tqdm import tqdm

DEBUG = True
if len(sys.argv) < 2:
    print("Usage: python funnymessages.py <chat.txt>")
    sys.exit(1)
if sys.argv[1].endswith('.csv'):
    import pandas as pd
    df = pd.read_csv(sys.argv[1])
else:
    df = df_from_whatsapp(sys.argv[1])

df = df.dropna(subset=['message'])
df = df[~df['message'].str.contains('omitted')]
df = df[~df['message'].str.contains('live location shared')]
df['message'] = df['message'].str.replace(' <This message was edited>', '')

usernames = df['username'].unique()
phone_numbers = set(df['message'].str.extract(r'@(\d{11,})').dropna().values.flatten())
if phone_numbers:
    users_string = "\n".join([f"{name}: {i}" for i, name in enumerate(usernames)])
    for p in phone_numbers:
        try:
            i = int(input(f"Which username does +{p} belong to? \n{users_string}\n>> "))
            df['message'] = df['message'].str.replace(f'@{p}', usernames[i])
        except:
            print(f"Invalide input for {p} - must be a number from 0 to {len(usernames)-1}")
    

for i, username in enumerate(usernames):
    df['username'] = df['username'].str.replace(username, f'Person {i+1}')
    df['message'] = df['message'].str.replace(username, f'<Person {i+1}>', flags=re.IGNORECASE)
    # remove possible artifacts, where the message has multiple <: <<<Person 1>>>
    df['message'] = df['message'].str.replace(f'<Person {i+1}>+', f'<Person {i+1}>', flags=re.IGNORECASE)

    print(f'Person {i+1} -> {username}')


df.to_csv("chat_tmp.csv", index=False)

index_last = 0
try:
    index_last = df[df['score'].notnull()].index[-1] - 2
    print(f"Detected scores, restarting from index {index_last}...")
except:
    pass

## Step 2: find funny messages
instructions = {'role': 'system', 'content': 'On a scale from 1 to 5, how weird is this conversation? [ONLY REPLY WITH A NUMBER - 1 is not weird, 5 is very weird]'}

def llm_response(messages):
    response = ollama.chat(
        model='qwen2:0.5b',
        messages=[instructions, {'role': 'user', 'content': messages}],
        options={'num_predict': 2}
    )['message']['content']
    return response

num_messages = 3
try:
    for i in tqdm(range(index_last, len(df)-(num_messages-1))):
        messages = f"{df.iloc[i]['username']}: {df.iloc[i]['message']}\n"
        for j in range(1, num_messages):
            messages += f"{df.iloc[i+j]['username']}: {df.iloc[i+j]['message']}\n"
        response = llm_response(messages)
        try:
            score = int(''.join(filter(str.isdigit, response[:2])))
            if score > 5:
                score = 5
            df.loc[i+2, 'score'] = score
            if score > 3 and DEBUG:
                tqdm.write(messages)
        except Exception as e:
            tqdm.write(f"Error: {e} - {response}")
except KeyboardInterrupt:
    df.to_csv("chat_tmp.csv", index=False)
    print("Interrupted, saving progress in chat_tmp.csv")
    exit(0)

# remove nan values
df = df.dropna(subset=['message'])
# remove tmp file
os.remove("chat_tmp.csv")
df.to_csv("chat_scores.csv", index=False)