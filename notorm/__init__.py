import psycopg2
from collections import defaultdict
import datetime
import inspect
import json
from decimal import Decimal
from psycopg2.extras import DateTimeRange
import weakref

db = None

class jsonable(object):
    pass

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
    def __init__(self, column_name, build=True, reverse=None):
        super(ForeignKeyList, self).__init__(column_name, build=build)
        self.reverse = reverse

    def build_relationships(self, attr_name, r, last_r, set_node = None):
        if hasattr(r, self.column_name):
            next_node = getattr(r, self.column_name)
            if next_node is not None and (last_r is None or next_node != getattr(last_r, self.column_name)):
                getattr(set_node, attr_name).append(next_node)
                if self.reverse:
                    setattr(next_node, "_" + self.reverse, weakref.ref(set_node))

                if hasattr(next_node, 'build_relationships') and self.build:
                    next_node.build_relationships(r, None)
            elif next_node is not None and hasattr(next_node, 'build_relationships'):
                next_node.build_relationships(r, last_r, getattr(set_node, attr_name)[-1])
        
class ForeignKeyDefaultDict(ForeignKey):
    def __init__(self, column_name, group_field, data_type, build=True):
        super(ForeignKeyDefaultDict, self).__init__(column_name, build=build)
        self.group_field = group_field
        self.data_type = data_type

    def build_relationships(self, attr_name, r, last_r, set_node = None):
        if hasattr(r, self.column_name):
            next_node = getattr(r, self.column_name)
            if next_node is not None and (last_r is None or next_node != getattr(last_r, self.column_name)):
                getattr(set_node, attr_name)[getattr(next_node, self.group_field)] = next_node
                if hasattr(next_node, 'build_relationships') and self.build:
                    next_node.build_relationships(r, None)
            elif next_node is not None and hasattr(next_node, 'build_relationships'):
                next_node.build_relationships(r, last_r, getattr(set_node, attr_name)[getattr(next_node, self.group_field)])

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
        for field, value in self._fields.items():
            if value in (dict, list, set):
                self.__dict__[field] = args.get(field, value())
            else:
                self.__dict__[field] = args.get(field, value)

        for attr_name, attr_value in inspect.getmembers(self.__class__):
            if isinstance(attr_value, ForeignKeyList):
                self.__dict__[attr_name] = []
            if isinstance(attr_value, ForeignKeyObject):
                self.__dict__[attr_name] = None
            if isinstance(attr_value, ForeignKeyDictList):
                self.__dict__[attr_name] = defaultdict(list)
            if isinstance(attr_value, ForeignKeyDefaultDict):
                self.__dict__[attr_name] = defaultdict(attr_value.data_type)

    def _asdict(self):
        return self.__dict__
    
    def __getattr__(self, name):
        if not name in self._fields:
            raise AttributeError("Field not Defined: %s" % name)
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

    @classmethod
    def loads(cls, data_string):
        data = json.loads(data_string)
        return cls(**data)

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

    def on_insert(self):
        pass


    def dumps(self):
        return json_dumps(self)


def json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, record):
        return obj._asdict()
    if isinstance(obj, datetime.time):
        return str(obj)
    if isinstance(obj, datetime.datetime):
        return str(obj)
    if isinstance(obj, datetime.date):
        return str(obj)
    if isinstance(obj, DateTimeRange):
        return {'lower': obj.lower, 'upper': obj.upper}
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    if isinstance(obj, defaultdict):
        return dict(obj)
    if isinstance(obj, jsonable):
        return obj.__dict__
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, weakref.ref):
        return obj().key

    raise TypeError("Can't convert Object to JSON")


def json_dumps(obj, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None,
               separators=None, encoding="utf-8", default=None, sort_keys=False, **kw):
    out = json.dumps(obj, default=json_default)
    return out

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
