import urllib2
from bs4 import BeautifulSoup as BS
import re

# we need to create the BeautifulSoup object
url = 'http://dota2.gamepedia.com/Earthshaker'
request = urllib2.Request(url, headers={'User-Agent': 'Magic Browser'})
connection = urllib2.urlopen(request)
html = connection.read()
soup = BS(html, 'html.parser')

for div in soup.findAll('div', style='display: flex; flex-wrap: wrap; align-items: flex-start;'):
    print '----------------------------'
    children = div.find('div', style=re.compile(r'font-weight: bold; font-size: 110%; border-bottom: 1px solid black;.*')).contents
    name = children[0]
    ability_special = [a['title'] for a in children[1].findAll('a', recursive=False)]
    print div.find('div', style='vertical-align:top; padding: 3px 5px;')