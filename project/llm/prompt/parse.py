
# Rewrite the question into a search query
REWRITE_QUESTION = """
Rewrite the following question into a statement as a retrieval query: {question}
It should be a statement in natural language to search for the relevant information in the lifelog retrieval system. It should include all the information from the question, excluding the question phrase.

Avoid using "search for", "find", or "retrieve" in the query. Keep it descriptive. Don't replace question words with placeholders like somewhere, something (except for someones). Use the active voice, preferable in the past/past continuous tense. Write it in the first person, as if you are telling a story.

Some examples:
Question: "How many times did I go to the gym last month?"
Rewrite: "I was in the gym last month."

Question: "What did I eat for breakfast on Monday?"
Rewrite: "I was eating breakfast on Monday."

Question: "When was the last time I went to the park, assuming today is 2022-03-01?"
Rewrite: "I was in the park, before 2022-03-01."

Question: "Where did I buy the MacBook Pro in summer 2021?"
Rewrite: "I was buying my MacBook Pro in summer 2021."

Question: "What is the brand of my car?"
Rewrite: "The logo of my car."

Question: "What is the brand of my glasses?"
Rewrite: "A close-up of my glasses."

Question: "How long did I go running last night? Assume I only went running once."
Rewrite: "I was running last night."

Question: "How many hours did I spend at work last week?"
Rewrite: "I was at work last week."

Question: "How long is my average commute time to work?"
Rewrite: "I was commuting to work."

Question: "What is the color of my car?"
Rewrite: "The outside of my car."

Answer in this format:

```json
{{
    "text": "A statement that is a search query",
}}
```
"""


QUESTION_CLASSIFICATION = """
I need to classify the following question into a category. The question can be classified into one of the following categories:
- frequency: questions that ask about the frequency of an event, like "how often", "how many times", "how frequently"
- time: questions that ask about the time of an event, like "when", "what time", "how long", "how much time", "what date", "what month", "how long"
- location: questions that ask about the location of an event, like "where", "what place", "what location", "what area", "what city", "what country", "which country", "which city", "which area", "name of the place", "name of the location", "name of the area", "name of the city", "name of the country"
- visual: questions that ask about the visual information of an event, like "what does it look like", "what do I see", "what is in the image"

Provide the category for the following question:
Question: {question}
Response:
```json
{{
    "category": "category" (frequency, time, location, visual)
}}
```
"""

SIMPLE_EXAMPLES = """
Query: "I was biking in the park near my house in the early morning."
Response:

```json
{{
    "main": {{
        "visual": "biking in the park",
        "time": "early morning",
        "location": "in the park near my house"
    }}
}}
```

Query: "I was having an Irish beer on St. Patrick's Day last year. Assuming this year is 2022."
Response:
```json
{{
    "main": {{
        "visual": "having an Irish beer",
        "date": "17th March 2021"
        "location": ""
    }}
}}
```
"""

COMPLICATED_EXAMPLES = """
Query: "When did I go to a restaurant outside of Ireland and not have a Guinness?"
Response:
```json
{{
    "main": {{
        "visual": "going to a restaurant",
        "location": ""
    }},
    "must_not": {{
        "visual": "having a Guinness"
        "location": "in Ireland"
    }}
}}
```

Query: "It was a very cold winter day in New York City. I walked to the bus at sunrise and went to a conference."
Response:
```json
{{
    "main": {{
        "visual": "very cold winter day, walking at sunrise to the bus",
        "location": "New York City",
        "date": "January, February, December"
        "time": "from 9am to 10am" // because it is at winter so sunrise is late
    }},
    "after": {{
        "visual": "going to a conference",
        "location": "New York City", # probably the same as the main location
        "time": "from 9am to 10am",
    }}
}}
```
"""

REWRITE_QUERY = """
I need to rewrite the following information into a single search query to find the relevant information from the lifelog retrieval system.
{query}
{eating_filters}
Response in the following format:
```json
{{
    "text": "A statement that is a search query",
}}
```
"""

