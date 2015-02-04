'''
This code is meant to provide a quick and dirty estimate for the genderedness of a category
It takes the category members, finds the most reasonable time slice for recent activity, and counts the proportion of
male and female contributors.
'''
from wikitools import wiki, api
import sys
import datetime
import re
import Keegan
reload(Keegan)

def Get_Category_Users(category,lang='en',num=50,years=10):
    '''
    input -
    category: string name from wikipedia (e.g "Category:Feminist_events")
    lang: language of article (e.g. 'en' for English)
    num: number of revisions to include from each article to make the estimate
    years: how far to go back in time to start pulling revisions. Note, years can be <1; e.g. years=.5 or .083 for half year or month. 
    
    output -
    userCounts = number of users editing the random pages by gender e.g. {'male':30,'female':134,'unknown':234}}
    editCounts = number of edits made to the random pages by gender e.g. {'male':45,'female':1334,'unknown':2234}}
        
    '''
    #set environmental variables
    ucount={'male':0,'female':0,'unknown':0}
    ecount={'male':0,'female':0,'unknown':0}
    genderDict={"male":0,'female':1,'unknown':-1}
    Users={} #variable for remembering users 
    dones=set() #variable for excluding duplicate articles
    datestart = datetime.datetime.now() - datetime.timedelta( 365*years )
    dateend = datetime.datetime.now()
    
    #import pages for category
    print ' >> '+ category + ' <<'
    try:
        # Some categories return as invalid, hence the try/except block
        # at least until we can figure out what is wrong with the API
        category_members = Keegan.get_category_members( category, 1, lang )
        print len(category_members)
    except:
        # Debugging purposes in case of failure
        print "-----"
        print "(FAIL)"
        print "cat: " + category
        print "lang: " + lang
        print category_members
        print "-----"
        return
    
    #get user data and counts for each page     
    for index,member in enumerate(category_members):
        print ' ' + member
        # Different categories can include the same page
        # skip if we've already been to that page
        if member not in dones:
            # Revisions in page
            Keegan.get_page_revisions( member, datestart, dateend, lang )
            revisions = Keegan.get_page_revisions( member, datestart, dateend, lang )
            revisions=revisions[0:num]
            
            users=set([rev['user'] for rev in revisions if "user" in rev])
            for user in users:
                if user not in Users.keys():
                    api_users = Keegan.get_user_properties(rev['user'], lang)
                    if 'gender' in api_users['users'][0]:
                        Users[user]=api_users['users'][0]['gender']
                        ucount[Users[user]]+=1
                    else:
                        Users[user]='unknown'
                        ucount[Users[user]]+=1
            
            for rev in revisions:
                if 'user' in rev:
                    g=Users[rev['user']]
                    ecount[g]+=1
            
            dones.update([member])
                        
                
        print "Category: " + category            
        print "Edit Count: ", ecount
        print "User Count: ", ucount
        userCounts[category]=ucount
        editCounts[category]=ecount
                
    return count

category="Category:Home_economics"
count=Get_Category_Users(category,lang='en',num=50,years=15)
