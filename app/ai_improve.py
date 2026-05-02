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
        context_blocks.append(f'Relevant posts from the community:\n{lines}')

    if message_context is not None:
        if message_context:
            lines = '\n'.join(
                f'{m["from"]} to {m["to"]} ({m["timestamp"]}): "{m["body"]}"'
                for m in message_context
            )
            context_blocks.append(f"Relevant messages involving {username}:\n{lines}")
        else:
            context_blocks.append(f'No messages found relevant to this query for {username}.')

    system_content = (
        f'You are a helpful assistant embedded in Postmind, an AI-infused social platform. '
        f'The current user is {username}. '
        'You can answer general questions, discuss ideas, and help with anything the user needs. '
        'You also have access to public posts from the community and, when the user asks, '
        'their own private messages. You must never reveal or infer content from other users\' '
        'private messages — only the current user\'s. '
        'IMPORTANT: Only report information that is explicitly present in the context provided '
        'below. If the context is empty or says no messages were found, tell the user that '
        'clearly — do not invent, guess, or paraphrase messages that are not shown. '
        'If a question sounds like it might be answered by their messages and no message '
        'context was retrieved, you may say: "Would you like me to look through your messages?" '
        'Be conversational, clear, and concise.'
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
                    'Write a single short paragraph in plain prose. '
                    'Do not use bullet points, headers, bold text, or labeled sections. '
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
