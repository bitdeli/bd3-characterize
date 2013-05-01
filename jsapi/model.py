from bitdeli.model import model, segment_model
from itertools import starmap, chain
from collections import namedtuple, Counter
from urlparse import urlparse

MAX_LEN = 32
CUTOFF = 4

def prop_key(name, value):
    return 'p%s:%s' % (name.encode('utf-8'), str(value)[:MAX_LEN].encode('utf-8'))

def propset(event):
    return starmap(prop_key, (x for x in event.iteritems() if x[0][0] != '$'))

@model
def build(profiles):
    for profile in profiles:
        uid = profile.uid
        if not uid:
            continue
        eventcount = Counter()
        props = set()
        
        for tstamp, group, ip, event in profile.get('events', []):
            eventcount[event['$event_name'].encode('utf-8')] += 1
            props.update(propset(event))
        for tstamp, group, ip, event in profile.get('$pageview', []):
            props.add(prop_key('$page view', urlparse(event['$page']).path))
            props.update(propset(event))
        for tstamp, group, ip, event in profile.get('$dom_event', []):
            props.add(prop_key('$dom event', event['$event_label']))
        
        for event, count in eventcount.iteritems():
            prefix = 'l' if count < CUTOFF else 'h'
            yield 'e:%s%s' % (prefix, event), uid
        for prop in props:
            yield prop, uid

@segment_model
def segment(model, segments, labels):
    return namedtuple('SegmentInfo', ('model', 'segments', 'labels', 'views'))\
                     (model, segments, labels, map(model.make_view, segments))
