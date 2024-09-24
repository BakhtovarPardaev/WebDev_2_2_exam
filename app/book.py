from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Genre, Book, Books_has_Genres, Cover, Review
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from auth import check_rights
from app import db, app
import markdown
import hashlib
import bleach
import os

book_bl = Blueprint('book', __name__, url_prefix='/book')


class ImageSaver:
    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file

    def _find_by_md5(self):
        self.md5_hash = hashlib.md5(self.uploaded_file.read()).hexdigest()
        self.uploaded_file.seek(0) 

        return Cover.query.filter(Cover.md5_hash == self.md5_hash).first()

    def save_image(self):
        existing_image = self._find_by_md5()
        if existing_image:
            return existing_image.id

        sanitized_name = secure_filename(self.uploaded_file.filename)

        last_cover = Cover.query.order_by(Cover.id.desc()).first()
        new_id = (last_cover.id + 1) if last_cover else 1
        new_cover = Cover(
            id=new_id,
            file_name=f"{new_id}_{sanitized_name}",
            mime_type=self.uploaded_file.mimetype,
            md5_hash=self.md5_hash
        )

        image_save_path = os.path.join(app.config['UPLOAD_FOLDER'], new_cover.storage_filename)
        self.uploaded_file.save(image_save_path)
        
        db.session.add(new_cover)
        db.session.commit()

        return new_cover.id
    

@book_bl.route('/new', methods=['GET', 'POST'])
@check_rights('new')
def create_book():
    if request.method == 'POST':
        try:
            form_info = request.form

            cover_image = request.files.get('cover_img')
            author = form_info.get('author')
            title = form_info.get('title')
            publisher = form_info.get('publisher')
            year_of_pub = form_info.get('year')
            page_count = form_info.get('amount')
            desc = bleach.clean(form_info.get('description'))

            if cover_image and cover_image.filename:
                cover_id = ImageSaver(cover_image).save_image()
                new_book = Book(
                    title=title, 
                    description=desc, 
                    year=year_of_pub,  
                    publisher=publisher, 
                    author=author, 
                    amount=page_count, 
                    cover_id=cover_id
                )
                db.session.add(new_book)
                db.session.commit()

                selected_genres = form_info.getlist('genre_id')
                for genre_id in selected_genres:
                    new_genre_link = Books_has_Genres(books_id=new_book.id, genres_id=genre_id)
                    db.session.add(new_genre_link)
                db.session.commit()

                flash(f'Книга "{new_book.title}" успешно добавлена!', 'success')
                return redirect(url_for('index'))
            else:
                flash("Обложка не загружена, пожалуйста, загрузите файл обложки", 'danger')
        except Exception as e:
            flash(f"При добавлении книги произошла ошибка: {str(e)}", 'danger')

        return redirect(url_for('book.create_book'))
    
    else:
        all_genres = Genre.query.all()
        return render_template('book/new.html', genres=all_genres)


@book_bl.route('/show/<int:book_id>')
def display_book(book_id):
    book_details = Book.query.get(book_id)
    book_genre_links = Books_has_Genres.query.all()
    cover_info = Cover.query.filter_by(id=book_details.cover_id).first()
    book_details.description = markdown.markdown(book_details.description)
    if cover_info:
        cover_url = cover_info.url 
    else:
        None

    user_review = None

    if current_user.is_authenticated:
        user_review_data = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if user_review_data:
            user_review = markdown.markdown(user_review_data.text)

    all_reviews = Review.query.filter_by(book_id=book_id).all()
    reviews_rendered = [{
        'get_user': r.get_user,
        'rating': r.rating,
        'text': markdown.markdown(r.text),
        'status': r.is_ok
    } for r in all_reviews]

    return render_template(
        'book/show.html',
        book=book_details, 
        book_genre=book_genre_links, 
        img=cover_url, 
        review=user_review, 
        reviews=reviews_rendered
    )


@book_bl.route('/delete/<int:book_id>', methods=['POST'])
@check_rights('delete')
def delete_book(book_id):
    try:
        book_to_delete = Book.query.get(book_id)
        cover_data = Cover.query.filter_by(id=book_to_delete.cover_id).first()
        db.session.delete(book_to_delete)
        db.session.commit()

        lenth = len(Book.query.filter_by(cover_id=book_to_delete.cover_id).all())
        if cover_data and lenth == 1:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'images', cover_data.file_name)
            os.remove(img_path)
            db.session.delete(cover_data)

        related_reviews = Review.query.filter_by(book_id=book_id).all()
        for review in related_reviews:
            db.session.delete(review)
        db.session.commit()

        genre_links = Books_has_Genres.query.filter_by(books_id=book_id).all()
        for link in genre_links:
            db.session.delete(link)
        db.session.commit()

        flash('Книга успешно удалена!', 'success')
    except Exception as e:
        flash(f"Произошла ошибка при удалении книги: {str(e)}", 'danger')

    return redirect(url_for('index'))


@book_bl.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@check_rights('edit')
def edit_book(book_id):
    book_to_edit = Book.query.get(book_id)
    all_genres = Genre.query.all()

    if request.method == 'POST':
        try:
            book_to_edit.title = request.form.get('title')
            book_to_edit.author = request.form.get('author')
            book_to_edit.publisher = request.form.get('publisher')
            book_to_edit.amount = request.form.get('amount')
            book_to_edit.year = request.form.get('year')
            book_to_edit.description = bleach.clean(request.form.get('description'))
            db.session.commit()

            # Обновление жанров
            Books_has_Genres.query.filter_by(books_id=book_id).delete()
            selected_genres = request.form.getlist('genre_id')
            for genre_id in selected_genres:
                new_link = Books_has_Genres(books_id=book_id, genres_id=genre_id)
                db.session.add(new_link)
            db.session.commit()

            flash(f'Книга "{book_to_edit.title}" успешно обновлена!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Произошла ошибка при обновлении книги: {str(e)}", 'danger')

        return render_template('book/edit.html', book=book_to_edit, genres=all_genres)
    
    else:
        selected_genres = Books_has_Genres.query.filter_by(books_id=book_id).all()
        selected_genres_ids = [g.genres_id for g in selected_genres]

        return render_template('book/edit.html', book=book_to_edit, genres=all_genres, 
                               selected_genres_list=selected_genres_ids)


@book_bl.route('/review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    book_for_review = Book.query.get(book_id)

    if request.method == 'POST':
        review_text = request.form.get('review')
        rating_score = int(request.form.get('mark'))

        new_review = Review(rating=rating_score, text=review_text, book_id=book_id, 
                            user_id=current_user.get_id(), status_id=1)
        book_for_review.rating_num += 1
        book_for_review.rating_sum += rating_score

        db.session.add(new_review)
        db.session.commit()

        flash('Ваш отзыв был успешно добавлен и отправлен на модерацию!', 'success')
        return redirect(url_for('book.display_book', book_id=book_for_review.id))
    
    existing_review = Review.query.filter_by(book_id=book_id, user_id=current_user.get_id()).first()
    if existing_review:
        #flash('Нельзя менять адрес строки, при повторном нарушении вы будете забанены', 'warning')
        return render_template('book/warning.html', book=book_for_review)

    return render_template('book/review.html', book=book_for_review)





