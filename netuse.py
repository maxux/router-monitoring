import subprocess
import operator
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

class Monitoring():
	def __init__(self):
		self.colors  = Colors()
		self.rows    = 0
		self.columns = 0
		self.index   = 0
	
	def initialize(self):
		sys.stdout.write("\033[2J\033[H")
		sys.stdout.write("\033[?25l")
		self.rows, self.columns = os.popen('stty size', 'r').read().split()
		
		self.rows = int(self.rows)
		self.columns = int(self.columns)
	
	def new(self):
		# new run
		self.index = 0
		
		# clean screen
		sys.stdout.write("\033[H")
	
	def separe(self):
		sys.stdout.write("\033[K\n")
		self.index += 1
	
	def clean(self):
		# clean rest of the screen
		while self.index < int(self.rows) - 1:
			sys.stdout.write("\033[K\n")
			index += 1
		
	def reset(self):
		sys.stdout.write("\033[?25h\n")
	
class WirelessMonitor():
	def __init__(self, console, interfaces=["wlan0"]):
		self.interfaces = interfaces
		self.console = console
		self.clients = {}
		self.colors = Colors()
	
	"""
	Source
	"""
	def readSource(self, interface):
		output = []

		proc = subprocess.Popen(['iw', 'dev', interface, 'station', 'dump'], stdout=subprocess.PIPE)
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
		
	def _update(self, interface):
		source = self.readSource(interface)
		current = {}
		
		for line in source:
			# ignore empty lines
			if line == "":
				continue
			
			# new station
			if line.startswith("Station"):
				words = line.split(" ")
				
				self.clients[words[1]] = {
					"bssid": words[1],
					"interface": interface
				}
				
				current = self.clients[words[1]]
				continue
			
			words = [x.strip() for x in line.split(':')]
			current[words[0]] = words[1]
	
		# grabbing ip address from arp cache
		if len(self.clients) > 0:
			self.setAddresses()
	
	def update(self):
		self.clients = {}
		
		for intf in self.interfaces:
			self._update(intf)

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
		tmp = client["signal"].split(' ')
		sig = float(tmp[0])
		
		fmt = "%s %s%s" % (tmp[0], tmp[-1], c.clear)
		
		if sig < -80:
			return c.red + fmt
		
		if sig < -70:
			return c.yellow + fmt
		
		if sig < -55:
			return c.blue + fmt
		
		return c.green + fmt
		
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
	def refresh(self):
		print(" Wireless MAC     | IP Address      | RX Data   | TX Data   | Signal")
		print("------------------+-----------------+-----------+-----------+----------")
		
		self.console.index += 2
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
			self.console.index += 1

class DHCPMonitor():
	def __init__(self, console, leaseFiles=["/var/lib/dhcp/dhcpd.leases"]):
		self.leaseFiles = leaseFiles
		self.console = console
		self.clients = {}
		self.colors = Colors()
	
	"""
	Source
	"""
	def readSource(self, leaseFile):
		leases = {}
		
		with open(leaseFile, 'r') as content:
			full = content.read()
		
		for lease in full.split("\nlease "):
			inner = lease.split('{\n')
			
			if len(inner) < 2:
				continue

			host = lease.partition(' ')[0]
			leases[host] = inner[1]
		
		for host in leases:
			leases[host] = leases[host].split(";\n")
			leases[host] = list(map(str.strip, leases[host]))
			leases[host].pop()
		
		return leases
	
	def readArp(self):
		output = []

		proc = subprocess.Popen(['ip', 'n'], stdout=subprocess.PIPE)
		for input in proc.stdout:
			output.append(input.decode('utf-8').rstrip())
		
		return output
	
	def setActive(self):
		arp = self.readArp()
		table = {}
		
		for line in arp:
			words = line.split(" ")
			
			if len(words) != 6:
				continue
			
			table[words[4]] = words[0]

		for client in self.clients:
			self.clients[client]['state'] = "inactive"

			if self.clients[client]['hardware'] in table:
				self.clients[client]['state'] = "active"
		
	def _update(self, interface):
		source = self.readSource(interface)
		current = {}
		
		for client in source:
			self.clients[client] = {}
			
			for line in source[client]:
				temp = line.split(' ')
				
				if temp[0] == 'ends':
					self.clients[client]['expire'] = '%s %s' % (temp[2], temp[3])
				
				if temp[0] == 'hardware':
					self.clients[client]['hardware'] = temp[2]
				
				if temp[0] == 'client-hostname':
					self.clients[client]['hostname'] = temp[1].strip('"')
	
		# grabbing ip address from arp cache
		if len(self.clients) > 0:
			self.setActive()
	
	def update(self):
		self.clients = {}
		
		for leaseFile in self.leaseFiles:
			self._update(leaseFile)

	"""
	Formatter
	"""
	def _colorizeState(self, client):
		c = self.colors
		color = c.green if client['state'] == "active" else c.red

		return color + client["state"] + c.clear
	
	"""
	Displayer
	"""	
	def refresh(self):
		print(" Client MAC       | IP Address      | Status    | Hostname")
		print("------------------+-----------------+-----------+----------------------")
		
		self.console.index += 2
		for client in sorted(self.clients, key = lambda c: self.clients[c]['state']):
			host = client
			client = self.clients[client]
			
			if client['state'] == 'inactive':
				break
			
			# sys.stdout.write(self._colorizeStation(client))
			sys.stdout.write(client['hardware'])
			sys.stdout.write(" | ")
			
			# sys.stdout.write(self._colorizeAddress(client))
			sys.stdout.write("%-15s" % host)
			sys.stdout.write(" | ")
			
			sys.stdout.write("%-20s | " % self._colorizeState(client))
			
			# sys.stdout.write(self._colorizeSignal(client))
			if 'hostname' in client:
				sys.stdout.write(client['hostname'])
			
			# end of line
			sys.stdout.write("\033K\n")
			self.console.index += 1

			if self.console.index >= self.console.rows - 1:
				break

class ConntrackMonitor():
	def __init__(self, console):
		self.console = console
		# self.colors = Colors()
		self._value = 0
		self._peak = 0
	
	"""
	Source
	"""
	def readSource(self):
		leases = {}
		
		with open("/proc/sys/net/netfilter/nf_conntrack_count", 'r') as content:
			full = content.read()
		
		return int(full)
	
	def update(self):
		self._value = self.readSource()
		
		if self._value > self._peak:
			self._peak = self._value
	
	"""
	Displayer
	"""	
	def refresh(self):
		print(" Tracking         | Count           | Peak")
		print("------------------+-----------------+-----------------------------------")
		
		self.console.index += 2
		sys.stdout.write("Connections      ")
		sys.stdout.write(" | ")
		sys.stdout.write("%-15d" % self._value)
		sys.stdout.write(" | ")
		sys.stdout.write("%d" % self._peak)
			
		sys.stdout.write("\033K\n")
		self.console.index += 1

		if self.console.index >= self.console.rows - 1:
			return

monitor = Monitoring()
monitor.initialize()

dhcp = DHCPMonitor(monitor)
wlz  = WirelessMonitor(monitor, ["wlan0", "wlan1"])
conn = ConntrackMonitor(monitor)

runid = 0

while True:
	if (runid % 20) == 0:
		monitor.initialize()

	try:
		monitor.new()

		wlz.update()
		dhcp.update()
		conn.update()
		
		wlz.refresh()
		monitor.separe()
		dhcp.refresh()
		monitor.separe()
		conn.refresh()
	
		time.sleep(1)

	except KeyboardInterrupt:
		monitor.reset()
		sys.exit(0)
	
	runid += 1
