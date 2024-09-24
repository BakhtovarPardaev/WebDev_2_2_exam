import math
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import MetaData, distinct, desc
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import markdown


app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')


convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app, db)

from auth import auth_bl as auth_bl, init_login_manager
from book import book_bl

app.register_blueprint(auth_bl)
app.register_blueprint(book_bl)


init_login_manager(app)

from models import *
PER_PAGE = 8


@app.route('/')
def index():
    genres = Genre.query.all()
    books_genres = Books_has_Genres.query.all()
    total_books = Book.query.count()
    years_available = db.session.query(distinct(Book.year)).order_by(desc(Book.year)).all()
    years_list = [str(year[0]) for year in years_available]


    current_page = request.args.get('page', 1, type=int)
    books_on_page = db.session.execute(db.select(Book).order_by(desc(Book.year)).limit(PER_PAGE).offset(PER_PAGE * (current_page - 1))).scalars().all()
    total_pages = math.ceil(total_books / PER_PAGE)

    search_title = request.args.get('title', '')
    selected_genres = [int(x) for x in request.args.getlist('genre_id')]
    selected_years = request.args.getlist('year')
    price_min = request.args.get('amount_from', '')
    price_max = request.args.get('amount_to', '')
    search_author = request.args.get('author', '')
    has_books = len(list(books_on_page)) > 0

    return render_template(
        'index.html',
        books=books_on_page,
        genres=genres,
        years=years_list,
        book_genre=books_genres,
        page=current_page,
        page_count=total_pages,
        rating=Book.rating,
        title=search_title,
        genres_list=selected_genres,
        years_list=selected_years,
        amount_from=price_min,
        amount_to=price_max,
        author=search_author,
        flag=has_books
    )


@app.route('/media/images/<cover_id>')
def image(cover_id):
    cover = Cover.query.get_or_404(cover_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], cover.file_name)


@app.route('/reviews')
@login_required
def reviews():
    user_reviews = Review.query.filter_by(user_id=current_user.id).all()

    reviews_markdown = []
    for review in user_reviews:
        reviews_markdown.append({
            'get_user': review.get_user,
            'rating': review.rating,
            'text': markdown.markdown(review.text),
            'status': review.status_id
        })

    return render_template('reviews/reviews.html', reviews=reviews_markdown)


@app.route('/reviewmoderation')
@login_required
def reviews_moder():
    pending_reviews_count = Review.query.filter_by(status_id=1).count()

    current_page = request.args.get('page', 1, type=int)
    pending_reviews = Review.query.filter_by(status_id=1).limit(PER_PAGE).offset(PER_PAGE * (current_page - 1)).all()
    total_pages = math.ceil(pending_reviews_count / PER_PAGE)

    reviews_markdown = []
    for review in pending_reviews:
        reviews_markdown.append({
            'id': review.id,
            'get_user': review.get_user,
            'rating': review.rating,
            'text': markdown.markdown(review.text),
            'status': review.status_id
        })

    return render_template('reviews/moder.html', reviews=reviews_markdown, page=current_page, page_count=total_pages)


@app.route('/checkreview/<review_id>')
@login_required
def check_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return render_template("404.html")

    return render_template(
        "reviews/edit.html", 
        review_id=review_id, 
        user=review.get_user(), 
        rating=review.rating, 
        text=markdown.markdown(review.text), 
        status=review.status_id
    )


@app.route('/checkreview/approve/<review_id>', methods=['GET', 'POST'])
@login_required
def approve(review_id):
    Review.query.filter(Review.id == review_id).update({'status_id': 2})
    db.session.commit()
    return redirect(url_for('reviews_moder'))


@app.route('/checkreview/reject/<review_id>', methods=['GET', 'POST'])
@login_required
def reject(review_id):
    Review.query.filter(Review.id == review_id).update({'status_id': 3})
    db.session.commit()
    return redirect(url_for('reviews_moder'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', title='Страница не найдена')







