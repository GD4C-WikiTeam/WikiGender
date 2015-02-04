from wikitools import wiki, api
import re
import sys
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

langs={'ar':'arabic','az':'Azərbaycanca','bg':'bulgarian','ca':'Català','cs':'Česky','da':'Dansk','de':'Deutsch','el':'Greek',
       'en':'English','es':'Español','eo':'Esperanto','et':'Estonian','eu':'Polish','fa':'Farsi','fr':'French','gl':'Galacian',
       'ko':'Korean','hy':'Hayeren','hi':'Hindi','hr':'Hrvatski','id':'Bahasa Indonesia','it':'Italiano','he':'Hebrew','la':'Latina',
       'lt':'Lietuvių','hu':'Magyar','ms':'Bahasa Melayu','min':'Bahaso Minangkabau','nl':'Nederlands','ja':'japanese','no':'Norsk (bokmål)',
       'nn':'Norsk (nynorsk)','uz':'Oʻzbekcha / Ўзбекча','pl':'Polski','pt':'Português','kk':'Қазақша / Qazaqşa / قازاقشا','ro':'Română',
       'ru':'Russian','sah':'Саха Тыла','simple':'Simple English','ceb':'Sinugboanong Binisaya','sk':'Slovenčina','sl':'Slovenščina',
       'sr':'Српски / Srpski','sh':'Srpskohrvatski / Српскохрватски','fi':'Suomi','sv':'Svenska','tr':'Türkçe','uk':'Українська',
       'vi':'Tiếng Việt','vo':'Volapük','war':'Winaray','zh':' Zhōngwén'}


def gender_users_by_lang(langs,num_of_articles=10,years=10):
    '''
    input -
    langs: dictionary of languages and their common names (ie {'en':"Enlgish"})
    num_of_articles: number of articles to randomly retrieve for each language
    years: how far to go back in time to start pulling revisions.  Note, years can be <1; e.g. years=.5 or .083 for half year or month. 
    
    output -
    userCounts = number of users editing the random pages by gender e.g. {'male':30,'female':134,'unknown':234}}
    editCounts = number of edits made to the random pages by gender e.g. {'male':45,'female':1334,'unknown':2234}}
    
    '''
    userCounts={}
    editCounts={}
    genderDict={'male':0,'female':1,'unknown':-1}
    datestart = datetime.datetime.now() - datetime.timedelta( round(365*years) )
    dateend = datetime.datetime.now()
    #lang='en'
    for lang,langName in langs.iteritems():
        print langName
        pages=Keegan.get_random_pages(num_of_articles,lang)
        Users={}
        ucount={'male':0,'female':0,'unknown':0}
        ecount={'male':0,'female':0,'unknown':0}
        print len(pages), ' articles retrieved'
        for pageid,info in pages.iteritems():
            #Get title
            member=info['title']
            # Revisions in page
            revisions=Keegan.get_page_revisions( member, datestart, dateend, lang )
            print " - revisions: " + str(len(revisions))
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
            # Get user info
                if 'user' in rev:
                    g=Users[rev['user']]
                    ecount[g]+=1
                else:
                    print "rev without 'user'"
                    print rev

        print "Language: " + lang
        print "Edit Count: ", ecount
        print "User Count: ", ucount
        userCounts[lang]=ucount
        editCounts[lang]=ecount
    return userCounts,editCounts


langs={'ar':'arabic','az':'Azərbaycanca','bg':'bulgarian','ca':'Català','cs':'Česky','da':'Dansk','de':'Deutsch','el':'Greek',
       'en':'English','es':'Español','eo':'Esperanto','et':'Estonian','eu':'Polish','fa':'Farsi','fr':'French','gl':'Galacian',
       'ko':'Korean','hy':'Hayeren','hi':'Hindi','hr':'Hrvatski','id':'Bahasa Indonesia','it':'Italiano','he':'Hebrew','la':'Latina',
       'lt':'Lietuvių','hu':'Magyar','ms':'Bahasa Melayu','min':'Bahaso Minangkabau','nl':'Nederlands','ja':'japanese','no':'Norsk (bokmål)',
       'nn':'Norsk (nynorsk)','uz':'Oʻzbekcha / Ўзбекча','pl':'Polski','pt':'Português','kk':'Қазақша / Qazaqşa / قازاقشا','ro':'Română',
       'ru':'Russian','sah':'Саха Тыла','simple':'Simple English','ceb':'Sinugboanong Binisaya','sk':'Slovenčina','sl':'Slovenščina',
       'sr':'Српски / Srpski','sh':'Srpskohrvatski / Српскохрватски','fi':'Suomi','sv':'Svenska','tr':'Türkçe','uk':'Українська',
       'vi':'Tiếng Việt','vo':'Volapük','war':'Winaray','zh':' Zhōngwén'}
   
userCounts,editCounts=gender_users_by_lang(langs,num_of_articles=200,years=20)
#editCounts=gender_edits_by_lang(langs,num_of_articles=200,years=10)

