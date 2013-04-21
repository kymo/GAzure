#encoding:utf-8
from bottle import route, get, post, run, template, request, response, redirect, view, template
import bson
from monkey import DBModel
from bottle import static_file
from pymmseg import mmseg
import thread
import md5
import os
import socket
import time, datetime
from beaker.middleware import SessionMiddleware
from func import SendEmailThread, html
#link the database 
db = DBModel('g_azure')
db.link_database()
#rsa token
TOKEN = 2113
#load dict
mmseg.dict_load_defaults()
#the state of mission
WAITING = 0
COMPILING = 1
RUNNING = 2
COMPLETED = 3

def user_auth(func):
    """ user authenticate

        this is a decorator for all url that need user's authtication
        before dealing with url,we need to get the identify of the visitor
        
        Args:
            is_login: a bool indicating whether the user has been logined or not

        Return:
            func or another func
    """
    def deco(*req, **st):
        req = dict()
        #get the timestamp
        time_stamp = request.get_cookie('azure_time_stamp', '0', TOKEN)
        time_now = time.time()
        req['user'] = ""
        if int(float(time_now)) - int(float(time_stamp))  < 7 * 24 * 60 * 60:
            user_email = request.get_cookie('azure_email_token', None, TOKEN)
            user_token = request.get_cookie('azure_password_token', None, TOKEN)
            if user_email and user_token:
                user = db.find_collection('user', {'email' : user_email, 'password' : md5.new(user_token).hexdigest()})
                req['user'] = user
            else:
                req['user'] = None
        return func(req)
    return deco

@route('/static/css/:filename')
def send_css(filename):
    """ send css file to client """
    return static_file(filename, root = './static/css/')

@route('/static/js/:filename')
def send_js(filename):
    """ send js file to client """
    return static_file(filename, root = './static/js/')

@route("/static/img/:filename")
def send_img(filename):
    """ send img file to client """
    return static_file(filename, root = './static/img/')

@route('/register','POST')
def register_end():
    """ get register data and register 
        need to keep the structure of the database the same as defied in mon_config.py

        Args:None
        Returns: a template object indicating the hint for identifying
        Raises: InsertException defined in monkey.py
    """
    #get the data from forms and save into database
    user_email = request.forms.get('email')
    user_passwd = request.forms.get('password')
    
    ids = db.find_collection('ids' ,{'name' : 'user'})
    user_id = ids[0]['ids'] + 1 if ids else 1 
    insert_dict = {
        'id'             : user_id,
        'name'           :'',
        'email'          : user_email,
        'profile'        : [],
        'password'       : md5.new(user_passwd).hexdigest(),
        'type'           : 0,
        'interest'       : [],
        'mission'        : []
        }
    if db.insert_collection('user', insert_dict): 
        if user_id == 1:
            db.insert_collection('ids', {'name' : 'user', 'ids' : 1})
        else:
            db.update_collection('ids' ,{'name' : 'user'}, {'ids' : user_id})
        #send email to user
        send_content = "127.0.0.1:8080/authenticate?token=" + md5.new(user_passwd).hexdigest() + "&" + "ID=" + user_email
        send_thread = SendEmailThread(user_email, send_content, "click the following link to authenticate")
        send_thread.start()

        return template('register_ok', email = user_email)
    else:
        return "sorry ,register failed"

@route('/register')
def register_start():
    """ go to register page """
    return template('register')


@route('/authenticate')
@user_auth
def authenticate(req):
    """ authenticate the user """
    token = request.query.token
    ID = request.query.ID
    find_dict = {'email' : ID}
    find_out = db.find_collection('user', find_dict)
    if find_out and find_out[0]['password'] == token:
        if find_out[0]['type'] == 1:
            return redirect('index')
        else:
           return template('authenticated_ok', user = find_out[0])
    else:
        return "failed,sorry"

