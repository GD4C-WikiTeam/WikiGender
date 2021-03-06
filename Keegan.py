from wikitools import wiki, api
import networkx as nx
from operator import itemgetter
from collections import Counter
import re, random, datetime, urlparse, urllib2, simplejson, copy
import pandas as pd

def is_ip(ip_string, masked=False):
	# '''
	# Input:
	# ip_string - A string we'd like to check if it matches the pattern of a valid IP address.
	# Output:
	# A boolean value indicating whether the input was a valid IP address.
	# '''
	if not isinstance(ip_string, str) and not isinstance(ip_string, unicode):
		return False
	if masked:
		ip_pattern = re.compile('((([\d]{1,3})|([Xx]{1,3}))\.){3}(([\d]{1,3})|([Xx]{1,3}))', re.UNICODE)
	else:
		ip_pattern = re.compile('([\d]{1,3}\.){3}([\d]{1,3})', re.UNICODE)
	if ip_pattern.match(ip_string):
		return True
	else:
		return False

def convert_to_datetime(string):
    dt = datetime.datetime.strptime(string,'%Y-%m-%dT%H:%M:%SZ')
    return dt
    
def convert_from_datetime(dt):
    string = dt.strftime('%Y%m%d%H%M%S')
    return string

def convert_datetime_to_epoch(dt):
    epochtime = (dt - datetime.datetime(1970,1,1)).total_seconds()
    return epochtime

def wikipedia_query(query_params,lang='en'):
	site = wiki.Wiki(url='http://'+lang+'.wikipedia.org/w/api.php')
	request = api.APIRequest(site, query_params)
	result = request.query()
	return result[query_params['action']]

def short_wikipedia_query(query_params,lang='en'):
	site = wiki.Wiki(url='http://'+lang+'.wikipedia.org/w/api.php')
	request = api.APIRequest(site, query_params)
	# Don't do multiple requests
	result = request.query(querycontinue=False)
	return result[query_params['action']]

def random_string(le, letters=True, numerals=False):
	def rc():
		charset = []
		cr = lambda x,y: range(ord(x), ord(y) + 1)
		if letters:
			charset += cr('a', 'z')
		if numerals:
			charset += cr('0', '9')
		return chr(random.choice(charset))
	def rcs(k):
		return [rc() for i in range(k)]
	return ''.join(rcs(le))

def clean_revision(rev):
	# We must deal with some malformed user/userid values. Some 
	# revisions have the following problems:
	# 1. no 'user' or 'userid' keys and the existence of the 'userhidden' key
	# 2. 'userid'=='0' and 'user'=='Conversion script' and 'anon'==''
	# 3. 'userid'=='0' and 'user'=='66.92.166.xxx' and 'anon'==''
	# 4. 'userid'=='0' and 'user'=='204.55.21.34' and 'anon'==''
	# In these cases, we must substitute a placeholder value
	# for 'userid' to uniquely identify the respective kind
	# of malformed revision as above. 
	revision = rev.copy()
	if 'userhidden' in revision:
		revision['user'] = random_string(15, letters=False, numerals=True)
		revision['userid'] = revision['user']
	elif 'anon' in revision:
		if revision['user']=='Conversion script':
			revision['user'] = random_string(14, letters=False, numerals=True)
			revision['userid'] = revision['user']
		elif is_ip(revision['user']):
			# Just leaving this reflection in for consistency
			revision['user'] = revision['user']
			# The weird stuff about multiplying '0' by a number is to 
			# make sure that IP addresses end up looking like this:
			# 192.168.1.1 -> 192168001001
			# This serves to prevent collisions if the numbers were
			# simply joined by removing the periods:
			# 215.1.67.240 -> 215167240
			# 21.51.67.240 -> 215167240
			# This also results in the number being exactly 12 decimal digits.
			revision['userid'] = ''.join(['0' * (3 - len(octet)) + octet \
											for octet in revision['user'].split('.')])
		elif is_ip(revision['user'], masked=True):
			# Let's distinguish masked IP addresses, like
			# 192.168.1.xxx or 255.XXX.XXX.XXX, by setting 
			# 'user'/'userid' both to a random 13 digit number
			# or 13 character string. 
			# This will probably be unique and easily 
			# distinguished from an IP address (with 12 digits
			# or characters). 
			revision['user'] = random_string(13, letters=False, numerals=True)
			revision['userid'] = revision['user']
	return revision

