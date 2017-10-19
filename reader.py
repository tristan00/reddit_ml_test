
import requests
import os
from bs4 import BeautifulSoup
import traceback
import sqlite3
import time
import re
import datetime
import operator
import random
import nltk
from nltk.corpus import movie_reviews
from nltk.tokenize import sent_tokenize, word_tokenize
#import sklearn

reddit_sleep_time = 3
writing_process_timeout = 300
writing_sleep_time= 180

main_bot = None
main_reader = None
sql_file = 'reddit_db.sqlite'
os.chdir(os.path.dirname(os.path.realpath(__file__)))
subreddits = ['dankmemes', 'me_irl', 'surrealmemes', 'totallynotrobots', 'funny', 'catsstandingup', 'aww', 'pics', 'gifs', 'videos', 'gaming', 'ProgrammerHumor']
random.shuffle(subreddits)

class post():
    def __init__(self, url, p_id):
        self.url = url
        self.p_id = p_id
        self.comments = []

class comment_data():
    def __init__(self, soup, p_id):
        self.soup = soup
        self.p_id = p_id

    def read_timestamp(self):
        self.time_str = self.soup.find('time')['datetime']
        self.comment_timestamp = datetime.datetime.strptime(self.time_str,'%Y-%m-%dT%H:%M:%S+00:00').timestamp()

    def read_text(self):
        self.text = self.soup.find('div', {'class':'md'}).text
        self.comment_words = split_comments_into_words(self.text)

    def read_upvotes(self):
        self.comment_upvotes = self.soup.find('span',{'class':'score unvoted'})['title']

    def read_all_parameters(self):
        self.read_timestamp()
        self.read_text()
        self.comment_id = self.soup.find('input', {'name':'thing_id'})['value']
        self.comment_upvotes = self.soup.find('span',{'class':'score unvoted'})['title']
        try:
            self.parent_id = self.soup.find('a',{'data-event-action':'parent'})['href'].replace('#','')
        except:
            self.parent_id = None

    def toDB(self, cursur):
        try:
            cursur.execute('insert into comment values(?,?,?,?, ?,?)', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            print('inserted comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
        except:
            try:
                cursur.execute('update comment set upvotes = ? where comment_id = ?', (self.comment_upvotes, self.comment_id.split('_')[1],))
                print('updated comment:', (self.p_id.split('_')[0], self.comment_id.split('_')[1], self.parent_id, self.comment_timestamp, self.text,  self.comment_upvotes))
            except:
                traceback.print_exc()

class Reader():
    def __init__(self, session):
        self.name = ""
        self.put_sub_to_db()
        self.session = session
        #self.write_posts_and_comments_to_db()

        self.word_dict = {}
        self.sentence_count_dict = {}
        self.g_comments = {}
        self.g_title = {}
        self.g_words = {}
        self.g_sentences = {}

        self.possible_comments = {}

    def read_all(self, count):
        for i in subreddits:
            print('reading posts in :', i)
            self.get_post_list(i)
        self.write_comments_to_db(count)

    def put_sub_to_db(self):
        conn = sqlite3.connect('reddit.db')
        cursor = conn.cursor()

        #TODO: create initial db creation code
        cursor.execute('create table if not exists {0} (sub_name TEXT PRIMARY KEY)'.format('subreddit'))
        cursor.execute('create table if not exists {0} (subreddit TEXT, post_id TEXT UNIQUE, post_title TEXT, timestamp TEXT, data_permalink TEXT, comment_count int, upvotes int)'.format('posts'))
        cursor.execute('create table if not exists {0} (post_id TEXT, comment_id TEXT PRIMARY KEY, parent_id TEXT, timestamp TEXT, text TEXT, upvotes int)'.format('comment'))

        conn.commit()
        conn.close()

    def write_post(self, conn, p, subreddit):
        #print(p.attrs)
        try:
            print('Inserting post:', p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
            try:
                conn.execute('insert into posts values(?,?,?,?,?,?,?)', (subreddit ,p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], 0, 0) )
            except:
                pass
            return (p['data-fullname'].split('_')[1], p.find('p',{'class':'title'}).find('a').text, p['data-timestamp'], p['data-permalink'], None, None)
        except:
            traceback.print_exc()
            return (None, None, None, None, None, None)

    def get_post_list(self, subreddit):
        conn = sqlite3.connect('reddit.db')
        tries = 3
        while tries >0:
            time.sleep(reddit_sleep_time)
            try:
                r = self.session.get('https://www.reddit.com/r/{0}/'.format(subreddit))
                soup = BeautifulSoup(r.text, "html.parser")

                posts = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

                print(len(posts))
                for p in posts:
                    self.write_post(conn, p, subreddit)
                conn.commit()
                conn.close()
                print('writing posts done')
                conn.close()
                break
            except:
                traceback.print_exc()
                conn.close()
                tries -= 1
                #fix

    def update_posts(self, soup, conn, p_id):
        comment_count = soup.find('a',{'data-event-action':'comments'}).text.replace(',','').split(' ')[0]
        upvotes = soup.find('span',{'class':'number'}).text.replace(',','')
        conn.execute('update posts set upvotes = ? where post_id = ?', (upvotes, p_id,))
        conn.execute('update posts set comment_count = ? where post_id = ?', (comment_count, p_id,))
        return soup.find_all('div', {'class': re.compile("entry unvoted.*")})

    def write_comments(self, p_url, p_id, conn):
        r = self.session.get('https://www.reddit.com' + p_url)
        soup = BeautifulSoup(r.text, "html.parser")
        try:
            self.update_posts(soup, conn, p_id)
        except:
            traceback.print_exc()
            return
        comment_soup = soup.find_all('div', {'class': re.compile("entry unvoted.*")})
        comment_list = []
        cursor = conn.cursor()
        for c in comment_soup:
            try:
                temp_c = comment_data(c, p_id)
                temp_c.read_all_parameters()
                temp_c.toDB(cursor)
            except:
                pass
                #traceback.print_exc()
        conn.commit()

    def write_comments_to_db(self, count):
        conn = sqlite3.connect('reddit.db')
        res = list(conn.execute('select distinct data_permalink, post_id from posts order by timestamp desc').fetchall())
        random.shuffle(res)
        #res = conn.execute('select distinct data_permalink, post_id from posts')
        if count is None:
            count = len(res)
        for p in res[0:count]:
            time.sleep(reddit_sleep_time)
            print(p)
            self.write_comments(p[0], p[1],conn)

        print('writing comments done')
        conn.commit()
        conn.close()

    def dereference_graphs(self, sub):
        print('building graphs')
        self.g_words.pop(sub,None)
        self.g_title.pop(sub,None)
        self.g_comments.pop(sub,None)
        self.g_sentences.pop(sub,None)

    def get_new_posts_ready_to_analyze(self, conn, subreddit, sorting):
        comment_min_len = 10
        min_comments = 2
        if sorting == 'top past hour':
            r = self.session.get('https://www.reddit.com/r/{0}/top/?sort=top&t=hour'.format(subreddit))
        elif sorting == 'new':
            r = self.session.get('https://www.reddit.com/r/{0}/new/'.format(subreddit))
        soup = BeautifulSoup(r.text,'html.parser')
        ps = soup.find('div', {'id':'siteTable'}).find_all('div', {'data-whitelist-status':'all_ads'}, recursive = False)

        posts = []
        for p in ps:
            post_data = self.write_post(conn, p, subreddit)
            p_url = post_data[3]
            p_id = post_data[0]
            temp_post = post(p_url, p_id)

            print(' p_id, P_url:', p_id, p_url)
            if p_url is None or p_id is None:
                continue

            #pick comment, second earliest since earliest is often mod post
            r = self.session.get('https://www.reddit.com' + p_url)
            soup = BeautifulSoup(r.text,'html.parser')
            comment_table = soup.find('div', {'class':'sitetable nestedlisting'})
            comments = comment_table.find_all('div', {'class': re.compile("entry unvoted.*")})
            if len(comments) < min_comments:
                continue

            comments_clean = []
            for c in comments:
                try:
                    if len(c.find('div', {'class':'md'}).text.lower()) < comment_min_len or 'http' in c.find('div', {'class':'md'}).text.lower():
                        continue
                    else:
                        try:
                            temp_c = comment_data(c, p_id)
                            temp_c.read_timestamp()
                            temp_c.read_text()
                            comments_clean.append(temp_c)
                        except:
                            traceback.print_exc()
                except:
                    pass
            comments_clean.sort(key = operator.attrgetter('comment_timestamp'), reverse = True)
            temp_post.comments=comments_clean
            posts.append(temp_post)
        return posts

    def get_possible_comment_list(self, subreddit, conn):
        self.possible_comments.setdefault(subreddit,[])
        if len(self.possible_comments[subreddit]) == 0:
            for i in conn.execute('select distinct comment.comment_id, comment.post_id, comment.text, comment.upvotes, posts.data_permalink, posts.data_permalink, posts.post_title from posts join comment on posts.post_id = comment.post_id where posts.subreddit like ?', (subreddit,)).fetchall():
                self.possible_comments[subreddit].append(i)
        return self.possible_comments[subreddit]

def login(session, password, user):
    if (isloggedin(session, user)):
        return 1
    try:
        login_data = {'api_type':'json','op':'login','passwd':password,'user':user}
        login_url = 'https://www.reddit.com/api/login/d{0}'.format(user)
        r = session.post(login_url, data = login_data)
    except:
        session = get_session()
        traceback.print_exc()

def isloggedin(session, user):
    r = session.get('https://www.reddit.com')
    if ((user in r.text) or ("dirty_cheeser" in r.text)):
        return 1
    else:
        return 0

def comment_similarity(c1, c2):
    c1_word = list(re.split(r'[^a-zA-Z0-9]+',c1.lower()))
    c2_words = list(re.split(r'[^a-zA-Z0-9]+', c2.lower()))

    value1 = 0
    for i in c1_word:
        if i in c2_words:
            c2_words.remove(i)

    return 1 - len(c2_words)/len(list(re.split(r'[^a-zA-Z0-9]+', c2.lower())))

def split_comments_into_words(c1):
    return word_tokenize(c1.lower())

def split_comments_into_sentences(c1):
    return sent_tokenize(c1.lower())

def get_session():
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:48.0) Gecko/20100101 Firefox/48.0'
    return s

def find_features(document, word_features):
    words = set(document)
    features = {}
    for w in word_features:
        features[w] = (w in words)
    return features


def run_demo():
    documents = [(list(movie_reviews.words(fileid)), category)
                 for category in movie_reviews.categories()
                 for fileid in movie_reviews.fileids(category)]
    random.shuffle(documents)

    all_words = []
    for w in movie_reviews.words():
        all_words.append(w.lower())

    all_words =nltk.FreqDist(all_words)
    word_features = list(all_words.keys())[:3000]
    featuresets = [(find_features(rev, word_features), category) for (rev, category) in documents]
    training_set = featuresets[:1900]
    testing_set = featuresets[1900:]

    classifier = nltk.NaiveBayesClassifier.train(training_set)
    print('accuracy: ', (nltk.classify.accuracy(classifier,testing_set)))
    print(classifier.show_most_informative_features(15))


def run_reader():
    creds=[]
    conn = sqlite3.connect('reddit.db')
    rs = conn.execute('select * from reddit_logins').fetchall()
    for r in rs:
        creds.append({'user_name':r[0], 'password':r[1]})
    main_reader = Reader(get_session())
    conn.close()
    return main_reader

    main_reader.read_all(1000)

def main():
    #reader = run_reader()
    #reader.read_all(1000)
    run_demo()


if __name__ == "__main__":
    main()