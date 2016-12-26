import sys
import urlparse
import re
import argparse

class Service:

    def __init__(self, service_name, url):
        self.service_name = service_name
        self.url = url
        parsed_url = urlparse.urlparse(url)
        self.scheme = parsed_url.scheme
        self.hostname = parsed_url.hostname
        self.container_name =  re.sub(r"[^\w]", '_', self.hostname)
        self.port = parsed_url.port
        if self.port is None:
            self.port = "80"

def gen_container_entry(container_name, service_list, record):
    print("""
    %s:
        image: parallel_wiremock
        command: > 
            parallel -vv --arg-sep=_x_ _x_""" % container_name)
    for service in service_list:
        record_string = ""
        if record:
            record_string = " --record-mappings --proxy-all %s://%s:%s" % (service.scheme, service.hostname, service.port)
        
        port_option = '--port'
        if 'https' in service.scheme:
            port_option = '--https-port'

        print("            'bash /docker-entrypoint.sh --root-dir %s %s %s%s'" % 
        (service.service_name, port_option, service.port, record_string))

    print("""        depends_on:
            - parallel_wiremock
        volumes:
            - '.:/home/wiremock'
        expose:""")
    
    for service in service_list:
        print("            - %s" % service.port)


def gen_links(services):
    print("        links:")
    for container_name in services:
        service_list = services[container_name]
        print("            - %s:%s" % (container_name,service_list[0].hostname))

    print("        depends_on:")
    for container_name in services:
        print("            - %s" % (container_name))

def gen_mocks(services, record):
    for container_name in services:
        service_list = services[container_name]
        gen_container_entry(container_name, service_list, record)

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

def parse_services(services_file):
    services = {}
    with open(services_file) as f:
        for line in f:
            if ('|' in line) and not line.strip().startswith('#'):
                parts = line.strip().split('|')
                service = Service(parts[0].strip(), parts[1].strip())
                if service.container_name not in services:
                    services[service.container_name] = [service]
                else:
                    services_list = services[service.container_name]
                    services_list.append(service)
    return services


def main(args):
    
    parser = argparse.ArgumentParser(prog='wiremockcomposegen',
                                     usage='%(prog)s [options]', description='a generate for wiremock docker compose files')
    parser.add_argument('-f', '--services-file', required=True ,nargs='?', help='the path to the service list file')
    parser.add_argument('-t', '--template-file', required=True ,nargs='?', help='the template file to use that contains the #<links> and #<mocks>')
    parser.add_argument('-r', '--record', action='store_true', required=False, help='start wiremock in record mode')
    parsed_args = parser.parse_args()

    services = parse_services(parsed_args.services_file)


    with open(parsed_args.template_file) as f:
        for line in f:
            if '#<links>' in line:
                gen_links(services)
            elif '#<mocks>' in line:
                gen_mocks(services, parsed_args.record)
            else:
                sys.stdout.write(line)

if __name__ == "__main__":
    main(sys.argv)
