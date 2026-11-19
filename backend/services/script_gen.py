from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GeneratedScript:
    niche: str
    language: str
    subreddit_or_tag: str
    author: str
    title: str
    hook: str
    body: str
    cta_ending: str
    full_narration: str
    description: str
    tags: list[str]
    image_prompts: list[str]
    source: str = "offline"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


NICHE_INFO: dict[str, dict[str, str]] = {
    "reddit": {
        "ru": "Истории с Reddit",
        "en": "Reddit Stories",
        "default_tag_ru": "r/AskReddit",
        "default_tag_en": "r/AskReddit",
    },
    "scary": {
        "ru": "Страшные истории",
        "en": "Scary Stories",
        "default_tag_ru": "r/nosleep",
        "default_tag_en": "r/nosleep",
    },
    "psychology": {
        "ru": "Психологические факты",
        "en": "Dark Psychology",
        "default_tag_ru": "Психология",
        "default_tag_en": "Psychology",
    },
    "motivation": {
        "ru": "Мотивация",
        "en": "Motivation & Mindset",
        "default_tag_ru": "Дисциплина",
        "default_tag_en": "Mindset",
    },
}


# ---------------------------------------------------------------------------
# Offline High-Retention Story Bank (3 stories per niche x 2 languages = 24)
# ---------------------------------------------------------------------------

