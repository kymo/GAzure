#encoding: utf-8
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import urllib2
import thread
import datetime
import socket
register_openers()


ADDR = ("127.0.0.1", 29000)
missions_ok, missions_no = 0,0
missions_total = 800
start_time, end_time = 0,0

def feedback(first, second):
    """ thread method """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen(10)
    while True:
        tcp_client, addr = server.accept()
        global missions_ok, missions_no
        ans = tcp_client.recv(1024)
        if ans == "OK":
            missions_ok += 1
        else:
            missions_no += 1
        if missions_ok + missions_no == missons_total:
            global end_time
            end_time = datetime.datetime.now()
            print end_time
            print missions_ok, missons_no
            break
dic = {
    'title' : '机器学习的应用算法',
    'introduction' : '这个算法不错哦，真的不错哦',
    'files' : open('pso.cu', 'rb'),
    'file_type' : 'c',
    'style' : '机器学习',
    'is_public' : 'checked',
}


datagen, headers = multipart_encode(dic)
request = urllib2.Request("http://127.0.0.1:8080/compute_mission?ID=412062385@qq.com", datagen, headers)
#get start  time
#start listen server to get the completed mission
thread.start_new_thread(feedback, (None, None))
start_time = datetime.datetime.now()
for i in range(0, 1000):
    urllib2.urlopen(request).read()



