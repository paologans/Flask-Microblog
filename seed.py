import random
from datetime import datetime, timezone, timedelta
from faker import Faker
from app import create_app, db
from app.models import User, Post, Message

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Posts — short (1 sentence), medium (2-3 sentences), long (3-4 sentences)
# ---------------------------------------------------------------------------

SHORT_POSTS = [
    "Accidentally made eye contact with a pigeon for too long. Felt judged.",
    "My morning alarm and I have a very complicated relationship.",
    "The sky at sunset looked like someone had just made it up on the spot.",
    "Small progress is still progress. Trying to remember that today.",
    "Nothing resets the mind quite like doing something with your hands.",
    "Caught myself smiling at nothing in particular today. That felt like a win.",
    "The best ideas always seem to arrive right when you are trying to fall asleep.",
    "Went for a walk without my phone and remembered what it felt like to just be somewhere.",
    "Good soup and a quiet evening. Sometimes that is genuinely enough.",
    "The city looks completely different when you are not rushing somewhere.",
    "Someone held the door open for me today and it genuinely made my afternoon.",
    "The smell of rain on pavement is genuinely one of the best things about being alive.",
    "Took a nap today and woke up unsure what year it was. Highly recommend.",
    "Hot take: the best time to have coffee is exactly when you should not have any more.",
    "My plant is finally growing again. I take this as a personal victory.",
    "Realized halfway through today that I had been mispronouncing a word for ten years.",
    "Forgot headphones today and just had to exist in the world with all its sounds.",
    "Asked for help today instead of struggling alone. Somehow still feel proud of that.",
    "People who are kind for no reason are the most interesting people to me.",
    "Watched the sunrise this morning entirely by accident and I am glad I did.",
    "Finished a project I genuinely thought I would never get through.",
    "The gym was empty this morning. Felt like I had the whole world to myself.",
    "Made a decision today that felt scary and right at the same time.",
    "Read something today that made me want to call someone I have not spoken to in a while.",
    "Today was the kind of unremarkable day that I think I will actually miss someday.",
]

MEDIUM_POSTS = [
    "Finally cleaned my desk and now I have no excuse not to be productive. Terrifying, honestly.",
    "Spent 20 minutes looking for my keys. They were in my hand the whole time. Classic.",
    "Started learning guitar six months ago and I can now play three chords with confidence. Progress.",
    "Fell asleep at 9pm last night and woke up feeling like a completely different, better person.",
    "Tried meditating for ten minutes. Spent nine of them thinking about what to have for dinner.",
    "Just watched a documentary that completely changed how I think about something I considered ordinary.",
    "There is something humbling about starting something new and being genuinely, spectacularly bad at it.",
    "Made pasta from scratch for the first time tonight. It was imperfect and absolutely delicious.",
    "The problem with getting better at something is that you immediately notice how far you still have to go.",
    "Overheard the most fascinating conversation on the train today. People are endlessly interesting.",
    "Tried a new café and the coffee was mediocre but the atmosphere was exactly what I needed.",
    "Had a conversation today that reminded me why I love talking to people who think differently than I do.",
    "Been rereading old messages lately and realizing how much things have quietly changed without me noticing.",
    "Spent the evening rearranging my room and now everything feels slightly more intentional. Strange how that works.",
    "That meeting could have been an email but it also turned out to be an unexpectedly good conversation.",
    "Took a different route home today and found a bookshop I never knew existed two streets from my flat.",
    "The older I get the more I appreciate people who just say exactly what they mean. It is so rare.",
    "Sometimes the most productive thing you can do is step completely away from what you are working on.",
    "There are few things better than a meal you were completely skeptical about turning out to be incredible.",
    "Finished something creative today and the feeling right after is so strange and so good all at once.",
    "Made a list of things I want to do this month. Already feel more like myself just writing it down.",
    "Something about this week has felt like a quiet turning point and I cannot fully explain why.",
    "Still thinking about something someone said to me three days ago. It landed in the best possible way.",
    "The version of me from a year ago would be genuinely surprised by where things have ended up.",
    "Just realized the thing I had been avoiding for weeks was actually not that bad once I started.",
]

