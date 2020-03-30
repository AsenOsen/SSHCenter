### What is it?

This is a simple SSH users management tool which able to do following operations over described servers:

* list SSH users
* search over SSH users
* add SSH users
* delete SSH users

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
		"all": [".*"],
		"local": ["local"]
	}
}
```

### Examples

List all descibed users on server `remote`:

```
python3 sshcenter.py remote list
```

Search user `Rookie` whoose public key has `*pub_key*` substring on each server in group `all` (all servers: `local` and `remote`):

```
python3 sshcenter.py -g all search -u Rookie -k pub_key
```

Add user public key `AAAAB3Nza...CtBYmxQ9Nb` of user `Rookie@Gmail.com` to each server in group `local`:

```
python3 sshcenter.py -g local add Rookie@Gmail.com AAAAB3Nza...CtBYmxQ9Nb
```

Delele user `Rookie@Gmail.com` from `local` server:

```
python3 sshcenter.py local del Rookie@Gmail.com
```