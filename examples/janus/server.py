#-*- coding: utf-8 -*-

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os

class EchoHTTPHandler(BaseHTTPRequestHandler):    
    def text_to_html(self, req_head):
        r""" 将请求头包装成 html，便于返回给 http 客户端 """
        html = '<html><head><title>Echo HTTP Header</title></head>' 
        html += '<body><div>'
        html += '<font color="blue">%s - %s - %s</font><br/><br/>'
        html = html % (self.client_address, self.request_version, self.path)
        for line in req_head.split('\n'):
            line = line.strip()
            if line.startswith('Via:') or line.startswith('X-Forwarded-For:'):
                line = '<font color="red">%s</font><br/>' % line
            else:
                line = '<font color="black">%s</font><br/>' % line
            html += line
        html += '</div></body></html>'

        return html
    def StartServer(self,roomid):
        print(os.path.dirname(os.path.abspath(__file__)))
        p = subprocess.Popen('sh dostart.sh 1234', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)   
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

    def do_GET(self):
        r""" 响应 get 请求，打印 http 头，并返回给 http 客户端 """
        print('%s - %s - %s' % (self.client_address, self.request_version, self.path))
        print(type(self.client_address))
        print('### request headers ###')
        req_head = str(self.headers)
        print('req_head: %s' % req_head)
        for line in req_head.split('\n'):
            line = line.strip()
            if line.startswith('Via:') or line.startswith('X-Forwarded-For:'):
                line = '%s%s%s' % (fg('red'), line, attr('reset'))
            print(line)
        self.send_response(200)
        self.end_headers()

        '''
        可选返回 text，html
        '''
        text = '%s - %s - %s\n---\n%s' % (self.client_address, 
                                            self.request_version, 
                                            self.path, 
                                            req_head)
        text = text.encode('utf8')
        html = self.text_to_html(req_head).encode('utf8')

        self.wfile.write(text)
        self.StartServer(1234)

    def do_POST(self):
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