@post('/authenticate')
def authenticate():
    """ authenticate post method
        we need to get the user's information to build his profile
    """
    
    ID = request.forms.get('ID')
    name = request.forms.get('name')
    email = request.forms.get('email')
    mobile = request.forms.get('mobile')
    department = request.forms.get('department')
    db.update_collection('user',{'email' : ID},{'type' : 1})
    """ we need to save the data to profile collection ,and link the user and the profile document """
    ids = db.find_collection('ids', {'name' : 'profile'})
    db_count = ids[0]['ids'] + 1 if ids else 1
    if db_count != 1:
        db.update_collection('ids', {'name' : 'profile'}, {'ids' : db_count})
    else:
        db.insert_collection('ids', {'name' : 'profile', 'ids' : 1})
    
    insert_dict = {
        'name' : name,
        'email' : email,
        'department' : department,
        'mobile' : mobile,
        'id' : db_count
        }

    db.insert_collection('profile', insert_dict)

    profile = db.find_collection('profile', {'id' : db_count})
    db.update_collection('user', {'email' : ID}, {'profile' : [bson.dbref.DBRef('profile', profile[0]['_id'])]})


@post('/add_tags')
def add_tags():
    ID = request.forms.get('ID')
    tag = request.forms.get('tag')
    tags = [item for item in tag.split(' ') if item != '']
    user = db.find_collection('user', {'email' : ID})
    if user:
        intest = user[0]['interest'] 
        for item in tags:
            intest.append(item)
            tag_doc = db.find_collection('tag', {'key' : item})
            if tag_doc:
                tag_d = tag_doc[0]
                db.update_collection('tag', {'key' : item}, {'interest' : tag_d['interest'] + 1})
            else:
                tag_dict = {
                    'key' : str(item),
                    'interest' : 1,
                    'mission_type' : 0,
                }
                db.insert_collection('tag', tag_dict)
        db.update_collection('user', {'email' : ID}, {'interest' : intest})
    else:
        pass

@route('/login','GET')
def login_page():
    """ redirect to the page needed to login 
        deal with request which has method : GET
    """
    return template('login')

@route('/login', method = 'POST')
def login():
    """ get params to authenticate the user'd identify 
        
        if login operation is legal, then redirect to personal page;
        else give the hint of failure

    """
    name = request.forms.get('mail')
    password = request.forms.get('password')
    is_cookie_allowed = request.forms.get('my')
    new_pass = md5.new(password).hexdigest()
    find_out = db.find_collection('user', {'email' : name})
    #print name, password, is_cookie_allowed
    if find_out and find_out[0]['password'] == new_pass:
        #if the user's has not be authenticated
        #return the alert words
        if find_out[0]['type'] == 0:
            return 'sorry ,please check you email first'
        elif is_cookie_allowed:  
            response.set_cookie('azure_email_token', name, TOKEN)
            response.set_cookie('azure_password_token', password, TOKEN)
            response.set_cookie('azure_time_stamp', str(time.time()), TOKEN)
        person_page_url = '/person_page?ID=' + name
        return redirect(person_page_url)
    else:
        return 'login failed ! please try again'
    response.set_cookie('visited', 'yes')
    return 'nice sdfdf'



@route('/index')
@route('/')
@user_auth
def index(req):
    """ index page method

        Args:
            name: a string indicating the  name of url

        Returns:
            None
    """
    #get the mission
    missions = db.find_collection('mission', {"public":1})
    mission_style = {WAITING : 'waiting', COMPILING : 'compiling', RUNNING : 'running', COMPLETED : 'completed'}
    for i in range(0, len(missions)):
        missions[i]['style'] = mission_style[missions[i]['type']]
        missions[i]['com_num'] = len(db.find_collection('comment', {'mission_id' : missions[i]['id']}))
    user = req['user'][0] if req['user'] else None
    is_auth = (user != None) 
    len_msg = 0
    if user:
        messages = db.find_collection('information', {'receiver_id' : user['id'], 'type' : 0})
        comments = db.find_collection('comment', {'receiver_id' : user['email'], 'type' : 0})
        len_msg = len(messages) + len(comments)
    return template('index', user = user, missions = missions, len_msg = len_msg, is_authenticated = is_auth)

