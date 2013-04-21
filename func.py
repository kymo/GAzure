#encoding:utf-8
import smtplib
from email.Message import Message

from time import sleep

import threading

#email settings
HOST     = "smtp.gmail.com"
USER     = "kymowind@gmail.com"
PSWD     = "googlekymowind"
FROM     = USER
POSTFIX  = "gmail.com" 
class SendEmailThread(threading.Thread):
    """ send email thread class
        because send email need several seconds, so as a consideration of the user's experience
        user multi-thread to deal with the send email process
    """
    def __init__(self, send_to_email, send_content, send_title):
        threading.Thread.__init__(self)
        self.send_to_email = send_to_email
        self.send_content = send_content
        self.send_title = send_title
    
    def run(self):
        print self.send_mail(self.send_to_email, self.send_title, self.send_content)
        print 'ok'
    def send_mail(self, to_list, sub, content):
        """ send email method 
            send email to user for authenticating.
        
            Args:
                to_list: a str indicating the user's email address
                sub: a str indicating the title of this email
                content: a str indicating the content of this email
        
            Returns:
                True if send successful else False

            Raise:
                Exception unknown
        """ 
        message = Message()
        message['Subject'] = sub
        message['From'] = FROM
        message['To'] = to_list
        message.set_payload(content)
        try:
            s = smtplib.SMTP(HOST, port = 587, timeout = 20)
            s.starttls()
            s.login(USER, PSWD)
            s.sendmail(FROM, to_list, message.as_string())
            s.quit()
            return True
        except Exception, e:
            return False



def html(content, position):
    """ to make content to a html content which can be used in search page
        
        Args:
            content: a str indicating the content which is needed to change to html
            position: a list which contains the position

        Return:
            a html string
    """
    start = 0
    final_html = []
    if position == []:
        final_html.append(content)
        return final_html
    #print content
    content = content.encode('utf-8')
    position.sort(lambda x,y :cmp(x[0], y[0]))
    for location in position:
        normal_article = content[start:location[0]]
        red_article = content[location[0]: location[1]]
        start = location[1]
        final_html.append(normal_article)
        final_html.append(red_article)
    final_html.append(content[start : len(content)])
    return final_html
