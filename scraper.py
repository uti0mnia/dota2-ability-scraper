from bs4 import BeautifulSoup as BS
import re
import os
import pprint

# constants
SPECIAL_SENTENCES = {
    'Unique Attack Modifier.': 'UNIQUE_ATTACK_MODIFIER',
    'Does not pierce spell immunity.': 'NO_PIERCE_SPELL_IMMUNE',
    'Partially pierces spell immunity.': 'PARTIAL_PIERCE_SPELL_IMMUNE',
    'Pierces spell immunity.': 'PIERCE_SPELL_IMMUNE',
    'Upgradable by Aghanim\'s Scepter.': 'AGHANIM_UPGRADE',
    'Disabled by Break.': 'DISABLED_BY_BREAK',
    'Partially disabled by Break.': 'PARTIAL_DISABLE',
    'Not disabled by Break.': 'NOT_DISABLED_BY_BREAK',
    'Not a Unique Attack Modifier.': 'NOT_UNIQUE_ATTACK_MODIFIER',
    'Cannot be used by illusions.': 'ILLUSIONS_CANNOT_USE',
    'Partially usable by illusions.': 'ILLUSIONS_PARTIAL_USE',
    'Can be used by illusions.': 'ILLUSIONS_CAN_USE',
    'Not blocked by Linken\'s Sphere.': 'NOT_BLOCKED_BY_LINKEN',
    'Partially blocked by Linken\'s Sphere.': 'PARTIAL_BLOCKED_BY_LINKEN',
    'Blocked by Linken\'s Sphere.': 'BLOCKED_BY_LINKEN'
}

# divs is an array of <ul> tags
# notes is the array used recursively, also the return value
def findNotes(divs, notes):
    # base case, we are done
    if len(divs) == 0:
        return notes

    # if there are any <ul>'s in the tag, recurse on them first
    elif len(divs[0].find('li').findAll('ul')) != 0: # if there are subpoints (i.e <ul> in the <li>)
        li = divs[0].find('li') # get the <li>
        ul_divs = li.findAll('ul') # get the sub points
        ul_notes = findNotes(ul_divs, []) # get the points for those sub points
        [d.extract() for d in ul_divs] # remove them from the tag since we're done
        text = li.text.encode('utf-8').strip() # get the text from the <li> (without children now)
        notes.append(text)
        notes.append(ul_notes)
        return findNotes(divs[1:], notes)

    # no subpoints, get the text and return in the notes
    else:
        [notes.append(div.text.encode('utf-8').strip()) for div in divs[0].findAll('li')]  # append all <li> text to the notes
        return findNotes(divs[1:], notes) # recurse with the rest


def fetch_abilities(soup):
    abilities = {}
    for div in soup.findAll('div', style='display: flex; flex-wrap: wrap; align-items: flex-start;'):
        children = div.find('div', style=re.compile(r'font-weight: bold; font-size: 110%; border-bottom: 1px solid black;.*')).contents
        # get name
        name = children[0].encode('utf-8')

        # get the special information
        ability_special = [SPECIAL_SENTENCES[a['title'].encode('utf-8')] for a in children[1].findAll('a', recursive=False)]

        # get the data about the ability
        div_data = div.find('div', style='vertical-align:top; padding: 3px 5px;')
        data = []

        # find all the divs
        for data_item in div_data.findAll('div'):
            # we want to break once we hit the modifiers
            if data_item.find('b') is not None and data_item.find('b').text == 'Modifiers':
                break
            if data_item.text.strip() != '': # make sure it's not empty (some are)
                if data_item.has_attr('style'):
                    if re.search(r'display: inline-block.*', data_item['style']): # we're checking if it has a style (i.e mana/cooldown) and we want to ignore it
                        continue
                a_tag = data_item.find('a') # this is for the special ablities (i.e aghs upgrade, linken partial, etc...)
                if a_tag is not None:
                    a_tag.append(SPECIAL_SENTENCES[a_tag['title']]) # we want to append the data so when we can add it when getting the div's text

                # we finally have a data object to push
                data.append(data_item.text.replace(u'\xa0', u' ').encode('utf-8').strip())

        modifiers = []
        # finding the modifiers
        for d in div_data.findAll('div', style='font-size: 85%; margin-left: 10px;'):
            modifiers += [item.strip().replace(u'\xa0', u' ').encode('utf-8') for item in d.text.strip().split('\n')]

        # finding notes
        note_div = div.find('div', style='flex: 2 3 400px; word-wrap: break-word;')
        if note_div is not None:
            notes = findNotes(note_div.findAll('ul', recursive=False), [])
        else:
            notes = []

        abilities[name] = {
            'abilitySpecial': ability_special,
            'data': data,
            'modifiers': modifiers,
            'notes': notes
        }

    return abilities

hero_abilities = {} # what we want to write to csv

# we need to get the abilities for each hero
for file in os.listdir('./hero_htmls/'):
    with open('./hero_htmls/' + file, 'r') as html:
        name = os.path.splitext(file)[0]
        hero_soup = BS(html.read(), 'html.parser')  # soupify the page to parse
        hero_abilities[name] = fetch_abilities(hero_soup)  # parse and save the data scraped
    break


# we want to write a new CSV
with open('abilities.csv', 'w') as file:
    for key in hero_abilities:
        

# # we want to write the hero abilities to a csv
# with open('ability_ex.txt', 'w') as file:
#     pp = pprint.PrettyPrinter(indent=4)
#     file.write(pp.pformat(hero_abilities))