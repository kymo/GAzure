
#encoding=utf-8
"""
application server to compute
get the client's file to compile and run and save the log file
author: kymo@whu
time: 2013-04-18
"""
import socket
import threading
import time
import os
import datetime
from func import SendEmailThread
from monkey import DBModel

#constant arguments
host = "127.0.0.1"
port = 28811
ADDR = (host, port)
BUFFER_SIZE = 1024
LISTEN_NUMBER = 10
QUEUE_SIZE = 32
COMPILE_SUCCESS = 0
COMPILING = 1
RUNNING = 2
COMPLETED = 3
#data structure
#compile queue and running queue


class Mission():
    """
    defined the mission which is under compiling
    """
    def __init__(self, mission_id, mission_file_path, mission_file_name, mission_file_style, mission_owner_id):
        self.mission_id = mission_id
        self.mission_file_path = mission_file_path
        self.mission_file_name = mission_file_name
        self.mission_file_style = mission_file_style
        self.mission_owner_id = mission_owner_id

class Queue():
    def __init__(self):
        self.queue = {}
        self.front = 0
        self.rear = 0

    def get_length(self):
        return (self.rear + QUEUE_SIZE - self.front + 1) % QUEUE_SIZE
    
    def push(self, mission):
        """ push a element into a queue
        
            Args:
                mission: a Mission object indicating a mission which will be inserted into the queue

            Return:
                True : if insertion is successful
                False: if insertion if failure.
        """
        #if it is full
        if (self.rear + 1) % QUEUE_SIZE == self.front:
            return False

        self.queue[str(self.rear)] = mission
        self.rear = (self.rear + 1) % QUEUE_SIZE
        return True

    def pop(self):
        """ pop a element from a queue
        Args:
            None
        Return:
            False: if pop is failure(empty)
            True: if pop is ok
        """
        if self.rear % QUEUE_SIZE == self.front:
            return False
        self.front = (self.front + 1) % QUEUE_SIZE
        
            
    def get_front(self):
        print 'front'
        """ get the front of the queue """  
        return self.queue[str(self.front)]

    def is_empty(self):
        """ is queue empty """
        return self.rear == self.front

#thread area 
#listen thread
#compile thread
#running thread


class ListenThread(threading.Thread):
    """
    listen thread:
    used to get the user's request
    and insert it into compile queue
    """
    def __init__(self, client_sock, client_ip, queue):
        threading.Thread.__init__(self)
        self.thread_over = False
        self.client_sock = client_sock
        self.client_ip = client_ip
        self.queue = queue
        
    def run(self):
        """
        thread method
        get the client connection, and get the mission data by json
        and then push it into the compile queue
        """
        ans = ""
        while True:
            data = self.client_sock.recv(BUFFER_SIZE)
            ans += data
            if len(data) < BUFFER_SIZE:
                break
        if ans:
            self.client_sock.send("True")
        import simplejson
        json = simplejson.loads(ans)
        mission = Mission(json['id'],json['code'], json['file_name'], json['file_style'], json['owner_id'])
        self.queue.push(mission)
        self.client_sock.close()

