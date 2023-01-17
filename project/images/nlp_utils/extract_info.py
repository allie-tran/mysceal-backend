from gensim.models.phrases import Phraser
from gensim.models import Word2Vec
from scipy.spatial.distance import cosine
from nltk import pos_tag
from collections import defaultdict
from ..nlp_utils.common import *
from ..nlp_utils.pos_tag import *
from ..nlp_utils.time import *
from ..nlp_utils.synonym import *
import numpy as np
init_tagger = Tagger(locations)
time_tagger = TimeTagger()
e_tag = ElementTagger()

bigram_phraser = Phraser.load(f"{COMMON_PATH}/bigram_phraser.pkl")


def morphy(word):
    result = ""
    try:
        result = wn.synsets(word)[0].lemmas()[0].name()
    except IndexError:
        result = wn.morphy(word)
    return result

def process_for_ocr(text):
    final_text = defaultdict(lambda : defaultdict(float))
    for word in text:
        final_text[word][word] = 1
        for i in range(0, len(word)-1):
            if len(word[:i+1]) > 1:
                final_text[word][word[:i+1]] += (i+1) / len(word)
            if len(word[i+1:]) > 1:
                final_text[word][word[i+1:]] += 1 - (i+1)/len(word)
    return final_text

def get_vector(word):
    if word:
        if model.wv.__contains__(word.replace(' ', "_")):
            return model.wv[word.replace(' ', "_")]
        words = [model.wv[word]
                for word in word.split() if model.wv.__contains__(word)]
        if words:
            return np.mean(words, axis=0)
        else:
            wn_word = wn.morphy(word)
            if model.wv.__contains__(wn_word):
                return model.wv[wn_word]
    return None


def get_deeplab_vector(word):
    if word:
        words = [model.wv[word]
                 for word in word.split(';') if model.wv.__contains__(word)]
        if words:
            return np.mean(words, axis=0)
        else:
            wn_word = wn.morphy(word)
            if model.wv.__contains__(wn_word):
                return model.wv[wn_word]
    return None



KEYWORD_VECTORS = {keyword: get_vector(keyword)
                   for keyword in all_keywords_without_attributes}
KEYWORD_VECTORS = {keyword: vector for (keyword, vector) in KEYWORD_VECTORS.items() if vector is not None}
DEEPLAB_VECTORS = {keyword: get_deeplab_vector(keyword)
                   for keyword in map2deeplab}
DEEPLAB_VECTORS = {keyword: vector for (
    keyword, vector) in DEEPLAB_VECTORS.items() if vector is not None}

class Word:
    def __init__(self, word, attribute=""):
        self.word = word
        self.attribute = attribute
        self.modifier = 50

    def expand(self):
        synonyms = [self.word]
        synsets = wn.synsets(self.word.replace(" ", "_"))
        all_similarities = defaultdict(float)
        if synsets:
            syn = synsets[0]
            synonyms.extend([lemma.name().replace("_", " ")
                             for lemma in syn.lemmas()])
            for name in [name.name() for s in syn.closure(hypo, depth=1) for name in s.lemmas()] + \
                    [name.name() for s in syn.closure(hyper, depth=1) for name in s.lemmas()]:
                name = name.replace("_", " ")
                if name in all_keywords:
                    all_similarities[name] = 1.0 * self.modifier
        deeplab_scores = defaultdict(float)
        for i, word in enumerate(synonyms):
            vector = get_vector(word)
            if vector is not None:
                similarities = [(keyword, 1-cosine(get_vector(word),
                                               KEYWORD_VECTORS[keyword])) for keyword in KEYWORD_VECTORS]
                similarities = sorted([s for s in similarities if s[1] > 0.7],  key=lambda s: -s[1])[:10]
                for sym, score in similarities:
                    all_similarities[sym] = max(
                        all_similarities[sym], score * (1-i*0.1) * self.modifier)
                similarities = [(keyword, 1-cosine(get_vector(word),
                                                   DEEPLAB_VECTORS[keyword])) for keyword in DEEPLAB_VECTORS]
                similarities = sorted(
                    [s for s in similarities if s[1] > 0.7],  key=lambda s: -s[1])[:10]
                for sym, score in similarities:
                    sym = deeplab2simple[sym]
                    deeplab_scores[sym] = max(
                        deeplab_scores[sym], score * (1-i*0.1))

            if word in all_keywords:
                all_similarities[word] = 2.0 * (1-i*0.1) * self.modifier

        deeplab_scores = defaultdict(float)
        attributed_similarities = {}
        if self.attribute:
            all_similarities[self.attribute] = 1.0
            for word, score in all_similarities.items():
                if f"{self.attribute} {word}" in all_keywords:
                    attributed_similarities[f"{self.attribute} {word}"] = score * 2

        return dict(sorted(list(all_similarities.items()) + list(attributed_similarities.items()), key=lambda x: -x[1])), deeplab_scores

    def __repr__(self):
        return " ".join(([self.attribute] if self.attribute else []) + [self.word])


