#encoding:utf-8
import socket
import threading

host = "127.0.0.1"
port = 27800
#addr for dispatch server
ADDR = (host, port)
LISTEN_NUMBER = 10
BUFFER_SIZE = 1024

locks = False
source_list = {}

class ListenThread(threading.Thread):
    
    def __init__(self, tcp_sock, addr):
        threading.Thread.__init__(self)
        self.tcp_sock = tcp_sock
        self.addr = addr

    def run(self):
        """thread method
        get the client connection ,and get the mission information data by json
        and then send it to gpu server
        """
        print 'listen thread start'
        ans = ""
        while True:
            data = self.tcp_sock.recv(BUFFER_SIZE)
            ans += data
            if len(data) < BUFFER_SIZE:
                break
        if ans:
            self.tcp_sock.send("True")
        print ans
        send_mission_thread = SendMissionThread(ans)
        send_mission_thread.start()
        self.tcp_sock.close()

class GetMissionThread(threading.Thread):
    """ communication_web thread """
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = None
    
    def run(self):
        print 'get mission thread start'
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(ADDR)
        self.server.listen(LISTEN_NUMBER)
        try:
            while True:
                tcp_client_sock, addr = self.server.accept()
                listen_thread = ListenThread(tcp_client_sock, addr)
                listen_thread.start()
        except Exception,e:
            print e
class SendMissionThread(threading.Thread):
    """ send mission thread
    get the gpu server's addr by searching the source list
    """
    def __init__(self, mission):
        threading.Thread.__init__(self)
        self.mission = mission
    
    def get_source_server(self):
        """ get source server 
            because the source list is a common shared resource, so we need to synchronize it 
        """
        #if the resource is locked ,then waiting
        global locks
        while locks:
            pass
        locks = True
        gpu_number, cur_key = 0, "127.0.0.1"
        for item in source_list.keys():
            if source_list[item]['gpu'] > gpu_number:
                cur_key, gpu_number = item, source_list[item]['gpu']
            elif source_list[item]['gpu'] == gpu_number:
                if source_list[item]['running'] > source_list[cur_key]['running']:
                   cur_key = item
        locks = False
        return (cur_key, 28811)

    def run(self):
        print 'send mission thread start'
        ADDRS = self.get_source_server()
        print ADDRS
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.connect(ADDRS)
        server_sock.send(self.mission)
        server_sock.close()

class GetSourceStateThread(threading.Thread):
    """ communication_gpu thread """

    def __init__(self):
        threading.Thread.__init__(self)
        self.server = None
        pass

    def run(self):
        print 'get source thread start'
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("127.0.0.1", 27811))
        self.server.listen(LISTEN_NUMBER)
        try:
            while True:
                tcp_client, addr = self.server.accept()
                print addr
                update_thread = UpdateSourceThread(tcp_client)
                update_thread.start()
        except Exception, e:
            print e


class UpdateSourceThread(threading.Thread):
    """ update source thread
        need to lock the resource first
    """
    def __init__(self, tcp_sock):
        threading.Thread.__init__(self)
        self.tcp_sock = tcp_sock

    def run(self):
        ans = ""
        while True:
            ans += self.tcp_sock.recv(BUFFER_SIZE)
            if len(ans) < BUFFER_SIZE:
                break
        import simplejson
        json = simplejson.loads(ans)
        key = json.keys()[0]
        global locks
        global source_list
        while locks:
            pass
        locks = True
        source_list[key] = json[key]
        locks = False
        print source_list

class DispatchServer():
    """ dispatch server """
    def __init__(self):
        self.server = None
        self.source_list = {}
        
    def server_start(self):
        """start server 
            It will open two threads:
            communication_com(get_mission_thread)
            communication_gpu(get_source_state_thread)
        """
        print 'server start'
        get_mission_thread = GetMissionThread()
        get_source_state_thread = GetSourceStateThread()
        get_mission_thread.start()
        get_source_state_thread.start()

if __name__ == "__main__":
    print locks
    dispatch_server = DispatchServer()
    dispatch_server.server_start()
