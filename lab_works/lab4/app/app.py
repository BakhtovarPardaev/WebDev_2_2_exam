from typing import Dict
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
import mysql.connector
import re

app = Flask(__name__)

application = app

app.config.from_pyfile('config.py')

db = MySQL(app)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа необходимо пройти аутентификацию'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, user_id, user_login):
        self.id = user_id
        self.login = user_login



def password_validation(password: str) -> Dict[str, str]:
    errors = {}

    if len(password) < 8 or len(password) > 128:
        errors['length'] = "Пароль должен содержать не менее 8 символов и не более 128 символов"


    if not re.search(r'[a-zа-я]', password):
        errors['lowercase'] = "Пароль должен содержать хотя бы одну строчную букву"
    if not re.search(r'[A-ZА-Я]', password):
        errors['uppercase'] = "Пароль должен содержать хотя бы одну заглавную букву"
    if not re.search(r'[0-9]', password):
        errors['digit'] = "Пароль должен содержать хотя бы одну цифру"

    if not re.search(r'^[A-Za-zА-Яа-я0-9~!?@#$%^&*_+\[\]{}></\\|"\',.:;]+$', password):
        errors['invalid_characters'] = "Пароль содержит недопустимые символы"

    return errors


def login_validation(login: str) -> tuple:
    if len(login) < 5:
        return False, "Логин должен содержать не менее 5 символов."
    elif not re.search(r'^[0-9a-zA-Z]+$', login):
        return False, "Логин может содержать только латинские буквы и цифры."
    elif re.search(r'[А-Яа-я]', login):
        return False, "Логин не должен содержать кириллические буквы."
    return True, ""


def validate(login: str, password: str, last_name: str, first_name: str, check_password: bool = True) -> Dict[str, str]:
    errors = {}

    if check_password:
        if len(password) == 0:
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль не должен быть пустым"
        elif len(password) < 8:
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль должен содержать не менее 8 символов."
        elif not re.search(r'[A-ZА-Я]', password):
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль должен содержать хотя бы одну заглавную букву."
        elif not re.search(r'[a-zа-я]', password):
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль должен содержать хотя бы одну строчную букву."
        elif not re.search(r'[0-9]', password):
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль должен содержать хотя бы одну цифру."
        elif re.search(r'\s', password):
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = "Пароль не должен содержать пробелы."
        elif not re.search(r'^[A-Za-zА-Яа-я0-9~!?@#$%^&*_+\[\]{}></\\|"\'.:,;" "]+$', password):
            errors['p_class'] = "is-invalid"
            errors['p_message_class'] = "invalid-feedback"
            errors['p_message'] = '''Пароль содержит недопустимые символы. Допустимые символы: латинские или кириллические буквы, арабские цифры, ~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " ' . , : ;'''

    if not login_validation(login):
        errors['l_class'] = "is-invalid"
        errors['l_message_class'] = "invalid-feedback"
        errors['l_message'] = "Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов."

    if len(login) == 0:
        errors['l_class'] = "is-invalid"
        errors['l_message_class'] = "invalid-feedback"
        errors['l_message'] = "Логин не должен быть пустым."

    if len(last_name) == 0:
        errors['ln_class'] = "is-invalid"
        errors['ln_message_class'] = "invalid-feedback"
        errors['ln_message'] = "Фамилия не должна быть пустой."

    if len(first_name) == 0:
        errors['fn_class'] = "is-invalid"
        errors['fn_message_class'] = "invalid-feedback"
        errors['fn_message'] = "Имя не должно быть пустым."

    return errors


@login_manager.user_loader
def load_user(user_id):
    query = 'SELECT id, login FROM users2 WHERE id = %s'

    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        return User(user.id, user.login) if user else None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        check = request.form.get('secretcheck') == 'on'

        query = 'SELECT id, login FROM users2 WHERE login=%s AND password_hash=SHA2(%s, 256)'

        try:
            with db.connection().cursor(named_tuple=True) as cursor:
                cursor.execute(query, (login, password))
                user = cursor.fetchone()

                if user:
                    login_user(User(user.id, user.login), remember=check)
                    next_url = request.args.get('next') or url_for('index')
                    flash('Вы успешно вошли!', 'success')
                    return redirect(next_url)
                else:
                    flash('Неверные учетные данные.', 'danger')

        except mysql.connector.errors.DatabaseError:
            flash('Произошла ошибка при входе.', 'danger')

    return render_template('login.html')


