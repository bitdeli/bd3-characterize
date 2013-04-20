from bitdeli.model import model, segment_model
from collections import namedtuple, Counter

MAX_LEN = 32
CUTOFF = 4

@model
def build(profiles):
    for profile in profiles:
        uid = profile.uid
        if not uid:
            continue
        eventcount = Counter()
        propset = set()
        for event in profile['events']:
            event = event[3]
            eventcount[event['$event_name'].encode('utf-8')] += 1
            for prop_name, prop_value in event.iteritems():
                if prop_name[0] != '$':
                    propset.add('p%s:%s' % (prop_name.encode('utf-8'),
                                            str(prop_value)[:MAX_LEN].encode('utf-8')))
        for event, count in eventcount.iteritems():
            prefix = 'l' if count < CUTOFF else 'h'
            yield 'e:%s%s' % (prefix, event), uid
        for prop in propset:
            yield prop, uid     

@segment_model
def segment(model, segments, labels):
    return namedtuple('SegmentInfo', ('model', 'segments', 'labels', 'views'))\
                     (model, segments, labels, map(model.make_view, segments))
