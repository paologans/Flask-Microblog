import json
import random
from datetime import datetime, timezone, timedelta
from faker import Faker
import sqlalchemy as sa
from app import create_app, db
from app.models import User, Post, Message
from app.embeddings import embed_batch

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# About me — coherent phrases or single sentences
# ---------------------------------------------------------------------------

ABOUT_ME = [
    "Reads too much, sleeps too little.",
    "Making things, mostly.",
    "Somewhere between figuring it out and pretending I already have.",
    "Still learning how to be here.",
    "Writer of lists, sender of long messages.",
    "Finds the interesting part in most things.",
    "Part-time overthinker, full-time coffee drinker.",
    "Trying to slow down and pay more attention.",
    "Better at starting things than finishing them.",
    "Currently reading three books at once and finishing none of them.",
    "Believes most problems can be solved by walking.",
    "Easily distracted by good questions.",
    "Works best in the late afternoon.",
    "More comfortable in small rooms than big ones.",
    "Chasing something, not sure what yet.",
    "Takes a long time to warm up but then won't stop talking.",
    "Deeply interested in how things work.",
    "Collects places more than things.",
    "Still figuring out what kind of person I want to be.",
    "Prefers the version of the day before anyone else wakes up.",
    "Fond of long conversations and short commutes.",
    "Has opinions about coffee that are probably too strong.",
    "Learning that rest is not the same as stopping.",
    "Always has a book nearby.",
    "Curious about people in a way that is hard to explain.",
    "Talks to strangers more than most people would expect.",
    "Good at remembering things that do not matter, bad at the things that do.",
    "Somewhere in the middle of a lot of things.",
    "Trying to write more and think less.",
    "The kind of person who stays until the last song.",
]

# ---------------------------------------------------------------------------
# Posts — phrases, sentences, and paragraphs
# ---------------------------------------------------------------------------

SHORT_POSTS = [
    "Needed that coffee more than I expected.",
    "Two hours of sleep. Still here.",
    "Something about today felt different.",
    "The quiet before everyone else wakes up.",
    "Finally.",
    "Of all the days.",
    "Managed to do one hard thing today and that feels like enough.",
    "The sky right now.",
    "Good grief.",
    "Running on nothing and somehow still moving.",
    "That was a lot.",
    "Back at it.",
    "One of those mornings.",
    "This city, sometimes.",
    "Almost.",
]

MEDIUM_POSTS = [
    "Been staring at the same paragraph for twenty minutes and I think the paragraph might be winning.",
    "Started the day earlier than planned and somehow it helped more than any amount of extra sleep would have.",
    "There is a specific kind of tired that only comes from caring too much about something, and I have been living in it lately.",
    "Cooked a proper meal for the first time in weeks and sat down to eat it like a person. Small victory.",
    "Called someone today just to say I was thinking of them. They picked up on the second ring.",
    "Every time I think I have figured something out about myself I find a new room I did not know existed.",
    "Spent an hour doing absolutely nothing and felt guilty the whole time, which kind of defeats the purpose.",
    "The version of this day I imagined last week and the version I actually got were completely different. Both fine.",
    "Took the long way home and remembered why I used to do that all the time.",
    "Said yes to something I normally would have avoided and it turned out to be exactly what I needed.",
    "Had a conversation today where I actually listened instead of waiting for my turn to talk. Felt different.",
    "The thing about finishing something is that the feeling is never quite what you imagined it would be.",
    "Woke up with an idea and wrote it down before it disappeared. That almost never happens.",
    "Some days the only thing you can do is get through them. Today was one of those and I got through it.",
    "Realized I have been carrying something for so long I forgot it was optional.",
    "Made a decision today that felt equal parts right and terrifying. I think that means it was the correct one.",
    "Three cups of coffee and a to-do list that keeps growing. This is fine.",
    "Ran into someone I had not seen in two years and we talked for an hour like no time had passed at all.",
]

