# !/usr/bin/env python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup as BS, NavigableString
import re
import os
import codecs
import urllib
import json
from pprint import pprint, pformat

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
    'Blocked by Linken\'s Sphere.': 'BLOCKED_BY_LINKEN',
    'Available at Secret Shop': 'SECRET_SHOP',
    'Available at Side Lane Shop': 'SIDE_SHOP',
    'Talent': 'TALENT'
}
HERO_HTMLS = './htmls/heroes/'
ITEM_HTMLS = './htmls/items/'

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
        text = li.text.encode('utf-8')
        notes.append(clean(text))
        notes.append(ul_notes)
        return find_notes(divs[1:], notes)

    # no subpoints, get the text and return in the notes
    else:
        texts = []
        for div in divs[0].findAll('li'):
            text = div.text.encode('utf-8')
            texts.append(clean(text))
        notes += texts
        return find_notes(divs[1:], notes) # recurse with the rest

def clean(str):
    str = str.strip()
    str = re.sub('\n+', '', str)
    str = re.sub(' +', ' ', str)
    return str

def fetch_abilities(soup, extra=True):
    abilities = []
    # iterate through all ability divs
    for ability_div in soup.findAll('div', style='display: flex; flex-wrap: wrap; align-items: flex-start;')[0:-1]:
        ability = {}
        children = ability_div.find('div', style=re.compile(r'font-weight: bold; font-size: 110%; border-bottom: 1px solid black;.*')).contents
        # get name
        name = children[0].encode('utf-8').strip()

        # get the special information
        ability_special = [SPECIAL_SENTENCES[a['title'].encode('utf-8')] for a in
                           children[1].findAll('a', recursive=False)]

        # get if aghs upgrade too since it's not shown in the title
        if len([x.get('alt') for x in ability_div.findAll('img') if x.get('alt') == 'Upgradable by Aghanim\'s Scepter.']) != 0:
            ability_special.append('AGHANIM_UPGRADE')


        # get "type" (i.e no target/passive/etc) and summary
        type_div = ability_div.find('div', style='padding: 15px 5px; font-size: 85%; line-height: 100%; text-align: center;')
        types = {}
        for type in type_div.findAll('div', recursive=False):
            if type.find('b') is None:
                continue

            # get the type val we're dealing with (ability, affects, damage, etc)
            b = type.find('b')
            val = b.text.encode('utf-8').strip()
            b.extract()

            # iterate through each block that's split by a br (this doesn't makes sense lol)
            extra = ''  # used to save if talent tree or aghs type
            strings = {}
            soups = [BS(x.strip(), 'html.parser') for x in unicode(''.join([unicode(child) for child in list(type.children)])).split('<br/>') if x.strip() != '']
            for s in soups:
                extra = ' '.join([SPECIAL_SENTENCES[a.get('title').encode('utf-8')] for a in s.findAll('a') if a.get('title').encode('utf-8') in SPECIAL_SENTENCES])  # if it works don't fix
                string = ' '.join([re.sub(r'\(|\)', '', x.encode('utf-8')) for x in s.findAll(text=True) if x.strip() != ''])
                string = clean(string)
                if extra is not '':
                    strings[extra] = [string]
                else:
                    if 'normal' in strings.keys():
                        strings['normal'] = strings['normal'].append(string.strip())
                    else:
                        strings['normal'] = [string.strip()]

            # save
            types[val] = strings

        # get description
        description = ability_div.find('div', style='vertical-align: top; padding: 3px 5px; border-top: 1px solid black;').text.encode('utf-8')
        description = clean(description)

        # find all the divs for data
        div_data = ability_div.find('div', style='vertical-align:top; padding: 3px 5px;')
        data = {}
        for data_item in div_data.findAll('div'):
            # we want to break once we hit a div with a style
            if data_item.has_attr('style'):
                break
            lines = [x.strip() for x in data_item.text.encode('utf-8').split(':')]  # [Radius, 0 (  Upgradable by Aghanim's Scepter. 900 )] or some shit
            data[lines[0]] = {}
            extras = [x for x in data_item.findAll('a')]  # AGHS and/or TALENT
            for extra in extras:
                data[lines[0]][extra.get('title')] = re.sub(' +', ' ', lines[1].split('(')[extras.index(extra) + 1].strip().replace(')', '')).replace('\n', '')
            data[lines[0]]['normal'] = lines[0]

        # get special details (i.e extra notes about the special)
        special_details = {}
        for special_div in div_data.findAll('div', style='margin-left: 50px;'):
            # this is for the special ablities (i.e aghs upgrade, linken partial, etc...)
            a_tag = special_div.find('a')
            if a_tag is not None:
                special = SPECIAL_SENTENCES[a_tag['title']]
            else:
                print 'No a-tag for ' + name

            text = special_div.text.encode('utf-8').strip()
            text = re.sub(' +', ' ', text)
            special_details[special] = text.replace('\n \n', '\n')


        modifiers = {}
        # finding the modifiers
        for d in div_data.findAll('div', style='font-size: 85%; margin-left: 10px;'):
            for item in d.text.strip().split('\n'):
                modifiers[item.strip().replace(u'\xa0', u' ').encode('utf-8')] = 'red' if d.find('span').get('style') == u'color:#631F1F;' else 'green'

        # finding notes
        note_div = ability_div.find('div', style='flex: 2 3 400px; word-wrap: break-word;')
        if note_div is not None:
            notes = find_notes(note_div.findAll('ul', recursive=False), [])
        else:
            notes = []

        ability[name] = {
            'ability_special': ability_special,
            'special_details': special_details,
            'types': types,
            'description': description,
            'data': data,
            'modifiers': modifiers,
            'notes': notes,
            'Cooldown': '',
            'Mana': '',
        }

        # are we getting cooldown and mana cost?
        if extra:
            # check if there's a cooldown "div"
            cooldown_atag = ability_div.find('a', title='Cooldown')
            if cooldown_atag is not None:
                cooldown = {}
                cooldown_div = cooldown_atag.parent.parent
                extra_a_tag = cooldown_div.find('a', recursive = False)

                # check if there is a TALENT or AGHS upgrade that changes the value
                if extra_a_tag is not None:
                    extra_cooldown = cooldown_div.text.split('(')[-1].replace(')', '')
                    cooldown[extra] = clean(extra_cooldown)

                # set the normal value of the cooldown
                normal_cooldown = cooldown_div.text.split('(')[0].replace(')', '')
                cooldown['normal'] = clean(normal_cooldown)
                ability[name]['Cooldown'] = cooldown

            # check if there's a mana div
            mana_atag = ability_div.find('a', title='Mana')
            if mana_atag is not None:
                mana = {}
                mana_div = mana_atag.parent.parent
                extra_a_tag = mana_div.find('a', recursive=False)

                # check if there is a TALENT or AGHS upgrade that changes the value
                if extra_a_tag is not None:
                    extra_mana = mana_div.text.split('(')[-1].replace(')', '')
                    mana[extra] = clean(extra_mana)

                # set the normal value of the mana
                normal_mana = mana_div.text.split('(')[0].replace(')', '')
                mana['normal'] = clean(normal_mana)
                ability[name]['Mana'] = mana

        # add to array
        abilities.append(ability)

    return abilities

