import sys
import urlparse
import re

class Service:

    def __init__(self, service_name, url):
        self.service_name = service_name
        
        parsed_url = urlparse.urlparse(url)
        self.hostname = parsed_url.hostname
        self.container_name =  re.sub(r"[^\w]", '_', self.hostname)
        self.port = parsed_url.port
        if self.port is None:
            self.port = "80"

def gen_container_entry(container_name, service_list):
    print("""
    %s:
        image: parallel_wiremock
        command: > 
            parallel -vv --arg-sep=_x_ _x_""" % container_name)
    for service in service_list:
        print("            'bash /docker-entrypoint.sh --record-mappings --root-dir %s --port %s --proxy-all http://%s:%s'" % 
        (service.service_name, service.port, service.hostname, service.port))

    print("""        depends_on:
            - parallel_wiremock
        volumes:
            - '.:/home/wiremock'
        expose:""")
    
    for service in service_list:
        print("            - %s" % service.port)


def main(args):
    
    if len(args) < 2:
        print('need services file as argument')
        exit(1)

    services_file = sys.argv[1]

    services = {}

    with open(services_file) as f:
        for line in f:
            parts = line.strip().split('|')
            service = Service(parts[0].strip(), parts[1].strip())
            if service.container_name not in services:
                services[service.container_name] = [service]
            else:
                services_list = services[service.container_name]
                services_list.append(service)

    print("        links:")
    for container_name in services:
        service_list = services[container_name]
        print("            - %s:%s" % (container_name,service_list[0].hostname))

    print("        depends_on:")
    for container_name in services:
        print("            - %s" % (container_name))


    for container_name in services:
        service_list = services[container_name]
        gen_container_entry(container_name, service_list)

    print("")

    print("""
    parallel_wiremock:
        build:
            context: .
            dockerfile: Dockerfile.wiremock
        image: parallel_wiremock
        user: "${UID}:${GID}"
        command: echo x
""")

if __name__ == "__main__":
    main(sys.argv)

