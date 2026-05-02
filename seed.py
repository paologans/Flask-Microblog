import json
import random
import numpy as np
from datetime import datetime, timezone, timedelta
from faker import Faker
import sqlalchemy as sa
from sklearn.metrics.pairwise import cosine_similarity
from app import create_app, db
from app.models import User, Post, Message
from app.embeddings import embed_batch

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# About me
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
# Topic-based post pools
# ---------------------------------------------------------------------------

SPORTS_POSTS = [
    "Game day. Let's go.",
    "That ref needs glasses.",
    "New PR today. Finally.",
    "Penalty in the 90th. Heartbreak.",
    "Gym at 6am. Worth it.",
    "Can't stop watching the highlights.",
    "Watched the game with everyone squeezed onto one couch. That last-minute goal had us all screaming.",
    "Three miles this morning and my legs are done. But the runner's high is real and I will be back tomorrow.",
    "Been training for six months for this race. Race day is in two weeks and I don't know if I'm ready.",
    "Lost by one point. One. I have been staring at the final score for twenty minutes and I still can't accept it.",
    "The comeback nobody saw coming. Down by 12 with four minutes left. I will talk about this game for years.",
    "Stayed up until midnight watching a game in a completely different time zone. This is my life now.",
    "The team played terribly in the first half and somehow turned it around. I don't understand this sport but I love it.",
    "My team hasn't won a championship in eleven years. Every season I say this is the year. Every season I end up on the couch in disbelief.",
    "Signed up for a half marathon on impulse six weeks ago. Training has been humbling. I run slower than I thought and hurt in places I forgot existed.",
    "There is something about being in a stadium with forty thousand people all wanting the same thing at the same time. Nothing else replicates that.",
    "Called a shot in pickup basketball and actually made it. I will be coasting on that for weeks.",
    "Watched my favorite player retire. The press conference got to me more than I expected. End of an era.",
    "Fantasy league is ruining how I watch sports. I'm rooting for individuals on opposing teams simultaneously. It's chaos.",
    "Personal record on the bench press after three months of consistency. The slow progress is the whole thing.",
]

POLITICS_POSTS = [
    "Voted. Did you?",
    "Turning off the news for a week.",
    "Read three different takes on the same story. All completely different.",
    "The debate was something else.",
    "Watching the election results come in with sweaty palms.",
    "Had a genuinely civil political conversation with someone who disagrees with me. Rare. Good.",
    "The problem with political discourse online is that nuance never goes viral. Only the extreme version gets amplified.",
    "Read the actual text of the bill instead of the hot takes. More complicated than either side admits.",
    "Town hall tonight. Surprised by how many people showed up and how few agreed on anything.",
    "I used to think I could predict political outcomes. I cannot. Nobody can. The uncertainty is the point.",
    "Local politics affects daily life more than national politics but nobody pays attention to it.",
    "The older I get the more I believe the most important work happens at the level nobody is watching.",
    "Read an editorial that made me genuinely reconsider something I thought I was certain about. That almost never happens.",
    "Election season makes me feel hope and dread simultaneously in proportions that shift by the hour.",
    "Watched the vote count flip three times last night. Did not sleep. Cannot stop refreshing.",
    "Talked to my grandparents about what politics felt like when they were young. The differences are staggering.",
    "Something about ballot initiatives being decided by margins smaller than the number of people who forgot to show up.",
    "Tried to explain a policy debate to someone outside the country and realized I could not explain why it was actually controversial.",
    "People keep saying democracy is fragile. I keep hoping they are wrong. The data is not reassuring.",
    "Attended a city council meeting for the first time. Boring, contentious, and more important than anything I watched on cable news.",
]