OFFLINE_STORIES: dict[str, dict[str, list[dict[str, Any]]]] = {
    "reddit": {
        "ru": [
            {
                "subreddit_or_tag": "r/AskReddit",
                "author": "u/night_auditor_99",
                "title": "Какое правило на вашей работе появилось только после одного жуткого случая?",
                "hook": "В нашем отеле строго запрещено открывать дверь номера 404 после двух часов ночи.",
                "body": (
                    "Я работал ночным администратором в старой гостинице на трассе и думал, что это просто глупая байка для новичков. "
                    "В прошлый вторник ровно в два пятнадцать на пульте загорелся вызов именно из 404-го, хотя по базе комната была пустой уже три недели. "
                    "Я поднялся на четвертый этаж с мастер-ключом, чтобы просто выключить телефон. "
                    "Когда я подошел к двери, изнутри кто-то тихо сказал моим голосом: «Я уже здесь, не заходи». "
                    "Я замер на месте, достал рацию и вызвал охрану. Через минуту мы открыли номер вместе. "
                    "Окно было распахнуто настежь, на столе стоял старый диктофон на повторе, а под кроватью лежал пропуск бывшего сменщика, уволенного два года назад."
                ),
                "cta_ending": "А какое самое странное правило есть у вас на работе? Напишите в комментариях.",
                "description": "Ночная смена в отеле обернулась вызовом охраны из-за пустого номера 404. Реальная ветка с Reddit.",
                "tags": ["reddit", "историисреддит", "ночнаясмена", "shorts", "отель", "мистика", "askreddit", "история"],
                "image_prompts": [
                    "dimly lit vintage hotel hallway at night, eerie warm lamp glow, cinematic vertical 9:16",
                    "hotel room door number 404 in moody shadows, dramatic lighting, vertical photorealistic",
                    "antique rotary phone glowing faintly on wooden nightstand in dark room, suspenseful",
                    "open hotel window curtains blowing in night wind, moonlight on floor, cinematic",
                    "old cassette voice recorder on dark oak desk, thriller movie still, vertical 9:16",
                ],
            },
            {
                "subreddit_or_tag": "r/MaliciousCompliance",
                "author": "u/dev_coffee_break",
                "title": "Босс заставил отчитываться за каждую минуту — и через неделю пожалел об этом",
                "hook": "Наш новый менеджер потребовал присылать отчет за каждые пятнадцать минут работы.",
                "body": (
                    "Он заявил, что программисты слишком много времени пьют кофе, и приказал фиксировать буквально каждое действие в таблице. "
                    "Я согласился и подключил к делу всю команду. В первый же день мы начали записывать всё до секунды: "
                    "две минуты — чтение его новых правил, четыре минуты — заполнение самой таблицы, восемь минут — ожидание ответа от его же отдела. "
                    "Когда наступало восемнадцать ноль ноль, мы закрывали ноутбуки ровно посреди фразы, ведь сверхурочные нужно согласовывать за двое суток. "
                    "Через пять дней его почта утонула в двух тысячах строк микроотчетов, а важный релиз встал из-за бумажной волокиты. "
                    "В пятницу утром он молча удалил таблицу и вернул нам свободный график."
                ),
                "cta_ending": "А как вы ставили на место токсичного начальника? Расскажите свою историю ниже.",
                "description": "История о том, как буквальное выполнение абсурдных приказов руководства спасает нервы.",
                "tags": ["reddit", "работа", "босс", "офис", "истории", "shorts", "it", "жиза"],
                "image_prompts": [
                    "modern glass office late evening, frustrated manager looking at monitor, cinematic vertical",
                    "close up of mechanical keyboard and complex spreadsheet on dark screen, moody neon light",
                    "two exhausted developers drinking espresso near glowing monitors, photorealistic",
                    "laptop closing abruptly on sleek wooden desk at 6pm, warm sunset reflections",
                    "crowded email inbox overflow concept on glowing computer screen, dramatic lighting",
                ],
            },
            {
                "subreddit_or_tag": "r/Glitch_in_the_Matrix",
                "author": "u/metro_line_7",
                "title": "Я зашел в лифт на шестом этаже, а вышел в доме, где жил десять лет назад",
                "hook": "Позавчера обычный лифт в моем бизнес-центре привез меня туда, где я не был десять лет.",
                "body": (
                    "Я нажал кнопку первого этажа и уткнулся в телефон, проверяя рабочую почту. "
                    "Двери открылись с привычным звонком, но вместо стеклянного холла я почувствовал запах жареного лука и старой краски. "
                    "Я поднял глаза и остолбенел: передо мной был облупленный зеленый подъезд пятиэтажки из моего детства, вплоть до трещины на плитке у почтовых ящиков. "
                    "На секунду в глубине коридора промелькнул наш старый сосед с собакой, который умер еще в две тысячи девятнадцатом. "
                    "Сердце ушло в пятки, я вслепую вдавил кнопку закрытия дверей, и кабина дернулась вниз. "
                    "Через три секунды я вышел в обычный холл офиса, но на ботинках осталась белая побелка."
                ),
                "cta_ending": "Случалось ли с вами такое, чему нет объяснения? Жду ваши истории в комментариях.",
                "description": "Сбой в матрице или игра памяти? Необычный случай в офисном лифте.",
                "tags": ["матрица", "reddit", "мистика", "загадка", "лифт", "shorts", "истории", "необъяснимое"],
                "image_prompts": [
                    "sleek metallic office elevator interior with glowing floor numbers, moody vertical",
                    "elevator doors opening to an old Soviet green stairwell hallway, surreal contrast",
                    "dimly lit vintage apartment corridor with cracked floor tiles, cinematic atmosphere",
                    "man standing frozen inside elevator looking out in shock, dramatic shadows",
                    "modern glass corporate lobby with white chalk dust footprints on dark floor",
                ],
            },
        ],
        "en": [
            {
                "subreddit_or_tag": "r/AskReddit",
                "author": "u/night_auditor_99",
                "title": "What workplace rule exists because of one terrifying incident?",
                "hook": "At my old highway hotel, we were strictly forbidden from opening room 404 after two AM.",
                "body": (
                    "I worked the graveyard shift and always assumed it was just a prank played on rookies. "
                    "Then last Tuesday at two fifteen, the front desk switchboard lit up with an internal call from room 404, even though the room had been vacant for three weeks. "
                    "I grabbed the master key and took the elevator upstairs just to unplug the phone. "
                    "As soon as I reached the door, I heard my own voice whisper from inside: I am already here, do not come in. "
                    "My blood ran cold. I stepped back and radioed security right away. "
                    "When we finally unlocked the door together, the window was wide open, an old voice recorder was looping on the desk, and a fired clerk's keycard was tucked under the mattress."
                ),
                "cta_ending": "What is the creepiest rule at your job? Drop your story in the comments.",
                "description": "A routine hotel night shift turned into a security call outside an empty room.",
                "tags": ["askreddit", "redditstories", "nightshift", "creepy", "shorts", "storytime", "hotel", "mystery"],
                "image_prompts": [
                    "dimly lit vintage highway hotel hallway at night, moody warm shadows, vertical 9:16",
                    "hotel room door number 404 under flickering hallway light, cinematic thriller",
                    "vintage hotel desk phone ringing in dark lobby, suspenseful shadows, photorealistic",
                    "open hotel window curtains blowing in night breeze under moonlight",
                    "old voice recorder sitting on dark wooden table, cinematic crime scene mood",
                ],
            },
            {
                "subreddit_or_tag": "r/MaliciousCompliance",
                "author": "u/dev_coffee_break",
                "title": "My boss forced us to log every 15 minutes, so we followed his rule literally",
                "hook": "Our new manager demanded a detailed spreadsheet update for every fifteen minutes of our day.",
                "body": (
                    "He claimed engineers spent too much time grabbing coffee and ordered us to track every single task. "
                    "Instead of arguing, I got the entire team on board. "
                    "On day one, we logged everything down to the second: two minutes reading his memo, four minutes filling out the tracker, and twelve minutes waiting for his own department to approve tickets. "
                    "At six PM sharp, every laptop snapped shut mid-sentence because overtime required forty-eight hours of written approval. "
                    "By Thursday, his inbox was buried under two thousand rows of micro-updates and a major launch stalled in paperwork. "
                    "Friday morning, he quietly deleted the spreadsheet and never brought it up again."
                ),
                "cta_ending": "Have you ever beat a micromanager at their own game? Tell us below.",
                "description": "When micromanagement collides with literal compliance in a tech office.",
                "tags": ["reddit", "maliciouscompliance", "workstories", "corporate", "shorts", "tech", "boss", "story"],
                "image_prompts": [
                    "modern glass office at dusk with stressed manager staring at laptop, vertical 9:16",
                    "close up of mechanical keyboard and glowing spreadsheet grid in dark room",
                    "software engineers drinking coffee by glowing dark monitors, cinematic style",
                    "sleek silver laptop closing on wooden desk at sunset, sharp depth of field",
                    "chaotic glowing inbox notifications reflection in glasses, moody cinematic",
                ],
            },
            {
                "subreddit_or_tag": "r/Glitch_in_the_Matrix",
                "author": "u/metro_line_7",
                "title": "I stepped into my office elevator and walked out in my childhood apartment",
                "hook": "Two days ago, my office elevator opened onto a building I left ten years ago.",
                "body": (
                    "I pressed the ground floor button and stared at my phone, answering an urgent message from my team. "
                    "When the chime rang and the doors slid open, the smell of toasted garlic and old hallway paint hit me instantly. "
                    "I looked up and froze. Instead of the glass corporate lobby, I was staring at the peeling green stairwell of my childhood home, right down to the cracked tile by the mailboxes. "
                    "Down the hall, a figure turned the corner walking a terrier that looked identical to our neighbor's dog who passed away years ago. "
                    "My heart hammered against my ribs as I slammed the close button blindly. "
                    "Three seconds later the doors opened to my normal lobby, except there was chalk dust on my shoes."
                ),
                "cta_ending": "Have you ever experienced a real glitch in the matrix? Comment below.",
                "description": "One ordinary elevator ride took a shocking surreal turn.",
                "tags": ["glitchinthematrix", "reddit", "mystery", "unexplained", "shorts", "storytime", "elevator", "viral"],
                "image_prompts": [
                    "modern brushed steel elevator interior with warm LED strip lighting, vertical",
                    "elevator doors opening onto an old peeling green vintage hallway, surreal lighting",
                    "dimly lit retro apartment corridor with cracked floor tiles, mysterious mood",
                    "person standing inside elevator staring in disbelief at glowing threshold",
                    "clean modern glass office lobby floor with faint white chalk footprints",
                ],
            },
        ],
    },
    "scary": {
        "ru": [
            {
                "subreddit_or_tag": "r/nosleep",
                "author": "u/watchtower_north",
                "title": "На записи с камеры домофона я увидел, как сам стою под дверью в три ночи",
                "hook": "Вчера утром телефон прислал уведомление: кто-то три минуты стоял у моей входной двери.",
                "body": (
                    "Я живу на двенадцатом этаже один и точно помню, что лег спать еще до полуночи. "
                    "Открыл архив видеозвонка, ожидая увидеть заблудившегося курьера или соседа. "
                    "На экране в ночном инфракрасном свете стоял человек в моей серой толстовке и смотрел прямо в глазок. "
                    "Когда картинка приблизилась, у меня перехватило дыхание: у него было точно мое лицо, только улыбка была слишком широкой и неподвижной. "
                    "Ровно в три ноль три он медленно поднял руку, трижды постучал в дверь и пошел не к лифту, а вверх по пожарной лестнице. "
                    "Я проверил замок: цепочка была накинута, но коврик перед дверью лежал вверх ногами."
                ),
                "cta_ending": "А вы бы открыли дверь после такого видео или сразу вызвали полицию?",
                "description": "Ночная запись с умного дверного звонка, от которой мурашки бегут по коже.",
                "tags": ["страшныеистории", "хоррор", "мистика", "домофон", "shorts", "ночь", "жутко", "триллер"],
                "image_prompts": [
                    "night vision doorbell camera footage style dark apartment corridor, eerie shadows, vertical",
                    "hooded silhouette standing motionless in front of dark apartment door, creepy glow",
                    "smartphone screen glowing in dark bedroom showing security camera alert",
                    "empty concrete fire escape stairwell lit by flickering fluorescent tube, horror",
                    "heavy metal apartment door with security chain locked from inside, dramatic shadows",
                ],
            },
            {
                "subreddit_or_tag": "r/creepypasta",
                "author": "u/forest_ranger_44",
                "title": "Почему егеря никогда не откликаются на зов по имени в тумане",
                "hook": "Старый лесничий в первый день предупредил меня: в густом тумане никому не отвечай.",
                "body": (
                    "Я устроился помощником на метеостанцию в северной тайге и списал его слова на старческую привычку. "
                    "На третью неделю под вечер со стороны болота потянулся плотный белый туман, видимость упала до пяти метров. "
                    "Когда я проверял датчики у края поляны, из кустов четко позвали меня по имени голосом моего напарника. "
                    "Я уже набрал воздух, чтобы крикнуть в ответ, но вспомнил: напарник уехал в поселок еще в обед на тракторе. "
                    "Голос повторил зов, но интонация была абсолютно одинаковой, словно воспроизвели запись. "
                    "Я тихо отступил в домик, запер засов и до рассвета слушал, как по крыльцу кружат тяжелые шаги."
                ),
                "cta_ending": "Смогли бы вы проработать одну смену в такой глуши? Напишите в комментариях.",
                "description": "Жуткое правило северных лесничих, которое однажды спасло жизнь стажеру.",
                "tags": ["лес", "страшилка", "тайга", "мистика", "shorts", "хоррор", "история", "туман"],
                "image_prompts": [
                    "dense eerie fog rolling through dark northern pine forest at dusk, vertical 9:16",
                    "isolated wooden weather station cabin in misty woods with single warm window",
                    "dark pine silhouettes fading into thick ghostly mist, horror movie atmosphere",
                    "rusted metal weather sensor post standing alone in foggy clearing",
                    "heavy wooden cabin door bolted from inside with shadows under crack",
                ],
            },
            {
                "subreddit_or_tag": "r/nosleep",
                "author": "u/subway_last_car",
                "title": "Последний поезд метро остановился в тоннеле, и свет погас на три минуты",
                "hook": "Если ваш поезд встал посреди перегона и погас свет, никогда не смотрите в темное стекло.",
                "body": (
                    "Я возвращался домой на последней электричке и в вагоне сидело всего четверо пассажиров. "
                    "Между двумя глубокими станциями состав резко затормозил, аварийные лампы моргнули и отключились. "
                    "В полной темноте светились только экраны телефонов, пока голос машиниста не приказал всем не подходить к окнам. "
                    "Девушка напротив не послушалась и прижалась лицом к стеклу, пытаясь разглядеть тоннель. "
                    "Через пару секунд по вагону прокатился сухой скрежет снаружи, будто кто-то провел ногтями вдоль всей двери, ровно на уровне глаз. "
                    "Когда свет наконец вернулся, на внешней стороне стекла остался четкий отпечаток слишком длинной ладони."
                ),
                "cta_ending": "Ездили когда-нибудь на самом последнем поезде метро? Поделитесь ощущениями.",
                "description": "Три минуты в обесточенном вагоне глубоко под землей.",
                "tags": ["метро", "страшныеистории", "ночь", "триллер", "shorts", "жутко", "городскиелегенды", "хоррор"],
                "image_prompts": [
                    "empty vintage subway car interior with flickering cold fluorescent lights, vertical",
                    "dark underground metro tunnel from train window, ominous shadows, cinematic",
                    "pitch black train compartment lit only by pale smartphone screen glow",
                    "scratched dark subway window reflection with eerie mist outside",
                    "long deserted underground metro platform late at night, thriller aesthetic",
                ],
            },
        ],
        "en": [
            {
                "subreddit_or_tag": "r/nosleep",
                "author": "u/watchtower_north",
                "title": "My smart doorbell caught me standing outside my apartment at 3 AM",
                "hook": "Yesterday morning my phone alerted me that someone stood outside my front door for three minutes.",
                "body": (
                    "I live alone on the twelfth floor and I know for a fact I was asleep before midnight. "
                    "I opened the doorbell archive expecting a lost delivery driver or a drunk neighbor. "
                    "Instead, in the grainy infrared night vision, a man wearing my exact gray hoodie was staring straight into the lens. "
                    "When I zoomed in, my stomach dropped. He had my exact face, except his smile was frozen way too wide and never blinked. "
                    "At three oh three sharp, he raised one hand, knocked softly three times, and walked toward the fire escape stairs instead of the elevator. "
                    "My deadbolt was still locked from inside, yet my welcome mat was flipped upside down."
                ),
                "cta_ending": "Would you stay in that apartment another night or pack immediately?",
                "description": "A chilling 3 AM smart doorbell notification that defies logic.",
                "tags": ["scarystories", "horror", "nosleep", "creepy", "shorts", "3am", "thriller", "nightmare"],
                "image_prompts": [
                    "grainy night vision security camera view of dark apartment hallway, vertical 9:16",
                    "hooded figure staring directly into doorbell camera in pitch dark hall",
                    "glowing smartphone screen held by trembling hand in dark bedroom",
                    "cold concrete fire exit staircase with flickering overhead tube light",
                    "heavy apartment front door with brass chain lock in moody shadows",
                ],
            },
            {
                "subreddit_or_tag": "r/creepypasta",
                "author": "u/forest_ranger_44",
                "title": "Why northern park rangers never answer voices calling their name in fog",
                "hook": "On my first day at the forest station, the old ranger gave me one warning about fog.",
                "body": (
                    "He told me if thick mist rolls in after dusk and someone calls my name, I must stay completely silent. "
                    "I laughed it off as an old timer's campfire superstition until my third week on the job. "
                    "Just before sunset, white fog swallowed the clearing so fast I could barely see five feet ahead. "
                    "While checking the rain gauge by the tree line, my partner's voice clearly called my name from the pines. "
                    "I almost yelled back before freezing. My partner had driven into town hours earlier for supplies. "
                    "The voice repeated my name again with the exact same flat tone, like a recording, while heavy footsteps circled my cabin until dawn."
                ),
                "cta_ending": "Could you survive a month working alone out in deep woods?",
                "description": "An unwritten survival rule deep inside the northern timberline.",
                "tags": ["scary", "forest", "ranger", "creepypasta", "shorts", "horrorstory", "fog", "survival"],
                "image_prompts": [
                    "thick white fog drifting between tall dark pine trees at twilight, vertical 9:16",
                    "lonely wooden ranger cabin glowing faintly inside misty forest",
                    "dark ominous tree line disappearing into dense white mist, thriller still",
                    "old metal weather station pole covered in dew inside eerie woods",
                    "wooden cabin door bolted shut with faint blue moonlight outside window",
                ],
            },
            {
                "subreddit_or_tag": "r/nosleep",
                "author": "u/subway_last_car",
                "title": "The last subway train stopped mid-tunnel and every light died",
                "hook": "If your midnight train stops inside a tunnel and the lights go out, never look at the glass.",
                "body": (
                    "I was riding the final metro train home with just three other tired passengers in the car. "
                    "Halfway beneath the river, the brakes screeched, the overhead tubes flickered, and darkness swallowed everything. "
                    "For ten seconds there was dead silence before the conductor's intercom crackled: stay seated and step away from the windows. "
                    "A guy across from me ignored the warning and pressed his face right up against the black glass to peer out. "
                    "Then came a slow metallic scrape running down the entire side of the train at eye level. "
                    "When power snapped back on a minute later, there was a long smeared handprint pressed into the tunnel grime outside his window."
                ),
                "cta_ending": "Do you ever get uneasy riding the last subway car at night?",
                "description": "Three terrifying minutes trapped underground between stations.",
                "tags": ["subway", "urbanlegend", "scary", "nosleep", "shorts", "horror", "midnight", "story"],
                "image_prompts": [
                    "empty retro subway train car with flickering cold lights late at night, vertical",
                    "black underground tunnel seen through scratched metro train window",
                    "pitch dark subway interior illuminated dimly by single phone screen",
                    "foggy train window glass with eerie smudge marks from outside",
                    "deserted underground subway platform receding into dark shadows",
                ],
            },
        ],
    },
    "psychology": {
        "ru": [
            {
                "subreddit_or_tag": "Психология",
                "author": "@mind_decoded",
                "title": "Эффект Прайминга: как одна фраза заставляет людей говорить вам «да»",
                "hook": "Ты замечал, что после трех маленьких «да» человек почти неспособен отказать в крупной просьбе?",
                "body": (
                    "В психологии это называют эффектом последовательного согласия или техникой «нога в двери». "
                    "Когда человек соглашается на крошечную и безопасную просьбу, его мозг моментально подстраивает самооценку: "
                    "он начинает воспринимать себя как отзывчивого и последовательного союзника. "
                    "Чтобы избежать внутреннего диссонанса при следующей просьбе, психика подсознательно толкает его снова сказать «да». "
                    "Этим ежедневно пользуются переговорщики, продавцы и даже обычные знакомые. "
                    "Но зная этот механизм, ты легко заметишь момент, когда разговор искусственно ведут к нужному ответу, и сможешь вовремя взять паузу."
                ),
                "cta_ending": "Замечали этот прием в жизни или на переговорах? Напишите в комментариях.",
                "description": "Разбор мощного психологического триггера: как работает техника последовательного согласия.",
                "tags": ["психология", "факты", "общение", "манипуляции", "саморазвитие", "shorts", "мозг", "лайфхак"],
                "image_prompts": [
                    "two people in intense calm conversation across dark wooden cafe table, cinematic vertical",
                    "glowing neural network synapses illuminated inside silhouette of human head",
                    "charismatic negotiator wearing minimalist dark blazer in warm spotlight",
                    "chessboard close up with dramatic shallow depth of field and moody lighting",
                    "person pausing thoughtfully before signing sleek dark contract, cinematic",
                ],
            },
            {
                "subreddit_or_tag": "Темная психология",
                "author": "@neuro_notes",
                "title": "Почему молчание в течение 4 секунд обезоруживает любого манипулятора",
                "hook": "Если на вас давят или хамят, просто промолчите четыре секунды и смотрите в переносицу.",
                "body": (
                    "Мозг человека эволюционно не выносит неловких пауз в конфликтном диалоге. "
                    "Любой манипулятор рассчитывает на вашу быструю эмоциональную реакцию: оправдания, злость или суетливый ответ. "
                    "Когда вместо этого вы сохраняете спокойное лицо и выдерживаете тишину всего на четыре секунды дольше нормы, сценарий собеседника рушится. "
                    "Чтобы заполнить вакуум, человек начинает сам оправдываться, повторяться или невольно раскрывать истинные мотивы. "
                    "Вы не сказали ни единого грубого слова, но полностью перехватили контроль над температурой комнаты."
                ),
                "cta_ending": "Пробовали когда-нибудь силу осознанной паузы? Делитесь опытом в комментариях.",
                "description": "Почему пауза в 4 секунды работает сильнее любого громкого спора.",
                "tags": ["психология", "уверенность", "переговоры", "манипуляция", "shorts", "факты", "интеллект", "общение"],
                "image_prompts": [
                    "calm confident person sitting quietly in dramatic chiaroscuro studio lighting, vertical",
                    "close up of focused eyes in soft amber shadow, cinematic portrait",
                    "minimalist luxury office meeting room with tense silence atmosphere",
                    "hourglass sand falling slowly in dark moody studio background",
                    "composed silhouette standing tall against city skyline at dusk",
                ],
            },
            {
                "subreddit_or_tag": "Нейронаука",
                "author": "@brain_hacks",
                "title": "Эффект Зейгарник: почему вы не можете забыть человека, с которым не договорили",
                "hook": "Почему незаконченные истории в голове болят сильнее, чем самые тяжелые финалы?",
                "body": (
                    "В начале прошлого века психолог Блюма Зейгарник заметила удивительную деталь в берлинском кафе: "
                    "официанты идеально помнили длинные заказы, пока клиенты не оплатили счет, но забывали всё через минуту после оплаты. "
                    "Наш мозг воспринимает незавершенный разговор или внезапное расставание как открытый фоновый процесс. "
                    "Он продолжает тратить энергию и прокручивать десятки альтернативных сценариев, пытаясь закрыть гештальт. "
                    "Поэтому лучший способ вернуть себе спокойный сон — не ждать идеального ответа извне, а самому поставить осознанную точку на бумаге."
                ),
                "cta_ending": "Какая незакрытая ситуация до сих пор всплывает у вас в памяти? Расскажите ниже.",
                "description": "Научное объяснение эффекта Зейгарник и того, как освободить голову от навязчивых мыслей.",
                "tags": ["зейгарник", "психология", "отношения", "мозг", "мысли", "shorts", "наука", "факты"],
                "image_prompts": [
                    "vintage European cafe table at night with warm golden lamp glow, cinematic vertical",
                    "person staring thoughtfully out rain-streaked train window at city lights",
                    "glowing puzzle pieces floating apart in dark surreal atmospheric light",
                    "hand writing final note in dark leather journal under warm desk lamp",
                    "peaceful sunrise over calm misty lake symbolizing mental clarity",
                ],
            },
        ],
        "en": [
            {
                "subreddit_or_tag": "Psychology",
                "author": "@mind_decoded",
                "title": "The Foot-in-the-Door Trick: why small yeses lead to huge favors",
                "hook": "Ever notice how getting someone to agree once makes them almost unable to say no later?",
                "body": (
                    "Psychologists call this the commitment and consistency bias, or the foot-in-the-door effect. "
                    "Once a person says yes to a tiny, harmless favor, their brain quietly updates their self-image: "
                    "I am the kind of person who helps out and follows through. "
                    "When a much larger request arrives minutes or days later, rejecting it creates uncomfortable mental friction. "
                    "To protect consistency, the mind nudges them into saying yes again. "
                    "Top negotiators use this daily, yet simply spotting the warm-up question gives you total power to pause before committing."
                ),
                "cta_ending": "Have you ever caught someone using this trick on you? Comment below.",
                "description": "How tiny commitments quietly reshape human decision-making.",
                "tags": ["psychology", "darkpsychology", "persuasion", "mindtricks", "shorts", "facts", "communication", "brain"],
                "image_prompts": [
                    "two professionals talking calmly across dark espresso table, cinematic vertical 9:16",
                    "illuminated glowing neural pathways inside human silhouette, dark backdrop",
                    "sharp minimalist chess pieces lit by warm side spotlight, moody contrast",
                    "confident speaker gesturing subtly in dim studio atmosphere",
                    "person pausing thoughtfully with pen hovering over dark notepad",
                ],
            },
            {
                "subreddit_or_tag": "Dark Psychology",
                "author": "@neuro_notes",
                "title": "Why a 4-second silence instantly breaks almost any manipulator",
                "hook": "Next time someone tries to corner you, stay silent for four full seconds and hold eye contact.",
                "body": (
                    "Human brains are wired to panic during unexpected silence inside a heated conversation. "
                    "Someone trying to intimidate or rush you relies on an instant emotional reflex: defending yourself, raising your voice, or over-explaining. "
                    "When you keep your expression neutral and wait four quiet seconds instead, their entire script collapses. "
                    "To escape the awkward vacuum, people almost always start backtracking, repeating themselves, or accidentally revealing what they truly want. "
                    "Without uttering a single harsh word, silence shifts every ounce of leverage straight to your side."
                ),
                "cta_ending": "Have you ever tried using deliberate silence in a tough moment?",
                "description": "Why four seconds of calm silence outperforms arguing back.",
                "tags": ["psychology", "confidence", "silence", "negotiation", "shorts", "mindset", "facts", "socialskills"],
                "image_prompts": [
                    "composed confident person seated in dark chiaroscuro lighting, vertical 9:16",
                    "macro portrait of calm focused eyes in warm amber shadow",
                    "sleek dark conference room with dramatic rim lighting and stillness",
                    "glass hourglass sand trickling slowly against black background",
                    "calm silhouette overlooking twilight city skyline through tall window",
                ],
            },
            {
                "subreddit_or_tag": "Neuroscience",
                "author": "@brain_hacks",
                "title": "The Zeigarnik Effect: why unfinished stories haunt your mind",
                "hook": "Why do unfinished conversations hurt ten times longer than clean endings?",
                "body": (
                    "In the nineteen twenties, psychologist Bluma Zeigarnik noticed waiters in Berlin could recite huge unpaid orders effortlessly, yet forgot everything seconds after the bill was paid. "
                    "Your brain treats an abrupt ending or unanswered message like an open background app draining battery nonstop. "
                    "It keeps replaying alternate endings because uncertainty feels like an unresolved threat. "
                    "That is why closure rarely comes from the other person. Writing down your own final decision tricks the brain into finally closing the tab."
                ),
                "cta_ending": "What unfinished chapter took you the longest to move past?",
                "description": "The neuroscience behind obsessive overthinking and mental closure.",
                "tags": ["zeigarnikeffect", "psychology", "overthinking", "neuroscience", "shorts", "brain", "closure", "facts"],
                "image_prompts": [
                    "classic European cafe table at dusk with warm amber lamp light, vertical 9:16",
                    "person looking out rainy window at blurred neon city reflections",
                    "glowing puzzle pieces suspended in dark misty void, conceptual art",
                    "fountain pen writing final words in dark leather notebook at night",
                    "golden sunrise breaking over calm still lake, peaceful closure mood",
                ],
            },
        ],
    },
    "motivation": {
        "ru": [
            {
                "subreddit_or_tag": "Дисциплина",
                "author": "@iron_routine",
                "title": "Правило 5 секунд и два процента: как вытащить себя из любого прокрастинационного дня",
                "hook": "Ты не ленивый — твой мозг просто ненавидит резкие старты и огромные цели.",
                "body": (
                    "Каждый раз, когда ты обещаешь себе с понедельника полностью изменить жизнь, психика включает режим защиты и саботирует всё к среде. "
                    "Вместо героизма попробуй правило микроскопического шага: открой задачу ровно на пять минут и разреши себе бросить сразу после таймера. "
                    "Самое тяжелое в любом деле — преодолеть трение первой минуты, пока дофамин еще на нуле. "
                    "Как только руки касаются клавиатуры или кроссовок, сопротивление падает в разы, и ты незаметно втягиваешься в поток. "
                    "Один процент прогресса каждый день за год умножает твои результаты в тридцать семь раз."
                ),
                "cta_ending": "Какой один маленький шаг ты сделаешь уже сегодня вечером? Напиши в комментариях.",
                "description": "Почему дисциплина строится на маленьких стартах, а не на редких вспышках вдохновения.",
                "tags": ["мотивация", "дисциплина", "продуктивность", "привычки", "успех", "shorts", "саморазвитие", "фокус"],
                "image_prompts": [
                    "athlete tying running shoes on dark asphalt road before dawn, cinematic vertical",
                    "focused creator working alone at minimalist desk before sunrise, warm lamp",
                    "dramatic mountain trail disappearing into golden morning mist, epic scale",
                    "close up of mechanical stopwatch and dark notebook on concrete desk",
                    "person standing on rooftop overlooking awakening city at golden hour",
                ],
            },
            {
                "subreddit_or_tag": "Фокус",
                "author": "@silent_work",
                "title": "Цена тишины: почему самые громкие люди редко доходят до вершины",
                "hook": "Когда ты рассказываешь всем о своих планах, мозг уже считает работу выполненной.",
                "body": (
                    "Исследования показывают странную ловушку: стоит нам похвастаться будущим проектом друзьям или в соцсетях, мы получаем дешевый выброс дофамина заранее. "
                    "Внутреннее чувство гордости усыпляет амбиции, и реальная пахота начинает казаться скучной. "
                    "Поэтому по-настоящему сильные люди пропадают с радаров на полгода. "
                    "Они работают в тишине, терпят первые провалы без зрителей и полируют навыки, пока вокруг все обсуждают тренды. "
                    "Пусть твоим самым громким заявлением станет готовый результат, с которым невозможно спорить."
                ),
                "cta_ending": "Согласны, что планы лучше держать в секрете до результата? Пишите ваше мнение.",
                "description": "Как перестать тратить энергию на пустые обещания и начать делать результат молча.",
                "tags": ["мотивация", "цели", "тишина", "успех", "саморазвитие", "shorts", "психологияуспеха", "работа"],
                "image_prompts": [
                    "lone programmer coding late at night lit by warm desk monitor glow, vertical",
                    "boxer training alone in dimly lit empty gym with chalk dust in air",
                    "architect sketching blueprints quietly under dramatic spotlight",
                    "dark rain outside glass studio while warm work desk glows steadily",
                    "sleek trophy or summit view emerging from fog at sunrise, cinematic",
                ],
            },
            {
                "subreddit_or_tag": "Характер",
                "author": "@daily_spark",
                "title": "Через пять лет ты пожалеешь только о тех шансах, где выбрал комфорт",
                "hook": "Никто в конце жизни не жалеет о том, что слишком смело попробовал и ошибся.",
                "body": (
                    "Страх неудачи мастерски маскируется под здравый смысл и шепчет: подожди идеального момента, подучи еще немного, начни с нового месяца. "
                    "Проблема в том, что идеального момента в календаре не существует. "
                    "Каждый месяц откладывания незаметно превращается в годы чужих сценариев и упущенных дверей. "
                    "Навык приходит не до прыжка, а прямо в процессе падения и быстрых попыток исправить курс. "
                    "Сделай ставку на свой рост прямо сейчас, даже если руки слегка дрожат от неизвестности."
                ),
                "cta_ending": "Какой шаг ты откладываешь уже больше месяца? Время назвать его вслух ниже.",
                "description": "Напоминание для тех, кто ждет идеального знака, чтобы начать действовать.",
                "tags": ["мотивация", "смелость", "рост", "жизнь", "shorts", "вдохновение", "дисциплина", "мысли"],
                "image_prompts": [
                    "hiker standing at edge of dramatic cliff looking across misty valley at dawn, vertical",
                    "sprinter poised on dark stadium track under dramatic floodlights",
                    "open door glowing with warm golden light at end of dark concrete hall",
                    "person stepping onto stage spotlight silhouette, inspiring cinematic mood",
                    "golden hour rays piercing through storm clouds over vast ocean",
                ],
            },
        ],
        "en": [
            {
                "subreddit_or_tag": "Discipline",
                "author": "@iron_routine",
                "title": "Why waiting for motivation keeps you stuck—and the 5-minute fix",
                "hook": "You are not lazy; your brain is simply wired to resist giant all-or-nothing goals.",
                "body": (
                    "Every time you swear to transform your entire life overnight, your nervous system reads it as a threat and sabotages you by Wednesday. "
                    "Drop the dramatic promises and use the five-minute rule instead. "
                    "Tell yourself you only have to work on the hard task for five tiny minutes, and you are free to quit when the timer rings. "
                    "The real enemy is never the work itself; it is the friction before the first minute. "
                    "Once momentum starts, resistance melts away, and compounding one percent daily transforms everything within a year."
                ),
                "cta_ending": "What is one task you will give five focused minutes to today?",
                "description": "Build unstoppable daily momentum without waiting for a burst of hype.",
                "tags": ["motivation", "discipline", "habits", "productivity", "shorts", "mindset", "focus", "growth"],
                "image_prompts": [
                    "runner lacing sneakers on dark misty street before sunrise, vertical 9:16",
                    "focused creator working quietly at dark desk under warm spotlight",
                    "steep alpine trail leading upward into golden dawn clouds, epic vertical",
                    "minimalist matte black timer and notebook on concrete table",
                    "silhouette standing on city rooftop overlooking warm golden sunrise",
                ],
            },
            {
                "subreddit_or_tag": "Focus",
                "author": "@silent_work",
                "title": "Build in silence: why announcing your goals secretly kills them",
                "hook": "The moment you announce your big plan to everyone, your brain thinks you already won.",
                "body": (
                    "Studies show that bragging about future goals triggers premature dopamine, giving you the emotional reward before any real work happens. "
                    "Suddenly the grind feels dull because you already tasted the applause. "
                    "That is why relentless builders vanish from the noise for six straight months. "
                    "They endure awkward early failures privately, sharpen their craft without an audience, and refuse to trade real progress for cheap praise. "
                    "Let your finished results make all the noise when the time is right."
                ),
                "cta_ending": "Do you work better quietly or when people hold you accountable?",
                "description": "Why protecting your focus in silence multiplies real execution.",
                "tags": ["mindset", "silentwork", "motivation", "success", "shorts", "grind", "discipline", "focus"],
                "image_prompts": [
                    "developer working late in quiet dark studio lit by warm screen glow, vertical",
                    "boxer shadowboxing alone in empty dim gym with floating dust beams",
                    "designer sketching quietly on dark drafting table under warm lamp",
                    "rainy window overlooking blurred city while steady work continues inside",
                    "climber reaching sunlit summit above sea of clouds, triumphant cinematic",
                ],
            },
            {
                "subreddit_or_tag": "Mindset",
                "author": "@daily_spark",
                "title": "Five years from now, you will only regret the risks you played safe",
                "hook": "Nobody reaches the end wishing they had waited even longer for the perfect time.",
                "body": (
                    "Fear loves disguising itself as smart planning, whispering that you need one more course, more savings, or a calmer month before starting. "
                    "Here is the harsh truth: that mythical perfect Monday never shows up on your calendar. "
                    "Every month spent waiting quietly hardens into years of watching bolder people claim the life you wanted. "
                    "Confidence never arrives before the jump; it is forged mid-air while adjusting your course. "
                    "Start scared, start small, just refuse to stay frozen in the waiting room."
                ),
                "cta_ending": "What leap have you been putting off this year? Name it in the comments.",
                "description": "Stop waiting for permission and take the leap while conditions are imperfect.",
                "tags": ["motivation", "mindset", "courage", "selfimprovement", "shorts", "inspiration", "success", "action"],
                "image_prompts": [
                    "traveler standing at edge of dramatic sunlit canyon ridge, vertical 9:16",
                    "sprinter set in starting blocks under dramatic stadium night lights",
                    "tall glowing doorway opening at end of dark concrete corridor",
                    "artist stepping out toward bright stage spotlight silhouette",
                    "sunbeams breaking through dark storm clouds over open ocean",
                ],
            },
        ],
    },
}


