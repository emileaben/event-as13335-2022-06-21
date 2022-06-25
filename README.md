# scripts/data to look at what happened at Cloudflare on 2022-06-21 from the perspective of RIS

This is part of an exercise for PhD students at TMA2022.

The python script filters for prefixes of origin AS13335 at the start of 2022-06-21 (exact matches), for a small set of "tier1" peers
It needs bgpdump installed to function.

Data file description.
Each line is a json-formatted representation of a bgp message element (ie. either an announce or a withdraw). lets call this an event

The keys _peer_ip_, and _pfx_ are the peerIP where this message was seen, pfx is the prefix in this event
The _idx_ is the sequence number of this event for the particular peer_ip/pfx-tuple
The first _idx_ (0) contains the state of the prefix at the beginning of the day (00:00:00 UTC) as seen in MRT dump files in RIS. This one has no timestamp, the rest of the events for this peer_ip/pfx-tuple has
All subsequent events for this peer_ip/pfx-tuple will contain a _ts_ key, which is the timestamp of the event, as a unix epoch time (ie. seconds since 1 Jan 1970)

If an event is a BGP announce it has the following extra keys:
_path_: the AS path (as a list of strings)
_comm_: BGP communities 
_agg_: the atomic aggregate (this looks fascinating. read up on ATOMIC_AGGREGATE / AGGREGATOR_ID ). Not used in the lab

If an event is a BGP withdraw it has the following extra keys:
_path_: is always an empty list
_W_ : this is set to a boolean True to indicate this is a withdraw message (this makes 'grep W' work on this file to quickly find the withdraw messages)

