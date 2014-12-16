from wikitools import wiki, api
import datetime
import Keegan
reload(Keegan)



def get_random_pages(num, lang):
    '''
    Input:
    num - An interger of the number of random pages to return
    lang - A string of the language to choose from
    
    Output:
    Results - A dictionary of page information {u'20082460': {u'ns': 0, u'pageid': 20082460, u'title': u'Yoshinari Takagi'}}
    '''
    Results={}
    for i in xrange(num):  
        url='http://'+lang+'.wikipedia.org/w/api.php?'
        w=wiki.Wiki(url=url)
        query={'action':'query','generator':'random','grnnamespace':'0'}#'rnlimit':str(num),
        request = api.APIRequest(w, query)
        result=request.query()
        Results.update(result['query']['pages'])
    return Results

import datetime
# Define categories to visit in each of the wikis
#categories = {
#    # German
#    #"de": [ "Kategorie:Frauenmuseum" ], # For some reason, the API returns a fault in here, even though this works:
##    https://de.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Kategorie:Kultur
#    # Portuguese
#    #"pt": [ "Categoria:Físicas", "Categoria:Astrônomas" ]
#    "en": ["Category:Feminist_movement"]
#}

# Define ranges

num_of_days = 365
# Define ranges
datestart = datetime.datetime.now() - datetime.timedelta( num_of_days )
dateend = datetime.datetime.now()

revisions = {}
users = {}

# Global counters
counter_male = 0
counter_female = 0
counter_other = 0
counter_unknown = 0

# Local counters
c_f = 0
c_m = 0
c_other = 0
c_unknown = 0
## Go over categories in the Wikipedias ##

num_of_articles=1000
lang='en'
pages=Keegan.get_random_pages(num_of_articles,lang)
print len(pages), ' articles retrieved'
for pageid,info in pages.iteritems():
    c_f = 0
    c_m = 0
    c_other = 0
    c_unknown = 0
    #Get title
    member=info['title']
    # Revisions in page
    revisions[member]=Keegan.get_page_revisions( member, datestart, dateend, lang )
    print " - revisions: " + str(len(revisions[member]))
    for rev in revisions[member]:
        # Get user info
        if "user" in rev: # Apparently, not all revisions have that...
            api_users = Keegan.cast_to_unicodeget_user_properties(rev['user'], lang)
            user = api_users["users"][0]
            if "gender" in user:
                if user['gender'] == "male":
                    c_m += 1
                    counter_male += 1
                elif user["gender"] == "female":
                    c_f += 1
                    counter_female += 1
                else:
                    c_other += 1
                    counter_other +=1
            else:
                c_unknown += 1
                counter_unknown += 1
        else:
            print "rev without 'user'"
            print rev
    # Print data
    sys.stdout.write( lang + ',' )
    sys.stdout.write( '"' + cat + '",' )
    sys.stdout.write( '"' + member + '",' )
    sys.stdout.write( str(c_m) + ',' + str(c_f) + ',' + str(c_other) + ',' + str(c_unknown) + '\n' )
        
    counter_total = counter_male + counter_female + counter_other + counter_unknown

    print ""
    print "Language: " + lang
    print "-----"
    print "m: " + str(counter_male);
    print "f: " + str( counter_female)
    print "other: "  + str(counter_other)
    print "unknown: "  + str(counter_unknown)

    print "total: " + str(counter_total)
    print ''