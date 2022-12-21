from flask import Flask, render_template, redirect, url_for, flash, abort
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager(app)

#create gravatar

gravatar = Gravatar(app,
                    size=100,
                    rating='x',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None
                    )

# create a user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class BlogPost(db.Model):

    # we first create the table name that we'll use to link the two
    # since this is a many to one, one has to be a child and the other a parent
    __tablename__ = "posts_table" # child (for User(author))
    # we create a column that has reference to the parent by using the parent id
    # so we can tell who the author is
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False) # (many to one) this links the all_posts to parent
    author_relationship = relationship('User', back_populates='post') #(one to many) this gives every post an author

    # link every blog post to various comments

    comments = relationship('Comment', back_populates='parent_post')

    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

# db.create_all()

class User(UserMixin, db.Model):
    __tablename__ = "user_table" # name of the parent to link
    id = db.Column(db.Integer, primary_key=True)

    post = relationship('BlogPost', back_populates='author_relationship') # first parameter is table, back_populates gives every post an author
                                    #whereas initially it was just supposed to be a relationship between one(parent)
                                    # to many (child)
    comment =  relationship('Comment', back_populates='comment_author')


    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)


class Comment(db.Model):
    __tablename__ = 'comments_table' # child
    id = db.Column(db.Integer, primary_key=True)


    # link between comment and User(author)
    author_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False)
    comment_author = relationship("User", back_populates='comment')

    # link comment(s) to blog post
    posts_id = db.Column(db.Integer, db.ForeignKey('posts_table.id'), nullable=False)
    parent_post = relationship("BlogPost", back_populates='comments') # link comments to author

    text = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()




@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()


    id = 0

    if current_user.is_authenticated:
        if int(current_user.id) == 1:
            id = current_user.id



    return render_template("index.html", all_posts=posts, authenticated=current_user.is_authenticated, admin=id)


@app.route('/register', methods=["GET", "POST"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():

        # create new entry
        # if email does not already exist, do this
        if not User.query.filter_by(email=form.email.data).first():
            new_entry = User(
                email=form.email.data,
                password= generate_password_hash(form.password.data ,method='pbkdf2:sha256', salt_length=8),
                name=form.name.data
            )

            db.session.add(new_entry)
            db.session.commit()

            login_user(new_entry)
        else:
            flash("You've already signed up with that email. Log in instead")
            return redirect(url_for('login'))

        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():

    form = LoginForm()

    if form.validate_on_submit():
        # check if the email and password match those in the database
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('This email does not exist. Try again!')
            return redirect(url_for('login'))

        elif not check_password_hash(user.password, form.password.data):
            flash('Your password is incorrect. Try again')

        else:
            print('You have been logged in')
            login_user(user)

            return redirect(url_for('get_all_posts'))



    return render_template("login.html", form=form)


@app.route('/logout')
def logout():

    logout_user()

    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):

    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(posts_id=post_id).all()

    print(comments)

    id = 0
    if current_user.is_authenticated:
        if int(current_user.id) == 1:
            id = current_user.id


    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please log in to comment')
            return redirect(url_for('login'))

        new_comment = Comment(
            author_id = int(current_user.get_id()),
            text = form.comment.data,
            posts_id = post_id
        )
        db.session.add(new_comment)
        db.session.commit()

        return redirect(url_for('show_post', post_id = post_id))



    return render_template("post.html", gravatar=gravatar, form=form, comments=comments,  post=requested_post, admin=id, authenticated=current_user.is_authenticated)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")



def admin_only(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        elif int(current_user.id) != 1:
               abort(403)

        return function()

    return wrapper

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            author_id = int(current_user.get_id()),
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, authenticated=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])

def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))



    return render_template("make-post.html", form=edit_form, authenticated=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
