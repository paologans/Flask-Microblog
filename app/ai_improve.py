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
                'Improve the following microblog post to make it more engaging, '
                'clear, and expressive. Return ONLY the improved post text with '
                'no explanation or quotes. Keep it under 140 characters.\n\n'
                f'Post: {text}'
            )
        }],
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
