from app import db
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from user_right import UserRight
import os
from flask import url_for


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return '<User: %r>' % self.role_name


class Status(db.Model):
    __tablename__ = 'statuses'
    id = db.Column(db.Integer, primary_key=True)
    status_name = db.Column(db.String(25), nullable=False)
    
    def __repr__(self):
        return '<Review: %r>' % self.status_name



class Books_has_Genres(db.Model):
    __tablename__ = 'books_has_genres'
    id = db.Column(db.Integer, primary_key=True)
    books_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    genres_id = db.Column(db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'), nullable=False)

    book = db.relationship('Book')
    genre = db.relationship('Genre')



class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(mysql.YEAR, nullable=False)
    publisher = db.Column(db.String(50), nullable=False)
    author = db.Column(db.String(50), nullable=False)
    rating_sum = db.Column(db.Integer, nullable=False, default=0)
    rating_num = db.Column(db.Integer, nullable=False, default=0)
    amount = db.Column(db.Integer, nullable=False)
    cover_id = db.Column(db.Integer, db.ForeignKey('covers.id', ondelete='CASCADE'))

    def __repr__(self):
        return '<Book: %r>' % self.title
    
    def get_img(self):
        img = Cover.query.filter_by(id=self.cover_id).first()
        if img:
            img = img.url
        return img

    @property
    def rating(self):
        if self.rating_num > 0:
            return round((self.rating_sum / self.rating_num), 2)
        return 0

    reviews = db.relationship('Review')
    books_genres = db.relationship('Books_has_Genres')
    cover = db.relationship('Cover')




class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(25), nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    middle_name = db.Column(db.String(25), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return '<User: %r>' % self.login

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role_id == 1
    
    @property
    def is_moder(self):
        return self.role_id == 2

    def can(self, action):
        users_policy = UserRight()
        method = getattr(users_policy, action, None)
        if method is not None:
            return method()
        return False


class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    genre_name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<Genre: %r>' % self.genre_name


class Cover(db.Model):
    __tablename__ = 'covers'
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    md5_hash = db.Column(db.String(150), nullable=False)

    def __repr__(self):
        return '<Cover: %r>' % self.file_name

    @property
    def storage_filename(self):
        _, ext = os.path.splitext(self.file_name)
        return _ + ext

    @property
    def url(self):
        return url_for('image', cover_id=self.id)



class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=sa.sql.func.now())
    #status_id = db.Column(db.Integer, db.ForeignKey('statuses.id', ondelete='CASCADE'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return f'<Reviews: {self.user_id} {self.created_at}>'
    
    def get_user(self):
        return db.session.execute(db.select(User).filter_by(id=self.user_id)).scalar().login

    @property
    def is_ok(self):
        return self.status_id == 2