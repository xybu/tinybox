all:
	
mbox:
	wget http://pdos.csail.mit.edu/mbox/mbox-latest-amd64.deb
	sudo dpkg -i mbox-latest-amd64.deb
	rm mbox-latest-amd64.deb