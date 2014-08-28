#!/usr/bin/env python3

'''
tinybox.py

A simple cgroup wrapper written in Python
'''

import os
import sys
import shlex
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
	print('Usage: tinybox [-h] [-p path] [-c path] [-c.<control>.<key>=<val>] [-r user] [-t sec] -- cmd [args]')
	print(' -h, --help			Display this help information')
	print(' -p, --path			Specify the cgroup path')
	print(' -c, --cgconf			Load cgroup limits from the given file path')
	print(' -c.<control>.<key>=<val>	Add cgroup limit <control>.<key>=<val>')
	print(' -r, --run-as			Run the command as the specified user')
	print(' -t, --timeout			Kill the cmd to run after the specified seconds')
	print(' --				Separate tinybox args with command to run')
	print(' cmd [args]			The command to execute inside tinybox')
	print('')
	print('The cgroup conf file should be a file with ini format like ')
	print('[cpu]\n shares = 500\n[memory]\n limit_in_bytes = 1M\n')

def cgroup_create(controllers, path, t_user = current_user, a_user = current_user):
	cmd = ['cgcreate', '-t', t_user + ':root', '-a', a_user + ':' + a_user, '-g', ','.join(controllers) + ':' + path]
	execute_cmd(cmd)
	# shell_script.append(' '.join(cmd))

def cgroup_set(controllers, path, config):
	args = []
	for c in controllers:
		for k in config[c]:
			args = args + ['-r', c + '.' + k + '=' + str(config[c][k])]
	args = ['cgset'] + args + [path]
	execute_cmd(args)
	# shell_script.append('cgset ' + ' '.join(args) + ' ' + path)

def cgroup_exec(controllers, path, cmd, runas = None, timeout = None):
	if cmd == None or cmd == '' or len(cmd) == 0: return
	# if timeout > 0: cmd = 'timeout --signal=9 ' + str(timeout) + ' sh -c ' + shlex.quote(cmd)
	if runas != None: cmd = ['su', runas, '--preserve-environment', '-c', shlex.quote(' '.join(cmd))]
	cmd = 'cgexec -g ' + ','.join(controllers) + ':' + path + ' --sticky ' + ' '.join(cmd)
	execute_cmd(cmd, shell = True, timeout = timeout)
	#shell_script.append(cmd)

def cgroup_delete(controllers, path):
	execute_cmd(['cgdelete', '-r', '-g', ','.join(controllers) + ':' + path + ''])

def execute_cmd(cmd, shell = False, timeout = None):
	if timeout == 0: timeout = None
	try:
		subprocess.call(cmd, shell = shell, timeout = timeout)
	except subprocess.TimeoutExpired:
		log('Execution timeout.')

def main():
	i = 1
	argc = len(sys.argv)
	
	cgroup_path = TINYBOX_PREFIX + '/task_' + current_pid
	runas_username = current_user
	timeout = None
	
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
				if ck_tokens[0] not in cgroup_config:
					cgroup_config.add_section(ck_tokens[0])
				cgroup_config[ck_tokens[0]][ck_tokens[1]] = kv_tokens[1]
		elif arg in ['-t', '--timeout']:
			i = i + 1
			try:
				timeout = int(sys.argv[i])
				if 'cpuacct' not in cgroup_config:
					cgroup_config.add_section('cpuacct')
			except (ValueError, IndexError) as e:
				log('Argument "-t" should be followed by an interger.')
				exit(1)
		elif arg in ['-r', '--run-as']:
			i = i + 1
			try: runas_username = sys.argv[i]
			except:
				log('Argument "-t" should be followed by an interger.')
				exit(1)
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
	
	cgroup_create(controllers, cgroup_path, t_user = runas_username, a_user = runas_username)
	cgroup_set(controllers, cgroup_path, cgroup_config)
	cgroup_exec(controllers, cgroup_path, cmd, runas_username, timeout)
	cgroup_delete(controllers, cgroup_path)

if __name__ == '__main__':
	main()
