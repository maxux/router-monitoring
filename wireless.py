import subprocess
import sys
import time
import os

class Colors():
	def __init__(self):
		self.red    = '\033[1;31m'
		self.green  = '\033[1;32m'
		self.yellow = '\033[1;33m'
		self.blue   = '\033[1;34m'
		self.pink   = '\033[1;35m'
		self.cyan   = '\033[1;36m'
		self.white  = '\033[1;37m'
		self.clear  = '\033[0m'

class WirelessMonitor():
	def __init__(self, interface="wlan0"):
		self.interface = interface
		self.clients = {}
		self.colors = Colors()
	
	"""
	Source
	"""
	def readSource(self):
		output = []

		proc = subprocess.Popen(['iw', 'dev', self.interface, 'station', 'dump'], stdout=subprocess.PIPE)
		for input in proc.stdout:
			output.append(input.decode('utf-8').rstrip())
		
		return output
	
	def readArp(self):
		output = []

		proc = subprocess.Popen(['ip', 'n'], stdout=subprocess.PIPE)
		for input in proc.stdout:
			output.append(input.decode('utf-8').rstrip())
		
		return output
	
	def setAddresses(self):
		arp = self.readArp()
		table = {}
		
		for line in arp:
			words = line.split(" ")
			
			if len(words) != 6:
				continue
			
			table[words[4]] = words[0]

		for bssid in self.clients:
			if bssid in table:
				self.clients[bssid]["ip"] = table[bssid]
			
			else:
				self.clients[bssid]["ip"] = None
		
	def update(self):
		self.clients = {}
		
		source = self.readSource()
		current = {}
		
		for line in source:
			# ignore empty lines
			if line == "":
				continue
			
			# new station
			if line.startswith("Station"):
				words = line.split(" ")
				
				self.clients[words[1]] = {"bssid": words[1]}
				current = self.clients[words[1]]
				continue
			
			words = [x.strip() for x in line.split(':')]
			current[words[0]] = words[1]
	
		# grabbing ip address from arp cache
		if len(self.clients) > 0:
			self.setAddresses()

	"""
	Formatter
	"""
	def _getSize(self, size):
		sizes = ["KB", "MB", "GB", "TB", "PB"]
		newsize = float(size) / 1000
		
		index = 0
		while newsize > 1000:
			index += 1
			newsize /= 1000

		unit = sizes[index]
		
		return "%.2f %s" % (newsize, unit)
	
	def _colorizeSignal(self, client):
		c = self.colors
		sig = float(client["signal"].split(' ')[0])
		
		if sig < -80:
			return c.red + client["signal"] + c.clear
		
		if sig < -70:
			return c.yellow + client["signal"] + c.clear
		
		if sig < -55:
			return c.blue + client["signal"] + c.clear
		
		return c.green + client["signal"] + c.clear
		
	def _colorizeStation(self, client):
		c = self.colors
		idle = float(client["inactive time"].split(' ')[0])
		
		if idle > 120000:
			color = c.yellow
		
		elif idle > 45000:
			color = c.blue
		
		elif client["authorized"]:
			color = c.green

		else:
			c.red
		
		return color + client["bssid"] + c.clear
		
	def _colorizeAddress(self, client):
		c = self.colors

		if client["ip"]:
			return c.green + ("%-15s" % client["ip"]) + c.clear
		
		return c.blue + ("%-15s" % "(unknown)") + c.clear
	
	"""
	Displayer
	"""
	def initialize(self):
		sys.stdout.write("\033[2J\033[H")
		sys.stdout.write("\033[?25l")
		self.rows, self.columns = os.popen('stty size', 'r').read().split()
	
	def reset(self):
		sys.stdout.write("\033[?25h\n")

	def refresh(self):
		sys.stdout.write("\033[H")
		print(" Station          | IP Address      | RX Data   | TX Data   | Signal")
		print("------------------+-----------------+-----------+-----------+----------")
		
		index = 2
		for client in self.clients:
			client = self.clients[client]
			
			sys.stdout.write(self._colorizeStation(client))
			sys.stdout.write(" | ")
			
			sys.stdout.write(self._colorizeAddress(client))
			sys.stdout.write(" | ")
			
			
			sys.stdout.write("%-9s | " % self._getSize(client['rx bytes']))
			sys.stdout.write("%-9s | " % self._getSize(client['tx bytes']))
			
			sys.stdout.write(self._colorizeSignal(client))
			
			# end of line
			sys.stdout.write("\033K\n")
			index += 1
			
			if index == int(self.rows) - 1:
				print("[+ %d more]" % len(self.clients) - index + 2)
				break
		
		# clearing old lines
		while index < int(self.rows) - 1:
			sys.stdout.write("\033[K\n")
			index += 1

wlz = WirelessMonitor()
wlz.initialize()

runid = 0

while True:
	if (runid % 20) == 0:
		wlz.initialize()

	try:
		wlz.update()
		wlz.refresh()
	
		time.sleep(1)

	except KeyboardInterrupt:
		wlz.reset()
		sys.exit(0)
	
	runid += 1