def cast_to_unicode(string):
    if isinstance(string,str):
        try:
            string2 = string.decode('utf8')
        except:
            try:
                string2 = string.decode('latin1')
            except:
                print "Some messed up encoding here"
    elif isinstance(string,unicode):
        string2 = string
    return string2

def get_user_revisions(user,dt_end,lang):
    '''
    Input: 
    user - The name of a wikipedia user with no "User:" prefix, e.g. 'Madcoverboy' 
    dt_end - a datetime object indicating the maximum datetime to return for revisions
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    revisions - A list of revisions for the given article, each given as a dictionary. This will
            include all properties as described by revision_properties, and will also include the
            title and id of the source article. 
    '''
    user = cast_to_unicode(user)
    revisions = list()
    dt_end_string = convert_from_datetime(dt_end)
    result = wikipedia_query({'action':'query',
                              'list': 'usercontribs',
                              'ucuser': u"User:"+user,
                              'ucprop': 'ids|title|timestamp|sizediff',
                              #'ucnamespace':'0',
                              'uclimit': '500',
                              'ucend':dt_end_string},lang)
    if result and 'usercontribs' in result.keys():
            r = result['usercontribs']
            r = sorted(r, key=lambda revision: revision['timestamp'])
            for revision in r:
                    # Sometimes the size key is not present, so we'll set it to 0 in those cases
                    revision['sizediff'] = revision.get('sizediff', 0)
                    revision['timestamp'] = convert_to_datetime(revision['timestamp'])
                    revisions.append(revision)
    return revisions

def get_user_properties(user,lang):
    '''
    Input:
    user - a string with no "User:" prefix corresponding to the username ("Madcoverboy"
    lang - a string (usually two digits) for the language version of Wikipedia to query

    Output:
    result - a dictionary containing attrubutes about the user
    '''
    user = cast_to_unicode(user)
    result = wikipedia_query({'action':'query',
                                'list':'users',
                                'usprop':'blockinfo|groups|editcount|registration|gender',
                                'ususers':user},lang)
    return result
    
def make_user_alters(revisions):
    '''
    Input:
    revisions - a list of revisions generated by get_user_revisions

    Output:
    alters - a dictionary keyed by page name that returns a dictionary containing
        the count of how many times the user edited the page, the timestamp of the user's
        earliest edit to the page, the timestamp the user's latest edit to the page, and 
        the namespace of the page itself
    '''
    alters = dict()
    for rev in revisions:
        if rev['title'] not in alters.keys():
            alters[rev['title']] = dict()
            alters[rev['title']]['count'] = 1
            alters[rev['title']]['min_timestamp'] = rev['timestamp']
            alters[rev['title']]['max_timestamp'] = rev['timestamp']
            alters[rev['title']]['ns'] = rev['ns']
        else:
            alters[rev['title']]['count'] += 1
            alters[rev['title']]['max_timestamp'] = rev['timestamp']
    return alters

def rename_on_redirect(article_title,lang='en'):
    '''
    Input:
    article_title - a string with the name of the article or page that may be redirected to another title
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    article_title - a string with the name of the article or page that the redirect resolves to
    '''
    result = wikipedia_query({'titles': article_title,
                                  'prop': 'info',
                                  'action': 'query',
                                  'redirects': 'True'},lang)
    if 'redirects' in result.keys() and 'pages' in result.keys():
        article_title = result['redirects'][0]['to']
    return article_title

