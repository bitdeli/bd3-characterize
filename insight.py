from bitdeli.insight import insight
from bitdeli.widgets import Text, Bar, Table
from itertools import groupby, islice
from collections import Counter, namedtuple

TOPN = 10
DIFF_TOPN = 3
DIFF_LIMIT = 0.05

NEGATIVE = lambda x: 'rgba(255, 36, 0, %f)' % min(0.8, x)
POSITIVE = lambda x: 'rgba(0, 163, 89, %f)' % min(0.8, x)

SEG1 = lambda x: 'rgba(118, 192, 255, %f)' % min(0.8, x)
SEG2 = lambda x: 'rgba(255, 197, 11, %f)' % min(0.8, x)

def attributes(model):
    def sort_key(k):
        return k.split(':', 1)[0]
    return groupby(sorted(model, key=sort_key), sort_key)
    
def cell(label, color):
    return {'label': label, 'background': color}
    
class Stats(object):

    def __init__(self, model):
        self.num_uids = float(len(model.unique_values()))
        self.model = model

    def show(self):
        for key, subkeys in attributes(self.model):
            if key == 'e':
                label = 'Event'
                keyfun = lambda x: x[3:]
            else:
                label = key[1:].capitalize()
                keyfun = lambda x: x.split(':', 1)[1]
            yield self._table(subkeys, keyfun, label)
        
    def _table(self, keys, keyfun, label):
        model = self.model
        def make_rows():
            counts = Counter()
            for key in keys:
                counts[keyfun(key)] += len(model[key])
            for item, count in counts.most_common(TOPN):
                r = count / self.num_uids
                yield {'item': cell(item, r),
                       'count': cell(count, r),
                       'percent': cell('%.1f%%' % (r * 100), r)}
        
        columns = [{'name': 'item', 'label': label, 'width': '60%'},
                   {'name': 'percent', 'label': '% of all users'},
                   {'name': 'count', 'label': 'Number of users', 'cell': 'integer'}]
        rows = list(make_rows()) 
        return rows[0]['count']['label'],\
               Table(size=(10, 'auto'),
                     data={'columns': columns, 'rows': rows})

class Comparison(object):

    def __init__(self, model, segments):
        self.num_uids = len(model.unique_values())
        self.segment_sizes = map(len, segments)
        self.model = model
        self.segments = segments
           
    def diff_all(self, keys):
        model = self.model
        segment = self.segments[0]
        segment_size = self.segment_sizes[0]
        for key in keys:
            t = s = 0
            for uid in model[key]:
                if uid in segment:
                    s += 1
                else:
                    t += 1
            #t = len(model[key])
            #s = sum(1 for uid in model[key] if uid in segment)
            #tr = float(t - s) / self.num_uids
            tr = float(t) / self.num_uids
            sr = float(s) / segment_size
            d = sr - tr
            if abs(d) > DIFF_LIMIT:
                color = NEGATIVE(abs(d)) if d < 0 else POSITIVE(d)
                #yield d, key, sr, tr, s, t - s, color
                yield d, key, sr, tr, s, t, color
                
    def diff_two(self, keys):
        model = self.model
        seg1, seg2 = self.segments
        size1, size2 = self.segment_sizes
        for key in keys:
            s1 = s2 = 0
            for uid in model[key]:
                if uid in seg1:
                    s1 += 1
                if uid in seg2:
                    s2 += 1
            r1 = float(s1) / size1
            r2 = float(s2) / size2
            d = r1 - r2
            if abs(d) > DIFF_LIMIT:
                color = SEG2(abs(r2)) if d < 0 else SEG1(r1)
                yield d, key, r1, r2, s1, s2, color
                
    def _table(self, head, tail, itemlabel, label1, label2):
        def format_item(key):
            if key[0] == 'e':
                prefix = 'in' if key[2] == 'l' else ''
                return '%s (%sfrequently)' % (key[3:], prefix)
            else:
                return key.split(':', 1)[1]
    
        def format_number(count, ratio):
            return '**{0:.1f}%** ({1:,})'.format(ratio * 100, count)
    
        def rows():           
            for diff, key, ratio1, ratio2, count1, count2, color in head + tail:
                yield {'item': cell(format_item(key), color),
                       'diff': cell('%.1f' % (diff * 100), color),
                       'seg1': cell(format_number(count1, ratio1), color),
                       'seg2': cell(format_number(count2, ratio2), color)}
    
        columns = [{'name': 'item', 'label': itemlabel, 'width': '50%'},
                   {'name': 'diff', 'label': 'Difference', 'cell': 'markdown'},
                   {'name': 'seg1', 'label': label1, 'cell': 'markdown'},
                   {'name': 'seg2', 'label': label2, 'cell': 'markdown'}]
    
        return Table(size=(12, 'auto'),
                     fixed_width=True,
                     data={'columns': columns, 'rows': list(rows())})
            
    def show(self, label1, label2, diff):
        def head_and_tail(lst, n=DIFF_TOPN):
            head = tail = []
            for positive, items in groupby(lst, lambda x: x[0] >= 0):
                if positive:
                    head = list(islice(items, n))
                else:
                    tail = list(items)[-n:]
            return head, tail
        
        for key, subkeys in attributes(self.model):
            head, tail = head_and_tail(sorted(diff(subkeys), reverse=True))
            if head or tail:
                label = 'Event' if key == 'e' else key[1:].split(':')[0].capitalize()
                yield max(abs(x[0]) for x in head + tail),\
                      self._table(head, tail, label, label1, label2)
        

################################################################################        
@insight
def view(model, params):
    def test_segment():
        import random
        random.seed(2)
        labels = ['First Segment' * 3, 'Second']
        segments = [frozenset(random.sample(model.unique_values(), 200)),
                    frozenset(random.sample(model.unique_values(), 200))]
        return namedtuple('SegmentInfo', ('model', 'segments', 'labels'))\
                         (model, segments, labels)
    #model = test_segment()
    if hasattr(model, 'segments'):
        comp = Comparison(model.model, model.segments)
        if len(model.segments) == 1:
            diff = comp.diff_all
            label1 = model.labels[0]
            label2 = 'All other users'
        else:
            diff = comp.diff_two
            label1, label2 = model.labels
        tables = comp.show(label1, label2, diff)
    else:
        tables = Stats(model).show()
    for count, widget in sorted(tables, reverse=True):
        yield widget
        
        