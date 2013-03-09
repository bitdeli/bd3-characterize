from bitdeli.insight import insight
from bitdeli.widgets import Text, Bar, Table
from itertools import groupby
from collections import Counter

TOPN = 10

def create_table(model, keys, keyfun, num_uids, label):
    def make_rows():
        counts = Counter()
        for key in keys:
            counts[keyfun(key)] += len(model[key])
        for item, count in counts.most_common(TOPN):
            r = count / num_uids
            p = '%.1f%%' % (r * 100)
            t = '**{percent:.1f}%** ({count})'.format(count=count,
                                                      percent=r * 100)
            yield {'item': {'label': item, 'background': r},
                   'count': {'label': count, 'background': r},
                   'percent': {'label': p, 'background': r}}
    
    columns = [{'name': 'item', 'label': label, 'width': '60%'},
               {'name': 'percent', 'label': '% of all users'},
               {'name': 'count', 'label': 'Number of users', 'cell': 'integer'}]
    rows = list(make_rows()) 
    return rows[0]['count']['label'],\
           Table(size=(10, 'auto'),
                 data={'columns': columns, 'rows': rows})
        
def basic_stats(model):
    def sort_key(k):
        return k.split(':', 1)[0]
    num_uids = float(len(model.unique_values()))
    for key, subkeys in groupby(sorted(model, key=sort_key), sort_key):
        if key == 'e':
            label = 'Event'
            keyfun = lambda x: x[3:]
        else:
            label = key[1:].capitalize()
            keyfun = lambda x: x.split(':', 1)[1]
        yield create_table(model, subkeys, keyfun, num_uids, label)
       
@insight
def view(model, params):
    if type(model) == tuple:
        yield ext(size=(12, 2),
                   data={'head': 'yay %s %s' % (map(len, model[1]), str(model[2]))})
    else:
        for count, widget in sorted(basic_stats(model), reverse=True):
            yield widget
