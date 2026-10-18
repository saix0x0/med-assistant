"""One working Sarvam call — proves the key + SDK are live.

This is the minimal "hello world" for Sarvam: it initializes the client and makes
one chat completion with sarvam-105b-conversations, then prints the reply. The key
is read from the environment (.env) — never hardcoded, never printed.

Run:
    .venv/bin/python -m scripts.hello_sarvam

Needs SARVAM_API_KEY set in .env first.
"""
from app import config


def main():
    if not config.SARVAM_API_KEY:
        print("No SARVAM_API_KEY found. Paste your key into .env, then re-run.")
        return

    from sarvamai import SarvamAI
    client = SarvamAI(api_subscription_key=config.SARVAM_API_KEY)

    messages = [{"role": "user",
                 "content": "Reply in one short English sentence to confirm you are working."}]
    try:
        resp = client.chat.completions(model=config.CHAT_MODEL, messages=messages)
    except TypeError:
        # some SDK versions expose .create(...)
        resp = client.chat.completions.create(model=config.CHAT_MODEL, messages=messages)

    print("Model:", config.CHAT_MODEL)
    print("Reply:", resp.choices[0].message.content)


if __name__ == "__main__":
    main()
