from BasicClass.TablePy import *
def test_table():
    test_table_body()
    test_table_functions_index()
    test_table_functions_string()

def test_table_body():
    a=Table([Index(0,0,0,0),Index(0,0,1,0),Index(0,0,2,0)])
    for k,v in a.iteritems():
        print k,v
    b=Table()

def test_table_functions_index():
    a=Table([Index(0,0,0,0),Index(0,0,1,0)])
    b=Table([Index(0,0,2,0),Index(0,0,3,0)])
    c=union(a=a,b=b)
    print 'c:\n',c
    print 'reverse_table(c):\n',reverse_table(c)
    print 'c["b"][Index(0,0,2,0)],c[Index(0,0,2,0)]:',c['b'][Index(0,0,2,0)],c[Index(0,0,2,0)]
    print 'subset:\n',subset(c,mask=lambda key: True if key.spin in (0,3) else False)

def test_table_functions_string():
    a=Table({'i1':0,'i2':1})
    b=Table({'i3':0,'i4':1})
    c=union(a=a,b=b)
    print 'c:\n',c
    print 'reverse_table(c)"\n',reverse_table(c)
    print 'c["b"]["i4"],c["i4"]:',c['b']['i4'],c['i4']
    print 'subset:\n',subset(c,mask=lambda key: True if key!='i1' else False)
