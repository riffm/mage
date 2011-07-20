# -*- codingL: utf-8 -*-

from sqlalchemy import orm, types, create_engine
from sqlalchemy.orm.query import Query

from .base import CommandDigest
from .utils import cached_property


class DBSession(orm.session.Session):

    def get(self, query, **kwargs):
        if not isinstance(query, Query):
            query = self.query(query)
        if kwargs:
            query = query.filter_by(**kwargs)
        return query.first()


def import_string(module_name, item_name=None):
    if item_name is None:
        return __import__(module_name, None, None, ['*'])
    return getattr(__import__(module_name, None, None, ['*']), item_name)


def construct_maker(databases, models=None, query_cls=Query, engine_params=None,
                    session_class=DBSession):
    '''
    databases - str with db uri or dict.
    models - str name of models package (module), default is 'module'
    query_cls - additional query class
    engine_params - additional engine params
    '''
    models = models or 'models'
    engine_params = engine_params or {}
    db_dict = {}
    if isinstance(databases, basestring):
        return orm.sessionmaker(class_=session_class, query_cls=query_cls,
                                autoflush=False)
    for ref, uri in databases.items():
        md_ref = '.'.join(filter(None, [models, ref]))
        metadata = import_string(md_ref, 'metadata')
        engine = create_engine(uri, **engine_params)
        engine.logger.name += '(%s)' % ref
        for table in metadata.sorted_tables:
            db_dict[table] = engine
    return orm.sessionmaker(class_=session_class, query_cls=query_cls, binds=db_dict,
                            autoflush=False)


class Commands(CommandDigest):
    '''
    sqlalchemy operations on models:
    db_name - key from databases dict, provided during init
    '''

    def __init__(self, databases, initial=None, engine_params=None, models=None):
        '''
        :*base_class* - base class of models (usualy result of declarative_meta())

        :*databases* - dict[db_name:db_uri]

        :*initial* - function that takes session object and populates 
                     session with models instances
        '''
        self.databases = databases if isinstance(databases, dict) else {'':databases}
        self.engine_params = engine_params or {}
        self.engine_params['echo'] = True
        self.models = models or 'models'
        self.initial = initial

    def command_sync(self, db=None):
        '''
        $ python manage.py sqlalchemy:sync [--db=name]

        syncs models with database
        '''
        for ref, uri in self.databases.items():
            if db and ref != db:
                continue
            md_ref = '.'.join(filter(None, [self.models, ref]))
            metadata = import_string(md_ref, 'metadata')
            engine = create_engine(uri, **self.engine_params)
            engine.logger.logger.name += '(%s)' % ref
            metadata.create_all(engine)

    def command_drop(self, db=None):
        '''
        $ python manage.py sqlalchemy:drop [--db=name]

        drops model's tables from database
        '''
        for ref, uri in self.databases.items():
            if db and ref != db:
                continue
            md_ref = '.'.join(filter(None, [self.models, ref]))
            metadata = import_string(md_ref, 'metadata')
            engine = create_engine(uri, **self.engine_params)
            engine.logger.logger.name += '(%s)' % ref
            metadata.create_all(engine)
            metadata.drop_all(engine, checkfirst=True)

    def command_initial(self, db=None):
        '''
        $ python manage.py sqlalchemy:initial [--db=name]

        populates models with initial data
        '''
        if self.initial:
            databases = db if db else self.databases
            session = construct_maker(databases, models=self.models,
                                      engine_params=self.engine_params)()
            #TODO: implement per db initial
            self.initial(session)

    def command_schema(self, model_name=None, db=None):
        '''
        $ python manage.py sqlalchemy:schema [model_name]

        shows CREATE sql script for model(s)
        '''
        from sqlalchemy.schema import CreateTable
        for ref, uri in self.databases.items():
            if db and not db == ref:
                continue
            md_ref = '.'.join(filter(None, [self.models, ref]))
            metadata = import_string(md_ref, 'metadata')
            for table in metadata.sorted_tables:
                if model_name:
                    if model_name == table.name:
                        print '-- database %r' % ref
                        print str(CreateTable(table))
                else:
                    print '-- database %r' % ref
                    print str(CreateTable(table))

    def command_reset(self, db=None):
        '''
        $ python manage.py sqlalchemy:reset [--db=name]
        '''
        self.command_drop(db)
        self.command_sync(db)
        self.command_initial(db)



# COLUMNS

from sqlalchemy import String, Integer, Text, Boolean, Date, DateTime
from sqlalchemy import Column, Table, ForeignKey
from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, \
                       ForeignKeyConstraint
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import object_session, composite
from sqlalchemy.orm.query import Query, _generative
from sqlalchemy.orm.util import _class_to_mapper
from sqlalchemy import orm, types, create_engine
from sqlalchemy.ext import declarative
from sqlalchemy.ext.associationproxy import association_proxy


def relation(*args, **kwargs):
    kwargs.setdefault('passive_deletes', 'all')
    return orm.relation(*args, **kwargs)


class StringList(types.TypeDecorator):

    impl = types.String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return ','.join(value)

    def process_result_value(self, value, dialect):
        if value is not None:
            return filter(None, value.split(','))


class IntegerList(types.TypeDecorator):

    impl = types.String

    def process_bind_param(self, value, dialect):
        if value is not None:
            return ','.join(str(item) for item in value)

    def process_result_value(self, value, dialect):
        if value is not None:
            return [int(item) for item in value.split(',') if item]


def get_html_class(safe_marker, impl_=types.Text):

    class HtmlTextJinja(types.TypeDecorator):
        '''Represants safe to render in template html markup'''

        impl = impl_

        def process_result_value(self, value, dialect):
            if value is not None:
                return safe_marker(value)

        def process_bind_param(self, value, dialect):
            if value is not None:
                return unicode(value)

    return HtmlTextJinja

try:
    from jinja2 import Markup
except ImportError:
    pass
else:
    HtmlTextJinja = get_html_class(Markup)
    HtmlStringJinja = get_html_class(Markup, impl_=types.String)
