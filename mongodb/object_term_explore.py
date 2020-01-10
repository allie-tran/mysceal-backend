import json
import pickle
from collections import Counter
from nltk import word_tokenize
from nltk.stem import PorterStemmer
from nltk import bigrams
from nltk import MWETokenizer

# place365 = json.load(open('data/u1_place365.json'))
# places = Counter()
# for image in place365:
#     for word in place365[image].split(", "):
#         places[word] += 1
#
# print(places.most_common(100).keys())

# GROUP 1
group1_text="""person: person
vehicle: bicycle, motorcycle, car, bus, train, truck, airplane, boat
outdoor: traffic light, fire hydrant, stop sign, parking meter, bench
animal: dog, horse, cow, sheep, giraffe, zebra, bear, bird, cat, dog, horse, sheep, cow, elephant, bear
accessory: backpack, umbrella, handbag, tie, suitcase, pen, glove
sport: frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket
kitchen: bottle, wine glass, cup, fork, knife, spoon, bowl
food: banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake, hamburger
furniture: chair, couch, potted plant, bed, dining table, toilet
electronic: tv, laptop, mouse, remote, keyboard, cell phone
appliance: microwave, oven, toaster, sink, refrigerator
indoor: book, clock, vase, scissors, teddy bear, hair drier, toothbrush"""
categories_1 = {}
for line in group1_text.split("\n"):
    category, words = line.split(': ')
    words = words.split(', ')
    categories_1[category] = set(words + [category])

# GROUP 2:
group2_text="""person: person
bicycle: bicycle, motorcycle
car: car
bus: bus, train, truck
airplane
boat
traffic light
stop sign
bench
outdoor: fire hydrant, parking meter
dog: dog, horse
animal: cow, sheep, giraffe, zebra, bear, bird, cat, elephant
backpack: backpack, handbag
umbrella
tie
suitcase
pen: baseball bat
glove
sport: frisbee, skis, snowboard, sports ball, kite, baseball glove, skateboard, surfboard, tennis racket
bottle
wine glass
cup
fork
bowl
apple
orange
hot dog
hamburger: donut
sandwich
cake
food: banana, orange, broccoli, carrot, pizza
chair
couch
potted plant
bed
dining table
furniture: toilet
tv
laptop
mouse
remote
keyboard
cell phone
microwave: microwave, toaster
oven
refrigerator
sink
book
clock
vase
toothbrush
indoor: scissors, teddy bear, hair drier"""
categories_2 = {}
for line in group2_text.split("\n"):
    if ':' not in line:
        categories_2[line] = {line}
    else:
        category, words = line.split(': ')
        words = words.split(', ')
        categories_2[category] = set(words + [category])

