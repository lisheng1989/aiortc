#-*- coding: utf-8 -*-

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os

class EchoHTTPHandler(BaseHTTPRequestHandler):    
   
    
    def StartServer(self,roomid):
        print(os.path.dirname(os.path.abspath(__file__)))
        strProcess = 'sh dostart.sh '+ str(roomid)
        print(strProcess)
        p = subprocess.Popen(strProcess, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)   
        print(p.stdout.readlines())   
        for line in p.stdout.readlines():   
            print(line,)   
        retval = p.wait()

    def StopServer(self):
        print(os.path.dirname(os.path.abspath(__file__)))
        p = subprocess.Popen('sh dostop.sh', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)   
        print(p.stdout.readlines())   
        for line in p.stdout.readlines():   
            print(line,)   
        retval = p.wait()
    def rtcClient(self):
        print(self.path)
        if(self.path !="/rtcclient"):
            return
        content_len = int(self.headers['Content-Length'])   
        post_body = self.rfile.read(content_len)
        data = json.loads(post_body)
        if(data['action'] is not None):
            str = data['action']
            if(str=='start'):
                id = data['room']
                print(id)
                self.StartServer(id)
            else:
                self.StopServer()
        #parsed_path = urlparse(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({
            'method': self.command,
            'path': self.path,
            'request_version': self.request_version,
            'protocol_version': self.protocol_version,
            'body': data
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
    server = HTTPServer((ip, port), EchoHTTPHandler)
    server.serve_forever()