# FOR DATA
def hero_data(soup, extra=True):
    # return object
    hero = {}

    # get description
    p = soup.find('div', id='mw-content-text').find('p')
    description = re.sub(' +', ' ', p.text.encode('utf-8')).replace('\n', '').strip()
    hero['description'] = description

    # get info
    tablebody = soup.find('table', class_='infobox')#.find('tbody')
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
    base_stats['attack_s'] = get_stat(stats_table[8], 1)

    hero['base_stats'] = base_stats


    # get misc stats
    misc_stats_table = trs[4].findAll('tr')
    misc_stats = {}
    for tr in misc_stats_table:
        misc_stat = get_stat(tr, 0).encode('utf-8').strip()
        misc_stat_value = get_stat(tr, 1).encode('utf-8').strip()
        misc_stats[misc_stat] = re.sub(' +', ' ', misc_stat_value).replace('\n', '')

    hero['misc_stats'] = misc_stats

    # get bio
    bio_trs = soup.find('div', class_='biobox').findAll('table')[1].findAll('tr', recursive=False)
    roles = []
    for a in bio_trs[2].findAll('td')[1].findAll('a'):
        if a.get('title') == 'Role':
            continue
        roles.append(a.get('title'))
    hero['roles'] = roles
    lore = bio_trs[3].findAll('td')[1].text.encode('utf-8').strip()
    lore = re.sub(' +', ' ', lore)
    lore = re.sub('\n+', '\n', lore)
    hero['lore'] = lore.replace('\n \n', '\n')

    #get abilities
    abilities = fetch_abilities(soup, extra)
    hero['abilities'] = abilities

    # get talents
    talents = {}
    talent_div = soup.find('span', id='Talents').parent.findNext('div')
    talent_table = talent_div.find('table')
    trs = talent_table.findAll('tr', recursive = False)[1:]
    for tr in trs:
        tds = tr.findAll('td', recursive = False)
        left = clean(tds[0].text)
        level = clean(tds[1].text)
        right = clean(tds[2].text)
        talents[level] = {
            'left': left,
            'right': right
        }
    note_div = talent_div.findAll('div', recursive = False)[1]
    if note_div is not None:
        notes = find_notes(note_div.findAll('ul', recursive=False), [])
    else:
        notes = []
    talents['notes'] = notes
    hero['talents'] = talents

    return hero

