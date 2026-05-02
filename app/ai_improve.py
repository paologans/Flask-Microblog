from openai import OpenAI
from flask import current_app


def improve_post(text):
    client = OpenAI(
        api_key=current_app.config['OPENROUTER_API_KEY'],
        base_url='https://openrouter.ai/api/v1'
    )
    response = client.chat.completions.create(
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
        }]
    )
    return response.choices[0].message.content.strip()