SCHOOL_POSTS = [
    "Three exams this week. Send help.",
    "Pulled an all-nighter. Not recommended.",
    "Group project where I did everything. Again.",
    "Library at midnight. We are all suffering together.",
    "Submitted the essay with forty seconds to spare.",
    "Professor extended the deadline. Today is a good day.",
    "Finished my last final. I can see the light.",
    "Started studying for the exam this morning. Exam is this afternoon. This is fine.",
    "Got feedback on a paper that actually made it better. Good professors are rare.",
    "Sat in the wrong lecture for fifteen minutes before realizing. Nobody said anything. We were all pretending.",
    "The gap between understanding something in class and doing it on an exam is where I currently live.",
    "Graduated. I expected to feel more. I feel mostly tired, hungry, and like something is ending.",
    "Third cup of coffee and I have read the same paragraph eleven times.",
    "Picked a research topic that seemed manageable and is now the entire history of human civilization.",
    "Had a professor who clearly loved what they were teaching. It changed how I listened. That energy is contagious.",
    "Semester is over and I do not know where the time went. I remember the first week. The rest is a blur.",
    "Office hours actually helped. I have been avoiding them for two years. Major life update.",
    "The scholarship came through. I sat in my car and cried for ten minutes before telling anyone.",
    "Realized halfway through the semester that I picked the wrong major. Now I have to figure out what the right one is.",
    "Study group was supposed to help. We spent two hours talking and thirty minutes on the material. Still better than alone.",
]

WORK_POSTS = [
    "Monday again.",
    "Meeting that could have been an email.",
    "Deadline survived.",
    "Just put my two weeks in.",
    "Got the promotion. Still processing.",
    "New job starts Monday. Terrified.",
    "Working from home means my cat attends all my meetings.",
    "The project that was supposed to take two weeks has now taken six. We don't speak of the original estimate.",
    "Performance review went better than expected. The bar was admittedly low.",
    "Started a new role today. The learning curve is vertical and everyone knows things I don't. Normal, probably.",
    "My manager gave me feedback I didn't want to hear and it was exactly right. The most annoying kind.",
    "Sent an email to the wrong person. It was fine. I am not fine.",
    "Three back-to-back meetings with no break. By the last one I had forgotten what words meant.",
    "Worked late again. The work was good though. Sometimes that is enough.",
    "Quit the job I was supposed to want. The relief hit before I even got to the parking lot.",
    "Had a one-on-one with my manager that was actually honest and useful. I forget those can happen.",
    "Week one at a new place. Everything is unfamiliar and absorbing that is the whole job right now.",
    "The colleague who is always calm in a crisis has become my professional role model. Studying their energy.",
    "Layoffs hit the team today. Still here, but the silence in the office is doing something to everyone.",
    "Turned down the counteroffer. The raise would have kept me. The problems would have stayed too.",
]

HEARTBREAK_POSTS = [
    "Delete. Block. Move on. In that order.",
    "Still checking my phone. Habit is cruel.",
    "Some days hit harder than others.",
    "Listening to the sad playlist again. Don't ask.",
    "Thought I saw them today. Wasn't them. Still felt like something.",
    "It is strange to miss someone you are better off without.",
    "Rearranged my whole apartment just to change how everything felt. It helped a little.",
    "Three months and something about today brought it all back. Grief is not linear.",
    "What I thought was a new start was an ending I hadn't finished processing. Found that out the hard way.",
    "I keep catching myself wanting to tell them things. Old habit from when they were the first person I told everything.",
    "Was fine all week and then a song came on and I was not fine anymore.",
    "Realized I had been trying to be the person they needed instead of who I actually am. You don't notice while it's happening.",
    "The version of us I kept in my head lasted longer than the relationship. Still letting go of someone who stopped existing.",
    "Deleted the photos. Went looking for them in the backup like an idiot. Still miss them. Still glad it ended.",
    "Some people come in and rearrange everything and then leave and you have to figure out a new order. I am in the middle of that.",
    "Ran into them today. Smiled. Said hello. Kept walking. Made it around the corner before it hit me.",
    "The hardest part is not the anger. The anger is easy. It is the quiet moments when you forget to be angry.",
    "Six months out and I am doing better. But better is not the same as healed and I am done pretending it is.",
    "Wrote a long message. Read it back. Deleted it. Wrote it again. Deleted it again. Some things do not need to be sent.",
    "The anniversary of nothing I can name but something my body still remembers. Some dates just exist now.",
]

