from flask import Flask, render_template, url_for, flash, redirect
from flaskblog.forms import RegistrationForm, LinkForm
import pandas as pd
import urllib3
from bs4 import BeautifulSoup
import json
import pylast
import requests
from bs4 import BeautifulSoup
import urllib.parse
import pylast
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']# '5791628bb0b13ce0c676dfde280ba245'

# PYLAST CONFIG --START--

#lastfm = open("lastfm.keys", "r")
#API_KEY = lastfm.readline()
#API_SECRET = lastfm.readline()
#username = lastfm.readline()
#password_hash = pylast.md5(lastfm.readline())
#network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
#username=username, password_hash=password_hash, session_key=None)
API_KEY = os.environ['API_KEY'] # "70d48262b0e787315b7cce695159b899"  # this is a sample key
API_SECRET = os.environ['API_SECRET']# "5150bc25a89cc30e9f7454e12a3afbac"

# In order to perform a write operation you need to authenticate yourself
username = os.environ['LASTFM_USERNAME']# "AlexSend57"
password_hash = pylast.md5(os.environ['LASTFM_PASSWORD'])

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                               username=username, password_hash=password_hash, session_key=None)
vars = [('"', '"'), ('«', '»'), ('“', '”')]

# PYLAST CONFIG --END-

# EXTRACTION FUNCTIONS --START--
def get_text(url):
    rs = requests.get(url)
    root = BeautifulSoup(rs.content, 'html.parser')
    article = root.select_one('article')
    return article.text

def there_are_letters(str):
    for i in range(len(str)):
        if str[i].isalpha():
            return True
    return False

def get_name(str, arr):
    str_copy = ""
    for i in range(len(str)):
        if str[i] != '*':
            str_copy += str[i].lower()
    i = 0
    curr = 0
    while i < len(arr):
        bef = curr
        curr = str_copy.find(arr[i], curr)
        if curr == -1 or (bef != 0 and (abs(bef - curr) == 0 or abs(bef - curr) > 1)):
            break
        curr += len(arr[i])
        i += 1
    ans = ' ' .join(arr[:i])
    if len(ans) > 0:
        return ans
    else:
        i = 0
        while i + 1 < len(str) and str[i].islower() and str[i + 1].isupper():
            i += 1
        return str[:i + 1]


def find_name(link):
    curr = link.split('/')
    i = len(curr) - 1
    while len(curr[i]) == 0:
        i -= 1
    return curr[i]


def without_strange_words(str, name):
    copy = str.lower()
    if copy.find(name.lower()) != -1:
        return False
    for i in range(len(strange_words)):
        if copy.find(strange_words[i].lower()) != -1:
            return False
    return True


def change_for_comp(str):
    ans = ""
    for i in range(len(str)):
        if str[i].isalpha():
            ans += str[i].lower()
    return ans


def check_song(song_name, session):
    search_results = pylast.TrackSearch(track_title=song_name, artist_name="", network=network)
    page = search_results.get_next_page()
    MAX = min(3, len(page))
    for i in range(MAX):
        second_flag = True
        if len(page) > i:
            second_flag = False
            res = page[i]
            art = res.artist
            tit = res.title
            if abs(len(tit) - len(song_name)) < 5 and (change_for_comp(tit)).find(change_for_comp(song_name)) != -1:
                print(res)
                return (True, art, tit)
    return (False, None, song_name)

# EXTRACTION FUNCTIONS --END--


@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def home():
    form = LinkForm()
    if form.validate_on_submit():
        inputLink = form.link.data
        if ("spotify.com" in inputLink):
            info = json.loads(processSpotify(inputLink))
        elif ("apple.com" in inputLink):
            info = json.loads(processApple(inputLink))
        else:
            info= json.loads(processGoogle(inputLink))
        print(info)
        for artist in info:
            for song, duration in info[artist]:
                print(song, duration)
        return render_template('result.html', title='Result', data=info)
    return render_template('login.html', title='Home', form=form)

@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/result", methods=['GET', 'POST'])
def result():
    return render_template('result.html', title='Result')



@app.route("/login", methods=['GET', 'POST'])
def login():
    return render_template('login.html', title='Login', form=form)