LONG_POSTS = [
    "Just finished a 5k run and my legs are completely dead but my mind feels incredible. There is something about pushing through discomfort that makes everything else feel manageable. Will I regret this tomorrow? Almost certainly.",
    "There is something deeply satisfying about finishing a book and just sitting quietly with it for a moment. You spent hours inside someone else's world and now you are back in yours. It always takes a beat to adjust.",
    "Spent an hour doing absolutely nothing on purpose today and I think I needed it more than anything else. No phone, no podcast, just sitting. It felt strange at first and then it felt like breathing again.",
    "The hardest part is never actually starting. It is trusting yourself enough to keep going once the initial energy wears off. That middle stretch where nothing feels finished and everything feels uncertain — that is the real test.",
    "Made a decision this week that felt equal parts terrifying and completely right. I have learned that those two feelings arriving together usually means you are headed somewhere real. Trusting the feeling.",
    "Had a conversation yesterday that I keep replaying. Not because anything dramatic was said but because it was one of those rare exchanges where both people were actually paying attention. Those are worth holding onto.",
    "I think I finally know what I want. Not in a grand life-plan way but in the quieter sense of recognising what feels right when you encounter it. Now the actual work of moving toward it begins.",
    "Every time I think I fully understand people, someone surprises me in the best possible way. A stranger was kind for absolutely no reason today and it shifted something in how I was carrying the rest of the afternoon.",
    "Rereading something I wrote two years ago today. The ideas are still there but the voice feels like someone I used to know well. It is interesting to watch yourself change through old writing.",
    "Started a new habit three weeks ago and I am at that awkward stage where it does not feel natural yet but stopping would feel like giving up on something. Just staying consistent and trusting the process.",
    "The weather broke today after what felt like weeks of the same grey sky. Everyone outside seemed lighter, like we had all collectively exhaled. Small environmental shifts do something real to the mood.",
    "Took a long walk this evening with no destination in mind. Ended up in a part of the city I rarely visit and remembered that most places have a completely different character when you arrive slowly and on foot.",
    "Read an article today that challenged something I thought I had figured out. I sat with the discomfort of being wrong for a while instead of immediately looking for counterarguments. It was oddly productive.",
    "Something shifted in how I am approaching work this week and I am not entirely sure what changed. Less resistance, more curiosity. I am not going to examine it too closely in case it goes away.",
    "Caught up with someone today I had not spoken to properly in over a year. We picked up exactly where we left off, which made me think about how some connections have a kind of permanence that does not depend on frequency.",
    "Went to a gallery alone this afternoon on a whim. Spent an hour with one painting I did not initially like and by the end of it I could not stop looking. Patience changes what you see.",
    "Called my parents today just to talk. No particular reason, no news to share. They sounded happy just to hear from me and I felt the specific guilt of someone who should do this more often.",
    "Spent the morning writing and nothing came out right for the first hour. Then something loosened and two pages arrived without effort. The trick seems to be staying at the desk long enough for the resistance to bore itself.",
    "Finished reading a biography that took me three months to get through. The subject lived such a strange and full life that by the end I felt I had lost a complicated friend I had never actually met.",
    "It is easy to romanticise busy periods once they are over. In the moment it was exhausting but now it just looks like momentum. I want to remember the actual texture of it more honestly.",
]

POST_POOL = SHORT_POSTS + MEDIUM_POSTS + LONG_POSTS

