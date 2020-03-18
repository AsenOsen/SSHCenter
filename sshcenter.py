import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional
from typing import Dict
from typing import List
import paramiko
import argparse
import re
from multiprocessing import Pool
from termcolor import colored

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

class SSHUser:

	def __init__(self, commented, key_type, key, username):
		self.enabled = commented is None
		self.key_type = key_type
		self.key = key
		self.username = username

	def short_key(self):
		return self.key[0:10] + "..." + self.key[-10:]

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

	def parse_ssh_users(self, client):
		users = []
		for user in client.exec(" cat .ssh/authorized_keys").split("\n"):
			r = re.search(r"(#)?\s*([^\s]+)\s+([^\s]+)\s+(.*)", user)
			users.append(SSHUser(r.group(1),r.group(2),r.group(3),r.group(4)))
		return users

	def get_ssh_users_tuple(self, server_name):
		server = self.config.servers.get(server_name)
		ssh = SSHClient(server)
		users = self.parse_ssh_users(ssh)
		return (server_name, users)

	def conver_list_of_tuples_to_dict(self, list_of_tuples):
		d = {}
		for k,v in list_of_tuples: d[k] = v
		return d

	def build_user_map(self, server_names):
		pool = Pool(16)
		users = pool.map(self.get_ssh_users_tuple, server_names)
		pool.close()
		pool.join()
		return self.conver_list_of_tuples_to_dict(users)

	def list_users(self, server_names, enabled_only):
		users = self.build_user_map(server_names)
		for server_name, users in users.items():
			print(colored("===== " + server_name + " =====", "green"))
			if enabled_only:
				users = filter(lambda user: user.enabled, users)
			for user in users:
				print(user)

	def search_user(self, server_names, username, userkey, enabled_only):
		users = self.build_user_map(server_names)
		for server_name, users in users.items():
			if enabled_only:
				users = filter(lambda user: user.enabled, users)
			if username:
				users = filter(lambda user: user.username.find(username) > -1, users)
			if userkey:
				users = filter(lambda user: user.key.find(userkey) > -1, users)
			for user in users:
				print(colored(server_name, "green") + " | " + user.username + " : " + user.short_key())


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

class Cli:

	def __init__(self):
		parser = argparse.ArgumentParser(description='SSH Access Center')
		parser.add_argument('--config','-c', action="store", default="config.json", help='Config file (default: config.json)')
		parser.add_argument('--group','-g', action="store_true", help='Group name')
		parser.add_argument('name', help='Server or group name')
		subparsers = parser.add_subparsers(dest="command", help='Commands')
		# list
		list_parser = subparsers.add_parser('list', help='List users')
		list_parser.add_argument('--enabled','-e', action="store_true", help='Enabled only users')
		# search
		search_parser = subparsers.add_parser('search', help='Search user')
		search_parser.add_argument('--user','-u', help='User name')
		search_parser.add_argument('--key','-k', help='Key part')
		search_parser.add_argument('--enabled','-e', action="store_true", help='Enabled only users')
		# add
		add_parser = subparsers.add_parser('add', help='Add user')
		add_parser.add_argument('publickey', help='Public key of user')
		add_parser.add_argument('username', help='Name of user')
		# del
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

	def is_search(self):
		return self.args.command == "search"

# Logic

cli = Cli()

# parse config
with open(cli.args.config) as data:
	config = Config.from_json(data.read())
	# merge default values
	for server in config.servers:
		for k,v in config.default.__dict__.items():
			if config.servers[server].__dict__[k] is None:
				config.servers[server].__dict__[k] = v

ssh_center = SSHCenter(config)
server_names = ssh_center.get_server_names(cli.args.name, cli.args.group)

if cli.is_list():
	ssh_center.list_users(server_names, cli.args.enabled)
elif cli.is_search():
	ssh_center.search_user(server_names, cli.args.user, cli.args.key, cli.args.enabled)