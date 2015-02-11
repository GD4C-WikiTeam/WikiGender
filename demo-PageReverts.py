import wikitools
import datetime
import hashlib as hsh
import re
import Keegan
reload(Keegan)



def tokenize(text,stopwords=[]):
    '''this function tokenizes `text` using simple rules:
    tokens are defined as maximal strings of letters, digits
    and apostrophies.
    The optional argument `stopwords` is a list of words to
    exclude from the tokenzation'''
    # make lowercase
    text = text.lower()
    # grab just the words we're interested in
    text = re.findall(r"[\d\w']+",text)
    # remove stopwords
    res = []
    for w in text:
        if w not in stopwords:
            res.append(w)
    
    return(res)



def page_revert_query(page,lang='en'):
    '''
    Adjust the Keegan code to return the comments made by editors to indicate revisions that are flagged as reverts in the comments
    but not determined to be revert by text comparison.
    

    '''
    revisions_dict={}
    result = Keegan.wikipedia_query({'titles': Keegan.rename_on_redirect(page),
                              'prop': 'revisions',
                              'rvprop': 'ids|timestamp|user|userid|size|comment|content',
                              'rvlimit': '5000',
                              'action': 'query'},lang)
    revisions=[]
    if result and 'pages' in result.keys():
        page_number = result['pages'].keys()[0]
        revs = result['pages'][page_number]['revisions']
        for revision in revs:
            rev = dict()
            rev['pageid'] = page_number
            rev['title'] = result['pages'][page_number]['title']
            rev['size'] = revision.get('size', 0) # Sometimes the size key is not present, so we'll set it to 0 in those cases
            rev['timestamp'] = Keegan.convert_to_datetime(revision['timestamp'])
            rev['comment']=revision['comment']
            rev['content'] = revision.get('*',unicode()) # Sometimes content hidden, return with empty unicode string
            rev['links'] = Keegan.link_finder(rev['content'])
            rev['user'] = revision['user']
            rev['userid'] = revision['userid']
            rev['revid'] = revision['revid']
            revisions.append(rev)
    return revisions

def get_page_reverts(page,lang='en',years=10.0,num=100):
    '''
    input -
    page: name from wikipedia (e.g "Category:Feminist_events")
    lang: language of article [NOTE THIS MUST BE UPDATED FOR OTHER LANGUAGES TO LOOK FOR "REVERT" IN COMMENTS]
    num: number of revisions to include from each article to make the estimate
        num can be 'all', in which case, no subsetting
    years: how far to go back in time to start pulling revisions.  Note, years can be <1; e.g. years=.5 or .083 for half year or month. 
        
    output -
    tagged: number of reverts identified by comments (e.g. "Reversion of user: MyName's edit. Not Related")
    inferred: number of reverts identified using md5 hashing to compare chunks of texts
    ties: dictionary of reverter, reverted, times reverter reverted the revertee. (e.g. {Me_You: 20 reverts})
    total: unique number of reverts including both inferred and tagged, but not double counting    
    '''
    
    datestart = datetime.datetime.now() - datetime.timedelta( 365*years )
    dateend = datetime.datetime.now()
    versions=page_revert_query(page, lang )  #code grabs all page revisions (up to 5000)
    #hash all article content for each revision.  This is used to super-charge the matching process.
    hashes=[hsh.md5((version['content']).encode('utf-8')).hexdigest() for version in versions]
    #generate a list of all the comments.  Used to maintain shared indexing with hashses so hashes[3] and comments[3] are same revision
    comments=[version['comment'] for version in versions]
    ties={}
    tagged=0
    inferred=0
    total=0
    for i in xrange(len(hashes)):
        flag=0
        cur_user=versions[i]['user']
        #This assumes the first two revisions cannot be considered reverts as they create the article.
        if i>2:
            if sum([a in versions[i]['comment'].lower() for a in ['revert','reverted','reverting','undid revision']])>0 or sum([a in tokenize(versions[i]['comment']) for a in ['rv', 'rvv','revert']])>0:
                tagged+=1
                flag=1
                print 'REVERT', versions[i]['user'], versions[i]['comment']+'\n'#,tokenize(versions[i]['comment'])
            else:
                print 'NO REV: ', versions[i]['user'], versions[i]['comment']+'\n'
            #if hashes[i-1]==hashes[i]:
            #    inferred+=1
            #    flag=1
            #Compare version i of the article to all version j<i to see if version i is the same as an earlier version
            for j in xrange(i-1):
                inflag=0
                last=''
                if hashes[j]==hashes[i]:
                    last=j
                    inflag=1
                    flag=1
                if inflag==1:
                    inferred+=1
                    tie=versions[i]['user']+'_'+versions[last]['user']
                    print 'INFERRED REVERT', tie, i,last, versions[i]['comment']
        
        if flag==1:
            total+=1
            tie=versions[i]['user']+'_'+versions[i-1]['user']
            if versions[i]['user']!=versions[i-1]['user']:
                if tie in ties.keys():
                    ties[tie]+=1
                else:
                    ties[tie]=1
    total=sum(ties.values())
    return tagged, inferred, ties,total

page='YesAllWomen'
tagged, inferred, ties, total=get_page_reverts(page,lang='en',years=10.0,num=100)

