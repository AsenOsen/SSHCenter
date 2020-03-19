### What is it?

This is a simple SSH users management tool which able to do following operations over described servers:

* list SSH users
* search over SSH users
* add SSH users
* delete SSH users (todo)

All SSH operations performed by the user you log in. 
This tool parses `~/.ssh/authorized_keys` and operates its contents due to selected operation.

### How it works?

It is total CLI:

```
usage: sshcenter.py [-h] [--config CONFIG] [--group]
                    name {list,search,add,del} ...

SSH Users Center

positional arguments:
  name                  Server or group name
  {list,search,add,del}
                        Commands
    list                List users
    search              Search user
    add                 Add user
    del                 Delete user

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Config file (default: config.json)
  --group, -g           Group name

```

### Servers description format (config.json)

```
{
	"default" : {
		"keyfile": "",
		"password": "",
		"user": ""
	},

	"servers": {
		"local": {
			"host": "127.0.0.1"
		},
		"remote": {
			"host": "8.8.8.8"
		}
	},

	"groups": {
		"all": ["local", "remote"],
		"local": ["local"]
	}
}
```

### Examples

List all descibed users on server `my_server_1`:

```
python3 sshcenter.py my_server_1 list
```

Search user `rookie` whoose public key has `*pub_key*` substring on each server in group `my_group_1`:

```
python3 sshcenter.py -g my_group_1 search -u rookie -k pub_key
```

Add user public key `AAAAB3Nza...CtBYmxQ9Nb` of user `Rookie@Gmail.com` to each server in group `local`:

```
python3 sshcenter.py -g local add Rookie@Gmail.com AAAAB3Nza...CtBYmxQ9Nb
```