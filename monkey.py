#copyright@kades
#encoding:utf-8


import pymongo, bson
from mon_config import *


class InsertException(Exception):
    """ raise insert exception to avoid user change their database structure randomly
        Attibutes:
            collection_name: a str indicating the name of a collection being inserted

    """
    def __init__(self, collection_name):
        """init InsertException with bash"""
        Exception.__init__(self)
        self.collection_name = collection_name

    def reason_collection_not_exist(self):
        """print Exception reason"""
        print 'waring: no collections %s in the database'%self.collection_name

    def reason_collection_structure_unsimilar(self):
        """ collection structure un similar """
        print 'warming: structure is not similar,please check you code'

class UpdateException(Exception):
    """ raise update exception
        Attibutes:
            collection_name: a str indicating the name of a collection being inserted
    
    """
    def __init__(self, collection_name):
        """init InsertException with bash"""
        Exception.__init__(self)
        self.collection_name = collection_name

    def reason_collection_not_exist(self):
        """print Exception reason"""
        print 'waring: no collections %s in the database'%self.collection_name

    def reason_collection_structure_unsimilar(self):
        """ collection structure un similar """
        print 'warming: structure is not similar,please check you code'


class DBModel():
    """ the fundamental opration of the database
    
        Attributes:
            da_name: a str indicating the name of database
            database: a database object indicating the database
    """
    def __init__(self, db_name):
        self.db_name = db_name
        self.database = None

    def link_database(self):
        try:
            database = pymongo.Connection('localhost', 27017)
            self.database = database[self.db_name]
            #build database 
            #if not exist, then make it exist
            collection_names = "&".join([item for item in self.database.collection_names()])
            for keys in COLLECTION_NAME.keys():
                if collection_names.find(keys) == -1:
                    self.database[keys].insert(COLLECTION_NAME[keys])
                else:
                    pass
        except Exception, e:
            print 'error when connection to mongo db'

    def insert_collection(self, cols_name, insert_cols):
        """ insert into collection collectionName values collections
        
            insert operation, and definition of the Exception when the user
            insert into a collection that doesn't exsit in the design file 
            mon_config.py

            Args:
                cols_name   :  a string indicating the name of collection which will be inserted
                insert_cols :  a dict indicating the content whichi will be inserted in to cols_name

            Returns:
                None

            Raise:
                InsertException: just a warning if cols_name doesn't exsit in database
        """
        collection_names = "&".join([item for item in self.database.collection_names()])
        isIn = collection_names.find(cols_name)
        try:
            if isIn == -1: 
                raise InsertException(cols_name)
        except InsertException, e:
            print e.reason_collection_not_exist()
        else:
            new_cols = insert_cols
            #print insert_cols
            is_already_in = self.find_collection(cols_name, insert_cols)
            if is_already_in:
                print 'the collection has been inserted into the database'
                return
            try:
                if self.dict_structure_similar(COLLECTION_NAME[cols_name], new_cols):
                    collection = self.database[cols_name]
                    try:
                        ret = collection.insert(insert_cols)
                        return ret
                    except Exception, e:
                        print e
                else:
                    raise InsertException(cols_name)
            except InsertException, e:
                print e.reason_collection_structure_unsimilar()
            return None

    def dict_structure_similar(self, dict_r, dict_t):
        """ just whether the dict_r has the same structure as dict_t has

            because we need to keep the normative of develop, so when operate the databse,we need to
            check the value(insert, update and so on) and the collection's dict has the same struture
            
            Args:
                dict_r: a dict indicating the frist one
                dict_t: a dict indicating the second one

            Returns:
                True if the same or False

            Raise:
                None
        """
        first_keys = [k for k in sorted(dict_r.keys())]
        second_keys = [k for k in sorted(dict_t.keys())]
        if first_keys == second_keys:#if the dicts's keys are the same
            for item in first_keys:
                if type(dict_r[item]) != type(dict_t[item]):
                    return False
            return True
        else:
            return False
    
    def update_dict_values(self, target_raw, update_values):
        """  update target_raw's value with update_values

            we need to control the consistent of databse
            so we need to update the collection's value but not the own collection
            which means if target_raw is {'sd':'sdf','sdf':'ss'}, and update_values is {'sd':'tt'},
            the collection will trun into {'sd':'tt','sdf':'ss'} but not {'sd':'tt'}

            Args:
                target_raw: a dict indicating the collection
                update_values: a dict indicating the update values

            Return:
                None: if the update_values is not the sub_tree of the target_raw's if they are regarded as a tree.
                new_target_raw: new collection

            Raise:
                None
        """
        for key_update in update_values.keys():
            found = False
            for key_raw in target_raw.keys():
                if key_update == key_raw:
                    found = True
                    break
            if found:
                up_values = update_values[key_update]
                up_values = u"".join(up_values) if isinstance(up_values, str) else update_values[key_update]
                if type(up_values) != type(target_raw[key_raw]):
                    return None
                elif isinstance(up_values, dict):
                    update_ans = self.update_dict_values(target_raw[key_raw], up_values)
                    if not update_ans:
                        return None
                    else:
                        target_raw[key_raw] = update_ans
                else:
                    target_raw[key_raw] = up_values
            else:
                target_raw[key_update] = update_values[key_update]
        return target_raw
    def auto_dereference(self, ObjectId):
        """ auto de reference """
        return self.database.dereference(ObjectId)

    def get_count(self, cols_name):
        """ get the number of the database """
        return self.database[cols_name].find().count()

    
    def update_collection(self, cols_name, update_condition, update_value):
        """ update the collection

            just as in insert_collection, we need to keep the consistent of database structure
            when update the collection ,we need to supply the search condition and the new value,
            but because mongo will replace the collection's value with new value ,which I think is
            inappropriate.We need to keep the struture stable.
            if the collection is empty ,do nothng.

            Args:
                cols_name   : a string indicating the collection's name gona to be updated
                update_cols : a dict indicating the content gona to be updated it contains {search_conditon, new value}
            
            Returns:
                None

            Raise:
                UpdateException
        """
        collection_names = '&'.join([item for item in self.database.collection_names()])
        try:
            if collection_names.find(cols_name) == -1:
                raise UpdateException(cols_name)
        except Exception, e:
            print e.reason_collection_not_exist()
        else:
            find_raws = self.find_collection(cols_name, update_condition)
            if not find_raws:
                return
            else:
                for item in find_raws:
                    update_ans = self.update_dict_values(item, update_value)
                    if update_ans:
                        st = self.database[cols_name].update(update_condition , update_ans)
                pass  
        pass

    def find_collection(self, cols_name, find_condition, **sort_condition):
        """ find value in collection cols_name

            find_condition is optional, if None,meaning find all,else find only one matching the find_condtion
            sort_condition is optional too, just for sorting

            Args:
                cols_name      : a string indicating the collection's name
                find_condition : a dict 
                sort_condition : a dict indicating condition for sorting if we want to sort the search outcome by name
                                the sort_condition show be like this: {"name":1} or {"name":0}
            Returns:
                find_raws      : a list contains the outcome

            Raise:
                Exception known
        """
        conditions = [pymongo.ASCENDING, pymongo.DESCENDING]
        try:
            sort_c = [(keys, conditions[sort_condition[keys]]) for keys in sort_condition.keys()]
            if find_condition :
                if find_condition is not "ONE":
                    if sort_c:
                        return [item for item in self.database[cols_name].find(find_condition).sort(sort_c)]
                    else:
                        outcome = self.database[cols_name].find(find_condition)
                        if outcome:
                            t = [item for item in outcome]
                            return t
                        else:
                            return []
                else:
                    return self.database[cols_name].find_one()
            else:
                if sort_c:
                    return [item for item in self.database[cols_name].find().sort(sort_c)]
                else: 
                    return [item for item in self.database[cols_name].find()]
        except Exception, e:
            print 'Error when search the collection %s !'%cols_name
            
    def remove_collection(self, cols_name, delete_cols):
        self.database[cols_name].remove(delete_cols)
        pass


'''
st = DBModel("tets")
st.link_database()
dic = {
    'name':'keyiss',
    'pattern':'yesss',
    'dict': {'name':'sdf'},
    'link_collection':'collection_2'}
sts = 0

dicr = {
    'name': 'nihaoma',

    'pattern':'fuckyou',
    'dict': {'name':'sdfsdfsddfsdfsdf'},
    }
while True:
    print '1: find 2:insert 3:update'
    choise = int(raw_input())
    if choise == 1:

        print st.find_collection('collection_1', "", pattern =1)
    elif choise == 2:
        sts += 1
        dics = {}
        dics = dic
        dics['pattern'] += str(sts) + dic['pattern']
        st.insert_collection('collection_1',dics)
    else:
        st.update_collection('collection_1', {'pattern':'yes'},dicr)

print 'main function begins'
'''
