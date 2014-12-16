from wikitools import wiki, 
import datetime
import Keegan
reload(Keegan)

#revisions = Keegan.get_page_revisions("Wedding_dress_of_Kate_Middleton",datetime.datetime.now() - datetime.timedelta(200),datetime.datetime.now(),"en")
#page_categories = Keegan.get_page_categories("Wedding_dress_of_Kate_Middleton", "en")
#category_members = Keegan.get_category_members("Category:Royal wedding dresses", 1, "en")
#user = Keegan.get_user_properties("USERNAME","en")



def get_random_pages(num, lang):
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

import datetime
# Define categories to visit in each of the wikis
categories = {
    # German
    #"de": [ "Kategorie:Frauenmuseum" ], # For some reason, the API returns a fault in here, even though this works:
#    https://de.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Kategorie:Kultur
    # Portuguese
    #"pt": [ "Categoria:Físicas", "Categoria:Astrônomas" ]
    "en": ["Category:Feminist_movement"]
}

# Define ranges
datestart = datetime.datetime.now() - datetime.timedelta( 24 )
dateend = datetime.datetime.now()

revisions = {}
users = {}
counter_male = 0
counter_female = 0
counter_other = 0
counter_unknown = 0
## Go over categories in the Wikipedias ##

# Iterate through languages
for lang in categories:
    print '-- Wikipedia: ' + lang + ' --'
    # Go over given categories
    for cat in categories[lang]:
        category_members = {}
        print ' >> '+ cat + ' <<'
        try:
            # Some categories return as invalid, hence the try/except block
            # at least until we can figure out what is wrong with the API
            category_members = Keegan.get_category_members( cat, 1, lang )
        except:
            # Debugging purposes in case of failure
            print "-----"
            print "(FAIL)"
            print "cat: " + cat
            print "lang: " + lang
            print category_members
            print "-----"

        # Go over pages in category
        for member in category_members:
            print ' ' + member
            # Different categories can include the same page
            # skip if we've already been to that page
            if ( member not in revisions ):
                # Revisions in page
                revisions[member] = Keegan.get_page_revisions( member, datestart, dateend, lang )
                print " - revisions: " + str(len(revisions[member]))
                for rev in revisions[member]:
                    # Get user info
                    api_users = Keegan.get_user_properties(rev['user'],lang)
                    user = api_users["users"][0]
                    if "gender" in user:
                        print " - gender: " + user['gender'];
                        if user['gender'] == "male":
                            counter_male += 1
                        elif user["gender"] == "female":
                            counter_female += 1
                        else:
                            counter_other +=1
                    else:
                        print ' - gender: not available' 
                        counter_unknown += 1
            else:
                # This is just for testing to see that we're skipping duplicate
                # mentions of the same pages
                print "*** Duplicate page skipped: " + member

    # Counters
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