@route('/logout', 'GET')
@user_auth
def log_out(req): 
    """ log out """
    response.set_cookie('azure_email_token', "", TOKEN)
    response.set_cookie('azure_password_token', "", TOKEN)
    current_url = request.query.get('url')
    return redirect('index')

@route('/get_mission_information', "POST")
def get_mission_information():
    """ get mission information (ajax method) """
    mission_id = request.forms.get("ID")
    mission = db.find_collection('mission', {'id': int(mission_id)})[0]
    if mission:
        mission['_id'] = str(mission['_id'])
        return mission
    else:
        return '500'

@route('/about')
@user_auth
def about(req):
    user = req['user'][0] if req['user'] else None
    is_auth = (user != None)
    len_msg = 0
    if user:
        messages = db.find_collection('information', {'receiver_id' : user['id'], 'type' : 0})
        comments = db.find_collection('comment', {'receiver_id' : user['email'], 'type' : 0})
        len_msg = len(messages) + len(comments)
    return template('about', len_msg = len_msg, user = user, is_authenticated = is_auth)

@get('/search')
@user_auth
def search_page(req):
    """ return search page """
    #get base element
    user = req['user'][0] if req['user'] else None
    is_auth = (user != None)
    len_msg = 0
    if user:
        messages = db.find_collection('information', {'receiver_id' : user['id'], 'type' : 0})
        comments = db.find_collection('comment', {'receiver_id' : user['email'], 'type' : 0})
        len_msg = len(messages) + len(comments)
    return template('search', user = user, len_msg = len_msg, is_authenticated = is_auth)


@post('/search')
@user_auth
def search_engine(req):
    """ search the database and retuen the values """
    #get search outcome

    '''
    search database and get the value just like
    'key' : mission(dict)
    '''
    key_word = request.forms.get('key_word')
    words_list = [item.text for item in mmseg.Algorithm(key_word)]
    words_list = list(set(words_list))
    words_dict = {}
    found = False
    for item in words_list:
        temp_item = db.find_collection('index', {'key' : item})
        if temp_item:
            words_dict[item] = temp_item[0]
            found = True
    '''
    now we need to calculate the mission's relatevity,and display them to browser;
    before that ,of course ,we need to do some operation to get the data we need
    '''
    start_time = time.time()
    if not found:
        return 'not found'
    else:
        score = {}
        position = {}
        missions = {}
        for item in words_dict.keys():
            for mis in words_dict[item]['mission']:
                mission = db.auto_dereference(mis)
                pos = words_dict[item]['position']
                relatevity = 0
                relatevity += 0.6 * len(words_dict[item]['position'][str(mission['id'])]['title']) + \
                        0.1 * len(words_dict[item]['position'][str(mission['id'])]['content'])
                
                style = mission['style']
                style = style.encode('utf-8') if isinstance(style, unicode) else style
                relatevity += 0.3 if style.find(item) != -1 else 0.0
                if score.has_key(str(mission['id'])): 
                    score[str(mission['id'])] += relatevity
                    for items in words_dict[item]['position'][str(mission['id'])]['content']:
                        position[str(mission['id'])]['content'].append(items)
                    for items in words_dict[item]['position'][str(mission['id'])]['title']:
                        position[str(mission['id'])]['title'].append(items)
                else:
                    missions[str(mission['id'])] = mission
                    position[str(mission['id'])] = {}
                    position[str(mission['id'])]['content'] = words_dict[item]['position'][str(mission['id'])]['content']
                    position[str(mission['id'])]['title'] = words_dict[item]['position'][str(mission['id'])]['title']
                    score[str(mission['id'])] = relatevity
        score = sorted(score.items(), lambda x,y:-cmp(x[1],y[1]))
        ret_dict = []
        end_time = time.time()
        for item,s in score:
            temp_dict = {}
            temp_dict['owner'] = missions[item]['owner_id']
            title_position = [pos for pos in position[item]['title'] if pos != []]
            temp_dict['title'] = html(missions[item]['title'], title_position)
            content_position = [pos for pos in position[item]['content'] if pos != []]
            temp_dict['content'] = html(missions[item]['introduction'], content_position)
            ret_dict.append(temp_dict)
        search_number = len(ret_dict)
        user = req['user'][0] if req['user'] else None
        is_auth = (user != None)
        return template('search_outcome', key = key_word, user = user, is_authenticated = is_auth, time = (end_time - start_time), number = search_number, outcome = ret_dict)

