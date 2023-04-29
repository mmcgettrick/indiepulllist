from subscriptions import app, db
from subscriptions.models import BlogEntry
from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import desc

@app.route('/reviews')
@app.route('/reviews/<id>')
def blog(id=None):
    if id is None:
        blog_entries = BlogEntry.query.order_by(desc(BlogEntry.date)).all()
        return render_template('blog.html', blog_entries=blog_entries, back=request.referrer, title='Reviews')
    else:
        blog_entry = BlogEntry.query.filter(BlogEntry.id == id).first()
        #todo next and previous
        next = BlogEntry.query.filter(BlogEntry.id > id).first()
        previous = BlogEntry.query.filter(BlogEntry.id < id).first()
        return render_template('blog_entry.html', blog_entry=blog_entry, back=request.referrer, next=next, previous=previous, title=blog_entry.title)