# Automatically parse the query into a different format
PARSE_QUERY = """
I need to parse information from a text query to find relevant information from the lifelog retrieval system. As my parser is rule-based, I need you to provide me with the relevant fields that I should consider. Be as specific as possible, because the parser is not very smart.

The fields are:
```
visual: str # what the lifelogger was doing visually
time: str # time hints, like "morning", "after 3pm", "at sunset"
date: str # date hints, like "last year", "on Christmas", "in 2020", "June 2019"
location: str # place's name, like "at home", "in France", "at the Guinness Storehouse", "in Barcelona"
```

If some location details are not specific (names of places, cities, countries), you should include them in visual field as they can be intepreted visually. Similarly, time information such as sunrise, sunset, or meal times can be included in the visual field. Only include the most specific information in the fields.  Don't say "any" or "unknown" or "unspecified". Just leave the field empty if the information is not available. Each field should be SHORT and CONCISE. Avoid saying "within the time range of 01/01/2019 and 01/07/2020" or "in the past" if the date is not specified.

One last thing, include a "must-not" query if there is any information that should be excluded from the search.

Some examples:
""" + SIMPLE_EXAMPLES + """
If there are some eating filters, please rephrase the query to include them.

Now it's your turn. Use no comments.
Provide the relevant fields for the following query:
Query:{query}
{eating_filters}
Response:
"""

# Parse before and after information
PARSE_BEFORE_AFTER = """
I need to find the relevant information from the lifelog retrieval system based on the before and after information. The system will retrieve the information based on the before and after information. The system will consider the before information as the query and the after information as the answer.
How many hours before and after each event should I consider to find the relevant information? The time unit is in hours. If you don't need to consider before or after, just put 0.

Do not invent any information. Think of this as "extracting". Most of the time, before and after are not needed.

For example, for the events "I am going to the airport to catch a flight to Paris". The before and after information could be:
```json
{{
    "main": "Going to the airport",
    "hours_after": "3-4", # 3-4 hours after the event
    "after": "I am at Paris"
}}
```

Example 2: "I was working at a cafe to wait for my friend. After that, we went to the cinema."
```json
{{
    "before": "working at a cafe",
    "hours_before": "0-1", # waited for 0-1 hour
    "main": "meeting my friend at the cafe",
    "hours_after": "1-2", # went to the cinema 1-2 hours after
    "after": "went to the cinema"
}}
```

Example 3: "I had a long walk in the park in the morning because I stayed out late the night before."
```json
{{
    "hours_before": 5-7, # it was the morning so, 7-8am, so last night was 10pm-2am, so 5-10 hours before
    "before": "stayed out late at night",
    "main": "long walk in the park",
}}
```

These are rational guesses. Now, provide the before and after information for the following query. Don't comment in the JSON.
Query: {query}
"""

PARSE_NEGATION = """
I need to find the relevant information from the lifelog retrieval system based on the negation information. The system will retrieve the information based on the negation information. The system will consider the negation information as the query and the relevant information as the answer.

For the text, please elaborate on the information so that the system can find the relevant information.

If there is any information that should be excluded from the search, provide the negation information to be used in a "$nor" query in MongoDB or "must_not" in Elasticsearch. The negation information should be as specific as possible. If there is no negation information, just leave it empty.

Example 1: "I was in the park at the weekend, but I didn't see any dogs."
text: "I was in the park on Saturday and Sunday"
must_not: "seeing any dogs"

Example 2: "I visited the museum outside of Ireland when it was dark."
text: "I visited the museum in the evening"
must_not: "in Ireland"

Query: {query}

Response:
```json
{{
    "text": "A statement that is a search query",
    "must_not": "A statement that should be excluded from the search"
}}
```
"""