@route('/person_page')
@user_auth
def home_page(req):
    """ person page 
        
        home_page method will be decorated by decorator
        if authenticated ,then is_login will be true,else it will be false
        
        Args:
            person_nid: a string indicating the nid of a person
            is_login: a boolean type indicating whether the visitor has been authenticated or not

        Returns:
            None
    """
    #get the page's owner
    ID = request.query.ID
    user = db.find_collection('user', {'email' : ID})
    is_self = (user == req['user'] )
    is_authenticated = (req['user'] != None)
    ret_dict = {
        'page_owner' : user,
        'is_authenticated' : is_authenticated
    }
    if not user:
        return 'sorry no such user exsit !'
    else:
        #we get the profile of the person
        profile = db.auto_dereference(user[0]['profile'][0])
        """ now we need to build the model of recommandation system
            when we publish a mission ,we can get a index document,
            now we also need to build a datastructure just like this:
            {
                'key' : tag,
                'mission' : [],
                'weight' : [], #just like the tag in search method, we use a binary number with 3 bits.
                               #first bit 1 indicating its existing in tags
                               #second bit 1 indicating its existing in title
                               #thired of course indicating its existing in content
            }
        """
        if is_self:
            ''' if the visitor is himself or herself 
                we need to return the recommonded mission and message number to the page
            '''
            #get the recommonded missions
            index_outcome ,missions = [], {}
            score ,interests = {}, []
            
            for item in user[0]['interest']:  
                item = item.encode('utf-8')
                temp = mmseg.Algorithm(item)
                for items in temp:
                    interests.append(items.text)
            for item in interests:
                index_tag = {
                    'key' : '',
                    'mission' : '',
                    'weight' : [],
                    }
    
                find_ans = db.find_collection('index', {'key' : item})
                if find_ans:
                    index_tag['key'] = item
                    if isinstance(item, unicode):
                        item = item.encode('utf-8')
                    for mis in find_ans[0]['mission']:
                        weight = 0
                        mission = db.auto_dereference(mis)
                        missions[str(mission['id'])] = mission
                        if mission['style'].encode('utf-8').find(item) != -1:
                            weight += 8
                        weight += find_ans[0]['bit'][str(mission['id'])]
                        if score.has_key(str(mission['id'])):
                            score[str(mission['id'])] += weight / 10.0
                        else:
                            score[str(mission['id'])] = weight / 10.0
            
            recommond_outcome = []
            score = sorted(score.items(), lambda x,y:-cmp(x[1],y[1]))
            for item,s in score:
                missions[item]['comment_number'] = str(len(db.find_collection('comment', {'mission_id' : missions[item]['id']})))
                missions[item]['process'] = 'completed' if missions[item]['type'] == 1 else 'uncompleted'
                recommond_outcome.append(missions[item])
            #get the message number
            messages = db.find_collection('information', {'receiver_id' : user[0]['id'], 'type' : 0})
            comments = db.find_collection('comment', {'receiver_id' : user[0]['email'], 'type' : 0})
            len_msg = len(messages) + len(comments)
            return template('home', is_myself = is_self, user = user[0], profile = profile,len_msg = len_msg, visitor = user[0], outcome = recommond_outcome , is_authenticated = is_authenticated)
        
        #print recommond_outcome
        else:
            newest = []
            visitor = req['user'][0] if req['user'] else None
            len_msg = 0
            if visitor:
                messages = db.find_collection('information', {'receiver_id' : visitor['id'], 'type' : 0})
                comments = db.find_collection('comment', {'receiver_id' : visitor['email'], 'type' : 0})
                len_msg = len(messages) + len(comments)
            newest_mission = db.find_collection('mission', {'public' : 1, 'owner_id' : ID})[:10]
            for item in newest_mission:
                item['comment_number'] = str(len(item['comment']))
                newest.append(item)
            return template('home', is_myself = is_self, len_msg = len_msg, user = user[0], visitor = visitor, profile = profile, outcome = newest , is_authenticated = is_authenticated)


