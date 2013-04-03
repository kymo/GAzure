#encoding:utf-8

'''the following is the definition of you db,the default mode don't need authentication when you
have finished designed you db_model, please run python mon_config.py,and the check whether it is
right just as you want you model be like
'''

#db_mode
DB_MODE = 1

#db_name
DB_NAME = 'test'

#db_auth_params
#DB_USER = ''
#DB_PASSWORD = ''

'''here is the main structure of you db collection_* stands for you collections' name in you db
and it can contain the link collections ,please notice that: if you want to link one document to
another one,please make keys of that document just like 'link_*',and the value of that key, of 
course, must be the document's name
'''
COLLECTION_NAME = {
    u'user':
        {
        u'name':'',
        u'email':'',
        u'profile':None,
        u'password':'',
        #more added here
        u'type':0,
        u'mission' : [],
        },
    u'mission':
        {
        u'owner_id':'',
        u'title':'',
        u'introduction':'',
        u'type': 0,
        u'code' : '',
        u'style' : '',
        u'public' : 0
        },
    u'information':
        {
        u'sender':None,
        u'content': None,
        u'comments':None,
        },
    #you can add as many as what you need here
    }


#the following comment should be reactive when you check whether you design is right

def run(dict_name):
    '''run to check whether the designation fits to you desitination
    '''
    keys = dict_name.keys()
    out_print = ""
    for item in keys:
        out_print += item
        if isinstance(dict_name[item], str):
            if item.find('link_') != -1:
                out_print += '(link) '
            else:
                out_print += '(str) '
        elif isinstance(dict_name[item], dict):
            out_print += '(dict) '

    print 'base keys:',
    print 'waring! empty values' if out_print == '' else out_print
    for item in keys:
        #if item is dict
        if isinstance(dict_name[item], dict):
            print item
            run(dict_name[item])
        elif item.find('link_collection') != -1:
            print 'link_to_document:',dict_name[item]
'''
print DB_NAME
run(COLLECTION_NAME)
'''
    

    
