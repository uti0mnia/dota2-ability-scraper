import urllib2
from bs4 import BeautifulSoup as BS
import re
from selenium import webdriver

special_sentences = {'Does not pierce spell immunity.': 'NO_PIERCE_SPELL_IMMUNE',
                     'Partially pierces spell immunity.': 'PARTIAL_PIERCE_SPELL_IMMUNE',
                     'Pierces spell immunity.': 'PIERCE_SPELL_IMMUNE',
                     'Upgradable by Aghanim\'s Scepter.': 'AGHANIM_UPGRADE',
                     'Disabled by Break.': 'DISABLED_BY_BREAK',
                     'Not disabled by Break.': 'NOT_DISABLED_BY_BREAK',
                     'Not a Unique Attack Modifier.': 'NOT_UNIQUE_ATTACK_MODIFIER',
                     'Cannot be used by illusions.': 'ILLUSIONS_CANNOT_USE',
                     'Can be used by illusions.': 'ILLUSIONS_CAN_USE',
                     'Not blocked by Linken\'s Sphere.': 'NOT_BLOCKED_BY_LINKEN',
                     'Partially blocked by Linken\'s Sphere.': 'PARTIAL_BLOCKED_BY_LINKEN',
                     'Blocked by Linken\'s Sphere.': 'BLOCKED_BY_LINKEN'}

# we need to create the BeautifulSoup object
# url = 'http://dota2.gamepedia.com/Earthshaker'
# driver = webdriver.Firefox()
# driver.get(url)
# soup = BS(driver.page_source, 'html.parser')
file = open('all.html', 'r')
soup = BS(file.read(), 'html.parser')
file.close()

for div in soup.findAll('div', style='display: flex; flex-wrap: wrap; align-items: flex-start;'):
    print '----------------------------'
    children = div.find('div', style=re.compile(r'font-weight: bold; font-size: 110%; border-bottom: 1px solid black;.*')).contents
    # get name
    name = children[0]

    # get the special information
    ability_special = [special_sentences[a['title'].encode('utf-8')] for a in children[1].findAll('a', recursive=False)]

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
                a_tag.append(special_sentences[a_tag['title']]) # we want to append the data so when we can add it when getting the div's text

            # we finally have a data object to push
            data.append(data_item.text.replace(u'\xa0', u' ').encode('utf-8').strip())

    modifiers = []
    # finding the modifiers
    for d in div_data.findAll('div', style='font-size: 85%; margin-left: 10px;'):
        modifiers += [item.strip().replace(u'\xa0', u' ').encode('utf-8') for item in d.text.strip().split('\n')]

    for d in data:
        print d


# driver.close()