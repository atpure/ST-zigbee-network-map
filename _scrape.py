import sys
import networkx as nx
import matplotlib.font_manager as fm
import re
import requests
from bs4 import BeautifulSoup

G       = nx.Graph()
if (len(sys.argv) > 1):
    cookies = {'JSESSIONID': sys.argv[1]}
else:
    cookies = {'JSESSIONID': input("JSESSIONID:")}
hostList = {
    'https://graph.api.smartthings.com',
    'https://graph-na02-useast1.api.smartthings.com',
    'https://graph-na04-useast2.api.smartthings.com',
    'https://graph-eu01-euwest1.api.smartthings.com',
    'https://graph-ap02-apnortheast2.api.smartthings.com'
}

for host in hostList:
    r       = requests.get(host+'/device/list', cookies=cookies, allow_redirects=False)
    print('Trying shard: ' + host)
    if (r.status_code == 302):
        print('Redirect deetected. Invalid login? Double check JSESSIONID')
        continue
    if (r.status_code == 200):
        print('Shard matching session found: '+ host)
        break

if (r.status_code == 302):
    print('Did not find any valid server, double check JSESSIONID')
    exit()

soup = BeautifulSoup(r.content, "html.parser")
translationDict = {}

if (len(soup.select('#device-table > tbody > tr')) == 0):
    print('No devices found, did you provide token to wrong shard?')
    exit()

for device in soup.select('#device-table > tbody > tr'):
    link = device.select('td:nth-of-type(1) > a')[0]
    deviceName        = link.text.strip()
    deviceDetailsLink = link.get('href')
    deviceType        = device.select('td:nth-of-type(2)')[0].text.strip()
    hubName           = device.select('td:nth-of-type(4)')[0].text.strip()
    deviceId          = device.select('td:nth-of-type(5)')[0].text.strip()
    deviceNetworkId   = device.select('td:nth-of-type(6)')[0].text.strip()
    deviceStatus      = device.select('td:nth-of-type(7)')[0].text.strip()
    G.add_node(hubName, details='{\'name\': hubName}')

    deviceDetails = requests.get(host+deviceDetailsLink, cookies=cookies)
    details = BeautifulSoup(deviceDetails.content, "html.parser")
    translationDict[deviceNetworkId] = deviceName
    translationDict[hubName]         = hubName
    deviceData = {
        'name':   deviceName,
        'Type':   deviceType,
        'ID':     deviceId,
        'NID':    deviceNetworkId,
        'Status': deviceStatus
    }
    G.add_node(deviceNetworkId, details=deviceData)
    routes = details.select('#meshRoute-label + td a')
    rssi   = details.select(
        '#deviceMetrics-label + td > ul > li:nth-of-type(2) > strong'
        )
    lqi   = details.select(
        '#deviceMetrics-label + td > ul > li:nth-of-type(1) > strong'
    )
    if rssi:
        translationDict[deviceNetworkId] = deviceName + '\n RSSI: ' + rssi[0].text + '\n LQI:' + lqi[0].text
        lqiValue = int(lqi[0].text)
        weightValue = 0
        colorValue = '#13d175'
        if lqiValue >= 200:
            weightValue = 2.5
        elif lqiValue >= 150 and lqiValue < 200:
            weightValue = 2
            colorValue = '#8dd6b3'
        elif lqiValue >= 100 and lqiValue < 150:
            weightValue = 1.5
            colorValue = '#abd6c2'
        else:
            weightValue = 1
            colorValue = '#ced9d4'
    deviceRoute = []
    if not routes:
        G.remove_node(deviceNetworkId)
        translationDict.pop(deviceNetworkId)
        print("REMOVED " + deviceNetworkId + " as it had no routes. (Wifi device?)\n")
    for route in routes:
        rex = re.search('.*\((.+)\).*', route.text)
        if route == routes[1]:
            print(deviceNetworkId + ' ' + deviceName + ' is connected to:')

        if rex and rex.group(1) != deviceNetworkId:
            deviceRoute.append(rex.group(1))
            print(rex.group(1))

        if route.text == hubName:
            deviceRoute.append(hubName)
            print(route.text)

        if route == routes[-1]:
            print("\n")

    previousroute = None
    for route in deviceRoute:
        if not previousroute:
            G.add_edge(deviceNetworkId, route, color=colorValue,weight=weightValue)
        else:
            G.add_edge(route, previousroute, color=colorValue,weight=weightValue)
        previousroute = route

font_name = fm.FontProperties(fname="c:/Windows/Fonts/malgun.ttf").get_name()
#font_name = 'AppleGothic'
d = dict(G.degree)
node_size=[v * 100 for v in d.values()]

edges = G.edges()
weights = [G[u][v]['weight'] for u,v in edges]
colors = [G[u][v]['color'] for u,v in edges]

options = {
    'font_family' : font_name,
    'font_size': 10,
    'node_size': node_size,
    'width': weights,
    'with_labels': True,
    'labels': translationDict,
    'node_color': '#DE781F',
    'edge_color': colors
}
nx.draw(G,**options)
