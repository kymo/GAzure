#encoding:utf-8
import smtplib
from email.mime.text import MIMEText
import threading
#email settings
HOST     = "smtp.qq.com"
USER     = "412062385"
PSWD     = "kymowind19910101"
POSTFIX  = "qq.com" 



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
        self.send_mail(self.send_to_email, self.send_title, self.send_content)

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
        me = sub + "<" + USER + "@" + POSTFIX + ">" 
        msg = MIMEText(content)
        msg['Subject'] = me
        msg['To'] = to_list
        try:
            s = smtplib.SMTP()
            s.connect(HOST)
            s.login(USER, PSWD)
            s.sendmail(me, to_list, msg.as_string())
            s.close()
            return True
        except Exception, e:
            return False