# GROUP 3
group3_text="""elevator: elevator lobby, elevator/door, bank vault, locker room
cafeteria: fastfood restaurant, restaurant kitchen, dining hall, food court, restaurant, butchers shop, restaurant patio, coffee shop, pizzeria, pub/indoor, bar, diner/outdoor, beer hall, bakery/shop, delicatessen
office cubicles
television room: television studio, living room
entrance hall: elevator lobby
balcony: balcony/exterior, balcony/interior
lobby: ballroom
driveway
church: church/indoor, synagogue/outdoor
room: nursery, childs room, utility room, waiting room
archive
tree: tree house, tree farm, forest road, greenhouse
ceiling: berth, elevator shaft, alcove, attic
wall: berth, dam, elevator shaft
campus: industrial area
gymnasium/indoor
catatomb: grotto
fountain
garden: roof garden, beer garden, zen garden, topiary garden, junkyard, yard, courtyard, campsite, greenhouse, patio
hotel_room: youth hostel, dorm room, motel, bedroom, hotel/outdoor
sea: ocean, wind farm, harbor, cliff, coast, boat deck
garage: garage/outdoor, parking garage/indoor, parking garage/outdoor
indoor
airport_terminal: airport terminal
aqueduct: canal
stairs: amphitheater, mezzanine, staircase
skyscraper: water tower, construction site
none: wheat field, boxing ring, embassy, manufactured home, hospital, ice skating rink, hangar/indoor, hangar/outdoor, waterfall, crevasse, burial chamber, lock chamber, fire escape
dark_room: movie theater/indoor, elevator shaft, home theater
bathroom: jacuzzi/indoor, shower
mezzanine: staircase
kitchen: galley, wet bar
roof: wind farm
store: candy store, hardware store, shopping mall/indoor, bazaar/indoor, bazaar/outdoor, assembly line, market/indoor, auto factory, general store/indoor, department store, supermarket, kasbah, gift shop
yard: junkyard, roof garder, beer garder, zen garden, topiary garden, courtyard, campsite, greenhouse, patio
music: stage, music studio, stage/outdoor
dorm_room: dorm room
bedroom: dorm room, motel
museum: science museum, recreation room, museum/outdoor, art gallery
clothing_store: clothing store, fabric store
closet: clothing store, dressing room, fabric store
street: bazaar/indoor, bazaar/outdoor, downtown, street, promenade, medina, arcade, alley
dining_room: bedchamber, dining table, dining room
road: forest road, desert road, trench, highway
jewelry: jewelry shop
auto_showroom: auto showroom
sauna
promenade: medina, arch, alley, corridor
arcade: promenade, medina, arch, alley, corridor
none: repair shop, martial arts gym, pagoda, physics laboratory, chemistry lab, biology laboratory, hospital room, kennel, stable
sushi bar: restaurant
shed: chalet, oast house, loading dock
living_room: living room
office: server room, computer room
landing_deck: airport, airplane cabin, runway
door: jail cell, bank vault, locker room, doorway/outdoor, barndoor, shopfront
window: jail cell, bow window/indoor
ice_cream_parlor: ice cream parlor
clothes: dressing room
rail: railroad track
none: rock arch, arena/performance, laundromat, badlands, natural history museum, golf course, swimming pool/indoor, lock chamber
station: bus station/indoor, airport terminal, train station/platform, subway station/platform
crowd: orchestra pit
parking_lot: parking lot, parking garage/outdoor, parking garage/indoor
conference_room: conference room, legislative chamber, conference center
escalator: escalator/indoor
outdoor
cockpit: airplane cabin, amusement arcade
none: art studio, volcano, fire station, oilrig, train interior, sky, art gallery, auditorium, iceberg, chalet, mausoleum, atrium/public
crosswalk
lecture_room: lecture room, classroom
field: hayfield
bridge
bookstore: library, archive, library/indoor
dark: movie theater/indoor, catacomb
drugstore: pharmacy
booth: phone booth, ticket booth, booth/indoor
residential_neighborhood: residential neighborhood
harbor: wind farm, windmill, boat deck
house: beach house, oast house, loading dock
basement: storage room
none: underwater/ocean deep, aquarium, pet shop, artists loft, operating room, veterinarians office, porch, bus interior, desert/sand, igloo
none: discotheque, carrousel, home office, lighthouse, bowling alley, landfill, flea market/indoor, music studio, amusement park, beauty salon, car interior
playground: sandbox
store: shoe shop, hardware store
hallway: corridor
gas_station: gas station
plaza
park
clean_room: clean room
reception
pantry: refrigerator"""
categories_3 = {}
for line in group3_text.split("\n"):
    if ':' not in line:
        categories_3[line] = {line}
    else:
        category, words = line.split(': ')
        words = words.split(', ')
        categories_3[category] = set(words + [category])

