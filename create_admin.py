from app import create_app, db
from app.models.user_model import User

app = create_app()

with app.app_context():

    # Check if admin already exists
    admin = User.query.filter_by(username="admin").first()

    if admin:
        print("Admin already exists!")

    else:
        admin = User(
            username="admin",
            email="admin@gmail.com",
            role="admin",
            is_active_account=True
        )

        admin.set_password("admin123")

        db.session.add(admin)
        db.session.commit()

        print("Admin created successfully!")