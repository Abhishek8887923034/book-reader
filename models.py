from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100))
    dob = db.Column(db.Date)
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.String(200))  # Path to profile picture
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    subscription = db.relationship('Subscription', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_active_subscription(self):
        if not self.subscription:
            return False
        current_sub = self.subscription[-1] if self.subscription else None
        if current_sub and current_sub.status == 'active' and current_sub.end_date > datetime.utcnow():
            return True
        return False

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100))
    content = db.Column(db.Text)
    chapters = db.relationship('Chapter', backref='book', lazy=True, order_by="Chapter.created_date")
    category = db.Column(db.String(50))
    cover_image = db.Column(db.String(200))
    published_date = db.Column(db.Date)
    rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    subscription_type = db.Column(db.String(20))
    payment_id = db.Column(db.String(100))
    order_id = db.Column(db.String(100))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class ReadingProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    last_read = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    position = db.Column(db.Integer)  # Paragraph number
    note = db.Column(db.Text)

class ReadingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    books = db.relationship('Book', secondary='reading_list_books')

reading_list_books = db.Table('reading_list_books',
    db.Column('list_id', db.Integer, db.ForeignKey('reading_list.id')),
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'))
)

class UserFollowing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    following_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    activity_type = db.Column(db.String(50))  # read, review, bookmark etc
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text)
    type = db.Column(db.String(50))  # new_follower, new_book, etc
    read = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

