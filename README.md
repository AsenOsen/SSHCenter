### What is it?

This is a simple SSH key management tool which able to do the following operations over described servers:

* list users
* add users
* delete users

### How it works?

It is total CLI:

```
usage: sshcenter.py [-h] [--config CONFIG] [--group] name {list,add,del} ...

SSH Access Center

positional arguments:
  name                  Server or group name
  {list,add,del}        Commands
    list                List users
    add                 Add user
    del                 Delete user

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Config file (default: config.json)
  --group, -g           Group name
```

### Config format

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