def _strip_json_fences(raw: str) -> str:
    cleaned = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _compose_full_narration(hook: str, body: str, cta: str) -> str:
    parts = [p.strip() for p in (hook, body, cta) if p and p.strip()]
    return " ".join(parts)


def _select_offline_story(
    niche: str,
    language: str,
    custom_topic: str = "",
    previous_titles: list[str] | None = None,
) -> GeneratedScript:
    lang = "ru" if language.lower().startswith("ru") else "en"
    niche_key = niche if niche in OFFLINE_STORIES else "reddit"
    pool = OFFLINE_STORIES[niche_key][lang]
    used = {t.strip().lower() for t in (previous_titles or []) if t.strip()}

    available = [item for item in pool if item["title"].strip().lower() not in used]
    chosen = random.choice(available if available else pool)

    title = chosen["title"]
    hook = chosen["hook"]
    body = chosen["body"]
    cta = chosen["cta_ending"]
    description = chosen["description"]
    tags = list(chosen["tags"])
    prompts = list(chosen["image_prompts"])

    topic = custom_topic.strip()
    if topic:
        if lang == "ru":
            title = f"{topic}: {title}" if len(topic) < 42 else topic
            hook = f"История про {topic}. {hook}"
            description = f"Тема: {topic}. {description}"
        else:
            title = f"{topic}: {title}" if len(topic) < 42 else topic
            hook = f"About {topic}. {hook}"
            description = f"Topic: {topic}. {description}"
        topic_tag = re.sub(r"[^\w]+", "", topic.lower())
        if topic_tag and topic_tag not in tags:
            tags.insert(0, topic_tag)

    return GeneratedScript(
        niche=niche_key,
        language=lang,
        subreddit_or_tag=chosen["subreddit_or_tag"],
        author=chosen["author"],
        title=title,
        hook=hook,
        body=body,
        cta_ending=cta,
        full_narration=_compose_full_narration(hook, body, cta),
        description=description,
        tags=tags[:12],
        image_prompts=prompts[:5],
        source="offline",
    )