def get_page_revisions(article_title,dt_start,dt_end,lang):
    '''
    Input: 
    article - A string with the name of the article or page to crawl
    dt_start - A datetime object indicating the minimum datetime to return for revisions
    dt_end - a datetime object indicating the maximum datetime to return for revisions
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl
    
    Output:
    revisions - A list of revisions for the given article, each given as a dictionary. This will
            include all properties as described by revision_properties, and will also include the
            title and id of the source article. 
    '''
    article_title = rename_on_redirect(article_title)
    dt_start_string = convert_from_datetime(dt_start)
    dt_end_string = convert_from_datetime(dt_end) 
    revisions = list()
    result = wikipedia_query({'titles': article_title,
                              'prop': 'revisions',
                              'rvprop': 'ids|timestamp|user|userid|size',
                              'rvlimit': '5000',
                              'rvstart': dt_start_string,
                              'rvend': dt_end_string,
                              'rvdir': 'newer',
                              'action': 'query'},lang)
    if result and 'pages' in result.keys():
            page_number = result['pages'].keys()[0]
            try:
                r = result['pages'][page_number]['revisions']
                for revision in r:
                        revision['pageid'] = page_number
                        revision['title'] = result['pages'][page_number]['title']
                        # Sometimes the size key is not present, so we'll set it to 0 in those cases
                        revision['size'] = revision.get('size', 0)
                        revision['timestamp'] = convert_to_datetime(revision['timestamp'])
                        revisions.append(revision)
            except KeyError:
                revisions = list()
    return revisions

def make_page_alters(revisions):
    '''
    Input:
    revisions - a list of revisions generated by get_page_revisions

    Output:
    alters - a dictionary keyed by user name that returns a dictionary containing
    the count of how many times the user edited the page, the timestamp of the user's
    earliest edit to the page, the timestamp the user's latest edit to the page, and 
    the namespace of the page itself
    '''
    alters = dict()
    for rev in revisions:
        if rev['user'] not in alters.keys():
            alters[rev['user']] = dict()
            alters[rev['user']]['count'] = 1
            alters[rev['user']]['min_timestamp'] = rev['timestamp']
            alters[rev['user']]['max_timestamp'] = rev['timestamp']
        else:
            alters[rev['user']]['count'] += 1
            alters[rev['user']]['max_timestamp'] = rev['timestamp']
    return alters

def get_page_content(page_title,lang):
    '''
    Input: 
    page_title - A string with the name of the article or page to crawl
    lang - A string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    revisions_dict - A dictionary of revisions for the given article keyed by revision ID returning a 
            a dictionary of revision attributes. These attributes include all properties as described 
            by revision_properties, and will also include the title and id of the source article. 
    '''
    article_title = rename_on_redirect(page_title)
    revisions_dict = dict()
    result = wikipedia_query({'titles': page_title,
                              'prop': 'revisions',
                              'rvprop': 'ids|timestamp|user|userid|size|content',
                              'rvlimit': '5000',
                              'action': 'query'},lang)
    if result and 'pages' in result.keys():
        page_number = result['pages'].keys()[0]
        revisions = result['pages'][page_number]['revisions']
        for revision in revisions:
            rev = dict()
            rev['pageid'] = page_number
            rev['title'] = result['pages'][page_number]['title']
            rev['size'] = revision.get('size', 0) # Sometimes the size key is not present, so we'll set it to 0 in those cases
            rev['timestamp'] = convert_to_datetime(revision['timestamp'])
            rev['content'] = revision.get('*',unicode()) # Sometimes content hidden, return with empty unicode string
            rev['links'] = link_finder(rev['content'])
            rev['username'] = revision['user']
            rev['userid'] = revision['userid']
            rev['revid'] = revision['revid']
            revisions_dict[revision['revid']] = rev
    return revisions_dict

