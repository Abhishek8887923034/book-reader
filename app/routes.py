from flask import Blueprint, render_template, request, redirect, url_for
from app.models import db, Book

main = Blueprint('main', __name__)

@main.route('/')
def home():
    books = Book.query.order_by(Book.created_date.desc()).all()
    return render_template('index.html', books=books)

@main.route('/book/<int:id>')
def read_book(id):
    book = Book.query.get_or_404(id)
    return render_template('read.html', book=book)

@main.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        content = request.form['content']
        
        new_book = Book(title=title, author=author, content=content)
        db.session.add(new_book)
        db.session.commit()
        
        return redirect(url_for('main.home'))
    
    return render_template('add_book.html') 