@route('/compute_mission' ,'POST')
def computer_mission():
    """ get the computer mission """
    com_title = request.forms.get('title')
    com_introduction = request.forms.get('introduction')
    com_file = request.files.files 
    file_type = request.forms.get('file_type') 
    is_public = request.forms.get('is_public')
    com_style = request.forms.get('style')
    ID = request.query.get('ID')
    
    user = db.find_collection('user', {'email' : ID})[0]
    file_style = {'python' : '.py', 'c' : '.c', 'c++' : '.cpp', 'cuda' : '.cu'}
    com_file_name = user['email'] + str(int(float(time.time()))) + com_file.filename
    file_path = str(os.getcwd()) + '/code/' + com_file_name
    file_o = open(file_path, 'w')
    file_o.write(com_file.file.read())
    file_o.close()

    index_m = db.find_collection('ids', {'name' : 'mission'})
    index = index_m[0]['ids'] + 1 if index_m else 1
    if index == 1:
        db.insert_collection('ids', {'name' : 'mission', 'ids' : 1})
    else:
        db.update_collection('ids', {'name' : 'mission'}, {'ids' : index})
    
    insert_dict = {
        'owner_id' : str(user['email']),
        'id'       : index,
        'title'    : com_title,
        'introduction' : com_introduction,
        'type'     : 0,
        'code'     : str(file_path),
        'style'    : com_style,
        'public'   : 1 if is_public else 0,
        'comment'  : [],
        }

    mis = db.insert_collection('mission', insert_dict)
    
    """
    now we need to send the mission information to backend
    """
    import simplejson
    insert_dict['file_name'] = com_file.filename
    insert_dict['file_style'] = file_type
    insert_dict['_id'] = str(insert_dict['_id'])
    # print tuple(simplejson.dumps(insert_dict))
    # print (insert_dict, 2)
    thread.start_new_thread(send_to_app_server, (simplejson.dumps(insert_dict), None))

    """
    following we will segment the title,content and tags,
    thus we can get a dict list with key indicating the key words and the value indicating
    the position that word begins and ends
    just like insert_list = [ {'key' : 'key1', 'position' : {'title' : (), 'content' : ()}, 'bit' : 5} ]
    """
    tags = [item for item in com_style.split(';') if item]
    insert_list = []
    for item in mmseg.Algorithm(com_title):
        insert_dic = {
            'key' : '',
            'bit' : 0,
            'position' : {}
        }
        insert_item = -1
        for it in range(0,len(insert_list)):
            insert_item = it if item.text == insert_list[it]['key'] else -1
            if insert_item != -1:
                break 
        if insert_item != -1:
            insert_list[insert_item]['position']['title'].append((item.start, item.end))
        else:
            insert_dic['key'] = item.text
            insert_dic['bit'] = 4 #100
            insert_dic['position']['title'] = []
            insert_dic['position']['content'] = []
            insert_dic['position']['title'].append((item.start, item.end))
            insert_list.append(insert_dic)

    for item in mmseg.Algorithm(com_introduction):
        insert_dic = {
            'key' : '',
            'bit' : 0,
            'position' : {}
        }
        insert_item = -1
        for it in range(0, len(insert_list)):
            insert_item = it if item.text == insert_list[it]['key'] else -1
            if insert_item != -1:
                break
        if insert_item != -1:
            insert_list[insert_item][u'position']['content'].append([item.start, item.end])
            insert_list[insert_item][u'bit'] = 6 # 110
        else:
            insert_dic['key'] = item.text
            insert_dic['bit'] = 2 #010
            insert_dic['position']['content'] = []
            insert_dic['position']['title'] = []
            insert_dic['position']['content'].append([item.start, item.end])
            insert_list.append(insert_dic)
    mission = db.find_collection('mission', {'_id' : mis})
    '''
    following codes will save the insert_list into index collection
    the definition of index will be found in mon_config.py
    '''
    mission_id = u''.join(str(mission[0]['id']))
    for item in insert_list:
        item_key = item['key']
        select_ans = db.find_collection('index', {'key' : item_key}) 
        if select_ans:
            missions = select_ans[0]['mission']
            positions = select_ans[0]['position'] 
            tags = select_ans[0]['bit']
            missions.append(bson.dbref.DBRef('mission', mission[0]['_id']))
            positions[mission_id] = item['position'] 
            tags[mission_id] = item['bit']
            db.update_collection('index', {'key' : item_key}, {u'mission' : missions, u'position' : positions, 'bit' : tags})
        else:
            insert_dict = {
                'key' : item['key'],
                'mission' : [ bson.dbref.DBRef('mission', mission[0]['_id'])],
                'position' : {mission_id : item['position']},
                'bit'   : {mission_id : item['bit']}
            }
            db.insert_collection('index', insert_dict)
    
    return 'yes you get it'

