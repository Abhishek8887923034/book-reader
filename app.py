from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Admin, Chapter, Book, Subscription
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from functools import wraps
import razorpay

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

UPLOAD_FOLDER = 'static/uploads/profiles'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize db with app
db.init_app(app)

# Razorpay configuration
razorpay_client = razorpay.Client(
    auth=(
        "rzp_test_XXXXXXXXXXXXX",  # Your Razorpay Test Key ID
        "XXXXXXXXXXXXXXXXXXXXXXX"   # Your Razorpay Test Secret Key
    )
)

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@app.context_processor
def utility_processor():
    return {
        'get_user': get_current_user
    }

@app.route("/")
def home():
    books = Book.query.all()
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template('index.html', books=books, User=User)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered", "warning")
            return redirect(url_for("register"))
        
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    books = Book.query.all()
    return render_template("dashboard.html", user=user, books=books)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('admin_id', None)
    flash("You have been logged out", "success")
    return redirect(url_for("login"))

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid email or password", "danger")
    
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if 'admin_id' not in session:
        flash("Please login as admin first", "warning")
        return redirect(url_for("admin_login"))
    
    books = Book.query.all()
    return render_template("admin_dashboard.html", books=books)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if 'admin_id' not in session:
        flash("Please login as admin first", "warning")
        return redirect(url_for("admin_login"))
    
    if request.method == "POST":
        title = request.form["title"]
        file = request.files["file"]
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash("Chapter uploaded successfully!", "success")
            return redirect(url_for("admin_dashboard"))
    
    return render_template("upload.html")

@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    
    # Plans
    plans = {
        'monthly': {
            'name': 'Monthly Plan',
            'description': 'Access all books for 30 days',
            'amount': 9900,  # ₹99 in paise
            'currency': 'INR',
            'period': 30,
        },
        'yearly': {
            'name': 'Yearly Plan',
            'description': 'Access all books for 365 days',
            'amount': 99900,  # ₹999 in paise
            'currency': 'INR',
            'period': 365,
        }
    }
    
    if request.method == "POST":
        plan_type = request.form.get("plan_type", "monthly")
        days = 30 if plan_type == "monthly" else 365
        
        # Create subscription without payment
        subscription = Subscription(
            user_id=user.id,
            end_date=datetime.utcnow() + timedelta(days=days),
            subscription_type=plan_type,
            status='active'
        )
        db.session.add(subscription)
        db.session.commit()
        
        flash("Subscription activated successfully!", "success")
        return redirect(url_for('dashboard'))
    
    return render_template("subscribe.html", plans=plans)

@app.route("/payment/success", methods=["POST"])
def payment_success():
    payment_id = request.form.get('razorpay_payment_id')
    order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')
    
    # Verify payment signature
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        })
        
        # Get payment details
        payment = razorpay_client.payment.fetch(payment_id)
        plan_type = payment['notes']['plan_type']
        user_id = int(payment['notes']['user_id'])
        
        # Add subscription
        user = User.query.get(user_id)
        days = 30 if plan_type == 'monthly' else 365
        
        subscription = Subscription(
            user_id=user.id,
            end_date=datetime.utcnow() + timedelta(days=days),
            subscription_type=plan_type,
            status='active',
            payment_id=payment_id,
            order_id=order_id
        )
        db.session.add(subscription)
        db.session.commit()
        
        flash("Payment successful! Your subscription is now active.", "success")
        return redirect(url_for('dashboard'))
        
    except:
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect(url_for('subscribe'))