def get_category_members(category_name, depth, lang='en'):
    '''
    Input: 
    category_name - The name of a Wikipedia(en) category, e.g. 'Category:2001_fires'. 
    depth - An integer in the range [0,n) reflecting the number of sub-categories to crawl
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    articles - A list of articles that are found within the given category or one of its
        subcategories, explored recursively. Each article will be a dictionary object with
        the keys 'title' and 'id' with the values of the individual article's title and 
        page_id respectively. 
    '''
    articles = []
    if depth < 0:
        return articles
    
    #Begin crawling articles in category
    results = wikipedia_query({'list': 'categorymembers',
                                   'cmtitle': category_name,
                                   'cmtype': 'page',
                                   'cmlimit': '500',
                                   'action': 'query'},lang)  
    if 'categorymembers' in results.keys() and len(results['categorymembers']) > 0:
        for i, page in enumerate(results['categorymembers']):
            article = page['title']
            articles.append(article)
    
    # Begin crawling subcategories
    results = wikipedia_query({'list': 'categorymembers',
                                   'cmtitle': category_name,
                                   'cmtype': 'subcat',
                                   'cmlimit': '500',
                                   'action': 'query'},lang)
    subcategories = []
    cat_trans={}
    if 'categorymembers' in results.keys() and len(results['categorymembers']) > 0:
        for i, category in enumerate(results['categorymembers']):
            cat_title = category['title']
	    cat_trans[category['title']]=str(category['pageid'])
            subcategories.append(cat_title)
    
    for category in subcategories:
	try:
	    articles += get_category_members(category,depth-1)
	except:
	    cat_id=cat_trans[category]
	    w=wiki.Wiki(url='http://de.wikipedia.org/w/api.php?')
	    query={'action':'query','prop':'info','pageids':cat_id,'inprop':'url'}
	    request = api.APIRequest(w, query)
	    result=request.query()
	    category_members = get_category_members( result['query']['pages'][cat_id]['title'], depth-1, lang )

    return articles

def get_random_pages(num, lang='en'):
    '''
    Input:
    num - An interger of the number of random pages to return
    lang - A string of the language to choose from
    
    Output:
    Results - A dictionary of page information {u'20082460': {u'ns': 0, u'pageid': 20082460, u'title': u'Yoshinari Takagi'}}
    '''
    Results={}
    while len(Results)< num:  
        url='http://'+lang+'.wikipedia.org/w/api.php?'
        w=wiki.Wiki(url=url)
        query={'action':'query','generator':'random','grnnamespace':'0'}#'rnlimit':str(num),
        request = api.APIRequest(w, query)
        result=request.query()
        Results.update(result['query']['pages'])
    return Results


def get_page_categories(page_title,lang='en'):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    categories - A list of the names of the categories of which the page is a member
    '''
    page_title = rename_on_redirect(page_title)
    results = wikipedia_query({'prop': 'categories',
                                   'titles': page_title,
                                   'cllimit': '500',
                                   'clshow':'!hidden',
                                   'action': 'query'},lang)
    if 'pages' in results.keys():
        page_number = results['pages'].keys()[0]
        categories = results['pages'][page_number]['categories']
        categories = [i['title'] for i in categories]
        categories = [i for i in categories if i != u'Category:Living people']
    else:
        print u"{0} not found in category results".format(page_title)
    return categories

def get_page_outlinks(page_title,lang='en'):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    outlinks - A list of all "alter" pages that link out from the current version of the "ego" page

    Notes:
    This uses API calls to return all [[links]] which may be slower and result in overlinking from templates
    '''
    # This approach is susceptible to 'overlinking' as it includes links from templates
    page_title = cast_to_unicode(page_title)
    page_title = rename_on_redirect(page_title)
    result = wikipedia_query({'titles': page_title,
                                  'prop': 'links',
                                  'pllimit': '500',
                                  'plnamespace':'0',
                                  'action': 'query'},lang)
    if 'pages' in result.keys():
        page_number = result['pages'].keys()[0]
        results = result['pages'][page_number]['links']
        outlinks = [l['title'] for l in results]
    else:
        print u"Error: No links found in {0}".format(page_title)
    return outlinks

def get_page_inlinks(page_title,lang='en'):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    inlinks - A list of all "alter" pages that link in to the current version of the "ego" page
    '''
    page_title = cast_to_unicode(page_title)
    page_title = rename_on_redirect(page_title)
    result = wikipedia_query({'bltitle': page_title,
                                  'list': 'backlinks',
                                  'bllimit': '500',
                                  'blnamespace':'0',
                                  'blfilterredir':'nonredirects',
                                  'action': 'query'},lang)
    if 'backlinks' in result.keys():
        results = result['backlinks']
        inlinks = [l['title'] for l in results]
    else:
        print u"Error: No links found in {0}".format(article_title)
    return inlinks

# Links inside templates are included which results in completely-connected components
# Remove links from templates by getting a list of templates used across all pages
def get_page_templates(page_title,lang):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    templates - A list of all the templates (which contain redundant links) in the current version
    '''
    page_title = cast_to_unicode(page_title)
    page_title = rename_on_redirect(page_title)
    result = wikipedia_query({'titles': page_title,
                                  'prop': 'templates',
                                  'tllimit': '500',
                                  'action': 'query'},lang)
    if 'pages' in result.keys():
        page_id = result['pages'].keys()[0]
        templates = [i['title'] for i in result['pages'][page_id]['templates']]
    return templates

