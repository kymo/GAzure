from bottle import route, get, post, run, template, request, response, redirect, view, template
from monkey import DBModel
from bottle import static_file
import md5
import os
import time, datetime
from beaker.middleware import SessionMiddleware
from func import SendEmailThread
#link the database 
db = DBModel('g_azure')
db.link_database()
#rsa token
TOKEN = 2113

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
    insert_dict = {
        'name'           :'',
        'email'          : user_email,
        'profile'        : None,
        'password'       : md5.new(user_passwd).hexdigest(),
        'type'           : 0,
        'mission'        : []
        }
    if db.insert_collection('user', insert_dict): 
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
def authenticate():
    """ authenticate the user """
    token = request.query.token
    ID = request.query.ID
    find_dict = {'email' : ID}
    find_out = db.find_collection('user', find_dict)
    if find_out and find_out[0]['password'] == token:
        db.update_collection('user',{'email' : ID},{'type' : 1})
        return "congratulations ,you have been authenticated please go to login, <a href = '/login'>login </a>"
    else:
        return "failed,sorry"


@route('/login','GET')
def login_page():
    """ redirect to the page needed to login 
        deal with request which has method : GET
    """
    return template('login_start')

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
    if find_out and find_out[0]['password'] == new_pass:
        if is_cookie_allowed:
            response.set_cookie('azure_email_token', name, TOKEN)
            response.set_cookie('azure_password_token', password, TOKEN)
            response.set_cookie('azure_time_stamp', str(time.time()), TOKEN)
        person_page_url = '/person_page?ID=' + name
        return redirect(person_page_url)
    else:
        return 'login failed ! please try again'
    response.set_cookie('visited', 'yes')
    return 'nice sdfdf'



@route('/')
@user_auth
def index(req):
    """ index page method

        Args:
            name: a string indicating the  name of url

        Returns:
            None
    """
    print req['user']
    return 'this is the index page'


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
    is_authenticated = (user == req['user'])
    ret_dict = {
        'page_owner' : user,
        'is_authenticated' : is_authenticated
    }
    if not user:
        return 'sorry no such user exsit !'
    else:
        return template('home', user = user[0], is_authenticated = is_authenticated)


@route('/compute_mission' ,'POST')
def computer_mission():
    """ get the computer mission """
    com_title = request.forms.get('title')
    com_introduction = request.forms.get('introduction')
    com_file = request.files.files 
    file_type = request.forms.get('file_type') 
    is_public = request.forms.get('is_public')
    compute_style = request.forms.get('style')
    ID = request.query.get('ID')

    user = db.find_collection('user', {'email' : ID})[0]
    file_style = {'python' : '.py', 'c' : '.c', 'c++' : '.cpp', 'cuda' : '.cu'}
    com_file_name = user['email'] + str(datetime.datetime.now()) + file_style[file_type]
    print com_file_name
    print os.getcwd()
    print type(com_file)
    file_path = str(os.getcwd()) + '/code/' + com_file_name
    file_o = open(file_path, 'w')
    file_o.write(com_file.file.read())
    file_o.close()
    print type(user['_id'])
    insert_dict = {
        'owner_id' : str(user['email']),
        'title'    : com_title,
        'introduction' : com_introduction,
        'type'     : 0,
        'code'     : str(file_path),
        'style'    : compute_style,
        'public'   : 1 if is_public else 0,
        }
    print insert_dict
    mis = db.insert_collection('mission', insert_dict)
    if mis:
        print 'yes you are'
    else:
        print 'sorry'
    
    if com_file:
        print 'es'
    else:
        print 'no'
    print type(com_file)
    return 'yes you get it'

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
    print st
    return 'visi %s'%name


run(host = 'localhost', port = 8080)