@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/users/')
@login_required
def show_users():
    query = 'SELECT * FROM users2'

    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        users = cursor.fetchall()

    return render_template('users/index.html', users=users)

@app.route('/users/create', methods=['POST', 'GET'])
@login_required
def create():
    user = {'login': '', 'first_name': '', 'last_name': '', 'middle_name': '', 'password': ''}
    errors = {
        'l_class': '', 'l_message_class': '', 'l_message': '',
        'p_class': '', 'p_message_class': '', 'p_message': '',
        'ln_class': '', 'ln_message_class': '', 'ln_message': '',
        'fn_class': '', 'fn_message_class': '', 'fn_message': ''
    }

    if request.method == 'POST':
        user['login'] = request.form['login']
        user['first_name'] = request.form['first_name']
        user['last_name'] = request.form['last_name']
        user['middle_name'] = request.form['middle_name']
        user['password'] = request.form['password']

        login_valid, login_message = login_validation(user['login'])
        if not login_valid:
            errors['l_class'] = 'is-invalid'
            errors['l_message_class'] = 'invalid-feedback'
            errors['l_message'] = login_message

        validation_errors = validate(user['login'], user['password'], user['last_name'], user['first_name'])
        if validation_errors:
            errors.update(validation_errors)
            return render_template('users/create.html', **errors, user=user)

        insert_query = '''INSERT INTO users2 (login, last_name, first_name, middle_name, password_hash)
                          VALUES (%s, %s, %s, %s, SHA2(%s, 256))'''

        try:
            with db.connection().cursor(named_tuple=True) as cursor:
                cursor.execute(insert_query, (user['login'], user['last_name'], user['first_name'], user['middle_name'], user['password']))
                db.connection().commit()
                flash(f'Пользователь {user["login"]} успешно создан.', 'success')
                return redirect(url_for('index'))
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash('При создании пользователя произошла ошибка.', 'danger')

    return render_template('users/create.html', **errors, user=user)

@app.route('/users/show/<int:user_id>')
def show_user(user_id):
    query = 'SELECT * FROM users2 WHERE users2.id=%s'

    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

    return render_template('users/show.html', user=user)



def validateEdit(login: str, last_name: str, first_name: str) -> Dict[str, str]:
    errors = {}

    if not login_validation(login):
        errors['l_class'] = "is-invalid"
        errors['l_message_class'] = "invalid-feedback"
        errors['l_message'] = "Логин должен состоять только из латинских букв и цифр и иметь длину не менее 5 символов"

    if len(login) == 0:
        errors['l_class'] = "is-invalid"
        errors['l_message_class'] = "invalid-feedback"
        errors['l_message'] = "Логин не должен быть пустым"

    if len(last_name) == 0:
        errors['ln_class'] = "is-invalid"
        errors['ln_message_class'] = "invalid-feedback"
        errors['ln_message'] = "Фамилия не должна быть пустой"

    if len(first_name) == 0:
        errors['fn_class'] = "is-invalid"
        errors['fn_message_class'] = "invalid-feedback"
        errors['fn_message'] = "Имя не должно быть пустым"

    return errors


@app.route('/users/edit/<int:user_id>', methods=['POST', 'GET'])
@login_required
def edit(user_id):
    errors = {
        'l_class': '', 'l_message_class': '', 'l_message': '',
        'ln_class': '', 'ln_message_class': '', 'ln_message': '',
        'fn_class': '', 'fn_message_class': '', 'fn_message': ''
    }

    if request.method == 'POST':
        user = {
            'login': request.form['login'],
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'middle_name': request.form['middle_name']
        }

        errors = validateEdit(user['login'], user['last_name'], user['first_name'])
        if errors:
            return render_template('users/edit.html', **errors, user=user)

        update_query = '''UPDATE users2 SET first_name = %s, last_name = %s, middle_name = %s WHERE id = %s'''

        try:
            with db.connection().cursor(named_tuple=True) as cursor:
                cursor.execute(update_query, (user['first_name'], user['last_name'], user['middle_name'], user_id))
                db.connection().commit()
                flash(f'Данные пользователя {user["login"]} успешно обновлены.', 'success')
                return redirect(url_for('show_user', user_id=user_id))
        except mysql.connector.errors.DatabaseError:
            db.connection().rollback()
            flash('При обновлении пользователя произошла ошибка.', 'danger')

            return render_template('users/edit.html', user=user, **errors)

    select_query = 'SELECT * FROM users2 WHERE id = %s'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(select_query, (user_id,))
        user = cursor.fetchone()
        user = {**user._asdict()}

    return render_template('users/edit.html', user=user, **errors)