# QUERY
query_categories_text="""person: person, women, woman, man, people, boy, girl, wife, sister, husband, friend, mom, dad, family, colleague
bicycle: bicycle, motorcycle, bike, motorbike
car: car, auto, automobile
bus: bus, train, truck, public transport, metro, tram
airplane: plane, airport
boat: port, harbour, harbor, ship, sea, ocean, bay, fishing
traffic light: intersection
stop sign: intersection, sign
bench: sit
outdoor: fire hydrant, parking meter
dog: dog, horse, pet, puppy
animal: cow, sheep, giraffe, zebra, bear, bird, cat, elephant
backpack: backpack, handbag, bag, knapsack, luggage
tie: curtain, window
suitcase: briefcase, luggage
pen: baseball bat, pencil
sport: frisbee, skis, snowboard, sports ball, kite, baseball glove, skateboard, surfboard, tennis racket, football, soccer
bottle: jug, jar, can, glass, drink
wine glass: glass
cup: jug, mug, pint, bowl
fork: spoon
bowl: bowl
apple
orange
sandwich: sandwich, burger, hamburger, bread
hot dog: sausage, hotdog, meat, barbecue
hamburger: donut, burger, cheeseburger, sandwich
cake: birthday, chocolate, brownie, pie
food: banana, sandwich, orange, broccoli, carrot, pizza, meal, seafood, eat, snack, meat, milk, cheese
chair: bench
couch: sofa
potted plant, futon
bed: pillow, sleep, mattress
dining table: table, desk
furniture: toilet
tv: television, screen
laptop: computer, ipad, tablet, notebook, macbook, mac
mouse
remote: remote control
keyboard
cell phone: phone, iphone, smartphone
microwave: microwave, toaster, oven, cooker, stove
oven: microwave, toaster, oven, cooker, stove
refrigerator: fridge, freezer
sink: bathroom, shower, dishes
book: read, notebook, bookcase, bookshelf, bookstore
clock: watch
vase: flower
toothbrush: toothpaste, brush, teeth
indoor: scissors, teddy bear, hair drier
"""
query_categories = {}
for line in query_categories_text.split("\n"):
    if ':' not in line:
        query_categories[line] = {line}
    else:
        category, words = line.split(': ')
        words = words.split(', ')
        query_categories[category] = set(words + [category])