@app.route('/book/<int:id>')
def read_book(id):
    if 'user_id' not in session:
        flash("Please login to read books", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    if not user.has_active_subscription():
        flash("Please subscribe to read books", "warning")
        return redirect(url_for("subscribe"))
    
    book = Book.query.get_or_404(id)
    
    # Get current chapter if specified in URL
    chapter_id = request.args.get('chapter', None)
    current_chapter = None
    if chapter_id:
        current_chapter = Chapter.query.get_or_404(chapter_id)
    else:
        current_chapter = book.chapters[0] if book.chapters else None
    
    # Get next and previous chapters
    next_chapter = None
    prev_chapter = None
    if current_chapter:
        chapters = book.chapters
        current_index = chapters.index(current_chapter)
        if current_index > 0:
            prev_chapter = chapters[current_index - 1]
        if current_index < len(chapters) - 1:
            next_chapter = chapters[current_index + 1]
    
    return render_template('read.html', 
                         book=book, 
                         current_chapter=current_chapter,
                         next_chapter=next_chapter,
                         prev_chapter=prev_chapter)

@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if 'admin_id' not in session:
        flash("Only admins can add books", "warning")
        return redirect(url_for("admin_login"))
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        content = request.form['content']
        
        new_book = Book(title=title, author=author, content=content)
        db.session.add(new_book)
        db.session.commit()
        
        flash("Book added successfully!", "success")
        return redirect(url_for('home'))
    
    return render_template('add_book.html')

@app.route("/manage_books")
def manage_books():
    if 'admin_id' not in session:
        flash("Please login as admin first", "warning")
        return redirect(url_for("admin_login"))
    
    books = Book.query.all()
    return render_template("manage_books.html", books=books)

@app.route("/delete_book/<int:id>", methods=["POST"])
def delete_book(id):
    if 'admin_id' not in session:
        flash("Please login as admin first", "warning")
        return redirect(url_for("admin_login"))
    
    book = Book.query.get_or_404(id)
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully!", "success")
    return redirect(url_for("manage_books"))

@app.route('/book/<int:book_id>/add_chapter', methods=['GET', 'POST'])
def add_chapter(book_id):
    if 'admin_id' not in session:
        flash("Only admins can add chapters", "warning")
        return redirect(url_for("admin_login"))
    
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        chapter = Chapter(
            title=title,
            content=content,
            book_id=book.id
        )
        db.session.add(chapter)
        db.session.commit()
        
        flash("Chapter added successfully!", "success")
        return redirect(url_for('edit_book', id=book.id))
    
    return render_template('add_chapter.html', book=book)

@app.route('/book/<int:id>/view')
def view_book(id):
    book = Book.query.get_or_404(id)
    return render_template('view_book.html', book=book)

@app.route('/book/<int:id>/edit', methods=['GET', 'POST'])
def edit_book(id):
    if 'admin_id' not in session:
        flash("Only admins can edit books", "warning")
        return redirect(url_for("admin_login"))
    
    book = Book.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update basic book info
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.content = request.form.get('content')
        
        # Handle chapters
        chapter_titles = request.form.getlist('chapter_title[]')
        chapter_contents = request.form.getlist('chapter_content[]')
        
        # Delete existing chapters
        for chapter in book.chapters:
            db.session.delete(chapter)
        
        # Add new chapters
        for title, content in zip(chapter_titles, chapter_contents):
            if title and content:  # Only add if both title and content exist
                chapter = Chapter(
                    title=title,
                    content=content,
                    book_id=book.id
                )
                db.session.add(chapter)
        
        db.session.commit()
        flash("Book and chapters updated successfully!", "success")
        return redirect(url_for('manage_books'))
    
    return render_template('edit_book.html', book=book)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))
    
    user = User.query.get(session['user_id'])
    
    user.name = request.form.get('name')
    user.phone = request.form.get('phone')
    user.address = request.form.get('address')
    user.bio = request.form.get('bio')
    
    dob = request.form.get('dob')
    if dob:
        user.dob = datetime.strptime(dob, '%Y-%m-%d')
    
    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for('profile'))

@app.route('/update_profile_pic', methods=['POST'])
def update_profile_pic():
    if 'user_id' not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))
    
    if 'profile_pic' not in request.files:
        flash('No file uploaded', 'warning')
        return redirect(url_for('profile'))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No file selected', 'warning')
        return redirect(url_for('profile'))
    
    if file and allowed_file(file.filename):
        user = User.query.get(session['user_id'])
        
        # Delete old profile pic if exists
        if user.profile_pic:
            old_pic_path = os.path.join(app.root_path, 'static', user.profile_pic)
            if os.path.exists(old_pic_path):
                os.remove(old_pic_path)
        
        # Save new profile pic
        filename = secure_filename(f"profile_{user.id}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = f"uploads/profiles/{filename}"
        db.session.commit()
        
        flash("Profile picture updated successfully!", "success")
    else:
        flash("Invalid file type", "warning")
    
    return redirect(url_for('profile'))

@app.route("/search")
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    books = Book.query
    if query:
        books = books.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%'))
        )
    if category:
        books = books.filter_by(category=category)
        
    books = books.all()
    return render_template('search.html', books=books, query=query)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        # Create admin
        admin = Admin.query.filter_by(email="abhisheknaduli@gmail.com").first()
        if not admin:
            admin = Admin(email="abhisheknaduli@gmail.com")
            admin.set_password("Abhi@123")
            db.session.add(admin)
            db.session.commit()
        
        # Create test user with subscription
        test_user = User.query.filter_by(email="vikas@gmail.com").first()
        if not test_user:
            test_user = User(email="vikas@gmail.com")
            test_user.set_password("Ram@123")
            db.session.add(test_user)
            db.session.commit()
            
            # Add active subscription
            subscription = Subscription(
                user_id=test_user.id,
                end_date=datetime.utcnow() + timedelta(days=30),
                subscription_type="monthly",
                status="active"
            )
            db.session.add(subscription)
            db.session.commit()
            
        # Create test book with chapters
        if not Book.query.first():
            test_book = Book(
                title="Test Book",
                author="Test Author",
                content="Welcome to the test book.",
                category="Fiction",
                published_date=datetime.utcnow().date(),
                rating=4.5,
                total_ratings=1
            )
            db.session.add(test_book)
            db.session.commit()
            
            # Add some test chapters
            chapters = [
                Chapter(
                    title="Chapter 1: Introduction",
                    content="This is the first chapter of our test book.",
                    book_id=test_book.id
                ),
                Chapter(
                    title="Chapter 2: Main Story",
                    content="The story continues in chapter 2...",
                    book_id=test_book.id
                ),
                Chapter(
                    title="Chapter 3: Conclusion",
                    content="Finally, we reach the end in chapter 3.",
                    book_id=test_book.id
                )
            ]
            for chapter in chapters:
                db.session.add(chapter)
            db.session.commit()
            
    app.run(debug=True)
