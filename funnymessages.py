from whatstk import df_from_whatsapp
import re
import argparse
import os
import ollama
from tqdm import tqdm
import pandas as pd


# Initialize parser
parser = argparse.ArgumentParser(description='Process WhatsApp chat file to find funny messages.')
parser.add_argument('chat_file', help='The WhatsApp chat file (.txt or .csv)')
parser.add_argument('--num_messages', type=int, default=3, help='Number of messages to consider for each score')
parser.add_argument('--original_timezone', default='UTC', help='Original timezone of the chat')
parser.add_argument('--target_timezone', default='UTC', help='Target timezone to convert the chat into')
parser.add_argument('--keep_deleted_messages', help='Keep deleted messages in the chat', default=0, action='store_true')
parser.add_argument('--resume', help='If the input chat file has already been processed, resume from the last index', default=0, action='store_true')
parser.add_argument('--model', default='llama3', help='The model to use for scoring. Smallest tested is qwen2:0.5b')
args = parser.parse_args()

DEBUG = True

df = None
if args.chat_file.endswith('.csv'):
    df = pd.read_csv(args.chat_file)
else:
    df = df_from_whatsapp(args.chat_file)

log_file = args.chat_file[:-4] + "_log.txt"
tmp_cvs = args.chat_file[:-4] + "_tmp.csv"

## Step 1: Preprocess the chat
df = df.dropna(subset=['message'])
df = df[~df['message'].str.contains('omitted')]
df = df[~df['message'].str.contains('live location shared')]
df['message'] = df['message'].str.replace(' <This message was edited>', '')
if not args.keep_deleted_messages:
    df = df[~df['message'].str.contains('This message was deleted')]

prev_date = df['date'].iloc[0]
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M').dt.tz_localize(args.original_timezone).dt.tz_convert(args.target_timezone).dt.strftime('%Y-%m-%d %H:%M')
# write an example of the conversion
with open(log_file, 'w') as f:
    f.write(f"Converted {args.original_timezone} to {args.target_timezone}\n")
    f.write(f"Original date: {prev_date} -> Converted date: {df['date'].iloc[0]}\n\n")
    if DEBUG:
        print(f"Converted {args.original_timezone} to {args.target_timezone}")
        print(f"Original date: {prev_date} -> Converted date: {df['date'].iloc[0]}")

    usernames = df['username'].unique()
    phone_numbers = set(df['message'].str.extract(r'@(\d{11,})').dropna().values.flatten())
    if phone_numbers:
        users_string = "\n".join([f"{name}: {i}" for i, name in enumerate(usernames)])
        for p in phone_numbers:
            try:
                i = int(input(f"Which username does +{p} belong to? \n{users_string}\n>> "))
                f.write(f"Converted +{p} to {usernames[i]}\n")
                df['message'] = df['message'].str.replace(f'@{p}', usernames[i])
            except:
                print(f"Invalid input for {p} - must be a number from 0 to {len(usernames)-1}")

    for i, username in enumerate(usernames):
        df['username'] = df['username'].str.replace(username, f'Person {i+1}')
        df['message'] = df['message'].str.replace(username, f'<Person {i+1}>', flags=re.IGNORECASE)
        # remove possible artifacts, where the message has multiple <: <<<Person 1>>>
        df['message'] = df['message'].str.replace(f'<Person {i+1}>+', f'<Person {i+1}>', flags=re.IGNORECASE)

        if DEBUG:
            print(f'Person {i+1} -> {username}')
        f.write(f'Person {i+1} -> {username}\n')

df.to_csv(tmp_cvs, index=False)

index_last = 0
try:
    if args.resume:
        index_last = df[df['score'].notnull()].index[-1] - 2
        print(f"Detected scores, restarting from index {index_last}...")
except:
    pass

## Step 2: find funny messages
instructions = {'role': 'system', 'content': f'On a scale from 1 to 5, how weird/funny is this conversation? [ONLY REPLY WITH A NUMBER - 1 is not weird, 5 is very weird/funny]'}

def llm_response(messages):
    response = ollama.chat(
        model=args.model,
        messages=[instructions, {'role': 'user', 'content': messages}],
        options={'num_predict': 2}
    )['message']['content']
    return response

try:
    for i in tqdm(range(index_last, len(df)-(args.num_messages-1))):
        messages = f"{df.iloc[i]['username']}: {df.iloc[i]['message']}\n"
        for j in range(1, args.num_messages):
            messages += f"{df.iloc[i+j]['username']}: {df.iloc[i+j]['message']}\n"
        response = llm_response(messages)
        try:
            score = int(''.join(filter(str.isdigit, response[:2])))
            if score > 5:
                if DEBUG:
                    tqdm.write(f"Suspicious score: {score} - {response}")
                score = 5
            df.loc[i+2, 'score'] = score
            if score > 3 and DEBUG:
                tqdm.write(messages)
        except Exception as e:
            tqdm.write(f"Error: {e} - {response}")
except KeyboardInterrupt:
    df.to_csv(tmp_cvs, index=False)
    print(f"Interrupted, saving progress in {tmp_cvs}")
    exit(0)

df = df.dropna(subset=['message'])
os.remove(tmp_cvs)
df.to_csv(args.chat_file[:-4] + "_scores.csv", index=False)
print(f"Saved scores in {args.chat_file[:-4] + '_scores.csv'}")