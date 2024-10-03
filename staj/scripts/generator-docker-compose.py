import yaml
import os

os.makedirs('../msmtprc', exist_ok=True)

# Define the file path
env_file = '.localenv'

# If the file already exists, remove it
if os.path.exists(env_file):
    os.remove(env_file)


# def generate_msmtprc_config(num_employees):
#     for i in range(num_employees):
#         msmtp_config_file = f'./msmtprc/msmtprc_employee_{i+1}'  # File path inside the directory
#         # Read the template file
#         with open('./msmtprc/msmtprc_template', 'r') as template:
#             config_data = template.read().replace('employee@localhost', f'employee_{i+1}@localhost')
        
#         # Write the config file for each employee
#         with open(msmtp_config_file, 'w') as config_file:
#             config_file.write(config_data)


def generate_docker_compose(num_web_servers, num_clients, num_dmz, squid_proxy_enabled, num_employees):
    services = {}
    networks = {}


    # Services

    # Add load balancer to the services
    services['load_balancer'] = {
        'image': 'nginx:1.21.3',
        'container_name': 'load_balancer',
        'ports': ['80:80'],
        'volumes': ['./nginx.conf:/etc/nginx/nginx.conf'],
        'networks': ['dmz_1'],
        'depends_on': [f'web{idx+1}' for idx in range(num_web_servers)]
    }

    # MySQL
    services['db_server'] = {
        'image': 'mysql:5.7',
        'container_name': 'db_server',
        'environment': {'MYSQL_ROOT_PASSWORD':'rootpassword','MYSQL_DATABASE':'corporate_db'},
        'networks':['internal_network']
    }

    # ElasticSearch
    services['elasticsearch'] = {
        'image': 'docker.elastic.co/elasticsearch/elasticsearch:7.10.2',
        'container_name': 'elasticsearch',
        'environment':{
            'discovery.type=single-node',
            'ES_JAVA_OPTS=-Xms1g -Xmx1g'},
        'ports': ['9200:9200'],
        'networks':['logging']
    }

    # logstash
    services['logstash'] = {
	'image': 'docker.elastic.co/logstash/logstash:7.10.2',
	'container_name': 'logstash',
	'volumes': [
    		'./logstash.conf:/usr/share/logstash/pipeline/logstash.conf',
    		'/var/log/mail.log:/var/log/mail.log'  # Assuming mail logs are stored here
	],
	'ports': ['5044:5044'],
	'networks': ['logging']
    }
    # kibana
    services['kibana'] = {
    'image': 'docker.elastic.co/kibana/kibana:7.10.2',
    'container_name': 'kibana',
    'ports':['5601:5601'],
    'networks':['logging']
    }

    # prometheus
    services['prometheus'] = {
        'image': 'prom/prometheus:v2.29.1',
        'container_name':'prometheus',
        'volumes': ['./prometheus.yml:/etc/prometheus/prometheus.yml'],
        'ports':['9090:9090'],
        'networks':['monitoring']
    }

    #grafana
    services['grafana'] = {
        'image': 'grafana/grafana:8.1.2',
        'container_name': 'grafana',
        'ports':['3000:3000'],
        'networks':['monitoring']
    }

    # Add SMTP (mail) server
    services['mail_server'] = {
        'image': 'mailserver/docker-mailserver:latest',
        'container_name': 'mail_server',
        'hostname' : 'mail',
        'domainname': 'localdomain.test',
        'environment': {
            'PERMIT_DOCKER' : 'network',
            'ENABLE_SPAMASSASSIN' : '0',
            'ENABLE_CLAMAV' : '0',
            'SSL_TYPE' : ""
        },
        'volumes': [
            './docker-data/dms/mail-data/:/var/mail/', 
            './docker-data/dms/mail-state/:/var/mail-state/', 
            './docker-data/dms/mail-logs/:/var/log/mail/',
            './docker-data/dms/config/:/tmp/docker-mailserver/',
            '/etc/localtime:/etc/localtime:ro'],
        'ports' : ['25:25'],
        'networks': ['internal_network']
    }

    # Add FTP server
    services['ftp_server'] = {
        'image': 'fauria/vsftpd',  # FTP server image
        'container_name': 'ftp_server',
        'ports': ['21:21', '21000-21010:21000-21010'],
        'networks': ['internal_network'],
        'environment': {
            'FTP_USER': 'employee',
            'FTP_PASS': 'password',
            'PASV_ADDRESS': '127.0.0.1',
            'PASV_MIN_PORT': '21000',
            'PASV_MAX_PORT': '21010'
        }
    }

    # Add Squid proxy if enabled
    if squid_proxy_enabled:
        services['squid_proxy'] = {
            'build' : {
                'context': '.',
                'dockerfile': 'Dockerfile.squid'
            },
            'container_name': 'squid_proxy',
            'ports': ['3128:3128'],
            'networks': [f'dmz_{i+1}' for i in range(num_dmz)] + ['internal_network'],
        }


    # Add web servers 
    for i in range(num_web_servers):
        services[f'web{i+1}'] = {
            'image': 'nginx:1.21.3',
            'container_name': f'web{i+1}',
            'networks': [f'dmz_{(i % num_dmz) + 1}'], 
        }

    # Add web clients
    for i in range(num_clients):
        services[f'client_machine{i+1}'] = {
            'image': 'alpine:3.14',
            'container_name': f'client_machine{i+1}',
            'networks': [f'dmz_{(i % num_dmz) + 1}'],  # Distribute to DMZs
            'command': 'tail -f /dev/null'
        }

    with open(env_file, 'w') as file:
            file.write(f"EMPLOYEES=")
            # file.write("MAIL_SERVER=mail.localdomain.test\n")
            
        for i in range(num_employees):
            # generate_msmtprc_config(num_employees)
            # Open a new .localenv file and write fresh content
            file.write(f"employee_{i},")
            services[f'employee_{i+1}'] = {
            'image': 'alpine:3.14',
            'container_name': f'employee_{i+1}',
            'networks': ['internal_network'],
            'volumes': [
                f'./msmtprc/msmtprc_employee_{i+1}:/root/.msmtprc'  # Mount the specific config file
            ],
            'command': 'sh -c "apk update && apk add --no-cache mailx msmtp && rm /usr/sbin/sendmail && ln -s /usr/bin/msmtp /usr/sbin/sendmail && tail -f /dev/null"'
            # sh -c "apk update && apk add --no-cache mailx msmtp && ln -s /usr/bin/msmtp /usr/sbin/sendmail && tail -f /dev/null"'
            }
        file.write(f"\n")
        file.write("MAIL_SERVER=mail.localdomain.test\n")

    # Add a single internal network
    networks['internal_network'] = {
        'driver': 'bridge',
        'ipam': {
            'config': [{'subnet':'192.168.192.0/20'}]
        }
    }

    networks['logging'] = {
        'driver': 'bridge', 
        'ipam': {
            'config': [{'subnet':'192.168.3.0/24'}]
        }
    }
    networks['monitoring'] = {
        'driver': 'bridge', 
        'ipam': {
            'config': [{'subnet':'192.168.4.0/24'}]
        }
    }

    # Add DMZs
    for i in range(num_dmz):
        networks[f'dmz_{i+1}'] = {
            'driver': 'bridge',
            'ipam': {
                'config': [{'subnet': f'192.168.{i+100}.0/24'}]
            }
        }

    # Create the docker-compose dictionary structure
    docker_compose = {
        'version': '3.8',
        'services': services,
        'networks': networks
    }

    # Write the generated compose file
    with open('docker-compose.yml', 'w') as file:
        yaml.dump(docker_compose, file, default_flow_style=False)


# Example usage:
if __name__ == "__main__":
    num_web_servers = int(input("Enter the number of web servers: "))
    num_clients = int(input("Enter the number of client machines: "))
    num_dmz = int(input("Enter the number of DMZ zones: "))
    squid_proxy_enabled = input("Enable Squid Proxy? (yes/no): ").lower() == 'yes'
    num_employees = int(input("Enter the number of employees: "))

    generate_docker_compose(num_web_servers, num_clients, num_dmz, squid_proxy_enabled, num_employees)
    print("Docker Compose file generated successfully.")