LONG_POSTS = [
    "Been thinking about how much changes without you noticing. Last year feels like a completely different chapter — different worries, different rhythm, different version of waking up every morning. Not sure if that is growth or just time passing, but it feels significant either way.",
    "There is something about finishing a long project that feels less like relief and more like standing in a room after everyone has left. You wanted it to end and now it has, and the silence is louder than you expected. I finished something today. I am sitting in that silence now.",
    "Had one of those conversations today that you keep turning over afterward. Nothing dramatic was said. No revelations. But something landed in a way that is still sitting with me hours later, and I am not ready to analyze it yet. Some things need time before they make sense.",
    "I think the thing I am working on the most right now is letting things be good without immediately worrying about when they will stop. It is harder than it sounds. The moment something feels right I catch myself bracing for the part where it does not. Trying to just be in it instead.",
    "Spent the afternoon at a place I used to go all the time and have not been to in over a year. Everything was the same and I was completely different. That combination does something to you. Like holding a photograph of a room you still live in.",
    "The older I get the more I appreciate people who just say what they mean. No performance, no layering, no waiting to see which version of the truth lands best. Just here is what I think, here is how I feel. It is rarer than it should be and I am trying to be better at it myself.",
    "Something shifted this week and I cannot fully explain what. Less resistance, maybe. More willingness to let things be what they are instead of what I need them to be. I do not want to examine it too closely in case it goes away.",
    "Read something this morning that I keep coming back to. It was not a quote or a headline, just a line in an ordinary email, from an ordinary person describing an ordinary day. And somehow it got at something I have been trying to say for months. That happens sometimes and it never stops being surprising.",
    "Went for a walk with no destination and ended up somewhere I had never been, three blocks from where I have lived for four years. I think I have been moving too fast to actually see anything. Going to try to walk slower. Look up more. That kind of thing.",
    "There is a version of every day that exists only in the early morning before anything has happened yet. No decisions made, no mistakes committed, no context built up. Just the possibility of the day. I have been trying to stay in that feeling a little longer before the rest of it starts.",
]

POST_POOL = SHORT_POSTS + MEDIUM_POSTS + LONG_POSTS

