import wikitools
import datetime
import Keegan
reload(Keegan)

#revisions = Keegan.get_page_revisions("Wedding_dress_of_Kate_Middleton",datetime.datetime.now() - datetime.timedelta(200),datetime.datetime.now(),"en")
#page_categories = Keegan.get_page_categories("Wedding_dress_of_Kate_Middleton", "en")
#category_members = Keegan.get_category_members("Category:Royal wedding dresses", 1, "en")
#user = Keegan.get_user_properties("USERNAME","en")


import datetime
# Define categories to visit in each of the wikis
categories = {
    # German
    "de": [ "Kategorie:Frauenmuseum" ],
    # Portuguese
    "pt": [ "Categoria:Físicas", "Categoria:Astrônomas" ]
}

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
print "running..."
# Iterate through languages
print "Language,Category,Page,Male,Female,Other,Unkown"
for lang in categories:
    # Go over given categories
    for cat in categories[lang]:
        category_members = {}
        try:
            # Some categories return as invalid, hence the try/except block
            # at least until we can figure out what is wrong with the API
            category_members = get_category_members( cat, 1, lang )
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
            # Different categories can include the same page
            # skip if we've already been to that page
            if ( member not in revisions ):
                c_f = 0
                c_m = 0
                c_other = 0
                c_unknown = 0
                # Revisions in page
                revisions[member] = get_page_revisions( member, datestart, dateend, lang )
                for rev in revisions[member]:
                    # Get user info
                    if "user" in rev: # Apparently, not all revisions have that...
                        api_users = get_user_properties(rev['user'], lang)
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
