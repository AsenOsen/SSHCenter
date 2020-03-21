#!/usr/bin/env python3

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

	def get(config):
		config = Config.from_json(config)
		# merge default values
		for server in config.servers:
			for k,v in config.default.__dict__.items():
				if config.servers[server].__dict__[k] is None:
					config.servers[server].__dict__[k] = v
		return config

# Domain

class SSHUser:

	def __init__(self, commented, key_type, key, username):
		self.enabled = commented
		self.key_type = key_type
		self.key = key
		self.username = username

	def __str__(self):
		valid = colored("[+]", "green") if self.enabled else colored("[X]", "red")
		short_key = self.key[0:10] + "..." + self.key[-10:]
		return "%sUser: %s (%s)" % (valid, self.username, short_key)


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
		for user in client.exec(" cat ~/.ssh/authorized_keys").split("\n"):
			r = re.search(r"(#)?\s*([^\s]+)\s+([^\s]+)\s+(.*)", user)
			users.append(SSHUser(r.group(1) is None,r.group(2),r.group(3),r.group(4)))
		return users

	def store_ssh_users(self, client, users):
		authorized_keys_contents = ""
		for user in users:
			commented = "#" if not user.enabled else ""
			authorized_keys_contents += "%s%s %s %s\n" % (commented, user.key_type, user.key, user.username)
		original_authorized_keys_contents = client.exec(" cat ~/.ssh/authorized_keys")
		client.exec(" echo \"%s\" > ~/.ssh/authorized_keys" % (authorized_keys_contents))
		if not client.test():
			client.exec(" echo \"%s\" > ~/.ssh/authorized_keys" % (original_authorized_keys_contents))

	def store_ssh_users_tuple(self, server_name_users_tuple):
		server_name = server_name_users_tuple[0]
		users = server_name_users_tuple[1]
		server = self.config.servers.get(server_name)
		ssh = SSHClient(server, server_name)
		self.store_ssh_users(ssh, users)

	def get_ssh_users_tuple(self, server_name):
		server = self.config.servers.get(server_name)
		ssh = SSHClient(server, server_name)
		users = self.parse_ssh_users(ssh)
		return (server_name, users)

	def convert_list_of_tuples_to_dict(self, list_of_tuples):
		d = {}
		for k,v in list_of_tuples: d[k] = v
		return d

	def get_users_dict(self, server_names):
		pool = Pool(16)
		users = pool.map(self.get_ssh_users_tuple, server_names)
		pool.close()
		pool.join()
		return self.convert_list_of_tuples_to_dict(users)

	def store_users_dict(self, users):
		pool = Pool(16)
		users = pool.map(self.store_ssh_users_tuple, users.items())
		pool.close()
		pool.join()

	def list_users(self, server_names, enabled_only):
		users = self.get_users_dict(server_names)
		for server_name, users in users.items():
			print(colored("===== " + server_name + " =====", "yellow"))
			if enabled_only:
				users = filter(lambda user: user.enabled, users)
			for user in users:
				print(user)

	def search_user(self, server_names, username, userkey, enabled_only):
		users = self.get_users_dict(server_names)
		for server_name, users in users.items():
			if enabled_only:
				users = filter(lambda user: user.enabled, users)
			if username:
				users = filter(lambda user: user.username.find(username) > -1, users)
			if userkey:
				users = filter(lambda user: user.key.find(userkey) > -1, users)
			for user in users:
				print(colored(server_name, "yellow") + " | " + str(user))

	def add_user(self, server_names, publickey, username, keytype):
		users = self.get_users_dict(server_names)
		new_user = SSHUser(True, keytype, publickey, username)
		for server_name, server_users in users.items():
			users[server_name] = server_users + [new_user]
		self.store_users_dict(users)

	def del_user(self, server_names, username):
		users = self.get_users_dict(server_names)
		for server_name, server_users in users.items():
			for user in server_users:
				if user.username == username:
					server_users.remove(user)
		self.store_users_dict(users)


class SSHClient:

	def __init__(self, server, name):
		self.server = server 
		self.name = name
		self.client = None

	def __del__(self):
		if self.client:
			self.client.close()

	def ssh_obtain_key(self):
		if self.server.keyfile:
			if self.server.password:
				return paramiko.RSAKey.from_private_key_file(self.server.keyfile, self.server.password)
			else:
				try:
					return paramiko.RSAKey.from_private_key_file(self.server.keyfile)
				except:
					return None
		else:
			return None

	def ssh_get_client(self):
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		key = self.ssh_obtain_key()
		password = self.server.password
		if key:
			client.connect(hostname = self.server.host, username = self.server.user, pkey = key)
		elif password:
			client.connect(hostname = self.server.host, username = self.server.user, password = password)
		else:
			raise Exception("Authentification failed for server: " + self.name)
		return client

	def exec(self, cmd):
		if not self.client:
			self.client = self.ssh_get_client()
		stdin , stdout, stderr = self.client.exec_command(cmd)
		output = stdout.read().strip()
		errors = stderr.read().strip()
		if len(errors)>0:
			print(errors)
		return output.decode("utf-8")

	def test(self):
		try:
			self.ssh_get_client()
			return True
		except:
			return False

class Cli:

	def __init__(self):
		parser = argparse.ArgumentParser(description='SSH Users Center')
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
		add_parser.add_argument('--keytype','-t', action="store", default="ssh-rsa", help='Type of publickey (default: ssh-rsa)')
		# del
		del_parser = subparsers.add_parser('del', help='Delete user')
		del_parser.add_argument('username', help='Name of user')
		self.args = parser.parse_args()
		self.validate()

	def validate(self):
		if not self.args.command:
			quit("Specify command")

	def is_list(self):
		return self.args.command == "list"

	def is_search(self):
		return self.args.command == "search"

	def is_add(self):
		return self.args.command == "add"

	def is_del(self):
		return self.args.command == "del"

# EntryPoint

if __name__ == "__main__":

	cli = Cli()

	# parse config
	with open(cli.args.config) as data: 
		config = Config.get(data.read())

	# ssh
	ssh_center = SSHCenter(config)
	server_names = ssh_center.get_server_names(cli.args.name, cli.args.group)

	# command selector
	if cli.is_list():
		ssh_center.list_users(server_names, cli.args.enabled)
	elif cli.is_search():
		ssh_center.search_user(server_names, cli.args.user, cli.args.key, cli.args.enabled)
	elif cli.is_add():
		ssh_center.add_user(server_names, cli.args.publickey, cli.args.username, cli.args.keytype)
	elif cli.is_del():
		ssh_center.del_user(server_names, cli.args.username)