# ---------------------------------------------------------------------------
# Conversations — full coherent dialogue threads
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    # Catching up
    [
        "Hey! It has been ages. How are you doing?",
        "Right? So much has happened. I honestly do not even know where to start.",
        "Start anywhere. I have time.",
        "Okay so I finally left that job I was complaining about.",
        "No way. How does it feel?",
        "Honestly terrifying and also the best decision I have made in a long time.",
        "That is exactly how the right decisions tend to feel.",
        "Yeah. Scary that it took me so long to just do it.",
        "You did it though. That is what counts.",
        "True. Anyway what about you? What have I missed?",
    ],
    # Making plans
    [
        "We keep saying we are going to get dinner and never actually doing it.",
        "I know, it is embarrassing at this point.",
        "Are you free any time this week?",
        "Thursday evening could work for me.",
        "Thursday is perfect. That new place on the corner?",
        "I walked past it the other day and it smelled incredible so yes.",
        "Great. Seven?",
        "Seven works. I will book a table.",
        "Amazing. I am actually looking forward to this.",
        "Same. It has been too long.",
    ],
    # Talking through a work problem
    [
        "Can I ask your opinion on something work-related?",
        "Of course, what is going on?",
        "My manager keeps taking credit for my ideas in meetings and I do not know how to handle it.",
        "That is incredibly frustrating. Has it happened more than once?",
        "Three times in the last month that I noticed.",
        "You need to document what you are contributing and when.",
        "I was worried about coming across as difficult if I said something.",
        "Being clear about your work is not difficult, it is necessary.",
        "You are right. I think I have been too passive about it.",
        "Start by having a direct conversation with them. Give them a chance to correct it.",
        "That feels scary but also the right move.",
        "It usually is. Let me know how it goes.",
    ],
    # Excited about something new
    [
        "I just signed up for a pottery class and I am irrationally excited about it.",
        "That is so fun! Have you done it before?",
        "Never. I have no idea what I am doing and that is sort of the point.",
        "I love that. When does it start?",
        "Next Saturday morning. Six weeks of classes.",
        "You are going to be obsessed. Fair warning.",
        "I already bought an apron so the obsession may have already started.",
        "Obviously. Send photos of whatever you make.",
        "Even if it looks terrible?",
        "Especially if it looks terrible.",
    ],
    # Recommending a book
    [
        "Have you read anything good lately? I am in a reading rut.",
        "Yes actually. I just finished one I think you would love.",
        "What is it?",
        "It is a novel about a woman who goes back to her hometown after years away.",
        "That sounds exactly like something I would pick up.",
        "The writing is so precise. Every sentence feels considered.",
        "I need that right now. What is it called?",
        "I will send you the link. You can probably get it at the library.",
        "Perfect. I need something to read this weekend anyway.",
        "You will get through it fast. It is one of those you cannot really put down.",
    ],
    # Venting and support
    [
        "I am having one of those weeks where everything feels like too much.",
        "I am sorry. Do you want to talk about it or just vent?",
        "Honestly just vent for a second if that is okay.",
        "Go for it.",
        "Everything I do feels behind. Work, personal stuff, everything.",
        "That feeling is so exhausting. Like you are always catching up.",
        "Exactly. And I cannot seem to get ahead of it.",
        "What would feel most manageable to tackle first?",
        "That is actually a useful question. Probably the work deadline.",
        "Start there and let the other stuff wait. Give yourself permission.",
        "You are right. I think I just needed someone to say that.",
        "That is what I am here for.",
    ],
    # Debating something lighthearted
    [
        "Okay I need your opinion. Is a hot dog a sandwich?",
        "Absolutely not.",
        "How is it not a sandwich? Filling between bread.",
        "The bread is connected on one side. That changes everything.",
        "That is a technicality, not an argument.",
        "It is a structurally significant technicality.",
        "By that logic a taco is not a sandwich either.",
        "Correct. A taco is a taco. These are different categories.",
        "You have clearly thought about this way too much.",
        "I have thought about it exactly the right amount.",
    ],
    # Following up on something
    [
        "Hey did you ever hear back about that application?",
        "I did! Got the email this morning actually.",
        "And?",
        "I got it. I honestly cannot believe it.",
        "Are you serious? That is incredible, congratulations!",
        "Thank you. I am still processing it.",
        "You worked so hard for this. You absolutely deserve it.",
        "I just kept thinking it would go to someone else.",
        "But it did not. It went to you because you were the right choice.",
        "I really needed to hear that. Thank you.",
        "Now we need to celebrate properly.",
        "Absolutely. Dinner is on me.",
    ],
    # Talking about a trip
    [
        "I booked a trip. I am finally going.",
        "No way! Where?",
        "Portugal. Two weeks in October.",
        "That is so exciting. Have you been before?",
        "Never. I have wanted to go for years.",
        "You are going to love Lisbon. The light there is unreal.",
        "Have you been?",
        "Years ago. Still think about it.",
        "Any recommendations?",
        "Go to the oldest bookshop in the world. Have a pastel de nata everywhere. Walk a lot.",
        "This is exactly the kind of advice I needed.",
        "October is a perfect time. Not too hot, not too busy.",
    ],
    # Late night check-in
    [
        "Are you still awake?",
        "Yeah. Cannot sleep. You?",
        "Same. Brain will not stop.",
        "What are you thinking about?",
        "Nothing specific. Just that restless kind of anxious energy.",
        "I know that feeling. It is the worst.",
        "Does anything actually help you when it gets like that?",
        "Honestly? Getting up and doing something small. Making tea. Reading.",
        "Lying in bed definitely makes it worse.",
        "Always. Your body thinks it is a problem to solve.",
        "Okay I am going to make tea.",
        "Good call. Hope your brain lets you rest soon.",
        "Thanks for being awake.",
        "Anytime.",
    ],
    # Discussing a show
    [
        "Please tell me you have watched that show everyone is talking about.",
        "Which one? There are too many.",
        "The one about the family and the house and the whole mystery.",
        "Oh yes. I watched the whole thing last weekend.",
        "I am on episode four and I need to talk about it with someone.",
        "No spoilers from me. What do you think so far?",
        "I cannot figure out who to trust and it is driving me insane.",
        "That is exactly the right way to feel at episode four.",
        "Is it actually as good as people say?",
        "Better. The ending genuinely got me.",
        "Okay I am watching the rest tonight.",
        "Clear your whole evening.",
    ],
    # Checking in after something hard
    [
        "Hey I just wanted to check in. How are you doing after everything?",
        "Honestly up and down. Some days are better than others.",
        "That makes complete sense. There is no right way to move through it.",
        "I keep expecting to feel more okay than I do.",
        "Give yourself time. Really.",
        "People keep saying that and I know it is true but it is hard to believe.",
        "I know. The gap between knowing something and feeling it is huge sometimes.",
        "Exactly. Thank you for checking in though. It means a lot.",
        "Of course. I mean it. Any time you want to talk.",
        "I might take you up on that.",
        "Please do.",
    ],
    # Making a decision together
    [
        "Okay I need a second opinion. Should I cut my hair short?",
        "Define short.",
        "Like, actually short. Above the shoulders.",
        "Do you want to or do you just feel like you should?",
        "That is a good question. Both maybe?",
        "If it is more want than should, do it.",
        "It will grow back either way right.",
        "Exactly. And you have been talking about it for months.",
        "I have, haven't I.",
        "Book the appointment. You will feel good.",
        "Okay. Doing it.",
        "Yes! Let me know how it goes.",
    ],
    # Sharing good news quietly
    [
        "Can I tell you something I have not told many people yet?",
        "Of course.",
        "I think I am actually happy. Like genuinely.",
        "That is not a small thing.",
        "I know. It feels strange to say out loud.",
        "Why strange?",
        "Because I spent so long not being and now I do not entirely trust it.",
        "I think that is a really honest thing to notice.",
        "I just wanted to tell someone who would understand why it is a big deal.",
        "I do understand. And I am really glad for you.",
    ],
    # Planning something creative
    [
        "I am thinking about starting a project but I keep talking myself out of it.",
        "What kind of project?",
        "Writing something. Not sure what yet. Just feels like something is there.",
        "That feeling is worth following.",
        "What if it goes nowhere?",
        "Then you learned something and tried something. That is not nothing.",
        "I think I am scared it will be bad.",
        "Everything starts bad. That is just the first draft.",
        "You make it sound so simple.",
        "It is and it is not. But starting is the only way to find out.",
        "Okay. I will start this weekend.",
        "Tell me how it goes.",
    ],
]