query_categories_text_2 = """elevator: elevator lobby, bank vault, locker room
cafeteria: fastfood restaurant, restaurant kitchen, dining hall, food court, restaurant, butchers shop, restaurant patio, coffee shop, pizzeria, pub/indoor, bar, diner/outdoor, beer hall, bakery/shop, delicatessen
office cubicles: office, work
television room: television studio, living room, tv room, living room
entrance hall: elevator lobby, entrance, gateway
balcony: balcony, fence
lobby: ballroom
driveway
church: synagogue, church, praying
room: nursery, childs room, utility room, waiting room
archive
tree: tree house, tree farm, forest road, greenhouse, plant, green
ceiling: berth, elevator shaft, alcove, attic, skylight, roof, wall
wall: berth, dam, elevator shaft
campus: industrial area, school, university, college
gymnasium/indoor: gym, sport
catatomb: grotto, grave
fountain: gazebo, monument
garden: roof garden, beer garden, zen garden, topiary garden, junkyard, yard, courtyard, campsite, greenhouse, patio, shrub
hotel_room: youth hostel, dorm room, motel, bedroom, hotel/outdoor, hotel, accommodation, resting, sleep
sea: ocean, wind farm, harbor, cliff, coast, boat deck, beach, wave, water
garage: garage/outdoor, parking garage/indoor, parking garage/outdoor, garage, car garage, parking garage
indoor
airport_terminal: airport terminal
aqueduct: canal
stairs: amphitheater, mezzanine, staircase, stair
skyscraper: water tower, construction site, tall building, high building, tower
none: wheat field, boxing ring, embassy, manufactured home, hospital, ice skating rink, hangar, waterfall, crevasse, burial chamber, lock chamber, fire escape
dark_room: movie theater/indoor, elevator shaft, home theater, dark room
bathroom: jacuzzi/indoor, shower, bath
mezzanine: staircase, stairs, stair
kitchen: galley, wet bar
roof: wind farm
store: candy store, hardware store, shopping mall/indoor, bazaar, assembly line, market/indoor, auto factory, general store/indoor, department store, supermarket, kasbah, gift shop
yard: junkyard, roof garder, beer garder, zen garden, topiary garden, courtyard, campsite, greenhouse, patio
music: stage, music studio, stage/outdoor, guitar, piano, artist, singer
dorm_room: dorm room
bedroom: dorm room, motel
museum: science museum, recreation room, museum/outdoor, art gallery
clothing_store: clothing store, fabric store, clothes
closet: clothing store, dressing room, fabric store, clothes, dressing, fabric
street: bazaar/indoor, bazaar, downtown, street, promenade, medina, arcade, alley, walk, walking
dining_room: bedchamber, dining table, dining room, dine, eating
road: forest road, desert road, trench, highway
jewelry: jewelry shop
auto_showroom: auto showroom, car showroom, cars
sauna
promenade: medina, arch, alley, corridor
arcade: promenade, medina, arch, alley, corridor
sushi bar: restaurant, sushi, bar
shed: chalet, oast house, loading dock, old house, small house, garden house
living_room: living room
office: server room, computer room
landing_deck: airport, airplane cabin, runway
door: jail cell, bank vault, locker room, doorway, barndoor, shopfront, entrance
window: jail cell, bow window/indoor
ice_cream_parlor: ice cream parlor, ice cream
clothes: dressing room
rail: railroad track
station: bus station, airport terminal, train station, platform, subway station
crowd: orchestra pit, crowds, many people
parking_lot: parking lot, parking garage, parking
conference_room: conference room, legislative chamber, conference center, conference
escalator: escalator
outdoor
cockpit: airplane cabin, amusement arcade, airplane, cabin
crosswalk: walk, cross the street, street crossing
lecture_room: lecture room, classroom, lecture, presentation
field: hayfield
bridge
bookstore: library, archive
dark: movie theater, catacomb
drugstore: pharmacy, drugs
booth: phone booth, ticket booth
residential_neighborhood: residential neighborhood, neighborhood
harbor: wind farm, windmill, boat deck, ship, boat, port
house: beach house, oast house, loading dock
basement: storage room
playground: sandbox
store: shoe shop, hardware store
hallway: corridor
gas_station: gas station, gas
plaza
park
clean_room: clean room
reception
pantry: refrigerator, fridge"""
for line in query_categories_text_2.split("\n"):
    if ':' not in line:
        query_categories[line] = {line}
    else:
        category, words = line.split(': ')
        words = words.split(', ')
        query_categories[category] = set(words + [category])


all_terms = set()
for category in categories_1:
    all_terms = all_terms.union(categories_1[category])
for category in categories_2:
    all_terms = all_terms.union(categories_2[category])
for category in query_categories:
    all_terms = all_terms.union(query_categories[category])

def process_description(text):
    description1 = set()
    description2 = set()

    for word in text.split(", "):
        word = word.split(' ', 1)[-1]
        for category in categories_1:
            if word in categories_1[category]:
                description1.add(category)

        for category in categories_2:
            if word in categories_2[category]:
                description2.add(category)

        for category in categories_3:
            if word in categories_3[category]:
                description1.add(category)
                description2.add(category)

    return list(description1), list(description2)

def process_query(text):
    description2 = set()

    string_bigrams = [" ".join(bg) for bg in bigrams(text.replace(",", "").split())]
    for word in text.split() + string_bigrams:
        for query_category in query_categories:
            if word in query_categories[query_category]:
                description2.add(query_category)

    description1 = set()
    for word in description2:
        if word in query_categories_text_2:
            description1.add(word)
        else:
            for category in categories_1:
                if word in categories_1[category]:
                    description1.add(category)

    return list(description1), list(description2)


print(process_description("1 person, 1 cup, 2 bowl, 1 potted plant, 1 dining table, indoor, bow window/indoor"))
print()
print(process_query("a shed at home"))
print(process_query("buying medicine"))
print(process_query("walking my dog at Howth"))
print(process_query("grilling hamburger in the yard"))
print(process_query("apple bowl and orange in the kitchen"))
print(process_query("red sign at the helix"))
#shopping at Donaghmede Shopping Centre