def send_to_app_server(dic, nothing):
    """ send mission information to app server to calculate

        Args:
            dic: a dict object indicating the information of the mission
        Return:
            None
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect(('127.0.0.1', 27800))
    while True:
        server_sock.send(dic)
        is_ok = server_sock.recv(512)
        if is_ok == 'True':
            break
    server_sock.close()

@post('/add_comment')
def add_comment():
    receiver_id = request.forms.get('receiver_id')
    mission_id = request.forms.get('mission_id')
    owner_id = request.forms.get('owner_id')
    send_id = request.forms.get('send_id')
    nimingfou = request.forms.get('nimingfou')
    style = 1 if nimingfou == 'checked' else 0
    content = request.forms.get('content')
    comment = db.find_collection('ids', {'name' : 'comment'})
    comment_cnt = comment[0]['ids'] + 1 if comment else 1
    if comment_cnt == 1:
        db.insert_collection('ids' , {'name' : 'comment', 'ids' : 1})
    else:
        db.update_collection('ids' , {'name' : 'comment'}, {'ids' : comment_cnt})
    insert_dict = {
            'sender_id' : send_id,
            'receiver_id' : receiver_id,
            'content' : content,
            'type' : 0,
            'style' : style,
            'mission_id' : int(mission_id),
            'owner_id' : owner_id,
            'id' : comment_cnt + 1,
            'time' : str(datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S'))
        }
    obj = (db.insert_collection('comment', insert_dict))
    
    mission = db.find_collection('mission', {'id' : int(mission_id)})
    comments = mission[0]['comment']
    comments.append(obj)
    ret_content = ""
    if receiver_id != '0':
        receiver = db.find_collection('user', {'email' : receiver_id})[0]
        receiver_name = db.auto_dereference(receiver['profile'][0])['name']
    ret_content += content
    # if sender is unkowned
     
    if send_id == '0':
        sender = "匿名用户"
    else:
        sender = db.find_collection('user', {'email' : send_id})[0]
        sender_name = db.auto_dereference(sender['profile'][0])['name']
    return_dict = {}
    return_dict['sender'] = sender_name
    return_dict['content'] = content
    return_dict['send_id'] = send_id
    return_dict['time'] = insert_dict['time']
    return_dict['img_url'] = '/static/img/avatar.png'
    
    import simplejson 
    return simplejson.dumps(return_dict)
@route('/mission_detail')
@user_auth
def mission_detail(req):
    """ get the mission and its comments """
    ID = request.query.get('ID')
    #print ID
    mission = db.find_collection('mission', {'id' : int(ID)})
    #print mission
    user = req['user'][0] if req['user'] else None
    is_auth = (user != None)
    #get comment and the one who make the comment
    comments = db.find_collection('comment', {'mission_id' : int(ID)})
    ret_comment = []
    for item in comments:
        sender = db.find_collection('user', {'email' : item['sender_id']})
        sender = sender[0] if sender else None
        if sender:
            item['img_url'] = '/static/img/avatar.png'
            sender_profile = db.auto_dereference(sender['profile'][0])
            if is_auth and sender == user:
                item['sender'] = sender_profile['name']
                item['sender_url'] = '/person_page?ID=' + sender['email']
            else:
                item['sender'] = sender_profile['name'] if item['style'] == 0 else '匿名用户'
                item['sender_url'] = '/person_page?ID=' + sender['email'] if item['style'] == 0 else '#'
            ret_comment.append(item)
    #get the mission's state
    state = {WAITING: 'waiting', COMPILING : 'compiling', RUNNING : 'running', COMPLETED : 'completed'}
    ret_state = {
        'mission_state' : '',
        'compile_infor' : '',
        'running_infor' : ''
    }
    ret_state['mission_state'] = state[mission[0]['type']]
    if mission[0]['type'] == COMPILING:
        compile_info = db.find_collection('compile_infor',{'mission_id' : mission[0]['id']})
        ret_infor = compile_info[0]['compile_content'].split('\n') if compile_info and compile_info[0]['success'] == 0 else None
        ret_state['compile_infor'] = ret_infor
    
    if mission[0]['type'] == COMPLETED:
        running_info = db.find_collection('running_infor', {'mission_id' : mission[0]['id']})
        ret_infor = running_info[0]['running_information']['value'].split('\n') if running_info else None        
        ret_state['running_infor'] = ret_infor
    visitor = db.find_collection('user', {'email' : mission[0]['owner_id']})[0]
    is_self = True if visitor and visitor == user else False
    print ret_state
    return template('mission_detail', ret_state = ret_state, is_self = is_self, is_authenticated = is_auth, user = user, comments = ret_comment, mission = mission[0])

@post('/delete_comment')
def delete_comment():
    ID = request.forms.get('ID')
    db.remove_collection('comment', {'id' : int(ID)})

@post('/ajax_recommond')
def return_recommond():
    page = int(request.forms.get('page'))
    mission = get_mission_by_condition({'public' : 1}, page)
    import simplejson

    return simplejson.dumps(mission)

@post('/ajax_com')
def return_complete():
    page = int(request.forms.get('page'))
    ID = request.forms.get('ID')
    mission = get_mission_by_condition({'owner_id' : ID, 'type' : 1}, page)
    #print mission
    import simplejson
    return simplejson.dumps(mission)

@post('/ajax_newest')
def return_newest():
    page = int(request.forms.get('page'))
    mission = get_mission_by_condition({'public' : 1}, page)
    import simplejson
    return simplejson.dumps(mission)

@post('/ajax_running')
def return_running():
    ID = request.forms.get('ID')
    page = int(request.forms.get('page'))
    mission = get_mission_by_condition({'owner_id' : ID, 'type' : 0}, page)
    import simplejson
    return simplejson.dumps(mission)

def get_mission_by_condition(dic, page):
    missions = db.find_collection('mission', dic)
    mission = []
    mission.append(len(missions[10 * page:10 * page + 10]))
    for item in missions[10 * page: 10 * page + 10]:
        temp = {}
        title = item['title'].encode('utf-8') if isinstance(item['title'], unicode) else item['title']
        content = item['introduction']
        temp['id'] = str(item['id'])
        temp['title'] = title
        temp['content'] = content[:100] 
        temp['comment_number'] = str(len(item['comment']))
        mission.append(temp)
    #print mission
    return mission

@post('/send_information')
@user_auth
def get_information(req):
    """ get information (or message) from a sender 
        after, redirect the url to the current page
    """
    content = request.forms.get('infor')
    ID = request.query.get('ID')
    public = request.forms.get('is_public')
    print public
    infor = db.find_collection('ids', {'name' : 'information'})
    infor_ids = infor[0]['ids'] + 1 if infor else 1
    insert_dict = {
        'sender_id' : 0 if not req['user'] else req['user'][0]['id'],
        'receiver_id' : int(ID),
        'content' : content,
        'time' : str(datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')),
        'style' : 0 if public == 'on' else 1,
        'type' : 0,
        'id' : infor_ids
        }

    if infor_ids == 1:
        db.insert_collection('ids', {'name' : 'information','ids' : 1})
    else:
        db.update_collection('ids', {'name' : 'information'}, {'ids' : infor_ids})
    db.insert_collection('information', insert_dict)
    return redirect('/person_page?ID=' + request.query.get('M'))

@route('/message_site')
@user_auth
def return_message(req):
    """ return the message of that user """
    user = req['user']
    if not user:
        return 'error occuried'
    else:
        messages = db.find_collection('information', {'receiver_id' : user[0]['id'], 'type' : 0})
        msg = []
        for item in messages:
            sender = db.find_collection('user', {'id' : item['sender_id']})
            sender_profile = db.auto_dereference(sender[0]['profile'][0])
            if user == sender:
                item['sender'] = sender_profile['name']
                item['sender_url'] = '/person_page?ID=' + user['email']
            else:
                item['sender'] = sender_profile['name'] if sender and item['style'] == 1 else None
                item['sender_url'] = '/person_page?ID=' + user[0]['email'] 
            item['sender_email'] = sender[0]['email'] if sender else None
            
            msg.append(item)

        return template('show_information', user = user[0], message = msg)

@post('/reply_msg')
def reply_msg():
    """ reply the message """
    Id = request.forms.get('id')
    sender_id = request.forms.get('sender_id')
    receiver_id = request.forms.get('receiver_id')
    content = request.forms.get('content').split(':')[2]
    infor = db.find_collection('ids', {'name' : 'information'})
    infor_ids = infor[0]['ids'] + 1 if infor else 1

    db.update_collection('information', {'id' : int(Id)}, {'type' : 1})

    insert_dict = {
            'sender_id' : int(sender_id),
            'receiver_id' : int(receiver_id),
            'content' : content,
            'time' : str(datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S')),
            'style' : 0,
            'type' : 0,
            'id' : infor_ids
        }
    if infor_ids == 1:
        db.insert_collection('ids', {'name' : 'information','ids' : 1})
    else:
        db.update_collection('ids', {'name' : 'information'}, {'ids' : infor_ids})
    db.insert_collection('information', insert_dict)

@post('/ignore_msg')
def ignore_msg():
    """ igonre message """
    ID = request.forms.get('ID')
    db.update_collection('information', {'id' : int(ID)}, {'type' : 1})

@post('/load_comment')
def load_comment():
    """ load comment """
    ID = request.forms.get('ID')
    comments = db.find_collection('comment', {'receiver_id' : ID, 'type' : 0})
    com = []
    com.append(len(comments))
    for item in comments:
        sender = db.find_collection('user', {'email' : item['sender_id']})
        mission = db.find_collection('mission', {'id' : int(item['mission_id'])})
        owner = db.find_collection('user', {'email' : item['owner_id']})

        sender_profile =  db.auto_dereference(sender[0]['profile'][0])
        
        item['sender'] = sender_profile['name'] if sender and item['style'] == 0 else '匿名用户'
        item['sender_url'] = '/person_page?ID=' + sender[0]['email'] if  sender and item['style'] == 0 else ''
        item['sender_email'] = sender[0]['email'] if sender else None
        item['owner'] = db.auto_dereference(owner[0]['profile'][0])['name']
        item['mission_title'] = mission[0]['title']
        item['_id'] = str(item['_id'])
        st = item['content'].split(':')
        if len(st) > 1:
            item['content'] = st[1]
        com.append(item)
    import simplejson
    return simplejson.dumps(com)


def check_login(func):
    st = request.get_cookie('visited', '0')
    if st:
        return func
    else:
        return 'no in'

@route('/check/')
@check_login
def check():
    name = request.get_cookie('visited', '0')
    st = request.get_cookie('counter','s')
    return 'visi %s'%name


run(host = 'localhost', port = 8080)