app = create_app()

with app.app_context():
    print('Clearing existing data...')
    db.drop_all()
    db.create_all()

    NOW = datetime.now(timezone.utc)
    SIX_MONTHS_AGO = NOW - timedelta(days=180)
    TWO_DAYS_AGO = NOW - timedelta(days=2)

    print('Creating 30 users...')
    users = []
    seen_usernames = set()
    seen_emails = set()

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
            about_me=fake.sentence(nb_words=12)[:140],
            last_seen=fake.date_time_between(start_date=SIX_MONTHS_AGO, end_date=NOW, tzinfo=timezone.utc),
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

    for user in users:
        for _ in range(random.randint(5, 10)):
            post = Post(
                body=pool_cycle[post_index % len(pool_cycle)],
                timestamp=fake.date_time_between(start_date=SIX_MONTHS_AGO, end_date=NOW, tzinfo=timezone.utc),
                author=user,
                language='en',
            )
            db.session.add(post)
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
        conv_start = fake.date_time_between(start_date=SIX_MONTHS_AGO, end_date=TWO_DAYS_AGO, tzinfo=timezone.utc)

        for i, body in enumerate(thread):
            sender, recipient = (user_a, user_b) if i % 2 == 0 else (user_b, user_a)
            msg = Message(
                sender=sender,
                recipient=recipient,
                body=body,
                timestamp=conv_start + timedelta(minutes=i * random.randint(2, 30)),
            )
            db.session.add(msg)

    print('Saving to database...')
    db.session.commit()
    print(f'Done! 30 users, {post_index} posts, {len(pairs)} conversations seeded.')
    print('Login with any username and password: password')