# --- LSC25
QA_QUERY_PARSE_PROMPT = """
You are given a natural language **question** about an event or activity to retrieve from a photo or lifelog database. The question may include temporal clues (e.g. "before", "after", "then", or refer to specific days and times). Your task is to break down the question into thematically distinct sub-questions if needed, and identify the **main information being asked**.

By default, assume there is **only one question** — unless there are **clear, distinct sub-questions** referring to **different time periods or actions**. Do not over-segment.

The **main question** is the one that contains the user's key intent — usually the most detailed or specific part. Other parts are for temporal or contextual reference.

Do **not** split just because:
- the question contains "before", "after", or "then"
- the structure is compound or complex
- the wording shifts
- extra context is included

Only split if there are **distinct sub-questions** referring to **different times or events**, and the answer would involve fetching **separate data or evidence**.

> ✅ Aim for **one question** in most cases, especially if the input is shorter than 20 words.
> 🔁 Only split into 2–3 parts if necessary for clarity.
> 🔢 Never return more than **5 total parts** (2 before, 1 main, 2 after).

Return a `max_time` (in minutes) and mark which part is the main one.

---

🧪 Examples

Example 1 – Single question with context

Input:
> What was I doing at the cafe? I think I had my laptop and someone joined me later.

Output:
```json
{{
  "temporal_events": [
    "What was I doing at the cafe? I think I had my laptop and someone joined me later."
  ],
  "max_time": 0,
  "main_event": 0
}}
⸻

Example 2 – Question with before-context
Input:

What did I do before arriving at the airport?

Output:

```json
{{
  "temporal_events": [
    "What did I do before arriving at the airport?"
  ],
  "max_time": 60,
  "main_event": 0
}}
```json
⸻

Example 3 – Clear multi-step timeline
Input:

What was I doing before going to school, and what did I do afterward?

Output:
```json
{{
  "temporal_events": [
    "What was I doing before going to school?",
    "going to school",
    "What did I do afterward?"
  ],
  "max_time": 120,
  "main_event": 1
}}
```
⸻

Example 4 – Light context, not a new question
Input:

What colour was my jumper when I was sitting in the kitchen? I think it was in the morning and the window was open.

Output:
```json
{{
  "temporal_events": [
    "What colour was my jumper when I was sitting in the kitchen? I think it was in the morning and the window was open."
  ],
  "max_time": 0,
  "main_event": 0
}}
```
⸻

Now your turn:

The question: {query} Return the JSON in this format:

```json
{{ "temporal_events": [ "before context if any", "main question", "after context if any" ], "max_time": 60, "main_event": 1 }}
```
"""

SPLIT_QUERY_PROMPT = """
You are given a list of temporally distinct events, extracted from a natural language summary.

Your task is to extract three types of information only if explicitly stated in each event:
	•	Visual information: What can be seen in the event (objects, people, actions).
	•	Temporal information: When the event occurred (only absolute or time-mappable expressions).
	•	Spatial information: Where the event occurred (only location data detectable via GPS).

Only include time references that could realistically be inferred from lifelog metadata, such as:
	•	Explicit clock time (e.g. "3 PM", "in the evening", "morning")
	•	Day references (e.g. "Monday", "weekend", "the next day")
	•	Time-specific markers that could correlate with system timestamps or schedules (e.g. "after school" only if the phrase is very specific and time-mappable)
	•	Date references (e.g. "on 2022-03-01", "in June 2021", "last year", "New Year's Eve")
❌ Do not include vague or relative references like:
	•	"after having lunch", "before going out", "later that day"
These are not mappable to system-level timestamps and should be excluded.
✅ Leave the field as an empty string if no explicit, time-mappable expression is mentioned.

Only include locations that could realistically be derived from GPS, such as:
	•	Place names, addresses, known landmarks, neighbourhoods
	•	Location types explicitly stated in the text (e.g. “a cafe”, “the university library”)
❌ Do not include relative or vague spatial descriptions like:
	•	“near a wall”, “on the left”, “next to the person”
These cannot be inferred from GPS or map data and should be excluded.
✅ Leave the field as an empty string if no GPS-mappable location is mentioned.

⸻

🚫 Important Constraints:
	•	Do not add or invent any new information. Only extract what’s already present in the event text.
	•	The visual information must be a shorter version of the original event text, and should contain only what could be visually observed (people, objects, actions, scenes).
	•	If something cannot be seen (e.g., “I felt nervous”, “I just came from somewhere”), exclude it from the visual summary.
	•	If no explicit temporal or spatial information is present, leave those fields empty strings ("").
	•	If events are clearly linked in time or location, you may share temporal/spatial information across them.

⸻

🚫 Common Mistakes to Avoid

❌ Do not describe things that are not mentioned.
❌ Do not infer emotions, motivations, or unmentioned objects.
❌ Do not say things like “a crowd was there” unless the input says so.

✅ Only copy, shorten, and filter.


⸻

Finally, merge the consecutive events if they share most of the same visual information, and are temporally or spatially close to each other, or can complement each other to add more information to the event.
⸻

Here is the summary: {summary}
Here are the events:
{events}

Return a JSON object with the following format:
```json
{{
    "events": [
        {{

            "event": "repeat the query",
            "visual": "what can be seen in the image(s) captured in the event",
            "time": (only absolute or time-mappable expressions).
            "location": (address, location, or GPS detectable location)
        }},
        {{
            "event": "here is an example query",
            "visual": "a building full of people",
            "time": "on Christmas Eve",
            "location": "at the Guinness Storehouse in Dublin"
        }}
    ],
    "main_event": 1 # the index of the main event (0-based)
}}
```
"""