async def generate_script(
    *,
    niche: str,
    language: str,
    custom_topic: str = "",
    api_key: str = "",
    base_url: str = "https://openrouter.ai/api/v1",
    model: str = "deepseek/deepseek-chat",
    previous_titles: list[str] | None = None,
) -> GeneratedScript:
    """
    Generate a vertical Shorts/TikTok script via an OpenAI-compatible LLM API,
    or via the rich built-in offline story bank when no API key is configured
    (or as fallback if the API fails).
    """
    lang = "ru" if language.lower().startswith("ru") else "en"
    niche_key = niche if niche in NICHE_INFO else "reddit"
    clean_key = api_key.strip()

    if not clean_key:
        logger.info("No LLM API key configured; using built-in offline story generator.")
        return _select_offline_story(niche_key, lang, custom_topic, previous_titles)

    from openai import AsyncOpenAI

    niche_label = NICHE_INFO[niche_key][lang]
    avoid_block = ""
    if previous_titles:
        avoid_list = "\n".join(f"- {t}" for t in previous_titles[-15:])
        avoid_block = f"\nAvoid repeating or closely resembling these recent titles:\n{avoid_list}\n"

    topic_line = (
        f"Specific user topic / angle: {custom_topic.strip()}"
        if custom_topic.strip()
        else "Pick a fresh, viral, highly engaging angle within the genre."
    )

    target_lang = "Russian" if lang == "ru" else "English"
    word_budget = "120-155 words" if lang == "ru" else "135-175 words"

    system_prompt = (
        "You are an elite YouTube Shorts and TikTok viral scriptwriter. "
        "Return ONLY valid raw JSON without markdown fences or commentary. "
        "Your spoken narration must be clean, conversational, fast-paced, and free of emojis, "
        "markdown formatting, or stage directions like [music] or (pause)."
    )

    user_prompt = (
        f"Write ONE viral 45-65 second vertical video script in {target_lang}.\n"
        f"Genre: {niche_label} ({niche_key}).\n"
        f"{topic_line}\n"
        f"{avoid_block}"
        "Structure requirements:\n"
        "1. hook: Explosive first 2 seconds that stops scrolling immediately (1 sentence).\n"
        f"2. body: Tight, vivid story/facts with rising tension ({word_budget} total across hook+body+cta_ending).\n"
        "3. cta_ending: Open-ended question or debate prompt that sparks comments.\n"
        "4. title: Punchy hook-card title (max 95 characters).\n"
        "5. subreddit_or_tag: Fitting label (e.g., r/AskReddit, r/nosleep, Psychology, Discipline).\n"
        "6. author: Realistic handle (e.g., u/night_shift or @mind_notes).\n"
        "7. description: 1-2 sentence upload description for Shorts/TikTok.\n"
        "8. tags: Array of 8-10 lowercase hashtag keywords without '#' symbol.\n"
        "9. image_prompts: Array of exactly 5 distinct, vivid vertical 9:16 cinematic image prompts IN ENGLISH "
        "for SDXL-Turbo matching the story beats (no text inside images).\n\n"
        "JSON keys required: subreddit_or_tag, author, title, hook, body, cta_ending, description, tags, image_prompts."
    )

    client = AsyncOpenAI(
        api_key=clean_key,
        base_url=base_url.strip() or "https://openrouter.ai/api/v1",
        timeout=45.0,
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=model.strip() or "deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.85 if attempt == 0 else 0.55,
            )
            content = response.choices[0].message.content or ""
            payload = json.loads(_strip_json_fences(content))

            hook = str(payload["hook"]).strip()
            body = str(payload["body"]).strip()
            cta = str(payload["cta_ending"]).strip()
            title = str(payload["title"]).strip()
            if not hook or not body or not title:
                raise ValueError("LLM returned empty hook/body/title")

            raw_tags = payload.get("tags") or []
            tags = [str(t).lstrip("#").strip() for t in raw_tags if str(t).strip()][:12]
            raw_prompts = payload.get("image_prompts") or []
            prompts = [str(p).strip() for p in raw_prompts if str(p).strip()][:6]
            while len(prompts) < 5:
                prompts.append(
                    f"cinematic vertical 9:16 moody scene illustrating {title}, dramatic lighting, photorealistic"
                )

            return GeneratedScript(
                niche=niche_key,
                language=lang,
                subreddit_or_tag=str(
                    payload.get("subreddit_or_tag") or NICHE_INFO[niche_key][f"default_tag_{lang}"]
                ).strip(),
                author=str(payload.get("author") or "u/shorts_story").strip(),
                title=title,
                hook=hook,
                body=body,
                cta_ending=cta,
                full_narration=_compose_full_narration(hook, body, cta),
                description=str(payload.get("description") or title).strip(),
                tags=tags,
                image_prompts=prompts,
                source="llm",
            )
        except Exception as exc:
            last_error = exc
            logger.warning("LLM script generation attempt %d failed: %s", attempt + 1, exc)

    logger.error("Falling back to offline story bank after LLM failure: %s", last_error)
    return _select_offline_story(niche_key, lang, custom_topic, previous_titles)
