import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional
from typing import Dict
from typing import List
import paramiko
import argparse
import re

@dataclass_json
@dataclass
class Server:
	host: Optional[str] = None
	user: Optional[str] = None
	keyfile: Optional[str] = None
	password: Optional[str] = None
	
@dataclass_json
@dataclass
class Config:
	default: Server
	servers: Dict[str, Server]
	groups: Dict[str, List[str]]

# Domain

class Cli:

	def __init__(self):
		parser = argparse.ArgumentParser(description='SSH Access Center')
		parser.add_argument('--config','-c', action="store", default="config.json", help='Config file (default: config.json)')
		parser.add_argument('--group','-g', action="store_true", help='Group name')
		parser.add_argument('name', help='Server or group name')
		subparsers = parser.add_subparsers(dest="command", help='Commands')
		list_parser = subparsers.add_parser('list', help='List users')
		list_parser.add_argument('--enabled','-e', action="store_true", help='Enabled only users')
		add_parser = subparsers.add_parser('add', help='Add user')
		add_parser.add_argument('publickey', help='Public key of user')
		add_parser.add_argument('username', help='Name of user')
		del_parser = subparsers.add_parser('del', help='Delete user')
		del_parser.add_argument('username', help='Name of user')
		# todo
		# rename parser
		# search_user parser
		self.args = parser.parse_args()
		self.validate()

	def validate(self):
		if not self.args.command:
			print("Specify command")
			quit()

	def is_list(self):
		return self.args.command == "list"

	def get_name(self):
		return self.args.name

	def get_group(self):
		return self.args.group

	def get_list_enabled_only(self):
		return self.args.enabled

	def get_config_file(self):
		return self.args.config

class SSHUser:

	def __init__(self, commented, key_type, key, username):
		self.enabled = commented is None
		self.key_type = key_type
		self.key = key
		self.username = username

	def __str__(self):
		valid = "+" if self.enabled else "-"
		return "User: %s (%s)" % (self.username, valid)


class SSHCenter:

	def __init__(self, config):
		self.config = config

	def get_server_names(self, name, group):
		if group and name in self.config.groups:
			return self.config.groups[name] 
		if not group and name in self.config.servers:
			return [name]
		return []

	def collect_server_by_names(self, server_names):
		return dict([(name,self.config.servers.get(name)) for name in server_names])

	def parse_ssh_users(self, client):
		users = []
		for user in client.exec(" cat .ssh/authorized_keys").split("\n"):
			r = re.search(r"(#)?\s*([^\s]+)\s+([^\s]+)\s+(.*)", user)
			users.append(SSHUser(r.group(1),r.group(2),r.group(3),r.group(4)))
		return users

	def list_users(self, server_names, enabled_only):
		servers = self.collect_server_by_names(server_names)
		for server in servers:
			print("===== Server: " + server + " =====")
			ssh = SSHClient(servers[server])
			users = self.parse_ssh_users(ssh)

			if enabled_only:
				users = filter(lambda user: user.enabled, users)

			for user in users:
				print(user)

class SSHClient:

	def __init__(self, server):
		self.server = server 

	def ssh_obtain_key(self):
		if self.server.keyfile:
			if self.server.password:
				return paramiko.RSAKey.from_private_key_file(self.server.keyfile, self.server.password)
			else:
				try:
					return paramiko.RSAKey.from_private_key_file(self.server.keyfile)
				except:
					return paramiko.RSAKey.from_private_key_file(self.server.keyfile, self.ssh_obtain_password())
		else:
			return None

	def ssh_obtain_password(self):
		if self.server.password:
			return self.server.password
		else:
			return input("Password:")

	def ssh_get_client(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		key = self.ssh_obtain_key()
		if key:
			client.connect(hostname = self.server.host, username = self.server.user, pkey = key)
		else:
			password = self.ssh_obtain_password()
			client.connect(hostname = self.server.host, username = self.server.user, password = password)
		return client

	def exec(self, cmd):
		client = self.ssh_get_client()
		stdin , stdout, stderr = client.exec_command(cmd)
		output = stdout.read().strip()
		errors = stderr.read().strip()
		if len(errors)>0:
			print(errors)
		client.close()
		return output.decode("utf-8")

# Logic

cli = Cli()

# parse config
with open(cli.get_config_file()) as data:
	config = Config.from_json(data.read())
	# merge default values
	for server in config.servers:
		for k,v in config.default.__dict__.items():
			if config.servers[server].__dict__[k] is None:
				config.servers[server].__dict__[k] = v

ssh_center = SSHCenter(config)
server_names = ssh_center.get_server_names(cli.get_name(), cli.get_group());

if cli.is_list():
	ssh_center.list_users(server_names, cli.get_list_enabled_only())