from bs4 import BeautifulSoup as BS
import re
import os
import json
from pprint import pprint

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
def find_notes(divs, notes):
    # base case, we are done
    if len(divs) == 0:
        return notes

    # if there are any <ul>'s in the tag, recurse on them first
    elif len(divs[0].find('li').findAll('ul')) != 0:  # if there are subpoints (i.e <ul> in the <li>)
        li = divs[0].find('li')  # get the <li>
        ul_divs = li.findAll('ul')  # get the sub points
        ul_notes = find_notes(ul_divs, [])  # get the points for those sub points
        [d.extract() for d in ul_divs]  # remove them from the tag since we're done
        text = li.text.encode('utf-8').strip().replace('\xe2\x80\x8b', '')  # get the text from the <li> (without children now)
        notes.append(text)
        notes.append(ul_notes)
        return find_notes(divs[1:], notes)

    # no subpoints, get the text and return in the notes
    else:
        [notes.append(div.text.encode('utf-8').strip().replace('\xe2\x80\x8b', '')) for div in divs[0].findAll('li')]  # append all <li> text to the notes
        return find_notes(divs[1:], notes) # recurse with the rest


def hero_data(soup, extra=True):
    # return object
    hero = {}

    # get description
    p = soup.find('div', id='mw-content-text').find('p')
    description = p.text.encode('utf-8')
    hero['description'] = description

    # get info
    tablebody = soup.find('table', class_='infobox').find('tbody')
    trs = tablebody.findAll('tr', recursive=False)

    # get attributes
    attributes_table = trs[2].findAll('th')
    attributes = {}
    for th in attributes_table:
        attributes[th.find('a').get('title')] = {
            'base': th.text.split('+')[0].encode('utf-8').strip(),
            'increment': th.text.split('+')[1].encode('utf-8').strip(),
            'primary': 1 if 'primary_attribute' in th.find('img').get('src') else 0
        }

    hero['attributes'] = attributes

    # get base stats
    get_stat = lambda tr, idx: tr.findAll('td')[idx].text.encode('utf-8').strip()
    stats_table = trs[3].findAll('tr')
    base_stats = {}
    base_stats['hp'] = get_stat(stats_table[1], 1)
    base_stats['hp_regen'] = get_stat(stats_table[2], 1)
    base_stats['mana'] = get_stat(stats_table[3], 1)
    base_stats['mana_regen'] = get_stat(stats_table[4], 1)
    base_stats['damage'] = {
        'min': get_stat(stats_table[5], 1).split('\xe2\x80\x92')[0],
        'max': get_stat(stats_table[5], 1).split('\xe2\x80\x92')[1],
    }
    base_stats['armor'] = get_stat(stats_table[6], 1)
    base_stats['spell_damage'] = get_stat(stats_table[7], 1)
    base_stats['attack/s'] = get_stat(stats_table[8], 1)

    hero['base_stats'] = base_stats


    # get misc stats
    misc_stats_table = trs[4].findAll('tr')
    misc_stats = {}
    for tr in misc_stats_table:
        misc_stats[get_stat(tr, 0).encode('utf-8').strip()] = get_stat(tr, 1).encode('utf-8').strip()

    hero['misc_stats'] = misc_stats

    # get bio
    bio_trs = soup.find('div', class_='biobox').findAll('tbody')[-1].findAll('tr', recursive=False)
    roles = []
    for a in bio_trs[2].findAll('td')[1].findAll('a'):
        if a.text is None or a.text == '':
            continue
        roles.append(a.text.encode('utf-8').strip())
    hero['roles'] = roles
    lore = bio_trs[3].findAll('td')[1].text.encode('utf-8').strip()
    hero['lore'] = lore


    #get abilities
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
            notes = find_notes(note_div.findAll('ul', recursive=False), [])
        else:
            notes = []

        abilities[name] = {
            'abilitySpecial': ability_special,
            'data': data,
            'modifiers': modifiers,
            'notes': notes,
            'Cooldown': '',
            'Mana': '',
        }

        # are we getting cooldown and mana cost?
        if extra:
            # check if there's a cooldown "div"
            if div.find('a', title='Cooldown') is not None:
                abilities[name]['Cooldown'] = div.find('a', title='Cooldown').parent.parent.text.encode('utf-8').strip()
            if div.find('a', title='Mana') is not None:
                abilities[name]['Mana'] = div.find('a', title='Mana').parent.parent.text.replace(u'\xa0', u' ').encode('utf-8').strip()

    hero['abilities'] = abilities
    pprint(hero, indent=2)
    return hero

def fetch_items(soup):
    # return dictionary
    item_data = {}

    # get the main div with the data
    div = soup.find('div', id='mw-content-text')  # get the div that contains the ul

    # get the ability data
    item_data = fetch_abilities(soup, True)

    # find the first ul that contains the additional information
    ul = div.find('ul', recursive=False)  # get the ul
    additional_info = []

    if ul is not None:
        for li in ul.findAll('li'):  # get each li in the ul
            if li.find('li') is not None:
                print 'Double li'
            additional_info.append(re.sub(' +', ' ', li.text.encode('utf-8').strip()).replace('\xe2\x80\x8b', '')) #  removes double whitespaces and other utf-8 bad chars

    item_data['additional_info'] = additional_info

    return item_data

# FOR HEROES
# we need to get the abilities for each hero
i = 0
num_files = len(os.listdir('./hero_htmls/'))
with open('heroes.json', 'w') as jsonfile:
    heroes = {}
    for file in os.listdir('./hero_htmls/'):
        if i == 1:
            break
        i += 1
        print str(i) + '/' + str(num_files)
        with open('./hero_htmls/' + file, 'r') as html:
            name = os.path.splitext(file)[0]
            print name
            hero_soup = BS(html.read(), 'html.parser')  # soupify the page to parse
            heroes[name] = hero_data(hero_soup)

    json.dump(heroes, jsonfile)


# FOR ITEMS
# i = 0
# num_files = len(os.listdir('./htmls/'))
# items = {}
# with open('items.json', 'w') as jsonfile:
#     for file in os.listdir('./htmls/'):
#         i += 1
#         print str(i) + '/' + str(num_files)  # logging
#         with open('./htmls/' + file, 'r') as html:
#             name = os.path.splitext(file)[0]
#             print name
#             soup = BS(html.read(), 'html.parser')
#             items[name] = fetch_items(soup)
#
#     json.dump(items, jsonfile)
