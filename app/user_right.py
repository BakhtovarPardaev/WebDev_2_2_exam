from flask_login import current_user

class UserRight:
    def new(self):
        return current_user.is_admin

    def delete(self):
        return current_user.is_admin

    def edit(self):
        return current_user.is_admin or current_user.is_moder

    def show(self):
        return current_user.is_authenticated

