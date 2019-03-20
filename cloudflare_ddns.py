from urllib3.exceptions import HTTPError as BaseHTTPError
import sys
import re
import json
import requests

'''
cloudflareDDNS

This script was created so I could update a dns record on cloudflare when my IP address changed
It uses ipify.org api to get your remote IP then updates the specified zone's dns on cloudflare

Brent Russsell
www.brentrussell.com
'''

# Zone in cloudflare. This will not contain a subdomain. It is the root of the domain e.g. example.com
zone = 'domain.com'

# The record to be updated e.g. cname.example.com or a.example.com or example.com
record = 'home.domain.com'

# Cloudflare API key at https://dash.cloudflare.com/profile
global_api_key = 'ENTER API KEY HERE'

# Cloudflare login email address
cloudflare_email = 'youremail@domain.com'


def raise_ex(msg, terminate):
    print(msg)
    terminate and sys.exit(1)


def getURL(url, rtype, headers='', payload=''):
    try:
        if rtype.lower() == 'put':
            r = requests.put(url, headers=headers, data=payload)
        else:
            r = requests.get(url, headers=headers)
    except requests.exceptions.Timeout:
        raise_ex("Connection to "+url + " Timmed out", True)
    except requests.exceptions.TooManyRedirects:
        raise_ex(url+" has redirected too many times", True)
    except requests.exceptions.HTTPError as e:
        raise_ex('HTTP Error '+e.response.status_code, True)
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
        raise_ex("Connection Error, could not connect to "+url, True)
    else:
        return r


def remoteIP():
    # https://www.ipify.org/ api to get public ip
    ip_api = 'https://api.ipify.org?format=json'
    ip = getURL(ip_api, 'get')
    if ip.content:
        data = json.loads(ip.content)
        if not data['ip']:
            raise_ex('No IP returned from '+ip_api, True)
        elif not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", data['ip']):
            raise_ex('A valid IP was not returned from '+ip_api, True)
        else:
            return data['ip']
    else:
        raise_ex("No content returned from "+ip_api, True)


def zoneData(headers):
    data = getURL('https://api.cloudflare.com/client/v4/zones?name=' +
                  zone, 'get', headers)
    zone_data = json.loads(data.content)
    if not zone_data['result'][0]['id']:
        raise_ex('Zone '+zone+' not found', True)
    else:
        return zone_data['result'][0]['id']


def recordData(headers, zone_id):
    data = getURL('https://api.cloudflare.com/client/v4/zones/' +
                  zone_id+'/dns_records?name='+record, 'get', headers)
    record_data = json.loads(data.content)
    if not record_data['result'][0]['id']:
        raise_ex('Zone '+record+' not found', True)
    else:
        return record_data['result'][0]['id']


def updateRecord(headers, zone_id, record_id, remote_ip):
    payload = dict(type="A", name=record,
                   content=remote_ip, ttl=1, proxied=False)

    data = getURL('https://api.cloudflare.com/client/v4/zones/' +
                  zone_id+'/dns_records/'+record_id, 'put', headers, json.dumps(payload))
    update = json.loads(data.content)
    if update['success']:
        return True


# Set headers to be used with cloudflare
headers = {
    'Content-Type': 'application/json',
    'X-Auth-Key': global_api_key,
    'X-Auth-Email': cloudflare_email
}

if float(str(sys.version_info[0])+'.'+str(sys.version_info[1])) < 3.7:
    raise_ex("Please upgrade to Python 3.7 or later", True)

remote_ip = remoteIP()
zone_id = zoneData(headers)  # Get Zone ID
record_id = recordData(headers, zone_id)  # Get record ID
if updateRecord(headers, zone_id, record_id, remote_ip):
    print('DNS for '+record+' updated to '+remote_ip)
else:
    print('DNS Update Failed')
