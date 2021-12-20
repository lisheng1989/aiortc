import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver  import ThreadingMixIn 
import json
import subprocess
import os


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer): 
    pass 

class SlowHandler(BaseHTTPRequestHandler): 
    def StartServer(self,roomid):
        print(os.path.dirname(os.path.abspath(__file__)))
        strProcess = 'sh dostart.sh '+ str(roomid)
        print(strProcess)
        p = subprocess.Popen(strProcess, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)   
        print(p.stdout.readlines())   
        for line in p.stdout.readlines():   
            print(line,)   
        retval = p.wait()
        print("start end")

    def StopServer(self):
        print(os.path.dirname(os.path.abspath(__file__)))
        print("stop start")
        p = subprocess.Popen('sh dostop.sh', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)   
        print(p.stdout.readlines())   
        for line in p.stdout.readlines():   
            print(line,)   
        retval = p.wait()
        print("stop end")

    def GetStatus(self):
        print('getstatus')
        p = subprocess.Popen('ps -ef | grep janus.py | grep -v "grep" | awk "{print $2}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #print(p.stdout.readlines())   
        room = 0
        for line in p.stdout.readlines():   
            print(line,)
            contents = str(line).split(" ")
            i=0
            for cs in  contents:
                i +=1
                if(cs=='--room'):
                    room=int(contents[i])
                    print(room)
        retval = p.wait()
        print("get status end")
        if(room<=0):
            return False,room
        else:
            return True,room
    
    def rtcClient(self):
        print(self.path)
        api=self.path
        data={}
        if self.path.find('?') != -1:
            reqUrl = self.path.split('?',1)[1]
            api = self.path.split('?',1)[0]
            parameters = reqUrl.split('&')
            for i in parameters:
                key,val = i.split('=',1)
                data[key] =val

        print("api",api)
        if(api !="/rtcclient"):
            return
        #if(self.headers['Content-Length'] is not None):
        #    content_len = int(self.headers['Content-Length'])
        #    if content_len != 0:   
        #        post_body = self.rfile.read(content_len)
        #        data = json.loads(post_body)
        bRet = True
        room = 0
        if(data['action'] is not None):
            str = data['action']
            if(str=='start'):
                room= data['room']
                print(room)
                self.StartServer(room)
            elif(str=='stop'):
                self.StopServer()
            elif(str=='getstatus'):
                bRet,room=self.GetStatus()


        #parsed_path = urlparse(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
           "status":bRet,
           "room":room
        }).encode())

    def do_GET(self):
        print('Get %s - %s - %s' % (self.client_address, self.request_version, self.path))
        print(type(self.client_address))
        self.rtcClient()

    def do_POST(self):
        print('Post %s - %s - %s' % (self.client_address, self.request_version, self.path))
        print(type(self.client_address))
        self.rtcClient()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Echo HTTP server.')
    parser.add_argument('-a', '--address', help='default: 0.0.0.0')
    parser.add_argument('-p', '--port', help='default: 5678', type=int)
    args = parser.parse_args()
    ip = args.address or '0.0.0.0'
    port = args.port or 8080
    print('Listening %s:%d' % (ip, port))
    server = ThreadedHTTPServer((ip, port), SlowHandler)
    server.serve_forever()