from bitdeli.model import model, segment_model

MAX_LEN = 32
CUTOFF = 4

def count_events(hours):
    s = 0
    for hour, count in hours:
        s += count
        if s >= CUTOFF:
            break
    return 'l' if s < CUTOFF else 'h'

@model
def build(profiles):
    for profile in profiles:
        uid = profile.uid
        if not uid:
            continue
        for event, hours in profile['events'].iteritems():
            event = event.encode('utf-8')
            yield 'e%s%s' % (count_events(hours), event), uid
        for prop_name, prop_values in profile['properties'].iteritems():
            prop_name = prop_name.encode('utf-8')
            for v in frozenset(prop_value[:MAX_LEN] for prop_value in prop_values):
                yield 'p%s:%s' % (prop_name, v.encode('utf-8')), uid

@segment_model
def segment(model, segments, labels):
    return model, segments, labels