def search(wordset, text):
    results = []
    text = " " + text + " "
    for keyword in wordset:
        if keyword:
            if " " + keyword + " " in text:
                results.append(keyword)
            # if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                # results.append(keyword)
    return results

# Partial match only
def search_possible_location(text):
    results = []
    gps_results = []
    for location in locations:
        for i, extra in enumerate(locations[location]):
            # Full match
            if i == 0 and re.search(r'\b' + re.escape(extra) + r'\b', text, re.IGNORECASE):
                return [extra], [(location, 1.0)], True
            if re.search(r'\b' + re.escape(extra) + r'\b', text, re.IGNORECASE):
                if extra not in results:
                    results.append(extra)
                gps_results.append((location, len(extra.split())/len(location.split())))
                break
    return results, gps_results, False

# gps_location_sets = {location: set([pl for pl in location.lower().replace(',', ' ').split() if pl not in stop_words]) for location, gps in map_visualisation}
gps_not_lower = {}
for loc in locations:
    for origin_doc, (lat, lon) in map_visualisation.items():
        if loc == origin_doc.lower():
            gps_not_lower[loc] = origin_doc

def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

class Query:
    def __init__(self, text, shared_filters=None):
        self.negative = ""
        self.disable_region = False
        if "—disable_region" in text:
            print("Disabling region")
            self.disable_region = True
            text = text.replace("—disable_region", "")
        self.disable_location = False
        if "—disable_location" in text:
            print("Disabling location")
            self.disable_location = True
            text = text.replace("—disable_location", "")
        if "NOT" in text:
            text, self.negative = text.split("NOT")
            self.negative = self.negative.strip(". \n").lower()
            self.negative = [word for word in self.negative.split() if word in all_keywords]
        text = text.strip(". \n").lower()
        self.time_filters = None
        self.date_filters = None
        self.driving = False
        self.on_airplane = False
        self.ocr_queries = []
        self.location_queries = []
        self.query_visualisation = defaultdict(list)
        self.location_filters = []
        self.country_to_visualise = []
        self.extract_info(text, shared_filters)
        self.expand()

    def extract_info(self, text, shared_filters=None):
        def search_words(wordset):
            return search(wordset, text)
        self.original_text = text

        quoted_text = " ".join(re.findall(r'\"(.+?)\"', text))
        text = text.replace(f'"{quoted_text}"', "")
        if "driving" in text:
            self.driving = True
            text = text.replace("driving", "")
        if "on airplane" in text:
            self.on_airplane = True
            # text = text.replace("on airplane", "")

        self.ocr = process_for_ocr(quoted_text.split())

        if not self.disable_location:
            self.locations = search_words(locations)
            self.place_to_visualise = [gps_not_lower[location] for location in self.locations]
            if self.locations:
                self.query_visualisation["LOCATION"].extend(self.locations)
            else:
                possible_locations = search_possible_location(text)
                if possible_locations:
                    self.query_visualisation["POSSIBLE LOCATION(S)"].extend(possible_locations)
        else:
            self.locations = []
            self.place_to_visualise = []


        print("Locations:", self.locations)
        for loc in self.locations:
            text = rreplace(text, loc, "", 1) #TODO!

        if not self.disable_region:
            self.regions = search_words(regions)
        else:
            self.regions = []

        for reg in self.regions:
            self.query_visualisation["REGION"].append(reg)
            for country in countries:
                if reg == country.lower():
                    self.country_to_visualise.append({"country": country, "geojson": countries[country]})
        for region in self.regions:
            text = rreplace(text, region, "", 1) #TODO!


        # processed = set([w.strip(",.") for word in self.regions +
                        #  self.locations for w in word.split()])
        # if not full_match:
        #     # self.locations.extend(search_words(
        #         # [w for w in ["hotel", "restaurant", "airport", "station", "cafe", "bar", "church"] if w not in self.locations]))
        #     for loc in self.locations[len(self.gps_results):]:
        #         for place, _ in map_visualisation:
        #             if loc in place.lower().split():
        #                 self.place_to_visualise.append(place)

        # if full_match:
        #     for loc in self.locations:
        #         self.query_visualisation["LOCATION"].append(loc)
        # else:
        #     for loc in self.locations:
        #         self.query_visualisation["POSSIBLE LOCATION"].append(loc)

        self.weekdays = []
        self.dates = None
        self.start = (0, 0)
        self.end = (24, 0)

        tags = time_tagger.tag(text)
        processed = set()
        for i, (word, tag) in enumerate(tags):
            if tag in ["WEEKDAY", "TIMERANGE", "TIMEPREP", "DATE", "TIME", "TIMEOFDAY"]:
                processed.update(word.split())
                self.query_visualisation[word] = [tag]
            if tag == "WEEKDAY":
                self.weekdays.append(word)
            elif tag == "TIMERANGE":
                s, e = word.split("-")
                self.start = adjust_start_end(
                    "start", self.start, *am_pm_to_num(s))
                self.end = adjust_start_end("end", self.end, *am_pm_to_num(e))
            elif tag == "TIME":
                if word in ["2015", "2016", "2018", "2019", "2020"]:
                    self.dates = get_day_month(word)
                else:
                    timeprep = ""
                    if i > 1 and tags[i-1][1] == 'TIMEPREP':
                        timeprep = tags[i-1][0]
                    if timeprep in ["before", "earlier than", "sooner than"]:
                        self.end = adjust_start_end(
                            "end", self.end, *am_pm_to_num(word))
                    elif timeprep in ["after", "later than"]:
                        self.start = adjust_start_end(
                            "start", self.start, *am_pm_to_num(word))
                    else:
                        h, m = am_pm_to_num(word)
                        self.start = adjust_start_end(
                            "start", self.start, h - 1, m)
                        self.end = adjust_start_end("end", self.end, h + 1, m)
            elif tag == "DATE":
                self.dates = get_day_month(word)
            elif tag == "TIMEOFDAY":
                if word not in ["lunch", "breakfast", "dinner", "sunrise", "sunset"]:
                    processed.add(word)
                # self.query_visualisation["TIME" if "TIME" in tag else tag].append(word)
                timeprep = ""
                if i > 1 and tags[i-1][1] == 'TIMEPREP':
                    timeprep = tags[i-1][0]
                if "early" in timeprep:
                    if "early; " + word in timeofday:
                        word = "early; " + word
                elif "late" in timeprep:
                    if "late; " + word in timeofday:
                        word = "late; " + word
                if word in timeofday:
                    s, e = timeofday[word].split("-")
                    self.start = adjust_start_end(
                        "start", self.start, *am_pm_to_num(s))
                    self.end = adjust_start_end(
                        "end", self.end, *am_pm_to_num(e))
                else:
                    print(
                        word, f"is not a registered time of day ({timeofday})")
        print(processed)
        print(tags)
        if shared_filters:
            if not self.weekdays:
                self.weekdays.extend(shared_filters.weekdays)
            if self.dates is None:
                self.dates = shared_filters.dates

        self.phrases = []
        unigrams = [
            word for word, tag in tags if word == ',' or word not in stop_words]
        for phrase in bigram_phraser[unigrams]:
            to_take = False
            for word in phrase.split('_'):
                if word not in processed:
                    to_take = True
                    break
            if to_take:
                self.phrases.append(phrase.replace('_', ' '))

        attributed_phrases = []
        taken = set()
        for i, phrase in enumerate(self.phrases[::-1]):
            if phrase == ",":
                continue
            n = len(self.phrases) - i - 1
            if n in taken:
                continue
            attribute = ""
            if n > 0 and self.phrases[n-1] in attribute_keywords:
                attribute = self.phrases[n-1]
                taken.add(n-1)
            attributed_phrases.append(Word(phrase, attribute))
        self.attributed_phrases = attributed_phrases[::-1]


    def expand(self):
        self.seperate_scores = {}
        self.scores = defaultdict(float)
        self.atfidf = defaultdict(float)
        self.keywords = []
        self.useless = []
        for word in self.attributed_phrases:
            expanded, deeplab = word.expand()
            self.seperate_scores[word.__repr__()] = expanded
            for keyword in expanded:
                self.scores[keyword] = max(
                    self.scores[keyword], expanded[keyword])
            for keyword in deeplab:
                self.atfidf[keyword] = max(
                    self.atfidf[keyword], deeplab[keyword])
            to_visualise = [w for w in expanded if w in all_keywords]
            if word.__repr__() in all_keywords:
                self.keywords.append(word.__repr__())
                self.query_visualisation[word.__repr__()] = "KEYWORD\n" + "\n".join(to_visualise)
            else:
                if expanded:
                    self.query_visualisation[word.__repr__(
                    )] = "NON-KEYWORD\n" + "\n".join(to_visualise)
                else:
                    self.useless.append(word.__repr__())

        for word in self.keywords:
            self.scores[word] += 20

    def get_info(self):
        return {"query_visualisation": [(hint, ", ".join(value)) for hint, value in self.query_visualisation.items()],
                "country_to_visualise": self.country_to_visualise,
                "place_to_visualise": self.place_to_visualise}

    def time_to_filters(self):
        if not self.time_filters:
            # Time
            s, e = self.start[0], self.end[0]
            if s > e: # TODO!
                s, e = e, 24
            self.time_filters = {
                                    "range":
                                    {
                                        "hour":
                                        {
                                            "gte": s,
                                            "lte": e
                                        }
                                    }
                                }

            # Date
            self.date_filters = []
            if self.dates:
                y, m, d = self.dates
                if y:
                    self.date_filters.append({"term": {"year": str(y)}})
                if m:
                    self.date_filters.append(
                        {"term": {"month": str(m).rjust(2, "0")}})
                if d:
                    self.date_filters.append(
                        {"term": {"date": str(d).rjust(2, "0")}})
            if self.start[0] != 0 and self.end[0] != 24:
                self.query_visualisation["TIME"] = [f"{self.start[0]}:00 - {self.end[0]}:00"]
            if str(self.dates) != "None":
                self.query_visualisation["DATE"] = [str(self.dates)]
        return self.time_filters, self.date_filters

    def make_ocr_query(self):
        if not self.ocr_queries:
            self.ocr_queries = []
            for ocr_word in self.ocr:
                dis_max = []
                for ocr_word, score in self.ocr[ocr_word].items():
                    dis_max.append(
                        {"rank_feature": {"field": f"ocr_score.{ocr_word}", "boost": 200 * score, "linear": {}}})
                self.ocr_queries.append({"dis_max": {
                    "queries": dis_max,
                    "tie_breaker": 0.0}})
        return self.ocr_queries
        #TODO: multiple word in OCR

    def make_location_query(self):
        if not self.location_filters:
            for loc in self.locations:
                place = gps_not_lower[loc]
                place = gps_not_lower[loc]
                dist = "0.5km"
                pivot = "5m"
                if "airport" in loc or "home" in loc:
                    dist = "2km"
                    pivot = "200m"
                elif "dcu" in loc:
                    dist = "1km"
                    pivot = "100m"

                for place_iter, (lat, lon) in map_visualisation.items():
                    if place == place_iter:
                        # self.location_queries.append({
                        #         "distance_feature": {
                        #             "field": "gps",
                        #             "pivot": pivot,
                        #             "origin": [lon, lat],
                        #             "boost": score * 50
                        #         }
                        #     })
                        self.location_filters.append({
                            "geo_distance": {
                                "distance": dist,
                                        "gps": [lon, lat]
                            }
                        })
                        break

            # # General:
            # if len(self.gps_results) < len(self.locations):
            #     for loc in self.locations[len(self.gps_results):]:
            #         loc_set = set(loc.split())
            #         for place, (lat, lon) in map_visualisation:
            #             set_place = gps_location_sets[place]
            #             if loc_set.issubset(set_place):
            #                 pivot = "5m"
            #                 if "airport" in set_place:
            #                     pivot = "200m"
            #                     self.location_filters.append({
            #                         "geo_distance": {
            #                             "distance": "2km",
            #                             "gps": [lon, lat]
            #                         }
            #                     })
            #                 elif "dcu" in set_place:
            #                     pivot = "100m"

            #                 self.location_queries.append({
            #                     "distance_feature": {
            #                         "field": "gps",
            #                         "pivot": pivot,
            #                         "origin": [lon, lat],
            #                         "boost": len(loc_set) / len(set_place) * 50
            #                     }
            #                 })
        # if self.location_queries:
            # return {"dis_max": {"queries": self.location_queries, "tie_breaker": 0.0}}
        return self.location_filters
