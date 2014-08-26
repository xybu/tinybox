#!/usr/bin/env python3

'''
tinybox.py

A simple cgroup wrapper written in Python
'''

import os
import sys
import subprocess
import configparser

current_pid = str(os.getpid())
current_uid = str(os.getuid())
current_gid = str(os.getgid())
current_user = os.environ['USER']

TINYBOX_PREFIX = 'tbox'

cgroup_config = configparser.ConfigParser()

shell_script = []

def log(msg):
	print(msg, file = sys.stderr)

def print_usage():
	print('Usage: tinybox [-h] [-p path] [-c path] [-c.<control>.<key>=<val>] -- cmd [args]')
	print(' -h, --help			Display this help information')
	print(' -p, --path			Specify the cgroup path')
	print(' -c, --cgconf			Load cgroup limits from the given file path')
	print(' -c.<control>.<key>=<val>	Add cgroup limit <control>.<key>=<val>')
	print(' --				Separate tinybox args with command to run')
	print(' cmd [args]			The command to execute inside tinybox')
	print('')
	print('The cgroup conf file should be a file with ini format like ')
	print('[cpu]\n shares = 500\n[memory]\n limit_in_bytes = 1M\n')

def add_cgcreate_cmd(controllers, path, t_user = current_user, a_user = current_user):
	shell_script.append('cgcreate -g ' + ','.join(controllers) + ':' + path)

def add_cgset_cmd(controllers, path, config):
	args = []
	for c in controllers:
		for k in config[c]:
			args = args + ['-r', c + '.' + k + '=' + str(config[c][k])]
	shell_script.append('cgset ' + ' '.join(args) + ' ' + path)

def add_cgexec_cmd(controllers, path, cmd):
	if cmd == None or cmd == '' or len(cmd) == 0: return
	shell_script.append('cgexec -g ' + ','.join(controllers) + ':' + path + ' --sticky ' + ' '.join(cmd))

def add_cgdelete_cmd(controllers, path):
	shell_script.append('cgdelete -r -g ' + ','.join(controllers) + ':' + path + '')

def run_shell_script(script, stdin = None):
	script = '\n'.join(shell_script) + '\n'
	print(script)
	subp = subprocess.Popen(script, shell = True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	oe = subp.communicate(bytes(stdin, 'utf-8'))
	ret = subp.wait()
	print('ret: ' + str(ret))
	print('stdout:\n' + oe[0].decode('utf-8'))
	print('stderr:\n' + oe[1].decode('utf-8'))

def main():
	i = 1
	argc = len(sys.argv)
	
	cgroup_path = TINYBOX_PREFIX + '/task_' + current_pid
	while i < argc:
		arg = sys.argv[i]
		if arg in ['-h', '--help']:
			print_usage()
			sys.exit(0)
		elif arg in ['-p', '--path']:
			i = i + 1
			if i >= argc:
				log('tinybox: Argument "-p" must be followed by a value.')
				exit(1)
			else:
				cgroup_path = sys.argv[i]
		elif arg == '-c':
			i = i + 1
			if i >= argc:
				log('tinybox: Argument "-c" must be followed by a value.')
				exit(1)			
			elif not os.path.isfile(sys.argv[i]):
				log('The path "' + sys.argv[i] + '" is not a file. Skipped.')
			else:
				try:
					cgroup_config.read(sys.argv[i])
				except OSError as e:
					log('An error occurred loading the cgroup conf file.')
					log('OSError ' + e.errno + ': ' + e.strerror)
		elif arg.startswith('-c.'):
			kv_tokens = arg[3:].split('=')
			ck_tokens = kv_tokens[0].split('.')
			if len(kv_tokens) != 2 or len(ck_tokens) != 2:
				log('Argument "' + arg + '" is not a valid cgroup param.')
			else:
				cgroup_config[ck_tokens[0]][ck_tokens[1]] = kv_tokens[1]
		elif arg == '--':
			i = i + 1	
			break
		else:
			log('Unknown argument "' + arg + '".')
			sys.exit(1)
		
		i = i + 1
	
	cmd = sys.argv[i:]
	controllers = cgroup_config.sections()
	
	if len(controllers) == 0:
		log('No cgroup limit set. Why do you use tinybox?')
		sys.exit(1)
	
	add_cgcreate_cmd(controllers, cgroup_path)
	add_cgset_cmd(controllers, cgroup_path, cgroup_config)
	
	add_cgexec_cmd(controllers, cgroup_path, cmd)
	add_cgexec_cmd(controllers, cgroup_path, ['pwd'])
	add_cgexec_cmd(controllers, cgroup_path, ['ls', '-asl'])
	add_cgexec_cmd(controllers, cgroup_path, ['cat'])
	
	add_cgdelete_cmd(controllers, cgroup_path)
	
	run_shell_script(shell_script, stdin = 'hi')
	

if __name__ == '__main__':
	main()
