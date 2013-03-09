from bitdeli.insight import insight
from bitdeli.widgets import Text, Bar, Table

@insight
def view(model, params):
    if type(model) == tuple:
        yield Text(size=(12, 2),
                   data={'head': 'yay %s' % str(model)})
    else:
        yield Text(size=(12, 2),
                   data={'head': 'Add a segment to get started'})
    
