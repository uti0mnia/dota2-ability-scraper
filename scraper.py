from bs4 import BeautifulSoup as BS
import re
import os
import pprint

class MyCSVString:
    def __init__(self, item='', delimiter=',', quote='"'):
        self.delimiter = delimiter
        self.quote = quote
        self.string = ''
        if item != '':
            self.string = quote + str(item).replace('\n', '\\n') + quote

    def write(self, item):
        if self.string == '':
            self.string += self.quote + str(item).replace('\n', '\\n') + self.quote
        else:
            self.string += self.delimiter + self.quote + str(item).replace('\n', '\\n') + self.quote

    def end_line(self):
        self.string += '\n'

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




# this function is meant to count the length of an array recursively
def recursive_length(array = [], length = 0):
    # base case
    if len(array) == 0:
        return length

    # recursive call on list in list
    item = array.pop(0)
    if isinstance(item, list):
        new_length = recursive_length(item, length)
        return recursive_length(array, new_length)

    # recursive call on object in list
    return recursive_length(array, length + 1)


# this function is meant to write a csv style string of an array, including the length of each sub array
def write_array_to_csv(array = [], csvstr = MyCSVString(), length = 0):
    # base case
    if len(array) == 0:
        return csvstr, length

    item = array.pop(0) # get the item we will write

    # prepare for recursion on a list
    if isinstance(item, list):
        csvstr.write(len(item))  # write the number of items in this array for reading (this is a sub item)
        new_csvstr, new_length  = write_array_to_csv(item, csvstr, length)
        return write_array_to_csv(array, new_csvstr, new_length)

    # item is not a list
    length += 1
    csvstr.write(item)

    # preparefor recursion on an object
    return write_array_to_csv(array, csvstr, length)


# this function is meant to write a dictionary of objects or arrays to a csv type string and return it
def write_to_csv(ability_dict = {}, csvstr = MyCSVString()):
    # base case
    if not ability_dict:
        return csvstr

    key, value = ability_dict.popitem() # get what we want to be writing

    # if it's a list, recursive write the list data
    if isinstance(value, list):
        csvstr.write(key)
        my_csv, length = write_array_to_csv(value, MyCSVString())
        csvstr.write(length)  # write the number of items that we'll be writing
        csvstr.write(my_csv.string[1:-1])  # write the array to the csv string (remove the 1st and last quotation)
        return write_to_csv(ability_dict, csvstr)  # recurse on the rest of the dictionary

    # it's not a list (it's a dictionary)
    csvstr.write(key)  # we want to write the name/ability name
    csvstr.write(len(value))  # write the number of abilities (otr data objects) we're about to write
    new_csvstr = write_to_csv(value, csvstr)  # get the new csv str from the value (the dictionary)
    return write_to_csv(ability_dict, new_csvstr)  # recurse on the rest of the dicionary and the new csv string

# we need to get the abilities for each hero
i = 0
num_files = len(os.listdir('./hero_htmls/'))
with open('abilities.txt', 'w') as csv:
    for file in os.listdir('./hero_htmls/'):
        i += 1
        print str(i) + '/' + str(num_files)
        with open('./hero_htmls/' + file, 'r') as html:
            name = os.path.splitext(file)[0]
            print name
            hero_soup = BS(html.read(), 'html.parser')  # soupify the page to parse
            line = write_to_csv({ name:  fetch_abilities(hero_soup) }, MyCSVString()).string
            csv.write( line + '\n')