# ---------------------------------------------------------------------------
# Conversations — natural flowing dialogue, mix of lengths and pacing
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    # Catching up after a while
    [
        "Hey. It has been a while. How are you actually doing?",
        "Honestly? Better than I was a few months ago. Still figuring some things out but I feel more like myself lately.",
        "That is good to hear. I was thinking about you the other day, wondered how things were going.",
        "I have been meaning to reach out. Life just gets in the way and then suddenly it is been three months.",
        "I know exactly what you mean. What has been going on?",
        "Work has been intense. I switched projects in the middle of everything which made the first few weeks rough. But it is settling down now.",
        "That timing sounds brutal.",
        "It was. But I think it was the right call. The old project was draining me in a way I was pretending not to notice.",
        "I have been there. Sometimes you need the chaos to finally make the move.",
        "Exactly. Anyway — what about you? What have I missed?",
        "Moved to a new place. Smaller but mine in a way the last one never felt.",
        "That is huge. How is it?",
        "Really good actually. I did not realize how much the old apartment was affecting my mood until I left it.",
    ],
    # Late night, neither can sleep
    [
        "Are you still awake?",
        "Yeah. Cannot turn my brain off tonight.",
        "Same. I have been lying here for over an hour.",
        "What are you thinking about?",
        "Nothing specific. Just that low hum of everything that is unresolved.",
        "I know that feeling exactly. It is not even worry, just... presence.",
        "Yes. Like your brain refuses to let the day end.",
        "Getting up helps me sometimes. Making tea, sitting somewhere that is not the bed.",
        "I might try that. I keep thinking if I just lie still long enough it will happen.",
        "Lying still definitely makes it worse for me. The stillness gives the thoughts more room.",
        "You are probably right. Okay. I am going to make tea.",
        "Good call. Hope it works.",
        "Thanks for being awake.",
        "Anytime. Sleep well when it comes.",
    ],
    # Processing a big decision
    [
        "Can I think out loud at you for a minute?",
        "Always. What is going on?",
        "I have been offered something. A role I did not expect and have been staring at the email for two days without responding.",
        "What is making you hesitate?",
        "It would mean leaving a team I really like. And moving to something completely different. The kind of different where you cannot really know what you are getting into until you are already in it.",
        "Is the hesitation about the people or the uncertainty?",
        "Both. Mostly the uncertainty, I think. I have been in this role long enough that I know what I am doing. The new thing would put me back at zero.",
        "That is uncomfortable but it is also the part that sounds most interesting.",
        "I know. That is what is frustrating about it. The scary part and the exciting part are the same thing.",
        "What does your gut say when you imagine yourself actually doing it?",
        "Nervous. But a kind of nervous that feels more like forward motion than dread.",
        "That sounds like an answer to me.",
        "Yeah. I think I already know. I just needed someone else to confirm the logic.",
        "You had it. I just sat here.",
    ],
    # Sharing good news
    [
        "I need to tell you something.",
        "Good something or bad something?",
        "Very good something. I got in.",
        "Wait — the program? The one you applied to three months ago and then decided not to think about?",
        "That one yes. I got the email this morning and I have been walking around in a daze ever since.",
        "That is incredible. Genuinely incredible. You worked so hard for that.",
        "I keep reading the email to make sure it says what I think it says.",
        "It says what you think it says.",
        "I did not let myself want it too much because I thought it would hurt less if it did not happen.",
        "And now it happened.",
        "And now it happened. I do not fully know what to do with that yet.",
        "You celebrate. That is what you do.",
        "Okay. Yes. Let us celebrate.",
        "Dinner. Soon. My pick, my treat.",
        "Deal.",
    ],
    # Recommending a book, going deep
    [
        "I finished that book you sent me.",
        "And?",
        "I have been thinking about it for three days and I still do not know exactly what to say about it.",
        "That is the right reaction I think.",
        "The ending destroyed me in a quiet way. Not dramatic. Just — final.",
        "Yes. That last chapter does something nothing else in the book does. Like it shifts the whole register.",
        "I had to put it down and just sit for a while. When does a book do that to you?",
        "Not often enough. I think that is part of why it stays with you when it does.",
        "What did you make of the narrator? I kept going back and forth on how much to trust them.",
        "Unreliable in the most honest way, I thought. Like they are lying about the facts but telling the truth about what the facts meant to them.",
        "That is a perfect way to put it. I am going to be thinking about that framing for a while.",
        "Send me whatever you read next. I want to return the favor.",
    ],
    # Venting, then landing somewhere real
    [
        "I need to complain for a minute and then I will be fine.",
        "Go.",
        "Everything feels like it is taking twice as long as it should and producing half the result. I am putting in more than I have and getting less back than I need and I cannot tell if I am the problem or the situation is.",
        "That sounds exhausting.",
        "It is. And the worst part is I cannot even properly explain it to anyone because it does not sound like a real problem when I say it out loud.",
        "It sounds like a real problem to me.",
        "Thank you. I think I needed someone to just say that.",
        "What is the one thing that is draining the most right now?",
        "Honestly? The feeling that I am behind on everything all the time. Not actually behind, just that constant low-grade sense of it.",
        "I know that feeling. It is not about the work, it is about the story you are telling about the work.",
        "That is uncomfortably accurate.",
        "What would it mean to just accept that you are exactly where you are right now? Not behind. Just here.",
        "I do not know. I have not tried that.",
        "Maybe start there.",
    ],
    # Making plans, back and forth
    [
        "We have been saying we should do something for weeks and I think we should actually do it.",
        "Fully agree. What did you have in mind?",
        "That place you mentioned a while back? The one near the market?",
        "Yes. I have been wanting to go back since the first time. Are you free this week?",
        "Wednesday evening?",
        "Wednesday works. Seven?",
        "Seven is perfect. Do you want to meet there or should I come to you?",
        "Meet there. It is easier from both directions.",
        "Done. I am actually looking forward to this.",
        "Same. It has been too long.",
    ],
    # Reconnecting after something hard
    [
        "Hey. I have been thinking about you. How are you doing after everything?",
        "Some days better than others. Today is okay.",
        "I am glad today is okay. There is no timeline for this kind of thing.",
        "People keep saying that. I know it is true but knowing it and feeling it are different things.",
        "Completely. The gap between understanding something and actually experiencing it that way is huge.",
        "I keep expecting to feel more settled than I do. Like I should be further along by now.",
        "You are exactly where you are supposed to be. That is not a small thing.",
        "It helps more than you would think to hear that.",
        "I mean it. And I am here when you want to talk and equally here when you just want to exist without having to explain anything.",
        "That second option is actually what I need most right now.",
        "Then that is what we do.",
    ],
    # Debating something with genuine interest
    [
        "I have been thinking about something and I want to hear your take.",
        "Sure.",
        "Do you think people fundamentally change or do they just get better at managing what they already are?",
        "That is a question I could think about for a long time. My instinct is that the core stays but what you do with it can shift dramatically.",
        "I keep going back and forth. I think I have changed in real ways but I also see the same patterns underneath.",
        "Maybe it is both. The pattern stays, the response to it changes. Which might be the only change that actually matters.",
        "So change is less about what you are and more about what you do when you encounter yourself.",
        "Something like that. Although I also think some people change in ways that seem to reach deeper than behavior. I just do not know how to explain that.",
        "I think I have met people like that. Something genuinely shifts and you can feel it when you are around them.",
        "Right. And you cannot manufacture it. It seems to happen from the inside.",
        "This is the kind of thing I want to keep thinking about.",
        "Same. Let us pick this back up sometime.",
    ],
    # Sharing something creative
    [
        "Can I show you something I have been working on?",
        "Of course.",
        "I have been writing again. Nothing I am ready to share widely but something I actually like for the first time in a long time.",
        "That is significant. What is it about?",
        "A person navigating something small that turns out to be connected to something much larger. Still finding its shape.",
        "I love that premise. The ordinary hinge into the enormous.",
        "Exactly. I was worried it was too quiet but I think the quietness is the point.",
        "Some of the best things are. What changed? You were stuck for a while.",
        "I stopped trying to make it good. Started just trying to make it true.",
        "That is the shift. Every time.",
        "It still might not work. But it feels alive in a way the other attempts did not.",
        "Then keep going. That feeling is the right signal.",
    ],
    # A conversation that wanders and lands
    [
        "Random question.",
        "Okay.",
        "What is the best decision you have made in the last year?",
        "Hmm. Probably leaving something that was not working even though I had no clear plan for what came next.",
        "That is brave.",
        "It was more desperate than brave honestly. But it ended up being the same thing.",
        "I think most of the brave things I have done were dressed up desperation.",
        "What is yours? Best decision?",
        "Saying no to something I would have said yes to just to avoid disappointing someone.",
        "That one is hard to learn.",
        "Still learning it. But I said no and the world did not end and I felt better than I expected.",
        "Those small nos add up.",
        "They really do.",
    ],
    # Checking in mid-week
    [
        "How is the week going?",
        "Honestly exhausting. But in a productive way I think.",
        "What is keeping you busy?",
        "Three things that all needed to happen at once and none of them could be moved.",
        "That kind of week. I had one of those last month. By Thursday I had nothing left.",
        "I am almost at Thursday.",
        "Almost there. What is getting you through it?",
        "Coffee. Knowing it ends. The small satisfaction of getting things done even when it is hard.",
        "The last one is underrated. Even when you are running on empty, finishing things feeds something.",
        "Yes. Every completed thing feels disproportionately good right now.",
        "Hang in there. Weekend is close.",
        "Counting down.",
    ],
    # Something observed, turning into a conversation
    [
        "I saw something today that I keep thinking about.",
        "What was it?",
        "An old man sitting alone in a cafe with a newspaper, completely still, for almost an hour. Not sad. Just completely present. Not checking anything.",
        "I find that kind of stillness almost radical now.",
        "That is exactly the word. Like watching something from a different time. The absence of urgency.",
        "I wonder sometimes if we have collectively forgotten what that feels like.",
        "Or maybe some people never lost it and we just stopped noticing them.",
        "That is a more hopeful reading.",
        "I think I need more hopeful readings lately.",
        "Me too. Maybe that is the thing we work on.",
    ],
    # Long overdue honesty
    [
        "I have been meaning to say something and I keep putting it off so I am just going to say it.",
        "Okay. I am listening.",
        "You were right about the thing you said back in the spring. The one I pushed back on pretty hard.",
        "I remember.",
        "I was not ready to hear it then. But you were right and I have been thinking about it for months.",
        "What changed?",
        "I stopped arguing with it and started sitting with it instead. And then I could not unsee what you were pointing at.",
        "I appreciate you saying that. I was not sure where we left that conversation.",
        "I think I just needed it to come from me eventually instead of being handed to me.",
        "That makes sense. Some things land differently when you arrive there yourself.",
        "Yeah. Anyway. Thank you for saying it even when I was not ready.",
        "That is what this is for.",
    ],
    # Two people being honest about missing each other
    [
        "I miss talking to you.",
        "I miss talking to you too. We let too much time go by.",
        "Life gets compressed somehow. Weeks disappear.",
        "I know. And then you realize you have not had a real conversation with someone who actually knows you in too long.",
        "Exactly that. The surface-level stuff is fine but it is not the same.",
        "No it is not. How are you really?",
        "Really? Tired in a way sleep does not fix. But also quietly okay in ways that are hard to explain.",
        "I think I know what you mean. Like the underlying current is okay even when the surface is rough.",
        "Yes. Something like that.",
        "I am glad the current is okay.",
        "Me too. What about you?",
        "Getting clearer on some things. Slower than I would like but moving.",
        "That is all any of us are doing.",
        "When can we actually see each other?",
        "Soon. I mean it this time.",
    ],
]