GOOD_VIBES_POSTS = [
    "Today was genuinely good.",
    "Grateful. Just that.",
    "Small win. Still counts.",
    "Told someone I loved them today. They said it back.",
    "Best day I have had in a while. Didn't plan it. Just happened.",
    "Laughed so hard today. The kind where you can't breathe.",
    "Random act of kindness from a stranger. Restored something.",
    "Finally did the thing I kept putting off and I feel a hundred times lighter.",
    "Made someone smile today without trying to. That is enough.",
    "Weekend felt long in the best way. Slow mornings, nowhere to be.",
    "Everything came together today in a way I didn't expect and I want to hold onto that feeling.",
    "Good news arrived when I had stopped expecting it. The timing was its own gift.",
    "Felt fully present for an entire hour and it was more restorative than any amount of sleep.",
    "Something about today reminded me that most of what I worry about never happens.",
    "Spent the afternoon with people I love doing nothing important. That is the whole thing.",
    "Woke up in a good mood for no reason and spent the whole day surprised it stayed.",
    "Called my parents for no reason other than I wanted to hear their voices. Right call.",
    "Finished something I am actually proud of. The feeling is quieter than I expected. Also better.",
    "Stranger paid for my coffee in line this morning. I have been paying it forward all day.",
    "Sat outside for an hour and did nothing and felt completely fine about it. Growth.",
]

FOOD_POSTS = [
    "Best meal I've had all year.",
    "The soup came out perfect this time.",
    "Burned dinner again. Ordering in.",
    "New recipe. Nailed it.",
    "Baked bread for the first time. Chaos and flour everywhere. Worth it.",
    "Made something with what was left in the fridge and it worked. I am unstoppable.",
    "That restaurant I have been meaning to try for months finally happened. The wait was worth it.",
    "Cooked for someone else for the first time in a long time. Feeding people is its own kind of care.",
    "Found a recipe for something I ate as a kid and tried to make it taste like I remembered. Close enough.",
    "Failed attempt at something ambitious. The apartment smells strange. I will try again next week.",
    "Coffee shop had something new on the menu and it is now my entire personality.",
    "There is a specific comfort in making a meal you have cooked a hundred times. Familiar, reliable, yours.",
    "Tried to recreate a restaurant dish. Not quite right. Mine. Liked it better for that.",
    "The thing about cooking for yourself is you have to care about yourself enough to bother. Some days that is the real task.",
    "Farmers market this morning. Bought too much. Have no regrets.",
    "Finally mastered scrambled eggs. Only took thirty years.",
    "Dinner party went well. No one got food poisoning. I am calling that a success.",
    "Found a hole-in-the-wall place two blocks from my apartment I somehow never noticed. It is perfect and I am furious.",
    "Made the sauce from scratch for the first time instead of from a jar. There is no going back.",
    "Stress-baked four dozen cookies at 11pm. Looking for people to take them off my hands.",
]

TECH_POSTS = [
    "It works and I have no idea why.",
    "Three hours on a bug. One line fix.",
    "Deployed on a Friday. I am not a wise person.",
    "The documentation lied to me.",
    "Merge conflict in a file I did not touch. Classic.",
    "Finally understand recursion. Only took two years.",
    "Debugging at midnight. Fun.",
    "Learned something today that made six months of confusion suddenly make sense. That click is worth the wait.",
    "Wrote a script to automate ten minutes of work. Script took three hours. Math checks out.",
    "Tried a new tool everyone is talking about. Went back to the old way after an hour. Maybe next year.",
    "Stack trace longer than most novels I have read. Scrolling to find the actual error is its own skill.",
    "Works in development. Does not work in production. This is physics.",
    "Pair programmed for the first time in a while. Having someone see your thought process is humbling and useful.",
    "Refactored code I wrote a year ago. I have many thoughts about who I was a year ago.",
    "Broke production. Fixed production. Told no one. This is called leadership.",
    "Finally got the test to pass and now I'm not sure it's testing the right thing. Progress.",
    "AI suggested a fix that worked immediately. Felt emotions I am not prepared to examine.",
    "Legacy codebase that has comments like 'don't touch this, it works, nobody knows why.' Found another one today.",
    "Code review left more comments than lines I changed. Growing as a person.",
    "Estimated two days. Took two weeks. Estimation is a skill I do not have.",
]

