import sys

from sqlalchemy import Column, ForeignKey, Integer, String

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship

from sqlalchemy import create_engine

Base = declarative_base()

#create category table
class Category(Base):
	__tablename__ = 'category'
	id = Column(Integer, primary_key = True)
	name = Column(String(40), nullable = False)
	description = Column(String(80))
	items = relationship('Item', backref='Category', lazy='dynamic')

#create item table
class Item(Base):
	__tablename__ = 'item'
	id = Column(Integer, primary_key = True)
	name = Column(String(40), nullable = False)
	description = Column(String(80))
	category_id = Column(Integer, ForeignKey('category.id'))
	category = relationship('Category')
	@property
	def serialize(self):
		#Returns object data in easily serializeable format
		return{
			'name' : self.name,
			'description' : self.description,
			'id' : self.id,
			'category' : self.category.name
		} 

#create user table
class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, primary_key = True)
	name = Column(String(80), nullable = False)
	email = Column(String(80))
	picture = Column(String(250))
		
engine = create_engine('postgresql://catalog:apassword@localhost/catalog')

Base.metadata.create_all(engine)