@app.route("/extract", methods=['GET', 'POST'])
def extract():
    form = LinkForm()
    if form.validate_on_submit():
        inputLink = form.link.data
        res = extractSongs(inputLink)
        return render_template('result.html', title='Result', data=res)
    return render_template('analyze.html', title='Extract', form=form)

if __name__ == '__main__':
    app.run(debug=True)

def processGoogle(url):
    START = 'https://play.google.com/'
    http = urllib3.PoolManager()
    response = http.request('GET', url)
    soup = BeautifulSoup(response.data)
    for link in soup.findAll('a'):
        l = link.get('href')
        if 'music' in l:
            nl = l
            break
    response = http.request('GET', START + nl)
    soup = BeautifulSoup(response.data)
    artists = [s.string for s in soup.find_all("div", {'class' : 'artist'})]
    songs = [s.string for s in soup.find_all("div", {'class' : 'track-title'})]
    duration = [s.string for s in soup.find_all("div", {'class' : 'fade-in'})]
    duration = [d for i, d in enumerate(duration) if i % 2 == 0]
    d = {}
    for i, ar in enumerate(artists):
        if ar in d:
            d[ar].append((songs[i], duration[i]))
        else:
            d[ar] = [(songs[i], duration[i])]
    return json.dumps(d, ensure_ascii=False)

def processApple(url):
    http = urllib3.PoolManager()
    html = http.request('GET', url)
    html_code = html.data
    soup = BeautifulSoup(html_code)
    tracks = soup.findAll("span", {"class" : "we-truncate we-truncate--single-line ember-view tracklist-item__text__headline targeted-link__target"})
    artists = soup.findAll("div", {"class" : "we-truncate we-truncate--single-line ember-view"})
    duration = soup.findAll("time", {"class" : "tracklist-item__duration"})
    res = dict()
    for i in range(len(tracks)):
        if artists[i]["aria-label"] in res.keys():
            res[artists[i]["aria-label"]].append((tracks[i].string.strip(), duration[i].contents[0]))
        else:
            res[artists[i]["aria-label"]] = [(tracks[i].string.strip(), duration[i].contents[0])]
    return json.dumps(res, ensure_ascii=False)

def processSpotify(url):
    http = urllib3.PoolManager()
    html = http.request('GET', url)
    html_code = html.data
    soup = BeautifulSoup(html_code)
    #print(soup.contents)
    tracks = soup.findAll("span", {"class" : "track-name"})
    artists = soup.findAll("span", {"class" : "artists-albums"})
    duration = soup.findAll("div", {"class" : "tracklist-col duration"})
    res = dict()
    for i in range(len(tracks)):
        if artists[i].contents[0].string in res.keys():
            res[artists[i].contents[0].string].append((tracks[i].contents[0].string, duration[i].next.next.contents[0]))
        else:
            res[artists[i].contents[0].string] = [((tracks[i].contents[0].string, duration[i].next.next.contents[0]))]
    return json.dumps(res, ensure_ascii=False)

def extractSongs(url):
    url = urllib.parse.unquote(url)
    content = get_text(url)
    names = []
    names_set = set()
    pairs_set = set()
    i = 0
    ans = {}
    while i < len(content):
        flag = True
        #if content[i] == vars[2][0]:
        #    print(i, content[i - 30:i + 30])
#         print(i)
        for jj in range(len(vars)):
            if not flag:
                break
            #if i == 3523:
            #    print(i, content[i], vars[jj][0])
            if content[i] == vars[jj][0]:
                #print(i)
                flag = False
                #print(len(names_set))
                j = i + 1
                while j < len(content) and content[j] != vars[jj][1]:
                    j += 1
                curr = content[i + 1:j]
                if curr not in names_set:
                   # print(curr)
                    flag, artist, song_name = check_song(curr, network)
                   # print(flag, artist, song_name)
                    names_set.add(song_name)
                    if flag and (artist, song_name) not in pairs_set:
                        # print(artist)
                        if (artist in ans):
                            ans[artist].append((song_name, "0:00"))
                        else:
                            ans[artist] = [(song_name, "0:00")]
                        pairs_set.add((artist, song_name))
                i = j
        i += 1
    # print(ans)
    return ans
