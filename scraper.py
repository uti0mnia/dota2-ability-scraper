from bs4 import BeautifulSoup as BS
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# constants
SPECIAL_SENTENCES = {
    'Does not pierce spell immunity.': 'NO_PIERCE_SPELL_IMMUNE',
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
        name = children[0]

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
        notes = findNotes(note_div.findAll('ul', recursive=False), [])

        abilities[name] = {
            'abilitySpecial': ability_special,
            'data': data,
            'modifiers': modifiers,
            'notes': notes
        }

    return abilities


# we need to create the BeautifulSoup object
base_url = 'http://dota2.gamepedia.com/'  # create the base url
main_page = 'Dota_2_Wiki'  # the page that will get all the hero names

firefox_profile = webdriver.FirefoxProfile('/Users/casey/Library/Application Support/Firefox/Profiles/5as9qp3r.testing')
driver = webdriver.Firefox(firefox_profile)  # create the webdriver
driver.get(base_url + main_page)  # load the page
soup_html = BS(driver.page_source, 'html.parser')  # parse the page

hero_abilities = {} # what we want to write to csv

# we need to get the abilities for each hero
for hero_div in soup_html.findAll('div', class_='heroentry'):
    hero_link = hero_div.find('a').get('href').replace('/', '')  # gets the hero name
    driver.get(base_url + hero_link)  # load the hero page
    hero_soup = BS(driver.page_source, 'html.parser')  # soupify the page to parse
    hero_abilities[hero_link.replace('_', ' ').title()] = fetch_abilities(hero_soup)  # parse and save the data scraped
    break  # for testing

driver.close()  # we're done so close the driver

# we want to write the hero abilities to a csv