def fetch_items(soup):
    # return dictionary
    item_data = {}

    # get the main div with the data
    div = soup.find('div', id='mw-content-text')  # get the div that contains the ul

    # get the ability data
    item_data['abilities'] = fetch_abilities(soup, True)

    # find the first ul that contains the additional information
    ul = div.find('ul', recursive=False)  # get the ul
    additional_info = []

    if ul is not None:
        for li in ul.findAll('li'):  # get each li in the ul
            if li.find('li') is not None:
                print 'Double li'
            additional_info.append(re.sub(' +', ' ', li.text.encode('utf-8').strip()).replace('\xe2\x80\x8b', '')) #  removes double whitespaces and other utf-8 bad chars

    item_data['additional_info'] = additional_info

    # find the table with the item info and get its <tr> tags
    trs = soup.find('table', class_='infobox').find('tbody').findAll('tr', recursive=False)
    item_data['availability'] = []
    for span in trs[0].findAll('span'):
        item_data['availability'].append(SPECIAL_SENTENCES[span.get('title')])
    item_data['lore'] = trs[3].text.encode('utf-8').strip()
    item_data['cost'] = re.sub(r'[a-z]|[A-Z]', '', trs[4].find('th').find('div').text)  # removes text (keeps cost + recipe)
    item_data['type'] = re.sub(r'Bought From', '', trs[4].find('th').findAll('div', recursive=False)[-1].text)

    # get the details
    detail_trs = trs[-1].find('tbody').findAll('tr')
    details = {}
    for tr in detail_trs:
        # make sure it's not empty
        if tr.find('td') is None or tr.find('td').text.strip() == '':
            continue
        detail = tr.find('td').text.encode('utf-8').strip()

        # if it's a recipe, we do something different
        if detail == 'Recipe':
            recipe_td = detail_trs[-1].find('td')  # the recipe is always the last tag

            # get what the item build into
            builds_into_div = recipe_td.find('div')
            builds_into = []
            for a in builds_into_div.findAll('a'):
                builds_into.append(re.sub(r'\(|\)|[0-9]', '', a.get('title')).encode('utf-8').strip())

            # get the items that build it
            builds_from_div = recipe_td.findAll('div', recursive=False)[-1]
            builds_from = []
            for a in builds_from_div.findAll('a'):
                builds_from.append(re.sub('\(|\)|[0-9]', '', a.get('title')).encode('utf-8').strip())

            details['builds_from'] = builds_from
            details['builds_into'] = builds_into
            break

        # we want to clear the br (make them into ',')
        for br in tr.findAll('td')[1].findAll('br'):
            br.name = 'p'
            br.insert(0, NavigableString(','))

        details[detail] = [x.strip() for x in tr.findAll('td')[1].text.encode('utf-8').split(',') if x.strip() != '']

    item_data['details'] = details

    return item_data

## IMAGES
def fetch_item_image(soup, name):
    table = soup.find('table', class_='infobox')
    tr = table.find('tbody').findAll('tr', recursive=False)[1]
    img = tr.find('img')
    urllib.urlretrieve(img.get('src'), './images/' + name + '.' + img.get('alt').split('.')[-1])

def fetch_hero_images(soup, hero_name):
    fetch_image(soup)
    fetch_ability_images(soup, hero_name)

