from openai import OpenAI
from flask import current_app


def improve_post(text: str, similar_posts: list = None) -> str:
    client = OpenAI(
        api_key=current_app.config['OPENROUTER_API_KEY'],
        base_url='https://openrouter.ai/api/v1'
    )

    context = ''
    if similar_posts:
        context = (
            '\n\nHere are some similar posts from the community. '
            'Use them as stylistic reference — do not copy them:\n'
        )
        for i, post in enumerate(similar_posts, 1):
            context += f'{i}. {post.body}\n'

    response = client.chat.completions.create(
        model='openai/gpt-oss-120b:free',
        max_tokens=200,
        messages=[{
            'role': 'user',
            'content': (
                'Improve the following microblog post to make it more engaging, '
                'clear, and expressive.'
                f'{context}'
                'Return ONLY the improved post text with no explanation or quotes. '
                'Keep it under 140 characters.\n\n'
                f'Post: {text}'
            )
        }],
        extra_body={'reasoning': {'enabled': True}}
    )
    return response.choices[0].message.content.strip()
