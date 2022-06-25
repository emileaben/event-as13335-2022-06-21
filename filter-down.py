#!/usr/bin/env python
import sys
from datetime import datetime,timedelta
import json
import gzip
import ipaddress
from urllib.request import urlopen
import requests
from subprocess import Popen,PIPE
from collections import Counter
import arrow
from dateutil import tz

# find the state at t1, then look at updates until t2
t1 = "2022-06-21T06"
t2 = "2022-06-21T08"
asn = '13335'

t1_arr = arrow.get( t1 )
t2_arr = arrow.get( t2 )

def _get_url_bview_pp( rrc, peer_ip, date_arr ):
    peer_ip_encoded = None
    #date_arr = arrow.get( date ) # TZ hopefully won't matter in this case, because we only use arrow to parse and then specify
    d1 = date_arr.format('YYYY-MM-DD')
    d2 = date_arr.format('HH')
    d3 = date_arr.format('YYYYMMDD')
    d4 = date_arr.format('HHmm')
    if ':' in peer_ip:
        peer_ip_encoded = "".join(['TODO'])
    else:
        peer_ip_encoded = "".join( map( lambda x: f"{int(x):02X}", peer_ip.split('.') ))
    url=f"https://www.ris.ripe.net/dumps-per-peer-rest/prototype/{rrc}/{d1}T{d2}/bview-{d3}T{d4}-{peer_ip_encoded}.gz"
    return url

def _get_url_updates( rrc, date_arr ):
    #date_arr = arrow.get( date )
    d1 = date_arr.format('YYYY.MM')
    d2 = date_arr.format('YYYYMMDD.HHmm')
    url=f"https://data.ris.ripe.net/{rrc}/{d1}/updates.{d2}.gz"
    return url

def get_initial_state( rrc, peer_ip, date, init_state):
    url = _get_url_bview_pp( rrc, peer_ip, date )
    cmd = "/usr/local/bin/bgpdump -m -"
    gzip_stream = urlopen(url)
    stream = gzip.open(gzip_stream, 'r')

    # can't get this to work without a temp file
    process = Popen(cmd.split(), stdin=PIPE, stdout=open('.outfile', 'w'), stderr=PIPE)
    for chunk in stream:
        process.stdin.write(chunk)

    outs,errs = process.communicate()
    with open('.outfile','rt') as inf:
        for line in inf:
            fields = line.split('|')
            peer_ip = fields[3]
            pfx = fields[5]
            key = (peer_ip, pfx )
            aspath_str = fields[6]
            aspath = fields[6].split(' ') # strings!
            comm = fields[11]
            agg = fields[13]
            if aspath_str.endswith(' 13335'):
                init_state[ key ] = [{
                    'path': aspath,
                    'comm': comm,
                    'agg': agg
                }]

'''
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '190.109.49.0/24', '174 262589 271952', 'IGP', '130.117.255.1', '0', '113061', '', 'NAG', '', '\n']
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '143.208.100.0/22', '174 263444 263124 263124 263124 263124 263124 263124 264465', 'IGP', '130.117.255.1', '0', '185041', '', 'NAG', '', '\n']
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '44.31.42.0/24', '174 15412 9304 134835 133846', 'IGP', '130.117.255.1', '0', '21032', '', 'NAG', '', '\n']
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '191.7.4.0/24', '174 263009 263009 53078 268696 263304', 'IGP', '130.117.255.1', '0', '184041', '', 'NAG', '', '\n']
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '84.205.78.0/24', '174 19151 12654', 'IGP', '130.117.255.1', '0', '145111', '', 'NAG', '65470 10.26.150.64', '\n']
['BGP4MP', '1655791225', 'A', '130.117.255.1', '174', '170.76.241.0/24', '174 21949 393457 397711', 'IGP', '130.117.255.1', '0', '70031', '', 'NAG', '', '\n']
'''

def process_updates( rrc, peer_set, date_arr, init_state ):
    url = _get_url_updates( rrc, date_arr )
    cmd = "/usr/local/bin/bgpdump -m -"
    gzip_stream = urlopen(url)
    stream = gzip.open(gzip_stream, 'r')

    process = Popen(cmd.split(), stdin=PIPE, stdout=open('.updates', 'w'), stderr=PIPE)
    for chunk in stream:
        process.stdin.write(chunk)

    outs,errs = process.communicate()

    upstreams = set()
    msgs = 0

    with open('.updates','rt') as inf:
        for line in inf:
            line = line.rstrip("\n")
            fields = line.split('|')
            peer_ip = fields[3]
            ts = int(fields[1])
            upd = None
            key = None
            if peer_ip in peer_set:
                if fields[2] == 'STATE':
                    print("TODO", fields ) # TODO state
                elif fields[2] == 'A': #announce
                    pfx = fields[5]
                    key = (peer_ip,pfx)
                    if key in init_state:
                        aspath_str = fields[6]
                        aspath = aspath_str.split(' ')
                        comm = fields[11]
                        agg = fields[13]
                        init_state[ key ].append({
                            'ts': ts,
                            'path': aspath,
                            'comm': comm,
                            'agg': agg
                        })
                elif fields[2] == 'W': #withdraw
                    pfx = fields[5]
                    key = (peer_ip,pfx)
                    if key in init_state:
                        init_state[ key ].append({
                            'ts': ts,
                            'W': True,
                            'path': []
                        })
    return init_state

interesting = (
    ("rrc01","195.66.227.163"), #Telia
    ("rrc25","130.117.255.1"), #COGENT
    ("rrc01","195.66.224.138"), #NTT
)
'''
    ("rrc00","12.0.1.63"), #ATT
    ("rrc01","195.66.225.35"), #Sprint AS1239
    ("rrc01","195.66.224.137"), #DTAG
    ("rrc00","208.51.134.248"), #GBLX
    ("rrc03","80.249.209.167"), #TATA
)
'''

rrcs = list( set( map( lambda x:x[0], interesting ) ) )
peer_set = set( map( lambda x:x[1], interesting ) )

init_state={} # keyed by peer/pfx pairs

for (rrc,peer_ip) in interesting:
    get_initial_state( rrc, peer_ip, t1_arr, init_state )

'''
upstreams = set()
for key in sorted( init_state.keys() ):
    val = init_state[ key ][0]
    ups = None
    for asn in reversed( val['path'] ):
        if asn != '13335':
            ups = asn
            break
    upstreams.add( ups )

print( sorted( list( upstreams ) ) )
print("LEN: ", len( upstreams ) )
'''

t_dt = t1_arr.datetime
t2_dt = t2_arr.datetime
new_ups = set()
while t_dt < t2_dt:
    t_arr = arrow.get( t_dt )
    for rrc in rrcs:
        init_state = process_updates( rrc, peer_set, t_arr, init_state )
    t_dt += timedelta(minutes=5)

for key in sorted( init_state.keys() ):
    for idx,upd in enumerate( init_state[key] ):
        upd['peer_ip'] = key[0]
        upd['pfx'] = key[1]
        upd['idx'] = idx
        print( json.dumps( upd ) )