class CompileThread(threading.Thread):
    """
    compile thread which contains a compile queue
    """
    def __init__(self, queue, run_queue, database):
        threading.Thread.__init__(self)
        self.queue = queue
        self.run_queue = run_queue
        self.db = database
    
    def run(self):
        """
        compile thread method
        get the mission from compile queue and compile it
        if successful, then push it into running queue
        else, save the compile data into database
        """
        while True:
            while not self.queue.is_empty():
                compile_mission = self.queue.get_front()
                self.queue.pop()
                #change the state of the mission
                self.db.update_collection('mission', {'id' : int(compile_mission.mission_id)}, {'type' : COMPILING})
                print 'get a mission: ', compile_mission.mission_id
                compile_ok, compile_infor = self.compile(compile_mission)
                print compile_infor
                is_success = False
                if compile_ok == COMPILE_SUCCESS:
                    is_success = True
                    temp_str = compile_mission.mission_file_path.split('.')
                    out = '.'.join(temp_str[i] for i in range(0, len(temp_str) - 1))
                    running_mission = Mission(compile_mission.mission_id, out, compile_mission.mission_file_name, compile_mission.mission_file_style, compile_mission.mission_owner_id)
                    self.run_queue.push(running_mission)
                else:
                    subject = "任务编译失败，请登录查看信息"
                    content = "任务查看:http://127.0.0.1:8080/mission_detail?ID=" + str(compile_mission.mission_id)
                    send_email_thread = SendEmailThread(compile_mission.mission_owner_id, content, subject)
                    send_email_thread.start()
                    pass
                #save compile failed information
                self.save_compile_infor(is_success, compile_infor, compile_mission.mission_id)

    def save_compile_infor(self, is_success, compile_infor, mission_id):
        """
        save compile failed information into database
        Args:
            is_success: a boolean object indicating whether compile is successfully
            compile_infor: a str indicating compile information ,but it will be None if compile successfully
            mission_id: int indicating the id of the mission
        Return:
            None
        """
        index_c = self.db.find_collection('ids', {'name' : 'compile_infor'})
        index = index_c[0]['ids'] + 1 if index_c else 1
        insert_dict = {
            'id' : index,
            'mission_id' : int(mission_id),
            'compile_content' : compile_infor,
            'time' : str(datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S")),
            'success' : 1 if is_success else 0,
        }
        self.db.insert_collection('compile_infor', insert_dict)
        if index == 1:
            self.db.insert_collection('ids', {'name' : 'compile_infor', 'ids' : 1})
        else:
            self.db.update_collection('ids', {'name' : 'compile_infor'}, {'ids' : index})


    def compile(self, mission):
        """ 
        get a mission and begin to compile it by teminal command
        Args:
            mission: a Mission object indicating the detail of mission
        Return:
            True: if compiled successfully
            False: if compiled unsuccessfully
        """
        cmd = self.get_compile_cmd(mission.mission_file_path)
        import commands
        status, output = commands.getstatusoutput(cmd)
        return status, output
    def get_compile_cmd(self, file_path):
        """ 
        get compile command according to the file style
        garantee that the file' type is legal !
        Args:
            file_path: the file's path
        Return:
            cmd
        """
        temp_str = file_path.split('.')
        out = '.'.join(temp_str[i] for i in range(0, len(temp_str) - 1))
        file_type = temp_str[len(temp_str) - 1]
        cmd = {'c' : 'gcc ', 'cpp' : 'g++ ', 'cu' : 'nvcc '}
        command = cmd[file_type] + file_path + ' -o ' + out
        return command

class RunningThread(threading.Thread):
    """
    Running thread which contains a running queue
    """
    def __init__(self, queue, database):
        threading.Thread.__init__(self)
        self.queue = queue
        self.db = database

    def run(self):
        """
        running thread method
        get a mission from mission queue and run it
        and of course the outcome will be save into running_infor collection
        """
        while True:
            while not self.queue.is_empty():
                running_mission = self.queue.get_front()
                #update the mission type
                self.db.update_collection('mission', {'id' : int(running_mission.mission_id)}, {'type' : RUNNING})
                print 'get a mission from compile', running_mission.mission_id
                self.queue.pop()
                self.running(running_mission)

                self.db.update_collection('mission', {'id' : int(running_mission.mission_id)}, {'type' : COMPLETED})
                
                subject = "任务运行成功，请登录查看信息"
                content = "任务查看:http://127.0.0.1:8080/mission_detail?ID=" + str(running_mission.mission_id)
                send_email_thread = SendEmailThread(running_mission.mission_owner_id, content, subject)
                send_email_thread.start()
                """
                running mission
                """

    def running(self, mission):
        """
        run the compiled mission
        Args:
            mission: a Mission object indicating the mission that is going to be runned
        Return:
            None
        """
        cmd = mission.mission_file_path
        out_stream = os.popen(cmd)
        infor = out_stream.readlines()
        self.save_running_infor(''.join(item for item in infor), mission.mission_id)

    def save_running_infor(self, mission_infor, mission_id):
        """
        save running information into collection: runnning_infor
        Args:
            mission_infor : a str indicating the content after run the mission
            mission_id    : a str indicating the id of the mission
        Return:
            None
        """

        index_c = self.db.find_collection('ids', {'name' : 'compile_infor'})
        index = index_c[0]['ids'] + 1 if index_c else 1
        insert_dict = {
            'id' : index,
            'running_information': {'value' : mission_infor},
            'tag' : [],
            'mission_id' : int(mission_id),
            'time' : str(datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S")),
            'success' : 1
        }
        self.db.insert_collection('running_infor', insert_dict)
        if index == 1:
            self.db.insert_collection('ids', {'name' : 'compile_infor', 'ids' : 1})
        else:
            self.db.update_collection('ids', {'name' : 'compile_infor'}, {'ids' : index})
#update thread 
class UpdateThread(threading.Thread):
    
    def __init__(self, compile_queue, running_queue, ip):
        threading.Thread.__init__(self)
        self.compile_queue = compile_queue
        self.running_queue = running_queue
        self.ip = ip

    def run(self):
        """ update thread
        send gpu source to dispatch server every 5 seconds
        """
        while True:
            print 'begin to send gpu information'
            time.sleep(5);
            ADDRS = ("127.0.0.1", 27811)
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.connect(ADDRS)
            print 'connect ok'
            compiling_number = self.compile_queue.get_length()
            running_number = self.running_queue.get_length()
            gpu = 10 - compiling_number - running_number
            send_dict = {str(self.ip) : {'gpu' : gpu, 'compiling' : compiling_number, 'running_number' : running_number}}
            import simplejson
            json = simplejson.dumps(send_dict)
            server_sock.send(json)
            print json
            server_sock.close()
        pass

#main server constructe
class ComputingServer():  
    def __init__(self):
        #init compile queue and running queue
        self.compile_queue = Queue()
        self.running_queue = Queue()
        #link database
        self.db = DBModel('g_azure')
        self.db.link_database()
        self.ip = "127.0.0.1"
        #init compile thread and running  thread
        self.compile_thread = CompileThread(self.compile_queue, self.running_queue, self.db)
        self.running_thread = RunningThread(self.running_queue, self.db)
        self.update_thread = UpdateThread(self.compile_queue, self.running_queue, self.ip)
        self.server = None
    
    def server_start(self):
        """ start server """
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(ADDR)
        self.server.listen(LISTEN_NUMBER)
        try:
            while True:
                print 'waiting for connection'
                tcp_client_sock, addr = self.server.accept()
                print 'connection from :', addr
                listen_thread = ListenThread(tcp_client_sock, addr, self.compile_queue)
                listen_thread.start()
        except Exception, e:
            print e

    def run(self):
        """ run server
        start server engin and the handle thread for compile and run
        """
        self.running_thread.start()
        self.compile_thread.start()
        self.update_thread.start()
        self.server_start()


if __name__ == '__main__':
    azure_server = ComputingServer()
    azure_server.run()