def random_delay_seconds() -> int:
    r = random.random()
    if r < 0.35:
        return random.randint(5, 90)          # quick reply
    elif r < 0.65:
        return random.randint(90, 900)        # few minutes
    elif r < 0.85:
        return random.randint(900, 10800)     # up to 3 hours
    else:
        return random.randint(10800, 259200)  # 3 hours to 3 days


app = create_app()

with app.app_context():
    NOW = datetime.now(timezone.utc)
    SIX_MONTHS_AGO = NOW - timedelta(days=180)

    print('Clearing existing data...')
    db.drop_all()
    db.create_all()

    print('Creating 30 users...')
    users = []
    seen_usernames = set()
    seen_emails = set()

    about_me_pool = ABOUT_ME.copy()
    random.shuffle(about_me_pool)

    while len(users) < 30:
        username = fake.user_name()[:64]
        email = fake.email()
        if username in seen_usernames or email in seen_emails:
            continue
        seen_usernames.add(username)
        seen_emails.add(email)

        u = User(
            username=username,
            email=email,
            about_me=about_me_pool[len(users) % len(about_me_pool)],
            last_seen=fake.date_time_between(
                start_date=SIX_MONTHS_AGO,
                end_date=NOW - timedelta(seconds=1),
                tzinfo=timezone.utc
            ),
        )
        u.set_password('password')
        db.session.add(u)
        users.append(u)

    db.session.flush()

    print('Creating posts...')
    shuffled_pool = POST_POOL.copy()
    random.shuffle(shuffled_pool)
    pool_cycle = shuffled_pool * 10
    post_index = 0
    created_posts = []

    for user in users:
        for _ in range(random.randint(5, 10)):
            post = Post(
                body=pool_cycle[post_index % len(pool_cycle)],
                timestamp=fake.date_time_between(
                    start_date=SIX_MONTHS_AGO,
                    end_date=NOW - timedelta(seconds=1),
                    tzinfo=timezone.utc
                ),
                author=user,
                language='en',
            )
            db.session.add(post)
            created_posts.append(post)
            post_index += 1

    print('Creating follow relationships...')
    for user in users:
        others = [u for u in users if u != user]
        for target in random.sample(others, random.randint(5, 15)):
            user.follow(target)

    print('Creating conversations...')
    pairs = set()
    for user in users:
        others = [u for u in users if u != user]
        for partner in random.sample(others, random.randint(3, 8)):
            pair = tuple(sorted([user.id, partner.id]))
            if pair not in pairs:
                pairs.add(pair)

    for (uid_a, uid_b) in pairs:
        user_a = next(u for u in users if u.id == uid_a)
        user_b = next(u for u in users if u.id == uid_b)
        thread = random.choice(CONVERSATIONS)

        # Start early enough that all messages fit before NOW
        max_possible_delay = len(thread) * 259200  # worst case: 3 days per message
        earliest_safe_start = SIX_MONTHS_AGO
        latest_safe_start = NOW - timedelta(seconds=max_possible_delay + 60)
        if latest_safe_start < earliest_safe_start:
            latest_safe_start = earliest_safe_start + timedelta(days=1)

        current_time = fake.date_time_between(
            start_date=earliest_safe_start,
            end_date=latest_safe_start,
            tzinfo=timezone.utc
        )

        for i, body in enumerate(thread):
            if i > 0:
                delay = random_delay_seconds()
                next_time = current_time + timedelta(seconds=delay)
                # Hard cap: never exceed NOW
                if next_time >= NOW:
                    next_time = current_time + timedelta(seconds=random.randint(1, 30))
                current_time = next_time

            sender, recipient = (user_a, user_b) if i % 2 == 0 else (user_b, user_a)
            msg = Message(
                sender=sender,
                recipient=recipient,
                body=body,
                timestamp=current_time,
            )
            db.session.add(msg)

    print('Generating embeddings for posts...')
    db.session.flush()
    all_posts = db.session.scalars(sa.select(Post)).all()
    bodies = [p.body for p in all_posts]
    vectors = embed_batch(bodies)
    for post, vec in zip(all_posts, vectors):
        post.embedding = json.dumps(vec)

    print('Saving to database...')
    db.session.commit()
    print(f'Done! 30 users, {post_index} posts, {len(pairs)} conversations seeded.')
    print('Login with any username and password: password')