def fetch_image(soup):
    table = soup.find('table', class_='infobox')
    img = table.find('img')
    name = table.find('tr').text.encode('utf-8').strip()
    urllib.urlretrieve(img.get('src'), './images/' + name + '.' + img.get('alt').split('.')[-1])

def fetch_ability_images(soup, owner):
    # get each ability
    for div in soup.findAll('div', style='display: flex; flex-wrap: wrap; align-items: flex-start;'):
        children = div.find('div', style=re.compile(r'font-weight: bold; font-size: 110%; border-bottom: 1px solid black;.*')).contents
        # get name
        name = children[0].encode('utf-8')
        div_img = div.find('div', class_=re.compile(r'ico_.*'))
        img = div_img.find('img')
        urllib.urlretrieve(img.get('src'), './images/' + name + '_' + owner + '.' + img.get('alt').split('.')[-1])

def replace_unicode(string):
    REPLACE_STRINGS = {
        '\u02da': '˚',
        '\u00b1': '±',
        '\u2019': '\'',
        '\u200b': '',
        '\u00a0': '',
        '\u2014': '-',
        '\u2026': '...',
        '\u201c': '\"',
        '\u201d': '\"',
        '\u00d7': 'x',
        '\u00b0': '˚',
        '\u2013': '-',
    }
    pattern = re.compile('|'.join(re.escape(key) for key in REPLACE_STRINGS.keys()))
    return pattern.sub(lambda x: REPLACE_STRINGS[x.group()], string)

## DATA
def fetch_images():
    i = 0
    num_files = len(os.listdir(HERO_HTMLS)) + len(os.listdir(ITEM_HTMLS))
    for file in os.listdir(HERO_HTMLS):
        i += 1
        print str(i) + '/' + str(num_files)
        with open(HERO_HTMLS + file, 'r') as html:
            name = os.path.splitext(file)[0]
            soup = BS(html.read(), 'html.parser')
            fetch_hero_images(soup, name)

    for file in os.listdir(ITEM_HTMLS):
        i += 1
        print str(i) + '/' + str(num_files)
        with open(ITEM_HTMLS + file, 'r') as html:
            name = os.path.splitext(file)[0]
            soup = BS(html.read(), 'html.parser')
            fetch_item_image(soup, name)


def get_heroes():
    # we need to get the abilities for each hero
    i = 0
    num_files = len(os.listdir(HERO_HTMLS))
    with open('heroes.json', 'w') as jsonfile:
        heroes = {}
        for file in os.listdir(HERO_HTMLS):
            i += 1
            print str(i) + '/' + str(num_files)
            with open(HERO_HTMLS + file, 'r') as html:
                name = os.path.splitext(file)[0]
                print name
                hero_soup = BS(html.read(), 'html.parser')  # soupify the page to parse
                heroes[name] = hero_data(hero_soup)

        json.dump(heroes, jsonfile, ensure_ascii=False)

def get_items():
    i = 0
    num_files = len(os.listdir(ITEM_HTMLS))
    items = {}
    with open('items.json', 'w') as jsonfile:
        for file in os.listdir(ITEM_HTMLS):
            i += 1
            print str(i) + '/' + str(num_files)  # logging
            with open(ITEM_HTMLS + file, 'r') as html:
                name = os.path.splitext(file)[0]
                print name
                soup = BS(html.read(), 'html.parser')
                items[name] = fetch_items(soup)

        json.dump(items, jsonfile, ensure_ascii=False)

def combine():
    # combine files into 1
    with open('heroes.json', 'r') as herofile:
        heroes = json.load(herofile)
        with open('items.json', 'r') as itemfile:
            items = json.load(itemfile)
            new_json = {
                'hero': heroes,
                'item': items,
            }
            with open('dota2.json', 'w') as dotafile:
                json.dump(new_json, dotafile)

## LOGGING
def pretty_print():
    # pretty print it for readability
    with open('heroes_fixed.json', 'r') as file:
        data = json.load(file)
        with open('heroes_pretty.json', 'w') as prettyfile:
            prettyfile.write(pformat(data, indent=2))

    with open('items_fixed.json', 'r') as file:
        data = json.load(file)
        with open('items_pretty.json', 'w') as prettyfile:
            prettyfile.write(pformat(data, indent=2))

get_heroes()
get_items()
# combine()