TRAVEL_POSTS = [
    "New city. No plan. Perfect.",
    "Lost. Also fine.",
    "Airport at 4am. Surprisingly peaceful.",
    "Everything I packed I did not need. Everything I did not pack I did.",
    "Traveling alone for the first time. Strange and good.",
    "The detour was the whole trip.",
    "Coffee in a place where I don't speak the language.",
    "Arrived somewhere I had been imagining for years. Different than I imagined. Better in some ways.",
    "Train travel is the only way to arrive somewhere. You see how far you have come.",
    "Three days with no signal. Came back feeling like a different person.",
    "The best parts of the trip were not in any itinerary. Things that went wrong. Unexpected conversations.",
    "Back somewhere I had been years ago. Place was the same. I was completely different. Strange combination.",
    "Sat in a square in a city where I knew no one and watched people live their lives and felt completely at peace.",
    "A stranger gave me wrong directions that led me somewhere better. I believe in this as a metaphor.",
    "Came home and everything felt slightly wrong-sized, like I had grown and the spaces hadn't yet.",
    "Missed a flight and it turned into the best day of the trip.",
    "Hostel stranger became a lifelong friend over three hours and a shared meal. This keeps happening.",
    "Took a night train across the country. Woke up somewhere new. Would do it again immediately.",
    "Tried to go off-season to avoid tourists. Was also a tourist.",
    "Three countries in a week and I cannot tell you what day it is. I am happy.",
]

LIFE_POSTS = [
    "Needed that coffee more than I expected.",
    "Something about today felt different.",
    "The quiet before everyone else wakes up.",
    "Finally.",
    "Managed to do one hard thing today and that feels like enough.",
    "Running on nothing and somehow still moving.",
    "One of those mornings.",
    "Been staring at the same paragraph for twenty minutes. I think the paragraph might be winning.",
    "Started the day earlier than planned and somehow it helped more than any extra sleep would have.",
    "Every time I think I have figured something out I find a new room I did not know existed.",
    "The version of today I imagined last week and the version I actually got were completely different. Both fine.",
    "Realized I have been carrying something for so long I forgot it was optional.",
    "There is a version of every day that exists only in the early morning before anything has happened yet.",
    "The older I get the more I appreciate people who just say what they mean.",
    "Something shifted this week and I cannot fully explain it. Less resistance. More willingness.",
    "Read something that got at something I have been trying to say for months. That happens sometimes.",
    "Went for a walk with no destination and ended up somewhere I had never been three blocks from my apartment.",
    "I think I have been moving too fast to actually see anything. Going to try walking slower.",
    "Been thinking about how much changes without you noticing. Last year feels like a different chapter.",
    "There is something about finishing a long project that feels less like relief and more like standing in a room after everyone left.",
]

# Map topic name → post pool
TOPIC_POOLS = {
    'sports':     SPORTS_POSTS,
    'politics':   POLITICS_POSTS,
    'school':     SCHOOL_POSTS,
    'work':       WORK_POSTS,
    'heartbreak': HEARTBREAK_POSTS,
    'good_vibes': GOOD_VIBES_POSTS,
    'food':       FOOD_POSTS,
    'tech':       TECH_POSTS,
    'travel':     TRAVEL_POSTS,
    'life':       LIFE_POSTS,
}
ALL_TOPICS = list(TOPIC_POOLS.keys())

# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

