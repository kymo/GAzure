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
    'user':
        {
            'id': 0,
            'name':'',
            'email':'',
            'profile':[],
            'password':'',
            #more added here
            'interest' : [],
            'type':0,
            'mission' : [],
        },
    'mission':
        {
            'owner_id':'',
            'id':0,
            'title':'',
            'introduction':'',
            'type': 0,
            'code' : '',
            'style' : '',
            'public' : 0,
            'comment' : [],
        },
    
    'compile_infor':
        {
            'id' : 0,
            'mission_id': 0,
            'compile_content' : '',
            'time' : '',
            'success' : 0,
        },
    'running_infor':
        {
            'id' : 0,
            'running_information' : {},
            'tag': [],
            'mission_id' : 0,
            'time' : '',
            'success' : 0,
        },
    'comment':
        {
            'sender_id' : '',
            'receiver_id' : '',
            'content' : '',
            'type' : 0,
            'style' : 0,
            'mission_id' : 0,
            'owner_id' : '',
            'id' : 0,
            'time' : '',
        },
    'tag':
        {
            'key' : '',
            'interest' : 0,
            'mission_type' : 0
        },
    'index':
        {
            'key': '',
            'mission' : [],
            'bit' : {},
            'position' : {}
        },
    'profile':
        {
            'name' : '',
            'email' : '',
            'department' : '',
            'mobile' : '',
            'id' : 0
        },

    'information':
        {
            'sender_id': 0,
            'receiver_id' : 0,
            'content': '',
            'time': '',
            'style' : 0,
            'type': 0,
            'id' : 0,

        },
    #ids
    'ids':
        {
            'name' : '',
            'ids' : 0,
        }
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
    

    
