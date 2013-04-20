from bitdeli.insight import insight
from bitdeli.widgets import Text, Table
from discodb.query import Q, Literal, Clause
from itertools import groupby, islice
from collections import Counter, namedtuple
import heapq

MAX_TABLES = 20
TOPN = 10
DIFF_TOPN = 3
DIFF_LIMIT = 0.05
DIFF_MIN_USERS = 10
DIFF_CAPTION = """
### What makes {0} different from {1}?

{color1} items are more typical to {0},
{color2} items are more typical to {1}.
"""

STATS_CAPTION = """
### What are top events and properties for all users?
"""

NEGATIVE = lambda x: 'rgba(255, 36, 0, %f)' % min(0.8, x)
POSITIVE = lambda x: 'rgba(0, 163, 89, %f)' % min(0.8, x)

SEG1 = lambda x: 'rgba(118, 192, 255, %f)' % min(0.8, x)
SEG2 = lambda x: 'rgba(255, 197, 11, %f)' % min(0.8, x)

COLORS = [{'color1': 'Green', 'color2': 'red'},
          {'color1': 'Blue', 'color2': 'yellow'}]

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

    def header(self):
        return Text(size=(12, 'auto'),
                    label='Showing top events and properties',
                    data={'text': STATS_CAPTION})
        
    def make_tables(self):
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

    def __init__(self, model, segments, labels, views):
        self.views = views
        self.labels = labels
        if len(self.labels) == 1:
            self.labels.append('all other users')
        self.num_uids = len(model.unique_values())
        self.segment_sizes = map(len, segments)
        self.min_users = max(DIFF_MIN_USERS,
                             int(DIFF_LIMIT * min(self.segment_sizes)))
        self.model = model
        self.segments = segments
           
    def diff_all(self, keys):
        model = self.model
        view = self.views[0]
        segment = self.segments[0]
        segment_size = self.segment_sizes[0]
        for key in keys:
            uids = model[key]
            t = len(uids)
            if t > self.min_users:
                s = len(model.query(Literal(key), view=view))
                #s = sum(1 for uid in uids if uid in segment)
                tr = float(t - s) / self.num_uids
                sr = float(s) / segment_size
                d = sr - tr
                if abs(d) > DIFF_LIMIT:
                    color = NEGATIVE(abs(d)) if d < 0 else POSITIVE(d)
                    yield d, key, sr, tr, s, t - s, color
                
    def diff_two(self, keys):
        model = self.model
        seg1, seg2 = self.segments
        view1, view2 = self.views
        size1, size2 = self.segment_sizes
        for key in keys:
            if len(model[key]) > self.min_users:
                s1 = len(model.query(Literal(key), view=view1))
                s2 = len(model.query(Literal(key), view=view2))
                r1 = float(s1) / size1
                r2 = float(s2) / size2
                d = r1 - r2
                if abs(d) > DIFF_LIMIT:
                    color = SEG2(abs(r2)) if d < 0 else SEG1(r1)
                    yield d, key, r1, r2, s1, s2, color
                
    def _table(self, head, tail, itemlabel):
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
                   {'name': 'seg1', 'label': self.labels[0], 'cell': 'markdown'},
                   {'name': 'seg2', 'label': self.labels[1], 'cell': 'markdown'}]
    
        return Table(size=(12, 'auto'),
                     fixed_width=True,
                     data={'columns': columns, 'rows': list(rows())})
    
    def make_tables(self, diff):
        def head_and_tail(it):
            head = []
            tail = []
            for x in it:
                if x[0] < 0:
                    if len(tail) > DIFF_TOPN:
                        heapq.heappushpop(tail, (abs(x[0]), x))
                    else:
                        heapq.heappush(tail, (abs(x[0]), x))
                else:
                    if len(head) > DIFF_TOPN:
                        heapq.heappushpop(head, x)
                    else:
                        heapq.heappush(head, x)
            return sorted(head, reverse=True), [x[1] for x in sorted(tail)]
        
        for key, subkeys in attributes(self.model):
            head, tail = head_and_tail(diff(subkeys))
            if head or tail:
                label = 'Event' if key == 'e' else key[1:].split(':')[0].capitalize()
                yield max(abs(x[0]) for x in head + tail),\
                      self._table(head, tail, label)
        
    def header(self):
        n = len(self.segments)
        suffix = 'all other users' if n == 1 else 'another segment'
        return Text(size=(12, 'auto'),
                    label='Comparing a segment to ' + suffix,
                    data={'text': DIFF_CAPTION.format(*self.labels,
                                                      **COLORS[n - 1])})
    
    
################################################################################        
@insight
def view(model, params):
    def test_segment():
        import random
        random.seed(21)
        labels = ['First Segment'] #, 'Second']
        segments = [frozenset(random.sample(model.unique_values(), 20))]
                    #frozenset(random.sample(model.unique_values(), 200))]
        return namedtuple('SegmentInfo', ('model', 'segments', 'labels', 'views'))\
                         (model, segments, labels, map(model.make_view, segments))
    #model = test_segment()
    if hasattr(model, 'segments'):
        comp = Comparison(model.model, model.segments, model.labels, model.views)
        if len(model.segments) == 1:
            diff = comp.diff_all
        else:
            diff = comp.diff_two
        tables = comp.make_tables(diff)
        yield comp.header()
    else:
        stats = Stats(model)
        tables = stats.make_tables()
        yield stats.header()
        
    tables = list(sorted(tables, reverse=True))
    for count, widget in tables[:MAX_TABLES]:
        yield widget
    if len(tables) > MAX_TABLES:
        yield Text(size=(12, 1),
                   data={'text': "Showing only the %d most characteristic "
                                 "properties out of %d properties in total." %\
                                 (MAX_TABLES, len(tables))})
 
