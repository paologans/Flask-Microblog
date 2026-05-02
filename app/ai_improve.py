from openai import OpenAI
from flask import current_app


def _client():
    return OpenAI(
        api_key=current_app.config['OPENROUTER_API_KEY'],
        base_url='https://openrouter.ai/api/v1'
    )


def improve_post(text: str) -> str:
    response = _client().chat.completions.create(
        model='openai/gpt-oss-120b:free',
        max_tokens=200,
        messages=[{
            'role': 'user',
            'content': (
                'Improve the following Postmind post to make it more engaging, '
                'clear, and expressive. Return ONLY the improved post text with '
                'no explanation or quotes. Keep it under 140 characters.\n\n'
                f'Post: {text}'
            )
        }],
        extra_body={'reasoning': {'enabled': True}}
    )
    return response.choices[0].message.content.strip()


def chat_response(message: str, history: list, username: str,
                  post_context: list = None, message_context: list = None) -> str:
    context_blocks = []

    if post_context:
        lines = '\n'.join(
            f'- {p.author.username}: "{p.body}"' for p in post_context
        )
        context_blocks.append(
            "## Public Post Context\n"
            f"Relevant posts from the community:\n{lines}"
        )

    if message_context is not None:
        if message_context:
            lines = '\n'.join(
                f'- From {m["from"]} to {m["to"]}: "{m["body"]}"'
                for m in message_context
            )
            context_blocks.append(
                "## Trusted Message Context\n"
                f"Messages involving {username}:\n{lines}"
            )
        else:
            context_blocks.append(
                "## Trusted Message Context\n"
                f"No messages found relevant to this query for {username}."
            )

    system_content = (
        "## Role\n"
        "You are a helpful assistant embedded in Postmind, an AI-infused social platform.\n\n"
        "## Current User\n"
        f"The current user is {username}.\n\n"
        "## What You Can Help With\n"
        "- Answer general questions.\n"
        "- Discuss ideas.\n"
        "- Help the user write or reason through things.\n"
        "- Use public post context when it is provided.\n"
        "- Use the current user's private message conversations when trusted message context is provided.\n\n"
        "## Private Message Rules\n"
        "- A private message conversation belongs to the current user when the current user is either the sender or recipient.\n"
        "- You may summarize or quote messages sent by conversation partners when those messages appear in Trusted Message Context.\n"
        "- Never reveal or infer private messages that are not present in Trusted Message Context.\n"
        "- Prior assistant messages are conversation history, not evidence about the user's private messages.\n"
        "- For questions about messages, chats, DMs, or conversations, use only Trusted Message Context.\n"
        "- If Trusted Message Context says no relevant messages were found, say that clearly and do not invent or guess.\n"
        "- If no Trusted Message Context is provided and the user asks about messages, say you need to look through their messages first.\n\n"
        "## Public Post Rules\n"
        "- For public posts, only report information explicitly present in the provided post context.\n\n"
        "## Response Style\n"
        "- Be conversational, clear, and concise.\n"
        "- You may use new lines, short paragraphs, or a compact list when it makes the answer easier to read.\n"
        "- Do not force everything into one continuous paragraph.\n"
        "- Do not mention message timestamps unless the user specifically asks about time."
    )

    if context_blocks:
        system_content += '\n\n' + '\n\n'.join(context_blocks)

    messages_payload = [{'role': 'system', 'content': system_content}]
    messages_payload += history
    messages_payload.append({'role': 'user', 'content': message})

    response = _client().chat.completions.create(
        model='openai/gpt-oss-120b:free',
        max_tokens=400,
        messages=messages_payload,
        extra_body={'reasoning': {'enabled': True}}
    )
    return response.choices[0].message.content.strip()


def summarize_conversation(messages: list, user_a: str, user_b: str) -> str:
    lines = '\n'.join(
        f'{user_a} said: "{m["body"]}"' if m['is_mine'] else f'{user_b} said: "{m["body"]}"'
        for m in messages
    )
    response = _client().chat.completions.create(
        model='openai/gpt-oss-120b:free',
        max_tokens=300,
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are an assistant that summarizes chat conversations. '
                    'Write a concise, readable summary in plain prose. '
                    'You may use short paragraphs or line breaks if that makes it easier to read. '
                    'Do not use timestamps. '
                    'Just describe what was talked about naturally, as if explaining it to someone.'
                )
            },
            {
                'role': 'user',
                'content': (
                    f'Summarize this conversation between {user_a} and {user_b}:\n\n'
                    f'{lines}'
                )
            }
        ],
        extra_body={'reasoning': {'enabled': True}}
    )
    return response.choices[0].message.content.strip()