CONVERSATIONS = [
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
    [
        "I need to complain for a minute and then I will be fine.",
        "Go.",
        "Everything feels like it is taking twice as long as it should and producing half the result.",
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
    [
        "I have been thinking about something and I want to hear your take.",
        "Sure.",
        "Do you think people fundamentally change or do they just get better at managing what they already are?",
        "My instinct is that the core stays but what you do with it can shift dramatically.",
        "I keep going back and forth. I think I have changed in real ways but I also see the same patterns underneath.",
        "Maybe it is both. The pattern stays, the response to it changes. Which might be the only change that actually matters.",
        "So change is less about what you are and more about what you do when you encounter yourself.",
        "Something like that. Although I also think some people change in ways that seem to reach deeper than behavior.",
        "I think I have met people like that. Something genuinely shifts and you can feel it when you are around them.",
        "Right. And you cannot manufacture it. It seems to happen from the inside.",
        "This is the kind of thing I want to keep thinking about.",
        "Same. Let us pick this back up sometime.",
    ],
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
    [
        "Random question.",
        "Okay.",
        "What is the best decision you have made in the last year?",
        "Probably leaving something that was not working even though I had no clear plan for what came next.",
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
    [
        "I saw something today that I keep thinking about.",
        "What was it?",
        "An old man sitting alone in a cafe with a newspaper, completely still, for almost an hour. Not sad. Just completely present.",
        "I find that kind of stillness almost radical now.",
        "That is exactly the word. Like watching something from a different time. The absence of urgency.",
        "I wonder sometimes if we have collectively forgotten what that feels like.",
        "Or maybe some people never lost it and we just stopped noticing them.",
        "That is a more hopeful reading.",
        "I think I need more hopeful readings lately.",
        "Me too. Maybe that is the thing we work on.",
    ],
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
        return random.randint(5, 90)
    elif r < 0.65:
        return random.randint(90, 900)
    elif r < 0.85:
        return random.randint(900, 10800)
    else:
        return random.randint(10800, 259200)


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

    # Assign each user 1-2 primary topics
    user_topics = []
    for i in range(30):
        primary = random.choice(ALL_TOPICS)
        secondary = random.choice([t for t in ALL_TOPICS if t != primary])
        user_topics.append((primary, secondary))

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
    created_posts = []
    # Track which topic each post belongs to (for liking logic)
    post_topics = []

    for idx, user in enumerate(users):
        primary, secondary = user_topics[idx]
        n_posts = random.randint(10, 15)
        primary_pool = TOPIC_POOLS[primary].copy()
        secondary_pool = TOPIC_POOLS[secondary].copy()
        random.shuffle(primary_pool)
        random.shuffle(secondary_pool)
        p_idx = 0
        s_idx = 0

        for _ in range(n_posts):
            roll = random.random()
            if roll < 0.55 and p_idx < len(primary_pool):
                body = primary_pool[p_idx % len(primary_pool)]
                topic = primary
                p_idx += 1
            elif roll < 0.80 and s_idx < len(secondary_pool):
                body = secondary_pool[s_idx % len(secondary_pool)]
                topic = secondary
                s_idx += 1
            else:
                # random topic
                rand_topic = random.choice(ALL_TOPICS)
                rand_pool = TOPIC_POOLS[rand_topic]
                body = random.choice(rand_pool)
                topic = rand_topic

            post = Post(
                body=body,
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
            post_topics.append(topic)

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

        max_possible_delay = len(thread) * 259200
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

    print('Generating embeddings for messages...')
    all_messages = db.session.scalars(sa.select(Message)).all()
    msg_bodies = [m.body for m in all_messages]
    msg_vectors = embed_batch(msg_bodies)
    for msg, vec in zip(all_messages, msg_vectors):
        msg.embedding = json.dumps(vec)

    # -----------------------------------------------------------------------
    # Topic-aware likes using cosine similarity
    # Each user's topic centroid is computed from their own post embeddings.
    # They then like posts from other users that are most similar to that centroid.
    # -----------------------------------------------------------------------
    print('Seeding post likes (topic-aware via cosine similarity)...')
    db.session.flush()

    # Build lookup: post_id → (post_obj, embedding_vector)
    post_vec_map = {}
    for post in all_posts:
        if post.embedding:
            post_vec_map[post.id] = (post, np.array(json.loads(post.embedding)))

    # Build lookup: user_id → list of (post, vec) for their own posts
    user_post_vecs = {u.id: [] for u in users}
    for post_id, (post, vec) in post_vec_map.items():
        user_post_vecs[post.user_id].append((post, vec))

    for user in users:
        own = user_post_vecs.get(user.id, [])
        if not own:
            continue

        # Compute topic centroid from user's own posts
        own_vecs = np.array([v for _, v in own])
        centroid = own_vecs.mean(axis=0, keepdims=True)  # shape (1, dim)

        # Gather all posts by other users
        others = [(p, v) for (p, v) in post_vec_map.values() if p.user_id != user.id]
        if not others:
            continue

        other_posts_list = [p for p, _ in others]
        other_vecs = np.array([v for _, v in others])

        # Cosine similarity between centroid and every other post
        sims = cosine_similarity(centroid, other_vecs)[0]  # shape (n_others,)

        # Take top 25% by similarity; like 40-65% of those randomly
        n_others = len(others)
        top_n = max(5, int(n_others * 0.25))
        top_indices = np.argsort(sims)[-top_n:][::-1]

        n_likes = random.randint(int(top_n * 0.40), int(top_n * 0.65))
        liked_indices = random.sample(list(top_indices), min(n_likes, len(top_indices)))

        for idx in liked_indices:
            post = other_posts_list[idx]
            post.liked_by.add(user)

    print('Saving to database...')
    db.session.commit()
    total_posts = len(all_posts)
    print(f'Done! 30 users, {total_posts} posts, {len(pairs)} conversations seeded.')
    print('Login with any username and password: password')