def get_page_links(page_title,lang='en'):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl that is the "ego" page
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    links - A dictionary keyed by ['in','out'] of all "alter" pages that link in to and out from the 
        current version of the "ego" page
    '''
    links=dict()
    links['in'] = get_page_inlinks(page_title,lang)
    links['out'] = get_page_outlinks(page_title,lang)
    return links

# Identify links based on content of revisions
def link_finder(content_string):
    '''
    Input:
    content_string - A string containing the raw wiki-markup for a page

    Output:
    links - A list of all "alter" pages that link out from the current version of the "ego" page

    Notes:
    This uses regular expressions to coarsely parse the content for instances of [[links]] and likely returns messy data
    '''
    links = list()
    for i,j in re.findall(r'\[\[([^|\]]*\|)?([^\]]+)\]\]',content_string):
        if len(i) == 0:
            links.append(j)
        elif u'#' not in i :
            links.append(i[:-1])
        elif u'#' in i:
            new_i = i[:i.index(u'#')]
            links.append(new_i)
    links = [l for l in links if u'|' not in l and u'Category:' not in l and u'File:' not in l]
    return links

def get_page_outlinks_from_content(page_title,lang='en'):
    '''
    Input:
    page_title - A string with the name of the article or page to crawl that is the "ego" page
    lang - A string (typically two-digits) corresponding to the language code for the Wikipedia to crawl

    Output:
    links - A list of all "alter" pages that link out from the current version of the "ego" page

    Notes:
    This uses regular expressions to coarsely parse the content for instances of [[links]] and may be messy
    '''
    page_title = cast_to_unicode(page_title)
    page_title = rename_on_redirect(page_title)
    
    # Get content from most recent revision of an article
    result = short_wikipedia_query({'titles': page_title,
                                  'prop': 'revisions',
                                  'rvlimit': '1',
                                  'rvprop':'ids|timestamp|user|userid|content',
                                  'action': 'query'},lang)
    if 'pages' in result.keys():
        page_id = result['pages'].keys()[0]
        content = result['pages'][page_id]['revisions'][0]['*']
        links = link_finder(content)
    else:
        print u'...Error in {0}'.format(page_title)
        links = list()
        
    return links

def get_user_outdiscussion(user_name,dt_end,lang='en'):
    '''
    Input:
    user_name - The name of a "ego" wikipedia user with no "User:" prefix, e.g. 'Madcoverboy' 
    dt_end - a datetime object indicating the maximum datetime to return for revisions
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    users - A list of all "alter" user talk pages that the ego has ever posted to
    '''
    # User revision code in only user namespace
    user_name = cast_to_unicode(user_name)
    users = dict()
    dt_end_string = convert_from_datetime(dt_end)
    result = wikipedia_query({'action':'query',
                                  'list': 'usercontribs',
                                  'ucuser': u"User:"+user_name,
                                  'ucprop': 'ids|title|timestamp|sizediff',
                                  'ucnamespace':'3',
                                  'uclimit': '500',
                                  'ucend':dt_end_string},lang)
    if result and 'usercontribs' in result.keys():
        r = result['usercontribs']
        for rev in r:
            alter = rev['title'][10:] # Ignore "User talk:"
            if alter not in users.keys():
                users[alter] = dict()
                users[alter]['count'] = 1
                users[alter]['min_timestamp'] = rev['timestamp']
                users[alter]['max_timestamp'] = rev['timestamp']
            else:
                users[alter]['count'] += 1
                users[alter]['max_timestamp'] = rev['timestamp']
    return users

def get_user_indiscussion(user_name,dt_end,lang='en'):
    '''
    Input:
    user_name - The name of a "ego" wikipedia user with no "User:" prefix, e.g. 'Madcoverboy' 
    dt_end - a datetime object indicating the maximum datetime to return for revisions
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    users - A list of all "alter" user talk pages that have ever posted to the user's talk page
    '''
    # Article revision code in only user talk page
    user_name = cast_to_unicode(user_name)
    users = dict()
    dt_end_string = convert_from_datetime(dt_end)
    result = wikipedia_query({'titles': u'User talk:'+user_name,
                                  'prop': 'revisions',
                                  'rvprop': 'ids|timestamp|user|userid|size',
                                  'rvlimit': '5000',
                                  'rvend': dt_end_string,
                                  'action': 'query'},lang)
    if result and 'pages' in result.keys():
        page_number = result['pages'].keys()[0]
        try:
            r = result['pages'][page_number]['revisions']
            for rev in r:
                if rev['user'] not in users.keys():
                    users[rev['user']] = dict()
                    users[rev['user']]['count'] = 1
                    users[rev['user']]['min_timestamp'] = rev['timestamp']
                    users[rev['user']]['max_timestamp'] = rev['timestamp']
                else:
                    users[rev['user']]['count'] += 1
                    users[rev['user']]['max_timestamp'] = rev['timestamp']
        except KeyError:
            pass
    return users

def get_user_discussion(user_name,dt_end,lang='en'):
    '''
    Input:
    user_name - The name of a "ego" wikipedia user with no "User:" prefix, e.g. 'Madcoverboy' 
    dt_end - a datetime object indicating the maximum datetime to return for revisions
    lang - a string (typically two characters) indicating the language version of Wikipedia to crawl

    Output:
    users - A dictionary keyed by the values ['in','out'] that combines both get_user_outdiscussion and
        get_user_indiscussion
    '''
    users=dict()
    users['out'] = get_user_outdiscussion(user_name,dt_end,lang)
    users['in'] = get_user_indiscussion(user_name,dt_end,lang)
    return users

def make_article_trajectory(revisions):
    '''
    Input:
    revisions - A list of revisions generated by get_page_revisions

    Output:
    g - A NetworkX DiGraph object corresponding to the trajectory of an article moving between users
        Nodes are users and links from i to j exist when user i made a revision immediately following user j
    '''
    g = nx.DiGraph()
    # Sort revisions on ascending timestamp
    sorted_revisions = sorted(revisions,key=lambda k:k['timestamp'])

    # Don't use the last revision
    for num,rev in enumerate(sorted_revisions[:-1]):
        # Edge exists between user and user in next revision
        edge = (rev['user'],revisions[num+1]['user'])
        if g.has_edge(*edge):
            g[edge[0]][edge[1]]['weight'] += 1
        else:
            g.add_edge(*edge,weight=1)
    return g

def make_editor_trajectory(revisions):
    '''
    Input:
    revisions - A list of revisions generated by get_user_revisions

    Output:
    g - A NetworkX DiGraph object corresponding to the trajectory of a user moving between articles
        Nodes are pages and links from i to j exist when page i was edited by the user immediately following page j
    '''
    g = nx.DiGraph()
    # Sort revisions on ascending timestamp
    sorted_revisions = sorted(revisions,key=lambda k:k['timestamp'])

    # Don't use the last revision
    for num,rev in enumerate(sorted_revisions[:-1]):
        # Edge exists between user and user in next revision
        edge = (rev['title'],revisions[num+1]['user'])
        if g.has_edge(*edge):
            g[rev['title']][revisions[num+1]['user']]['weight'] += 1
        else:
            g.add_edge(*edge,weight=1)
    return g

def fixurl(url):
    # turn string into unicode
    if not isinstance(url,unicode):
        url = url.decode('utf8')

    # parse it
    parsed = urlparse.urlsplit(url)

    # divide the netloc further
    userpass,at,hostport = parsed.netloc.rpartition('@')
    user,colon1,pass_ = userpass.partition(':')
    host,colon2,port = hostport.partition(':')

    # encode each component
    scheme = parsed.scheme.encode('utf8')
    user = urllib2.quote(user.encode('utf8'))
    colon1 = colon1.encode('utf8')
    pass_ = urllib2.quote(pass_.encode('utf8'))
    at = at.encode('utf8')
    host = host.encode('idna')
    colon2 = colon2.encode('utf8')
    port = port.encode('utf8')
    path = '/'.join(  # could be encoded slashes!
        urllib2.quote(urllib2.unquote(pce).encode('utf8'),'')
        for pce in parsed.path.split('/')
    )
    query = urllib2.quote(urllib2.unquote(parsed.query).encode('utf8'),'=&?/')
    fragment = urllib2.quote(urllib2.unquote(parsed.fragment).encode('utf8'))

    # put it back together
    netloc = ''.join((user,colon1,pass_,at,host,colon2,port))
    return urlparse.urlunsplit((scheme,netloc,path,query,fragment))

def convert_months_to_strings(m):
	if len(str(m)) > 1:
		new_m = unicode(m)
	else:
		new_m = u'0'+unicode(m)
	return new_m

def get_url(article_name,lang,month,year):
    url = u"http://stats.grok.se/json/" + lang + u"/" + unicode(year) + convert_months_to_strings(month) + u"/" + article_name
    fixed_url = fixurl(url)
    return fixed_url

def requester(url):
    opener = urllib2.build_opener()
    req = urllib2.Request(url)
    f = opener.open(req)
    r = simplejson.load(f)
    result = pd.Series(r['daily_views'])
    return result

def clean_timestamps(df):
    to_drop = list()
    for d in df.index:
        try:
            datetime.date(int(d[0:4]),int(d[5:7]),int(d[8:10]))
        except ValueError:
            to_drop.append(d)
    df2 = df.drop(to_drop,axis=0)
    df2.index = pd.to_datetime(df2.index)
    return df2

def get_pageviews(article,lang,min_date,max_date):
    rng = pd.date_range(min_date,max_date,freq='M')
    rng2 = [(i.month,i.year) for i in rng]
    ts = pd.Series()
    for i in rng2:
        url = get_url(article,lang,i[0],i[1])
        result = requester(url)
        ts = pd.Series.append(result,ts)
    ts = ts.sort_index()
    ts = clean_timestamps(ts)
    ts = ts.asfreq('D')
    return ts

def make_pageview_df(article_list,lang,min_date,max_date):
    df = pd.DataFrame(index=pd.date_range(start=min_date,end=max_date))
    l = len(article_list)
    for num,a in enumerate(article_list):
        try:
            print "{0} / {1} : {2}".format(num+1,l,a)
            ts = get_pageviews(a,lang,min_date,max_date)
            df[a] = ts
        except:
            print u'Something happened to {0}'.format(unicode(a))
            pass
    return df

def editors_other_activity(article_title,dt_start,dt_end,ignorelist,lang):
    revisions = get_page_revisions(article_title,dt_start,dt_end,lang)
    revision_alters = make_page_alters(revisions)
    revision_alters2 = {k:v for k,v in revision_alters.iteritems() if k not in ignorelist}
    
    alter_contributions = dict()
    for num,editor_alter in enumerate(revision_alters2.keys()):
        print u"{0} / {1}: {2}".format(num+1,len(revision_alters2.keys()),editor_alter)
        alter_contributions[editor_alter] = get_user_revisions(editor_alter,dt_start,lang)
        
    #el = directed_dict_to_edgelist(alter_discussions)
    return revisions,alter_contributions

def editing_primary_discussion_secondary(article_title,dt_start,dt_end,ignorelist,lang):
    revisions = get_page_revisions(article_title,dt_start,dt_end,lang)
    revision_alters = make_page_alters(revisions)
    revision_alters2 = {k:v for k,v in revision_alters.iteritems() if k not in ignorelist}
    
    alter_discussions = dict()
    for num,editor_alter in enumerate(revision_alters2.keys()):
        print u"{0} / {1}: {2}".format(num+1,len(revision_alters2.keys()),editor_alter)
        alter_discussions[editor_alter] = get_user_discussion(editor_alter,dt)
        
    #el = directed_dict_to_edgelist(alter_discussions)
    return revisions,alter_discussions