QUERY_PARSE_PROMPT = """
You are given a natural language narrative describing an event or activity to look for in a photo database. Some clues are given to describe the context of the event (e.g. "before", "after", "then"). Your task is split the narrative into thematically relevant events, and identify the main event.

⚠️ By default, assume there is **only one event** — unless there are **clear, distinct actions** that occur **at separate times** (before/after/then). Do not guess. Do not over-segment.

The main event is the most detailed one, while the others are just for temporal or contextual reference.

Do not split just because:
- the sentence starts with "then" or "after"
- the tone changes
- there is a full stop
- the scene seems to shift
- extra information is added

Only split if there are **multiple thematic events** that are **clearly distinct** and **occur at different times**, e.g. half an hour apart or even hours apart, that clearly take place at different locations.

> ✅ Aim for **one event** in most cases, especially if the query is shorter than 20 words. 
> 🔁 Only split into 2 or 3 events if absolutely necessary.  
> 🔢 Never return more than **5 events total** (2 before, 1 main, 2 after).

Return a `max_time` (in minutes) and mark which event is the main one.

---

### 🧪 Examples

#### Example 1 – Single Event (with context)
**Input:**
> I was working on my laptop in the lab. There were two whiteboards full of scribbles. My colleague came by later but I stayed focused on my code.

**Output:**
```json
{{
  "temporal_events": [
    "I was working on my laptop in the lab. There were two whiteboards full of scribbles. My colleague came by later but I stayed focused on my code."
  ],
  "max_time": 0,
  "main_event": 0
}}



⸻

Example 2 – 2 Events (clear before–main)

Input:

I was sitting outside the library, after grabbing a coffee from the campus cafe.

Output:

{{
  "temporal_events": [
    "grabbing a coffee from the campus cafe.",
    "sitting outside the library."
  ],
  "max_time": 10,
  "main_event": 1
}}



⸻

Example 3 – 3 Events, re-ordered chronologically

Input:

I was walking around the city centre. Before that I was in a meeting. After the walk, I went to get lunch near the river.

Output:

{{
  "temporal_events": [
    "being in a meeting.",
    "walking around the city centre.",
    "getting lunch near the river."
  ],
  "max_time": 90,
  "main_event": 1
}}



⸻

Example 4 – Supportive explanation (should not be split)

Input:

I was looking for my keys in the kitchen. It was in DCU and I was having a coffee. I couldn't remember where I put them. I was in a hurry to get to the lab.

Output:

{{
  "temporal_events": [
    "I was looking for my keys in the kitchen. It was in DCU and I was having a coffee. I couldn't remember where I put them. ",
    "I am at a lab."
  ],
  "max_time": 0,
  "main_event": 0
}}



⸻

Example 5 – Light context, no new event

Input:

I was in the kitchen making coffee. It was a sunny day and I could hear birds outside. The window was open and it was early morning. After that, I went to the lab.

Output:

{{
  "temporal_events": [
    "I was in the kitchen making coffee. It was a sunny day and I could hear birds outside. The window was open and it was early morning.",
    "I went to the lab."
  ],
  "max_time": 0,
  "main_event": 0
}}



⸻

Now your turn:

The query: {query}
Return the JSON in this format:

{{
  "temporal_events": [
    "before event if any",
    "main event",
    "after event if any"
  ],
  "max_time": 60,
  "main_event": 1
}}
"""
