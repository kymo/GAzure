#encoding:utf-8
from pymmseg import mmseg
import time


mmseg.dict_load_defaults()


text = '速发算法优化遗传速度地方meandfjl leant'

now_s = time.time()
print now_s
ans = {}
for tok in mmseg.Algorithm(text):
    print type(tok.text)
    ans[tok.text] = [] if not ans.has_key(tok.text) else ans[tok.text]
    ans[tok.text].append(tok.start)
    ans[tok.text].append(tok.end)
    
    print tok.text, tok.start, tok.end
for key in ans.keys():
    print key
now_t = time.time()
print ans
print now_t
print now_t - now_s

st = 'sdfsdf;sdfsdf;sdfsdf;'
ts =  [item for item in st.split(';')]
print ts



import pymongo
import bson
from monkey import DBModel
tt = pymongo.Connection('localhost', 27017)
st = tt.g_azure
mis = st.index.find()
for item in mis:
    print item, item['key']

'''
db = DBModel('g_azure')
db.link_database()
for item in db.find_collection('mission', {'public' : 1}):
    print item
    st = db.find_collection('index', {'key' : 'yes'})
    
    if st:
        temp = st[0]['mission'].append(bson.dbref.DBRef('mission', item['_id']))
        db.update_collection('index', {'key':'yes'},{'mission' : temp})
    else:
        db.insert_collection('index',  {'key':'yes', 'mission' :[bson.dbref.DBRef('mission', item['_id'])], 'bit':2,'position':[4]})

st = [{'key':'sdf','sdfsd':'sdf'}, {'key':'sdf','sfsdf':'sdfds'}]
tr = 'sdf' in [item['key'] for item in st]
print tr
'''