@app.route('/users/delete/')
@login_required
def delete():
    try:
        user_id = request.args.get('user_id')
        query = 'DELETE FROM users2 WHERE id = %s'

        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id,))
            db.connection().commit()
            flash(f'Пользователь {user_id} успешно удален.', 'success')

    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('При удалении пользователя произошла ошибка.', 'danger')

    return redirect(url_for('show_users'))

@app.route('/pass_change', methods=["POST", "GET"])
@login_required
def change():
    errors = {
        'old_password_class': '',
        'old_password_message_class': '',
        'old_password_message': '',
        'new_password_class': '',
        'new_password_message_class': '',
        'new_password_message': '',
        'confirm_password_class': '',
        'confirm_password_message_class': '',
        'confirm_password_message': ''
    }

    if request.method == "POST":
        user_id = current_user.id
        password = request.form['password']
        n_password = request.form['n_password']
        n_password_2 = request.form['n2_password']

        if not password:
            errors['old_password_class'] = 'is-invalid'
            errors['old_password_message_class'] = 'invalid-feedback'
            errors['old_password_message'] = 'Пароль не может быть пустым'
        else:
            check_password_query = 'SELECT * FROM `users2` WHERE id = %s AND password_hash = SHA2(%s, 256)'
            try:
                with db.connection().cursor(named_tuple=True) as cursor:
                    cursor.execute(check_password_query, (user_id, password))
                    user = cursor.fetchone()

                    if not user:
                        errors['old_password_class'] = 'is-invalid'
                        errors['old_password_message_class'] = 'invalid-feedback'
                        errors['old_password_message'] = 'Старый пароль не соответствует текущему'
                    else:
                        if not n_password:
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = 'Пароль не может быть пустым'
                        elif not n_password_2:
                            errors['confirm_password_class'] = 'is-invalid'
                            errors['confirm_password_message_class'] = 'invalid-feedback'
                            errors['confirm_password_message'] = 'Пароль не может быть пустым'
                        elif len(n_password) < 8:
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = "Пароль должен содержать не менее 8 символов."
                        elif not re.search(r'[A-ZА-Я]', n_password):
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = "Пароль должен содержать хотя бы одну заглавную букву."
                        elif not re.search(r'[a-zа-я]', n_password):
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = "Пароль должен содержать хотя бы одну строчную букву."
                        elif not re.search(r'[0-9]', n_password):
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = "Пароль должен содержать хотя бы одну цифру."
                        elif re.search(r'\s', n_password):
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = "Пароль не должен содержать пробелы."
                        elif not re.search(r'^[A-Za-zА-Яа-я0-9~!?@#$%^&*_+\[\]{}></\\|"\'.:,;]+$', n_password):
                            errors['new_password_class'] = 'is-invalid'
                            errors['new_password_message_class'] = 'invalid-feedback'
                            errors['new_password_message'] = '''Пароль содержит недопустимые символы. Допустимые символы: латинские или кириллические буквы, арабские цифры, ~ ! ? @ # $ % ^ & * _ - + ( ) [ ] { } > < / \ | " ' . , : ;'''
                        elif n_password != n_password_2:
                            errors['confirm_password_class'] = 'is-invalid'
                            errors['confirm_password_message_class'] = 'invalid-feedback'
                            errors['confirm_password_message'] = 'Пароли не совпадают'
                        else:
                            update_password_query = 'UPDATE `users2` SET password_hash = SHA2(%s, 256) WHERE id = %s'
                            cursor.execute(update_password_query, (n_password, user_id))
                            db.connection().commit()
                            flash('Пароль успешно обновлен.', 'success')
                            return redirect(url_for('index'))

            except mysql.connector.errors.DatabaseError:
                db.connection().rollback()
                flash('При обновлении пароля возникла ошибка.', 'danger')

    return render_template('users/change.html', **errors)

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5100)
