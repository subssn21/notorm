
import psycopg2
from collections import OrderedDict, namedtuple, defaultdict
import copy
import datetime
import inspect
import momoko
from tornado import gen

db = None

class InfDateAdapter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
    def getquoted(self):
        if self.wrapped == datetime.date.max:
            return "'infinity'::date"
        elif self.wrapped == datetime.date.min:
            return "'-infinity'::date"
        else:
            return psycopg2.extensions.DateFromPy(self.wrapped).getquoted()

class ForeignKey(object):
    def __init__(self, column_name, build=True):
        self.column_name = column_name
        self.build = build

class ForeignKeyList(ForeignKey):
    def build_relationships(self, attr_name, r, last_r, set_node = None):
        if hasattr(r, self.column_name):
            next_node = getattr(r, self.column_name)
            if next_node is not None and (last_r is None or next_node != getattr(last_r, self.column_name)):
                getattr(set_node, attr_name).append(next_node)
                if hasattr(next_node, 'build_relationships') and self.build:
                    next_node.build_relationships(r, None)
            elif next_node is not None and hasattr(next_node, 'build_relationships'):
                next_node.build_relationships(r, last_r, getattr(set_node, attr_name)[-1])
        
class ForeignKeyObject(ForeignKey):
    def build_relationships(self, attr_name, r, last_r, set_node = None):
        if hasattr(r, self.column_name) and getattr(r, self.column_name) is not None:
            next_node = getattr(r, self.column_name)
            if next_node is not None and (last_r is None or next_node != getattr(last_r, self.column_name)):
                setattr(set_node, attr_name, next_node)
            if hasattr(next_node, 'build_relationships') and self.build:
                next_node.build_relationships(r, last_r, getattr(set_node, attr_name))

class ForeignKeyDictList(ForeignKey):
    def __init__(self, column_name, group_field, build=True):
        super(ForeignKeyDictList, self).__init__(column_name, build=build)
        self.group_field = group_field
    def build_relationships(self, attr_name, r, last_r, set_node = None):
        if hasattr(r, self.column_name):
            next_node = getattr(r, self.column_name)
            if next_node is not None and (last_r is None or next_node != getattr(last_r, self.column_name)):
                getattr(set_node, attr_name)[getattr(next_node, self.group_field)].append(next_node)
                if hasattr(next_node, 'build_relationships'):
                    next_node.build_relationships(r, None)
            elif next_node is not None and hasattr(next_node, 'build_relationships'):
                next_node.build_relationships(r, last_r, getattr(set_node, attr_name)[-1])

class record(object):
    def __init__(self, **args):
        self.__dict__.update(self._fields)

        for attr_name, attr_value in inspect.getmembers(self.__class__):
            if isinstance(attr_value, ForeignKeyList):
                self.__dict__[attr_name] = []
            if isinstance(attr_value, ForeignKeyObject):
                self.__dict__[attr_name] = None
            if isinstance(attr_value, ForeignKeyDictList):
                self.__dict__[attr_name] = defaultdict(list)
        
        self.__dict__.update(args)

    def _asdict(self):
        return self.__dict__
    
    def __getattr__(self, name):
        return self._fields[name]

    def update(self, **args):
        for k,v in args.items():
            setattr(self, k, v)
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cursor.execute(self.update_qry, self._asdict())
        
    def __repr__(self):
        return str(self._asdict())
        
    @classmethod
    def insert(cls, **args):
        obj = cls(**args)
        obj.save()

    @classmethod 
    def update_or_insert(cls, id, **args):
        if id:
            mar = cls.get(id)
            #Update the data
            mar.update(**args)
        else:
            cls.insert(**args)

    def build_relationships(self, r, last_r, set_node = None):
        """
        r: The Record from the database
        last_r: The previous record from the database
        """
        if not set_node:
            set_node = self
        #Go through each Class Attribute for this class
        for attr_name, attr_value in inspect.getmembers(self.__class__):
            if isinstance(attr_value, ForeignKey):
                attr_value.build_relationships(attr_name, r, last_r, set_node)

    def save(self):
        if self.id:
            self.update()
        else:
            cursor = db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
            cursor.execute(self.insert_qry, self.__dict__)
            results = cursor.fetchone()
            if results:
                self.id = results[0]

class AsyncRecord(record):
    @gen.coroutine
    def update(self, **args):
        for k,v in args.items():
            setattr(self, k, v)
        
        cursor = yield db.execute( 
                                self.update_qry, 
                                self._asdict(), 
                                cursor_factory=psycopg2.extras.NamedTupleCursor)        
        
    @gen.coroutine
    def save(self):
        if self.id:
            self.update()
        else:
            cursor = yield db.execute(
                                    self.insert_qry, 
                                    self.__dict__, 
                                    cursor_factory=psycopg2.extras.NamedTupleCursor)        
            results = cursor.fetchone()
            if results:
                self.id = results[0]


def json_default(obj):
    if isinstance(obj, record):
        return obj.__dict__
    if isinstance(obj, datetime.time):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return str(obj)
    if isinstance(obj, datetime.date):
        return str(obj)

def build_relationships(results, root_class):
    r_list = []
    current_root = None
    last_r = None
    if not isinstance(root_class, (list,tuple)):
        root_class = [root_class]
    for r in results:
        for root in root_class:
            if getattr(r, root) and current_root != getattr(r, root):
                current_root = getattr(r, root)
                r_list.append(current_root)
                last_r = None
        if current_root:
            current_root.build_relationships(r, last_r)
        last_r = r
    return r_list
